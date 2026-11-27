"""One-click runner for the author's released synthetic Reddit dataset."""

import argparse
import getpass
import json
import os
import runpy
import sys
import tempfile
import types
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "data" / "synthetic" / "synthetic_dataset.jsonl"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-prompts", type=int, default=0)
    parser.add_argument("--no-eval", action="store_true")
    return parser.parse_args()


def load_rows(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def validate_dataset(path):
    rows = load_rows(path)
    if not rows:
        raise ValueError(f"Dataset is empty: {path}")
    for index, row in enumerate(rows, start=1):
        required = {"personality", "feature", "response", "hardness"}
        missing = required - row.keys()
        if missing:
            raise ValueError(f"Row {index} is missing fields: {sorted(missing)}")
    return rows


def config_path_value(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def make_runtime_config(template_path, temp_dir, model, dataset_path, outpath, limit, is_eval):
    with template_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    config["store"] = False
    config["gen_model"]["name"] = model
    config["task_config"]["path"] = config_path_value(dataset_path)
    config["task_config"]["outpath"] = config_path_value(outpath)
    config["task_config"]["eval"] = is_eval
    if is_eval:
        config["task_config"]["decider"] = "none"
    elif limit:
        config["task_config"]["max_prompts"] = limit
    path = temp_dir / (("eval_" if is_eval else "infer_") + template_path.name)
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(config, stream, allow_unicode=True, sort_keys=False)
    return path


def run_original_main(config_path):
    saved_argv = sys.argv
    try:
        sys.argv = [str(ROOT / "main.py"), "--config_path", str(config_path)]
        runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
    finally:
        sys.argv = saved_argv


def extract_accuracy(path):
    counts = {}
    rows = load_rows(path)
    for row in rows:
        for model_evaluations in row.get("evaluations", {}).values():
            for reviewer_evaluations in model_evaluations.values():
                for attribute, hits in reviewer_evaluations.items():
                    if not isinstance(hits, list):
                        continue
                    result = counts.setdefault(attribute, {"labels": 0, "top1": 0, "top3": 0})
                    result["labels"] += 1
                    result["top1"] += int(bool(hits) and hits[0] == 1)
                    result["top3"] += int(any(value == 1 for value in hits[:3]))
    return rows, counts


def main():
    args = parse_args()
    os.chdir(ROOT)
    dataset = Path(os.getenv("DATASET_PATH", str(DEFAULT_DATASET))).expanduser()
    if not dataset.is_absolute():
        dataset = (ROOT / dataset).resolve()
    if not dataset.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset}")
    rows = validate_dataset(dataset)
    print(f"Dataset: {dataset}")
    print(f"Rows: {len(rows)}")
    print("Dataset validation: OK")
    if args.check_only:
        print("Check-only mode: no API call made.")
        return 0
    if args.max_prompts < 0:
        raise ValueError("--max-prompts must be >= 0")

    model = os.getenv("LLM_MODEL", "gpt-6.1-sol")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        api_key = getpass.getpass("Paste a NEW API key (input hidden): ").strip()
    if not api_key:
        print("No API key supplied; stopping without a request.", file=sys.stderr)
        return 2

    import openai
    openai.api_key = api_key
    organization = os.getenv("OPENAI_ORG_ID", "")
    if hasattr(openai, "organization"):
        openai.organization = organization
    api_base = os.getenv("OPENAI_API_BASE", "https://sub2api.luciferai.cc/v1")
    os.environ["OPENAI_API_BASE"] = api_base
    openai.api_base = api_base

    credentials = types.ModuleType("credentials")
    credentials.openai_org = organization
    credentials.openai_api_key = api_key
    sys.modules["credentials"] = credentials

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = ROOT / "author_dataset_runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    prediction_path = output_dir / "predictions.jsonl"
    evaluation_path = output_dir / "evaluation.jsonl"

    try:
        with tempfile.TemporaryDirectory(prefix="author_runtime_", dir=ROOT) as temp_name:
            temp_dir = Path(temp_name)
            infer_config = make_runtime_config(
                ROOT / "configs/reddit/running/reddit_synthetic_gpt6_astra.yaml",
                temp_dir, model, dataset, prediction_path, args.max_prompts, False,
            )
            print(f"Using model: {model}")
            print(f"Using API base: {api_base}")
            print(f"Profile limit: {args.max_prompts or 'all'}")
            print("Running original main.py inference...")
            run_original_main(infer_config)
            if not prediction_path.exists():
                raise RuntimeError("Inference ended without predictions.jsonl")

            if not args.no_eval:
                eval_config = make_runtime_config(
                    ROOT / "configs/reddit/eval/reddit_eval_gpt6_astra.yaml",
                    temp_dir, model, prediction_path, evaluation_path, 0, True,
                )
                print("Running original evaluation with decider=none...")
                run_original_main(eval_config)
                if not evaluation_path.exists():
                    raise RuntimeError("Evaluation ended without evaluation.jsonl")

        print(f"Predictions: {prediction_path}")
        if args.no_eval:
            return 0
        evaluated, counts = extract_accuracy(evaluation_path)
        print(f"Evaluation: {evaluation_path}")
        print(f"Evaluated profiles: {len(evaluated)}")
        print("Accuracy from the authors' evaluation output:")
        for attribute, result in sorted(counts.items()):
            n = result["labels"]
            top1 = f"{result['top1'] / n:.1%}" if n else "N/A"
            top3 = f"{result['top3'] / n:.1%}" if n else "N/A"
            print(f"  {attribute}: labels={n}, Top-1={top1}, Top-3={top3}")
        return 0
    finally:
        sys.modules.pop("credentials", None)
        openai.api_key = None
        if hasattr(openai, "organization"):
            openai.organization = None


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)