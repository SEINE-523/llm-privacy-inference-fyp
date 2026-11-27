"""Text-volume saturation scan.

For each persona, run the attack on the first ``n`` texts for every
``n = 1 .. len(texts)`` and find:

* ``strict_n``   – first n where all 9 attributes are non-abstain.
* ``coverage_n`` – first n where the model has produced every attribute it
  will ever produce for this person (union over all n).
* ``stable_n``   – first n after which the 9-attribute top-1 vector no longer
  changes through the end of that person's texts.

The last definition is the practical "model's profile is complete" point,
because some attributes (e.g. exact income, birthplace) are never inferable
from the current synthetic texts and therefore never reach ``strict_n``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .dataset import DEFAULT_ATTRIBUTES, DatasetError, build_profiles, describe
from .run import (
    ATTRIBUTES,
    CONFIDENCE_THRESHOLD,
    DEFAULT_MODEL,
    build_messages,
    call_deepseek,
    mock_reply,
    parse_prediction,
    score,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT.parent / "database"


def _vector(record: dict, attributes) -> tuple:
    prediction = record.get("prediction") or {}
    return tuple(
        (prediction.get(attr) or {}).get("guesses", [None])[0]
        if not (prediction.get(attr) or {}).get("abstain", True)
        else None
        for attr in attributes
    )


def _guessed_set(record: dict, attributes) -> set[str]:
    prediction = record.get("prediction") or {}
    return {
        attr for attr in attributes
        if not (prediction.get(attr) or {}).get("abstain", True)
    }


def _accuracy(record: dict, attributes) -> float:
    scores = record.get("scores") or {}
    values = [scores.get(attr, {}).get("top1", 0) for attr in attributes]
    return sum(values) / len(values) if values else 0.0


def analyse_person(records: list[dict], attributes) -> dict:
    """Compute the three saturation points for one persona's n-scan."""
    valid = sorted(
        [record for record in records if record.get("status") in {"ok", "mock"}],
        key=lambda record: int(record["n"]),
    )
    if not valid:
        return {"status": "error", "strict_n": None, "coverage_n": None, "stable_n": None}

    strict_n = next((int(record["n"]) for record in valid if record.get("all_guessed")), None)
    ever = set()
    for record in valid:
        ever |= _guessed_set(record, attributes)
    coverage_n = None
    for record in valid:
        if _guessed_set(record, attributes) >= ever:
            coverage_n = int(record["n"])
            break

    vectors = [(int(record["n"]), _vector(record, attributes)) for record in valid]
    last_change = 0
    for (n_left, left), (n_right, right) in zip(vectors, vectors[1:]):
        if left != right:
            last_change = n_left
    stable_n = last_change + 1 if last_change else int(vectors[0][0])

    final = valid[-1]
    stable_record = next((record for record in valid if int(record["n"]) == stable_n), final)
    coverage_record = next((record for record in valid if int(record["n"]) == coverage_n), final)
    strict_record = next((record for record in valid if int(record["n"]) == strict_n), None)
    return {
        "status": "ok",
        "max_n": int(valid[-1]["n"]),
        "strict_n": strict_n,
        "coverage_n": coverage_n,
        "stable_n": stable_n,
        "ever_guessed": sorted(ever),
        "non_abstain_at_stable": len(_guessed_set(stable_record, attributes)),
        "top1_at_stable": round(_accuracy(stable_record, attributes), 4),
        "top1_at_coverage": round(_accuracy(coverage_record, attributes), 4),
        "top1_at_strict": round(_accuracy(strict_record, attributes), 4) if strict_record else None,
        "top1_at_full": round(_accuracy(final, attributes), 4),
        "top1_correct_full": sum(
            (final.get("scores") or {}).get(attr, {}).get("top1", 0) for attr in attributes
        ),
    }


def aggregate(records: list[dict], attributes) -> tuple[list[dict], list[dict]]:
    """Return per-person rows and the n-by-n curve."""
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record["profile_id"], []).append(record)

    rows = []
    for profile_id in sorted(grouped):
        result = analyse_person(grouped[profile_id], attributes)
        result["profile_id"] = profile_id
        rows.append(result)

    curve = []
    for n in sorted({int(record["n"]) for record in records}):
        current = [
            record for record in records
            if int(record["n"]) == n and record.get("status") in {"ok", "mock"}
        ]
        if not current:
            continue
        top1 = sum(_accuracy(record, attributes) for record in current) / len(current)
        top3 = sum(
            sum((record.get("scores") or {}).get(attr, {}).get("top3", 0) for attr in attributes)
            / len(attributes)
            for record in current
        ) / len(current)
        curve.append({
            "n": n,
            "personas": len(current),
            "mean_top1": round(top1, 4),
            "mean_top3": round(top3, 4),
        })
    return rows, curve


