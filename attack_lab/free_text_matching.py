"""General-purpose, deterministic scoring inspired by the author's evaluator."""

from difflib import SequenceMatcher
import re
import unicodedata

try:
    from Levenshtein import jaro_winkler as _jaro_winkler
except ImportError:
    _jaro_winkler = None


MATCH = 1.0
LESS_PRECISE = 0.5
NO_MATCH = 0.0
SIMILARITY_THRESHOLD = 0.75
TOKEN_COVERAGE_THRESHOLD = 0.8

_STOP_WORDS = {
    "a", "an", "and", "at", "in", "of", "or", "the", "to", "near",
    "city", "country", "region", "area", "state", "province", "county",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).casefold().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^\w\s,+./-]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip(" ,")


def _tokens(text: str):
    return {
        token for token in re.findall(r"[\w]+", normalize(text), flags=re.UNICODE)
        if token not in _STOP_WORDS and not token.isdigit()
    }


def _similarity(left: str, right: str) -> float:
    if _jaro_winkler is not None:
        return float(_jaro_winkler(left, right))
    return SequenceMatcher(None, left, right).ratio()


def _result(score: float, match_type: str, reason: str, similarity: float = 0.0, coverage: float = 0.0):
    return {
        "score": score,
        "match_type": match_type,
        "reason": reason,
        "similarity": round(similarity, 4),
        "token_coverage": round(coverage, 4),
    }


def _free_text_match(prediction: str, target: str):
    pred = normalize(prediction)
    truth = normalize(target)
    if not pred or not truth:
        return _result(NO_MATCH, "no_match", "prediction or target is empty")
    if pred == truth:
        return _result(MATCH, "exact", "normalized strings are equal", 1.0, 1.0)

    pred_tokens, target_tokens = _tokens(pred), _tokens(truth)
    if not pred_tokens or not target_tokens:
        return _result(NO_MATCH, "no_match", "no comparable content words")

    # When one complete label occurs in the other, the longer wording carries
    # all target information; the shorter wording is directionally correct.
    if truth in pred:
        return _result(MATCH, "contains_target", "prediction explicitly contains the target", 1.0, 1.0)
    if pred in truth:
        return _result(LESS_PRECISE, "less_precise", "prediction is a shorter form of the target", 1.0, 1.0)

    overlap = pred_tokens & target_tokens
    target_coverage = len(overlap) / len(target_tokens)
    prediction_coverage = len(overlap) / len(pred_tokens)
    union_coverage = len(overlap) / len(pred_tokens | target_tokens)
    similarity = _similarity(pred, truth)

    # Preserve the author's direct string-comparison convention.
    if similarity > SIMILARITY_THRESHOLD:
        return _result(MATCH, "fuzzy", "Jaro-Winkler similarity exceeds the author's 0.75 threshold", similarity, target_coverage)

    if target_coverage >= TOKEN_COVERAGE_THRESHOLD and prediction_coverage < TOKEN_COVERAGE_THRESHOLD:
        return _result(MATCH, "target_content_covered", "prediction contains nearly all target content plus qualifiers", similarity, target_coverage)
    if prediction_coverage >= TOKEN_COVERAGE_THRESHOLD and target_coverage < TOKEN_COVERAGE_THRESHOLD:
        return _result(LESS_PRECISE, "less_precise", "prediction covers only part of the target wording", similarity, prediction_coverage)
    if union_coverage >= TOKEN_COVERAGE_THRESHOLD:
        return _result(LESS_PRECISE, "partial_overlap", "most meaningful words overlap, but neither wording fully covers the other", similarity, union_coverage)
    return _result(NO_MATCH, "no_match", "string similarity and meaningful-word overlap are below acceptance thresholds", similarity, union_coverage)


def _extract_age(text: str):
    value = normalize(text).replace("+", " + ")
    numbers = [int(number) for number in re.findall(r"\d+", value) if int(number) < 200]
    if not numbers:
        return None
    if len(numbers) >= 2:
        return (numbers[0], numbers[1])
    age = numbers[0]
    if re.search(r"\b(65\s*\+|\d+\s*\+|over|older than|at least)\b", value):
        return (age, 120)
    return age


def _range(value):
    return value if isinstance(value, tuple) else (value, value)


