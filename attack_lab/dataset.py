"""Adapter from the thread-level ``database/`` release to passive-inference profiles.

The database stores one JSONL row per ``(thread, participant)``:

    {
      "thread_id": "thread_city_country_25",
      "feature": "city_country",
      "person_id": "pers107",
      "profile": {...nine persona attributes...},
      "comments": [{"node_id": "0.0", "parent_id": "0", "depth": 1,
                    "text": "...", "guesses": [...]}, ...]
    }

All rows that share a ``thread_id`` describe one complete thread, sliced by
participant.  The attack works on one person at a time, so this module groups
the slices by ``person_id`` across every thread file and emits one profile per
person with all nine attributes:

    age, sex, city_country, birth_city_country, education, occupation,
    income, income_level, relationship_status

Only ``texts`` is ever sent to the model; ``labels`` stays local.
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path
from typing import Iterable

SEX_OPTIONS = ("Male", "Female")
EDUCATION_OPTIONS = (
    "No Highschool",
    "In Highschool",
    "HS Diploma",
    "In College",
    "College Degree",
    "PhD",
)
INCOME_LEVEL_OPTIONS = ("Low", "Medium", "High")
RELATIONSHIP_OPTIONS = (
    "No relation",
    "In relation",
    "Engaged",
    "Married",
    "Divorced",
    "Widowed",
)

# attribute -> (profile field, kind).  ``age`` is copied as an exact number;
# categorical values are mapped to the author's option names.
LABEL_FIELDS = {
    "age": ("age", "age"),
    "sex": ("sex", "sex"),
    "city_country": ("city_country", "location"),
    "birth_city_country": ("birth_city_country", "location"),
    "education": ("education", "education"),
    "occupation": ("occupation", "occupation"),
    "income": ("income", "income"),
    "income_level": ("income_level", "income_level"),
    "relationship_status": ("relationship_status", "relationship"),
}

SUPPORTED_ATTRIBUTES = tuple(LABEL_FIELDS)
DEFAULT_ATTRIBUTES = SUPPORTED_ATTRIBUTES

AS_OF_DATE = "2026-10-30"
TEXT_MIN_CHARS = 10
TEXT_MAX_CHARS = 2000


class DatasetError(ValueError):
    """Raised when a database file cannot be turned into attack profiles."""


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def education_option(value: str) -> str:
    """Map a free-form degree string onto the six paper-style options."""
    text = _normalise(value)
    if not text:
        raise DatasetError("education value is empty")
    if "phd" in text or "doctor" in text:
        return "PhD"
    if "no highschool" in text or "no high school" in text or text in {"no hs", "none"}:
        return "No Highschool"
    if "in highschool" in text or "in high school" in text or "high school student" in text:
        return "In Highschool"
    if "hs diploma" in text or "high school diploma" in text or "highschool diploma" in text:
        return "HS Diploma"
    if "studying" in text or "student" in text or "in college" in text or "undergrad" in text:
        return "In College"
    if any(word in text for word in ("bachelor", "master", "degree", "college", "university", "associate")):
        return "College Degree"
    raise DatasetError(f"cannot map education value to an option: {value!r}")


def relationship_option(value: str) -> str:
    """Map the dataset's relationship values onto a categorical option."""
    text = _normalise(value)
    if text in {"single", "no relation", "none"}:
        return "No relation"
    if text in {"in relation", "in a relationship", "relationship", "dating"}:
        return "In relation"
    if text == "engaged":
        return "Engaged"
    if text == "married":
        return "Married"
    if text == "divorced":
        return "Divorced"
    if text == "widowed":
        return "Widowed"
    raise DatasetError(f"cannot map relationship status to an option: {value!r}")


def income_level_option(value: str) -> str:
    text = _normalise(value)
    if text in {"low", "lower"}:
        return "Low"
    if text in {"middle", "medium", "mid"}:
        return "Medium"
    if text in {"high", "upper"}:
        return "High"
    raise DatasetError(f"cannot map income level to Low/Medium/High: {value!r}")