def _mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _fmt(value) -> str:
    return f"{value:.2f}" if value is not None else "—"


def write_report(rows: list[dict], curve: list[dict], records: list[dict], output: Path, attributes) -> None:
    output.mkdir(parents=True, exist_ok=True)
    summary_fields = [
        "profile_id", "status", "max_n", "strict_n", "coverage_n", "stable_n",
        "non_abstain_at_stable", "top1_at_stable", "top1_at_coverage",
        "top1_at_strict", "top1_at_full", "top1_correct_full",
    ]
    with (output / "saturation_summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=summary_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in summary_fields})

    with (output / "saturation_curve.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["n", "personas", "mean_top1", "mean_top3"])
        writer.writeheader()
        writer.writerows(curve)

    strict_count = sum(1 for row in rows if row.get("strict_n") is not None)
    coverage_values = [row.get("coverage_n") for row in rows if row.get("coverage_n") is not None]
    stable_values = [row.get("stable_n") for row in rows if row.get("stable_n") is not None]
    mean_max = _mean([row.get("max_n") for row in rows])
    mean_coverage = _mean(coverage_values)
    mean_stable = _mean(stable_values)

    lines = [
        "# 文本量饱和点实验（Text-Volume Saturation）",
        "",
        f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",
        f"- 模型：`{records[0].get('model', '—') if records else '—'}`",
        f"- 人物数：{len(rows)}",
        f"- 请求数：{len(records)}（每人 n=1..全部文本）",
        f"- 属性数：{len(attributes)}",
        "",
        "## 指标定义",
        "",
        "| 指标 | 定义 |",
        "|---|---|",
        "| `strict_n` | 第一个“9 个属性全部非弃答”的 n；若从未出现则为空 |",
        "| `coverage_n` | 第一个“已经给出该人最终会给出的全部属性”的 n（并集口径） |",
        "| `stable_n` | 第一个“9 属性 Top-1 向量不再变化”的 n（实际饱和点） |",
        "| `top1_at_stable` | 在 `stable_n` 处的 9 属性平均 Top-1 |",
        "| `top1_at_full` | 使用全部文本时的 9 属性平均 Top-1 |",
        "",
        "> 为什么主指标用 `stable_n`：当前数据中精确收入、出生地等属性没有线索，模型始终弃答，"
        "所以 9 属性全部非弃答的 `strict_n` 几乎不可达；`stable_n` 衡量“模型的人物画像不再变化”的时点。",
        "",
        "## 总体结果",
        "",
        f"- 达到 `strict_n` 的人物：**{strict_count}/{len(rows)}**",
        f"- `stable_n` 平均值：**{mean_stable:.2f}**" if mean_stable is not None else "- `stable_n` 平均值：—",
        f"- `coverage_n` 平均值：**{mean_coverage:.2f}**" if mean_coverage is not None else "- `coverage_n` 平均值：—",
        f"- 每人最大文本数平均值：**{mean_max:.2f}**" if mean_max is not None else "- 最大文本数平均值：—",
        "",
        "## 每人结果",
        "",
        "| 编号 | profile_id | 最大 n | strict_n | coverage_n | stable_n | 稳定时 Top-1 | 全文本 Top-1 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(rows, start=1):
        lines.append(
            f"| R{index:02d} | {row['profile_id']} | {row.get('max_n', '—')} | "
            f"{row.get('strict_n') if row.get('strict_n') is not None else '—'} | "
            f"{row.get('coverage_n') if row.get('coverage_n') is not None else '—'} | "
            f"{row.get('stable_n') if row.get('stable_n') is not None else '—'} | "
            f"{row.get('top1_at_stable', '—')} | {row.get('top1_at_full', '—')} |"
        )

    lines += [
        "",
        "## n 与平均准确率",
        "",
        "| n | 人物数 | 平均 Top-1 | 平均 Top-3 |",
        "|---:|---:|---:|---:|",
    ]
    for point in curve:
        lines.append(
            f"| {point['n']} | {point['personas']} | {point['mean_top1']:.2f} | {point['mean_top3']:.2f} |"
        )

    lines += [
        "",
        "## 解读",
        "",
        f"1. `strict_n` 达到人数：{strict_count}/{len(rows)}；模型不会声称自己推断出了全部 9 个属性，缺失主要集中在无文本线索的属性。",
        f"2. `stable_n` 是更可用的“人物画像完成”指标：平均 **{_fmt(mean_stable)}** 条文本后，Top-1 属性向量不再变化。",
        f"3. `coverage_n` 衡量模型已经给出它最终会给出的属性集合，平均 **{_fmt(mean_coverage)}** 条；适合与 `stable_n` 对照。",
        "4. n 的平均值应结合 `max_n` 一起看：不同人物可用文本数不同（5–25 条）。",
        "",
        "## 产物",
        "",
        "- `saturation_runs.jsonl`：每次 n 的请求、解析、评分",
        "- `saturation_summary.csv`：每人一行",
        "- `saturation_curve.csv`：n 与平均准确率",
        "- `saturation_report.md`：本文件",
        "",
    ]
    (output / "saturation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--settings", type=Path, default=ROOT / "settings.json")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "results" / "deepseek_saturation")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--attributes", nargs="+", choices=ATTRIBUTES, default=list(DEFAULT_ATTRIBUTES))
    parser.add_argument("--mock", action="store_true", help="Offline scan; no API calls")
    args = parser.parse_args(argv)

    if args.limit < 0:
        parser.error("--limit must be nonnegative")
    attributes = tuple(args.attributes)
    try:
        summary = describe(args.dataset)
        profiles = build_profiles(args.dataset, attributes=attributes, min_texts=1)
    except DatasetError as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 2
    if args.limit:
        profiles = profiles[:args.limit]
    if not profiles:
        parser.error("no profiles selected")

    settings = {}
    if not args.mock:
        if not args.settings.exists():
            parser.error(f"settings file not found: {args.settings}")
        settings = json.loads(args.settings.read_text(encoding="utf-8"))
        key = os.getenv("DEEPSEEK_API_KEY") or settings.get("api_key", "")
        if not key or key.startswith("PASTE_"):
            parser.error("Fill attack_lab/settings.json api_key or set DEEPSEEK_API_KEY")

    args.output.mkdir(parents=True, exist_ok=True)
    run_path = args.output / "saturation_runs.jsonl"
    if run_path.exists():
        parser.error(f"output already contains saturation_runs.jsonl: {args.output}")

    records = []
    with run_path.open("x", encoding="utf-8") as stream:
        for profile in profiles:
            for n in range(1, len(profile["texts"]) + 1):
                messages = build_messages(profile, n, attributes=attributes)
                text_ids = [entry["text_id"] for entry in profile["texts"][:n]]
                record = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "profile_id": profile["profile_id"],
                    "n": n,
                    "text_count": n,
                    "text_ids": text_ids,
                    "input_texts": [
                        {"text_id": entry["text_id"], "text": entry["text"]}
                        for entry in profile["texts"][:n]
                    ],
                    "model": "mock" if args.mock else (
                        os.getenv("DEEPSEEK_MODEL")
                        or os.getenv("LLM_MODEL")
                        or settings.get("model", DEFAULT_MODEL)
                    ),
                    "attributes": list(attributes),
                    "ground_truth": profile["labels"],
                }
                start = time.monotonic()
                try:
                    if args.mock:
                        raw, usage, response_id = json.dumps(mock_reply(attributes)), {}, None
                    else:
                        raw, usage, response_id = call_deepseek(messages, settings, attributes=attributes)
                    record["raw_response"] = raw
                    record["usage"] = usage
                    record["response_id"] = response_id
                    record["prediction"] = parse_prediction(
                        raw, set(text_ids), attributes=attributes,
                        confidence_threshold=CONFIDENCE_THRESHOLD,
                        strict_evidence=False,
                    )
                    record["scores"] = score(record["prediction"], profile["labels"], attributes=attributes)
                    record["all_guessed"] = all(
                        not record["prediction"][attr]["abstain"] for attr in attributes
                    )
                    record["status"] = "mock" if args.mock else "ok"
                except (RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    record["status"] = "error"
                    record["error"] = str(exc)[:500]
                record["latency_seconds"] = round(time.monotonic() - start, 3)
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                records.append(record)
                print(f"{profile['profile_id']} n={n} status={record['status']}")
    rows, curve = aggregate(records, attributes)
    write_report(rows, curve, records, args.output, attributes)
    print(f"Saved {run_path}, {args.output / 'saturation_summary.csv'}, {args.output / 'saturation_report.md'}")
    return 1 if any(record["status"] == "error" for record in records) else 0


if __name__ == "__main__":
    sys.exit(main())
