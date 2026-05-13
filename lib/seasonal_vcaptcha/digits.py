"""Digit word normalization for spoken CAPTCHA responses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

DEFAULT_DIGIT_ALIASES: dict[str, str] = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "for": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "ate": "8",
    "nine": "9",
}

DEFAULT_GRAMMAR_PHRASES: tuple[str, ...] = (
    "zero",
    "oh",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
)


def words_to_digits(
    text: str,
    *,
    aliases: Mapping[str, str] | None = None,
    max_digits: int | None = None,
) -> str:
    """Convert recognized digit words into a digit-only string.

    Unknown tokens are retained only when they are already numeric. This preserves
    the legacy dialplan-safe behavior: stdout is only digits or empty.
    """

    mapping = aliases or DEFAULT_DIGIT_ALIASES
    normalized_tokens: list[str] = []
    for token in text.strip().lower().split():
        normalized_tokens.append(mapping.get(token, token))

    digits = "".join(ch for ch in "".join(normalized_tokens) if ch.isdigit())
    if max_digits is not None and max_digits >= 0:
        return digits[:max_digits]
    return digits


def grammar_from_phrases(phrases: Sequence[str] | None = None) -> str:
    """Return a Vosk grammar JSON array from allowed phrases."""

    import json

    return json.dumps(list(phrases or DEFAULT_GRAMMAR_PHRASES), separators=(",", ":"))