def sex_option(value: str) -> str:
    text = _normalise(value)
    if text in {"male", "m", "man"}:
        return "Male"
    if text in {"female", "f", "woman"}:
        return "Female"
    raise DatasetError(f"cannot map sex to Male/Female: {value!r}")


def clean_text(text: str) -> str:
    """Normalise obvious export noise without rewriting the author's voice."""
    value = str(text).replace("\ufffd", "-")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _node_key(node_id: str):
    parts = []
    for part in str(node_id).split("."):
        parts.append((0, int(part), "") if part.isdigit() else (1, 0, part))
    return tuple(parts)


def discover_files(path: str | Path) -> list[Path]:
    """Accept a JSONL file, a directory, or a glob such as ``database/*.jsonl``."""
    raw = str(path)
    candidate = Path(raw).expanduser()
    if candidate.is_dir():
        files = sorted(candidate.glob("*.jsonl"))
    elif candidate.is_file():
        files = [candidate]
    else:
        files = sorted(Path(match) for match in glob.glob(raw))
    files = [file for file in files if file.suffix.lower() == ".jsonl"]
    if not files:
        raise DatasetError(f"no .jsonl files found at {raw}")
    return files


def _validate_profile(profile: dict, where: str) -> None:
    if not isinstance(profile, dict):
        raise DatasetError(f"{where}: profile must be an object")
    missing = [field for field, _ in LABEL_FIELDS.values() if field not in profile]
    if missing:
        raise DatasetError(f"{where}: profile is missing fields {sorted(set(missing))}")


def derive_labels(profile: dict) -> dict[str, str]:
    """Map all nine persona fields onto the labels the attack will score."""
    labels: dict[str, str] = {}
    for attribute, (field, kind) in LABEL_FIELDS.items():
        if kind == "age":
            age = profile[field]
            if not isinstance(age, int) or isinstance(age, bool) or not 18 <= age <= 120:
                raise DatasetError(f"age must be an integer in 18-120, got {age!r}")
            labels[attribute] = str(age)
            continue
        value = profile.get(field)
        if not isinstance(value, str) or not value.strip():
            raise DatasetError(f"profile field {field!r} must be a nonempty string")
        if kind == "sex":
            labels[attribute] = sex_option(value)
        elif kind == "education":
            labels[attribute] = education_option(value)
        elif kind == "income_level":
            labels[attribute] = income_level_option(value)
        elif kind == "relationship":
            labels[attribute] = relationship_option(value)
        else:
            labels[attribute] = value.strip()
    return labels


def _iter_candidates(records: Iterable[dict]):
    """Yield comments in a stable reading order."""
    for record in records:
        for comment in sorted(record["comments"], key=lambda item: (item["depth"], _node_key(item["node_id"]))):
            yield record, comment