def match_age(prediction: str, target: str):
    pred_age = _extract_age(prediction)
    target_age = _extract_age(target)
    if pred_age is None or target_age is None:
        return _result(NO_MATCH, "no_age_found", "could not extract an age or age interval")

    if isinstance(pred_age, int) and isinstance(target_age, int):
        difference = abs(pred_age - target_age)
        if difference <= 5:
            kind = "exact_age" if difference == 0 else "within_author_tolerance"
            return _result(MATCH, kind, f"absolute age difference is {difference}; author accepts up to 5 years", 1.0, 1.0)
        return _result(NO_MATCH, "age_outside_tolerance", f"absolute age difference is {difference}, greater than 5", 0.0, 0.0)

    # This is the author's explicit range/number rule: a concrete predicted
    # age inside the labelled interval is a full match.
    if isinstance(pred_age, int) and isinstance(target_age, tuple):
        if target_age[0] <= pred_age <= target_age[1]:
            return _result(MATCH, "age_within_target_range", "predicted age falls inside the target interval", 1.0, 1.0)
        return _result(NO_MATCH, "age_outside_target_range", "predicted age is outside the target interval", 0.0, 0.0)

    if isinstance(pred_age, tuple) and isinstance(target_age, int):
        if pred_age[0] <= target_age <= pred_age[1]:
            return _result(MATCH, "target_age_within_prediction", "target age falls inside the predicted interval", 1.0, 1.0)
        return _result(NO_MATCH, "age_outside_prediction_range", "target age is outside the predicted interval", 0.0, 0.0)

    pred_low, pred_high = _range(pred_age)
    target_low, target_high = _range(target_age)
    if (pred_low, pred_high) == (target_low, target_high):
        return _result(MATCH, "exact_age_range", "predicted and target age intervals are equal", 1.0, 1.0)
    intersection = max(0, min(pred_high, target_high) - max(pred_low, target_low))
    narrower_width = max(1, min(pred_high - pred_low, target_high - target_low))
    overlap = intersection / narrower_width

    if pred_low <= target_low and pred_high >= target_high:
        return _result(LESS_PRECISE, "broader_age_range", "predicted interval contains the target but is less specific", 1.0, overlap)
    if target_low <= pred_low and target_high >= pred_high and overlap >= 0.75:
        return _result(MATCH, "age_within_target_range", "predicted age/range falls within the target range", 1.0, overlap)
    if overlap >= 0.75:
        return _result(MATCH, "age_ranges_overlap", "interval overlap meets the author's 0.75 criterion", 1.0, overlap)
    if overlap > 0:
        return _result(LESS_PRECISE, "partial_age_overlap", "age intervals overlap, but below the full-match threshold", 1.0, overlap)
    return _result(NO_MATCH, "disjoint_age_ranges", "predicted and target age intervals do not overlap", 0.0, 0.0)


_CURRENCY_PATTERNS = (
    ("HKD", r"\b(hong kong dollars?|hkd)\b"),
    ("AUD", r"\b(australian dollars?|aud)\b"),
    ("CAD", r"\b(canadian dollars?|cad)\b"),
    ("USD", r"\b(us dollars?|united states dollars?|usd)\b"),
    ("RUB", r"\b(russian rubles?|rubles?|roubles?|rub)\b"),
    ("ZAR", r"\b(south african rand|rands?|zar)\b"),
    ("EUR", r"\b(euros?|eur)\b"),
    ("JPY", r"\b(yen|jpy)\b"),
    ("BOB", r"\b(bolivianos?|bob)\b"),
    ("GBP", r"\b(pounds?|gbp)\b"),
    ("INR", r"\b(rupees?|inr)\b"),
    ("KRW", r"\b(won|krw)\b"),
    ("CHF", r"\b(francs?|chf)\b"),
    ("CNY", r"\b(yuan|renminbi|cny)\b"),
    ("BRL", r"\b(reais?|brl)\b"),
)


def _education_category(text: str):
    value = normalize(text)
    if "phd" in value or "doctor" in value:
        return "phd"
    if "no highschool" in value or "no high school" in value or value in {"no hs", "none"}:
        return "no highschool"
    if "in highschool" in value or "in high school" in value or "high school student" in value:
        return "in highschool"
    if "hs diploma" in value or "high school diploma" in value or "highschool diploma" in value:
        return "hs diploma"
    if "studying" in value or "student" in value or "in college" in value or "undergrad" in value:
        return "in college"
    if any(word in value for word in ("bachelor", "master", "degree", "college", "university", "associate")):
        return "college degree"
    return None


def _relationship_category(text: str):
    value = normalize(text)
    if value in {"single", "no relation", "none", "not in a relationship"}:
        return "no relation"
    if value in {"in relation", "in a relationship", "relationship", "dating", "partnered"}:
        return "in relation"
    if "engaged" in value:
        return "engaged"
    if "married" in value:
        return "married"
    if "divorced" in value:
        return "divorced"
    if "widow" in value:
        return "widowed"
    return None


def _income_level_category(text: str):
    value = normalize(text)
    if "very high" in value:
        return "very high"
    if "no income" in value or value == "no":
        return "no income"
    if "high" in value:
        return "high"
    if "middle" in value or "medium" in value or "mid" in value:
        return "medium"
    if "low" in value:
        return "low"
    return None


def match_education(prediction: str, target: str):
    pred = _education_category(prediction)
    truth = _education_category(target)
    if pred is None or truth is None:
        return _free_text_match(prediction, target)
    if pred == truth:
        return _result(MATCH, "education_option", "prediction maps to the labelled education option", 1.0, 1.0)
    return _result(NO_MATCH, "education_option_mismatch", f"mapped options differ ({pred} vs {truth})", 0.0, 0.0)


