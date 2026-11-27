"""Run the authors' original Reddit inference and evaluation on two fictional users."""

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
DEMO_DIR = ROOT / "two_user_demo"
DATASET = DEMO_DIR / "users.jsonl"
ATTRIBUTES = ("age", "location", "occupation")


def validate_dataset():
    with DATASET.open(encoding="utf-8") as stream:
        users = [json.loads(line) for line in stream if line.strip()]
    if len(users) != 2:
        raise ValueError("The demo dataset must contain exactly two fictional profiles.")
    for user in users:
        if len(user.get("comments", [])) < 3:
            raise ValueError(f"{user.get('author')}: expected at least three comments")
        reviews = user.get("reviews", {})
        annotations = [value for reviewer in reviews.values() for value in reviewer.values()]
        if {key for reviewer in reviews.values() for key in reviewer} != set(ATTRIBUTES):
            raise ValueError(f"{user.get('author')}: expected age, location, occupation labels")
        if any(not value.get("estimate") for value in annotations):
            raise ValueError(f"{user.get('author')}: every label needs an estimate")
    return users


def make_runtime_config(template_path, temp_dir, model, dataset_path, outpath, is_eval):
    with template_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    # The author's generated log filename contains colons that Windows rejects.
    # Prediction and evaluation JSONL outputs are configured separately below.
    config["store"] = False
    config["gen_model"]["name"] = model
    config["task_config"]["path"] = str(dataset_path.relative_to(ROOT))
    config["task_config"]["outpath"] = str(outpath.relative_to(ROOT))
    config["task_config"]["eval"] = is_eval
    if is_eval:
        config["task_config"]["decider"] = "none"
    path = temp_dir / (("eval_" if is_eval else "infer_") + template_path.name)
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(config, stream, allow_unicode=True, sort_keys=False)
    return path


def run_original_main(config_path):
    saved_argv = sys.argv
    saved_stdout = sys.stdout
    try:
        sys.argv = [str(ROOT / "main.py"), "--config_path", str(config_path)]
        runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
    finally:
        sys.stdout = saved_stdout
        sys.argv = saved_argv


def extract_accuracy(path):
    profiles = []
    with path.open(encoding="utf-8") as stream:
        profiles = [json.loads(line) for line in stream if line.strip()]

    counts = {attribute: {"labels": 0, "top1": 0, "top3": 0} for attribute in ATTRIBUTES}
    for profile in profiles:
        for model_evaluations in profile.get("evaluations", {}).values():
            for reviewer_evaluations in model_evaluations.values():
                for attribute, hits in reviewer_evaluations.items():
                    if attribute not in counts or not isinstance(hits, list):
                        continue
                    counts[attribute]["labels"] += 1
                    counts[attribute]["top1"] += int(bool(hits) and hits[0] == 1)
                    counts[attribute]["top3"] += int(any(value == 1 for value in hits[:3]))
    return profiles, counts


def main():
    os.chdir(ROOT)
    users = validate_dataset()
    print("Local demo dataset validated: 2 fictional users, 3 labels per user.")
    if "--check-only" in sys.argv:
        print("Check-only mode: no API call made.")
        return 0

    model = os.getenv("LLM_MODEL", "gpt-6.1-sol")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        api_key = getpass.getpass("Paste a NEW API key (input hidden): ").strip()
    if not api_key:
        print("No API key supplied; stopping without making a request.", file=sys.stderr)
        return 2

    import openai

    openai.api_key = api_key
    organization = os.getenv("OPENAI_ORG_ID", "")
    if hasattr(openai, "organization"):
        openai.organization = organization
    api_base = os.getenv(
        "OPENAI_API_BASE", "https://sub2api.luciferai.cc/v1"
    )
    os.environ["OPENAI_API_BASE"] = api_base
    openai.api_base = api_base

    credential_module = types.ModuleType("credentials")
    credential_module.openai_org = organization
    credential_module.openai_api_key = api_key
    sys.modules["credentials"] = credential_module

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = DEMO_DIR / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    prediction_path = output_dir / "predictions.jsonl"
    evaluation_path = output_dir / "evaluation.jsonl"

    try:
        with tempfile.TemporaryDirectory(prefix="runtime_", dir=DEMO_DIR) as temp_name:
            temp_dir = Path(temp_name)
            infer_config = make_runtime_config(
                ROOT / "configs/reddit/running/reddit_synthetic_gpt6_astra.yaml",
                temp_dir, model, DATASET, prediction_path, False,
            )
            eval_config = make_runtime_config(
                ROOT / "configs/reddit/eval/reddit_eval_gpt6_astra.yaml",
                temp_dir, model, prediction_path, evaluation_path, True,
            )

            print(f"Using model: {model}")
            print("Running original main.py Reddit inference...")
            run_original_main(infer_config)
            if not prediction_path.exists():
                raise RuntimeError("Inference ended without creating predictions.jsonl")

            print("Running original main.py evaluation path (decider=none; no extra model judgment calls)...")
            run_original_main(eval_config)
            if not evaluation_path.exists():
                raise RuntimeError("Evaluation ended without creating evaluation.jsonl")

        evaluated, counts = extract_accuracy(evaluation_path)
        print(f"Predictions: {prediction_path}")
        print(f"Evaluation: {evaluation_path}")
        print(f"Evaluated profiles: {len(evaluated)}")
        print("Accuracy from the authors' evaluation output:")
        for attribute, result in counts.items():
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
        if os.getenv("OPENAI_API_KEY"):
            os.environ.pop("OPENAI_API_KEY", None)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
