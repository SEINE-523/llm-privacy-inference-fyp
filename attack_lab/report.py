"""Per-person Markdown reports for a full-text attack run.

Every report keeps the original ``profile_id``, ``text_id`` and attribute keys
so it can be compared directly with ``runs.jsonl`` and ``summary.csv``.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _cell(value) -> str:
    text = str(value).replace("|", "\\|").replace("\n", " ").strip()
    return text or "—"


def _fmt_score(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def _mean(values) -> float | None:
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _score(record: dict, attribute: str) -> dict:
    return (record.get("scores") or {}).get(attribute, {})


def _prediction(record: dict, attribute: str) -> dict:
    return (record.get("prediction") or {}).get(attribute, {})


def _index_table(profile_rows: list[dict], attributes, prefix: str = "") -> list[str]:
    headers = ["编号", "profile_id", "文本数", "平均 Top-1", "报告"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in profile_rows:
        record = row["records"][0]
        values = [
            _score(record, attr).get("top1")
            for attr in attributes
            if _score(record, attr)
        ]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["report_id"],
                    row["profile_id"],
                    str(row["num_texts"]),
                    _fmt_score(_mean(values)),
                    f"[{row['profile_id']}.md]({prefix}{row['profile_id']}.md)",
                ]
            )
            + " |"
        )
    return lines


def _person_report(row: dict, attributes) -> str:
    record = row["records"][0]
    ground_truth = record.get("ground_truth") or {}
    lines = [
        f"# {row['report_id']} · {row['profile_id']}",
        "",
        f"- **report_id**：`{row['report_id']}`",
        f"- **profile_id**：`{row['profile_id']}`",
        f"- **文本总数**：{row['num_texts']}",
        f"- **来源线程**：{', '.join(record.get('source_threads') or []) or '—'}",
        f"- **模型**：`{record.get('model', '—')}`",
        "",
        "> 编号规则：`report_id` 按 `profile_id` 排序生成，固定不变；"
        "`profile_id`、`text_id` 与 `runs.jsonl` / `summary.csv` 完全一致。",
        "",
        "## 真实标签",
        "",
        "| 属性 | 真值 |",
        "|---|---|",
    ]
    for attr in attributes:
        lines.append(f"| `{attr}` | {_cell(ground_truth.get(attr, '—'))} |")

    lines.extend(["", "## 全部文本", ""])
    if record.get("status") not in {"ok", "mock"}:
        lines.append(f"> 运行失败：{_cell(record.get('error', 'unknown error'))}")
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(["### 输入文本", ""])
    input_texts = record.get("input_texts") or []
    if input_texts:
        for item in input_texts:
            snippet = str(item.get("text", "")).replace("\n", " ")
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            lines.append(f"- `{item.get('text_id', '?')}`：{snippet}")
    else:
        lines.append(f"- text_ids：{', '.join(record.get('text_ids') or []) or '—'}")

    lines.extend(
        [
            "",
            "### 属性结果",
            "",
            "| 属性 | 真值 | 置信度 | Top-1 猜测 | Top-1 分 | Top-3 猜测 | 弃答 | 证据 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for attr in attributes:
        pred = _prediction(record, attr)
        score = _score(record, attr)
        guesses = pred.get("guesses") or []
        top1 = guesses[0] if guesses else "—"
        top3 = " / ".join(guesses) if guesses else "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{attr}`",
                    _cell(ground_truth.get(attr, "—")),
                    _cell(pred.get("confidence", "—")),
                    _cell(top1),
                    _fmt_score(score.get("top1_score")),
                    _cell(top3),
                    "是" if pred.get("abstain") else "否",
                    _cell(", ".join(pred.get("evidence_ids") or []) or "—"),
                ]
            )
            + " |"
        )

    lines.extend(["", "### 逐属性分析", ""])
    for attr in attributes:
        pred = _prediction(record, attr)
        score = _score(record, attr)
        guesses = pred.get("guesses") or []
        lines.extend(
            [
                f"#### `{attr}`",
                f"- 真值：`{_cell(ground_truth.get(attr, '—'))}`",
                f"- 置信度：`{_cell(pred.get('confidence', '—'))}`",
                f"- 猜测：{' / '.join(f'`{g}`' for g in guesses) if guesses else '—'}",
                f"- Top-1 得分：{_fmt_score(score.get('top1_score'))}；Top-3 得分：{_fmt_score(score.get('top3_score'))}",
                f"- 证据：{', '.join(f'`{x}`' for x in (pred.get('evidence_ids') or [])) or '—'}",
                f"- 弃答：{'是' if pred.get('abstain') else '否'}",
                f"- 理由：{_cell(pred.get('reason', '—'))}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def write_person_reports(records: Iterable[dict], output_dir: Path, attributes) -> dict:
    """Write index, one file per persona, and a combined document."""
    output_dir = Path(output_dir)
    reports_dir = output_dir / "person_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for record in records:
        grouped.setdefault(str(record.get("profile_id", "unknown")), []).append(record)

    rows = []
    for index, (profile_id, person_records) in enumerate(sorted(grouped.items()), start=1):
        rows.append(
            {
                "report_id": f"R{index:02d}",
                "profile_id": profile_id,
                "records": person_records,
                "num_texts": person_records[0].get("num_texts", len(person_records[0].get("text_ids") or [])),
            }
        )

    metadata = [
        f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",
        f"- 人物数：{len(rows)}",
        f"- 记录数：{sum(len(row['records']) for row in rows)}",
        "",
        "编号 `R01…` 按 `profile_id` 排序生成，固定不变；"
        "每个编号对应一个 `profile_id`，便于与 `runs.jsonl`、`summary.csv` 对照。",
        "",
    ]
    index_lines = ["# 人物智能体分析索引", "", *metadata, *_index_table(rows, attributes), ""]
    (reports_dir / "index.md").write_text("\n".join(index_lines), encoding="utf-8")

    sections = []
    for row in rows:
        content = _person_report(row, attributes)
        (reports_dir / f"{row['profile_id']}.md").write_text(content, encoding="utf-8")
        sections.append(content)

    combined = [
        "# 人物智能体分析汇总",
        "",
        *metadata,
        "## 索引",
        "",
        *_index_table(rows, attributes, prefix="person_reports/"),
        "",
        "---",
        "",
    ]
    combined.extend(sections)
    (output_dir / "person_analysis.md").write_text("\n\n".join(combined), encoding="utf-8")

    return {
        "index": reports_dir / "index.md",
        "combined": output_dir / "person_analysis.md",
        "directory": reports_dir,
    }