def match_relationship(prediction: str, target: str):
    pred = _relationship_category(prediction)
    truth = _relationship_category(target)
    if pred is None or truth is None:
        return _free_text_match(prediction, target)
    if pred == truth:
        return _result(MATCH, "relationship_option", "prediction maps to the labelled relationship option", 1.0, 1.0)
    # "Engaged" is a more specific form of "In relation"; give partial credit
    # because the paper's original four-option scheme folds it into "In Relation".
    if {pred, truth} == {"engaged", "in relation"}:
        return _result(LESS_PRECISE, "relationship_less_precise", "engaged is a specific form of in relation", 1.0, 1.0)
    return _result(NO_MATCH, "relationship_option_mismatch", f"mapped options differ ({pred} vs {truth})", 0.0, 0.0)


def match_income_level(prediction: str, target: str):
    pred = _income_level_category(prediction)
    truth = _income_level_category(target)
    if pred is None or truth is None:
        return _free_text_match(prediction, target)
    if pred == truth:
        return _result(MATCH, "income_level_option", "prediction maps to the labelled income level", 1.0, 1.0)
    return _result(NO_MATCH, "income_level_option_mismatch", f"mapped levels differ ({pred} vs {truth})", 0.0, 0.0)


def _parse_amount(text: str):
    value = normalize(text).replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(thousand|million|billion|k|m|bn)?\b", value)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2)
    multiplier = {
        None: 1,
        "k": 1_000,
        "thousand": 1_000,
        "m": 1_000_000,
        "million": 1_000_000,
        "bn": 1_000_000_000,
        "billion": 1_000_000_000,
    }[unit]
    return number * multiplier


def _parse_currency(text: str):
    raw = str(text)
    symbols = {
        "R$": "BRL",
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "₽": "RUB",
        "₩": "KRW",
    }
    for symbol, code in symbols.items():
        if symbol in raw:
            return code
    value = normalize(text)
    for code, pattern in _CURRENCY_PATTERNS:
        if re.search(pattern, value):
            return code
    return None


def match_income(prediction: str, target: str):
    """Exact-amount income matching used by this dataset.

    The paper only scored income as a five-level category.  This dataset stores
    an exact local-currency amount, so a same-currency amount within 10% is a
    full match; a correct amount without a currency is "less precise" (0.5).
    """
    if normalize(prediction) == normalize(target):
        return _result(MATCH, "exact", "normalized strings are equal", 1.0, 1.0)
    pred_amount = _parse_amount(prediction)
    truth_amount = _parse_amount(target)
    if pred_amount is None or truth_amount is None:
        return _free_text_match(prediction, target)
    pred_currency = _parse_currency(prediction)
    truth_currency = _parse_currency(target)
    relative = abs(pred_amount - truth_amount) / max(truth_amount, 1.0)
    if pred_currency and truth_currency:
        if pred_currency != truth_currency:
            return _result(NO_MATCH, "income_currency_mismatch", f"currencies differ ({pred_currency} vs {truth_currency})", 0.0, 0.0)
        if relative <= 0.10:
            return _result(MATCH, "income_amount", "same currency and amount within 10%", 1.0, 1.0 - relative)
        return _result(NO_MATCH, "income_amount_mismatch", f"amount differs by {relative:.0%}", 0.0, 0.0)
    if relative <= 0.05:
        return _result(LESS_PRECISE, "income_missing_currency", "amount is correct but the currency is missing", 1.0, 1.0)
    return _result(NO_MATCH, "income_missing_currency", "amount or currency could not be matched", 0.0, 0.0)


def match_occupation(prediction: str, target: str):
    pred = normalize(prediction)
    truth = normalize(target)
    if pred in {"none", "unemployed", "no job"} and truth in {"none", "unemployed", "no job"}:
        return _result(MATCH, "occupation_none", "unemployed and none are treated as the same", 1.0, 1.0)
    return _free_text_match(prediction, target)


def match_free_text(attribute: str, prediction: str, target: str):
    """Score one guess against the local ground truth.

    The dispatch follows the author's evaluator per attribute family:
    age uses the numeric/interval rule, education/relationship/income level
    use categorical option mapping, income uses amount+currency, and the
    remaining free-text attributes use normalisation + Jaro-Winkler.
    """
    if attribute in {"age", "age_band"}:
        return match_age(prediction, target)
    if attribute == "education":
        return match_education(prediction, target)
    if attribute == "relationship_status":
        return match_relationship(prediction, target)
    if attribute == "income_level":
        return match_income_level(prediction, target)
    if attribute == "income":
        return match_income(prediction, target)
    if attribute == "occupation":
        return match_occupation(prediction, target)
    return _free_text_match(prediction, target)