def build_profiles(
    path: str | Path,
    attributes: Iterable[str] = DEFAULT_ATTRIBUTES,
    min_texts: int = 3,
) -> list[dict]:
    """Group participant slices by ``person_id`` and return attack profiles."""
    attributes = tuple(attributes)
    unknown = [name for name in attributes if name not in LABEL_FIELDS]
    if unknown:
        raise DatasetError(f"unsupported attributes: {unknown}; choose from {SUPPORTED_ATTRIBUTES}")
    if not attributes:
        raise DatasetError("at least one attribute is required")
    if min_texts < 1:
        raise DatasetError("min_texts must be positive")

    files = discover_files(path)
    grouped: dict[str, list[dict]] = {}
    file_order = {file: index for index, file in enumerate(files)}

    for file in files:
        with file.open(encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                where = f"{file}:{line_no}"
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise DatasetError(f"{where}: invalid JSON ({exc})") from exc
                if not isinstance(row, dict):
                    raise DatasetError(f"{where}: each line must be a JSON object")
                for key in ("person_id", "thread_id", "profile", "comments"):
                    if key not in row:
                        raise DatasetError(f"{where}: missing field {key!r}")
                _validate_profile(row["profile"], where)
                person_id = row["person_id"]
                thread_id = row["thread_id"]
                if not isinstance(person_id, str) or not person_id.strip():
                    raise DatasetError(f"{where}: person_id must be a nonempty string")
                if not isinstance(thread_id, str) or not thread_id.strip():
                    raise DatasetError(f"{where}: thread_id must be a nonempty string")
                if not isinstance(row["comments"], list) or not row["comments"]:
                    raise DatasetError(f"{where}: comments must be a nonempty list")
                for comment in row["comments"]:
                    for key in ("node_id", "parent_id", "depth", "text"):
                        if key not in comment:
                            raise DatasetError(f"{where}: comment missing field {key!r}")
                    if not isinstance(comment["text"], str):
                        raise DatasetError(f"{where}: comment text must be a string")
                    if not isinstance(comment["depth"], int) or comment["depth"] < 0:
                        raise DatasetError(f"{where}: comment depth must be a nonnegative integer")
                row["_file_order"] = file_order[file]
                grouped.setdefault(person_id, []).append(row)

    if not grouped:
        raise DatasetError(f"no participant rows found in {path}")

    profiles: list[dict] = []
    for person_id, records in grouped.items():
        records.sort(key=lambda item: (item["_file_order"], item["thread_id"]))
        expected = derive_labels(records[0]["profile"])
        for record in records[1:]:
            current = derive_labels(record["profile"])
            if current != expected:
                raise DatasetError(
                    f"{person_id}: profile values disagree between threads "
                    f"({records[0]['thread_id']} vs {record['thread_id']})"
                )

        texts: list[dict] = []
        seen_text: set[str] = set()
        seen_id: set[str] = set()
        for record, comment in _iter_candidates(records):
            body = clean_text(comment["text"])
            if not body or body in seen_text:
                continue
            if not TEXT_MIN_CHARS <= len(body) <= TEXT_MAX_CHARS:
                continue
            text_id = f"{record['thread_id']}:{comment['node_id']}"
            if text_id in seen_id:
                raise DatasetError(f"{person_id}: duplicate text_id {text_id!r}")
            seen_id.add(text_id)
            seen_text.add(body)
            texts.append(
                {
                    "text_id": text_id,
                    "text": body,
                    "source_thread": record["thread_id"],
                    "depth": comment["depth"],
                }
            )

        if len(texts) < min_texts:
            continue
        labels = {name: expected[name] for name in attributes}
        profiles.append(
            {
                "profile_id": person_id,
                "origin": "synthetic",
                "split": "test",
                "as_of_date": AS_OF_DATE,
                "texts": texts,
                "labels": labels,
                "label_source": "synthetic_persona",
                "quality": {"label_certainty": "high"},
                "source_threads": sorted({record["thread_id"] for record in records}),
            }
        )

    if not profiles:
        raise DatasetError(
            f"{path}: no persona has at least {min_texts} usable texts; "
            "lower --min-texts or check the input"
        )
    profiles.sort(key=lambda item: item["profile_id"])
    return profiles


def describe(path: str | Path) -> dict:
    """Small, side-effect-free summary used by the CLI."""
    files = discover_files(path)
    people: set[str] = set()
    threads: set[str] = set()
    rows = 0
    for file in files:
        with file.open(encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise DatasetError(f"{file}:{line_no}: invalid JSON ({exc})") from exc
                if not isinstance(row, dict):
                    raise DatasetError(f"{file}:{line_no}: each line must be a JSON object")
                rows += 1
                people.add(row.get("person_id"))
                threads.add(row.get("thread_id"))
    return {"files": [file.name for file in files], "rows": rows, "threads": len(threads), "people": len(people)}
