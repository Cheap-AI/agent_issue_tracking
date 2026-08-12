from pathlib import Path


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def find_matches(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    matches = [term for term in terms if term.lower() in lowered]
    return matches
