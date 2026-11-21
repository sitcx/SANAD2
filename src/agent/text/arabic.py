"""Arabic-aware text helpers shared by the CV reader, matching and job search.

normalize_arabic() folds spelling variants (أ/إ/آ -> ا, ى -> ي, ة -> ه), strips diacritics and
tatweel, converts Arabic-Indic digits and lower-cases Latin text, so «اكسل» and «إكسل» compare equal.
Ported from the teammate's TypeScript (server/text/arabic.ts); behaviour kept identical.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable
from functools import lru_cache

_DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = re.compile("ـ")
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي", "ة": "ه"})
_DIGITS = str.maketrans({**{chr(0x0660 + i): str(i) for i in range(10)}, **{chr(0x06F0 + i): str(i) for i in range(10)}})
_ZERO_WIDTH = re.compile("[‌-‏]")
_SPACES = re.compile(r"\s+")
_KEEP_SYMBOLS = set("+#./-")


def _keep(char: str) -> bool:
    return char.isalpha() or char.isnumeric() or char in _KEEP_SYMBOLS or char.isspace()


@lru_cache(maxsize=65536)   # the same skills and titles are normalised thousands of times while matching
def normalize_arabic(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = _DIACRITICS.sub("", value)
    value = _TATWEEL.sub("", value)
    value = value.translate(_FOLD).translate(_DIGITS).lower()
    value = _ZERO_WIDTH.sub("", value)
    value = "".join(char if _keep(char) else " " for char in value)
    return _SPACES.sub(" ", value).strip()


def tokenize(text: str) -> list[str]:
    return [token.strip(".") for token in re.split(r"[\s/-]+", normalize_arabic(text)) if token.strip(".")]


_PREFIXES = ["وبال", "وال", "بال", "كال", "فال", "لل", "ال", "و", "ب", "ل", "ف", "ك"]
_SUFFIXES = ["هما", "كما", "تين", "تم", "ين", "ون", "ات", "ان", "ها", "هم", "كم", "نا", "ني", "ه", "ك", "ي", "ت"]


def arabic_variants(word: str) -> list[str]:
    """Light stemming: candidate base forms of an Arabic word, most specific first."""
    base = normalize_arabic(word)
    out = [base]
    if not re.search("[؀-ۿ]", base):
        return out
    for prefix in _PREFIXES:
        if base.startswith(prefix) and len(base) - len(prefix) >= 2 and base[len(prefix):] not in out:
            out.append(base[len(prefix):])
    for form in list(out):
        for suffix in _SUFFIXES:
            if form.endswith(suffix) and len(form) - len(suffix) >= 2 and form[: -len(suffix)] not in out:
                out.append(form[: -len(suffix)])
    return out


def unique_strings(values: Iterable[str], limit: float = math.inf) -> list[str]:
    """Distinct values (compared after normalisation), first spelling kept, whitespace collapsed."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        value = _SPACES.sub(" ", raw or "").strip()
        key = normalize_arabic(value)
        if not value or not key or key in seen:
            continue
        seen.add(key)
        out.append(value)
        if len(out) >= limit:
            break
    return out


_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def ar_digits(value: object) -> str:
    """123 -> «١٢٣» (also used where the TypeScript used toLocaleString('ar-SA') on integers)."""
    return re.sub(r"\d", lambda m: _AR_DIGITS[int(m.group())], str(value))


def to_ascii_digits(value: str) -> str:
    return value.translate(_DIGITS)


def js_round(value: float) -> int:
    """JavaScript Math.round (halves go up), not Python's banker's rounding."""
    return math.floor(value + 0.5)
