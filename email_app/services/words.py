from pathlib import Path
import random

RAW_WORDS = Path(__file__).resolve().parents[2] / "words.txt"
FILTERED_WORDS = Path(__file__).resolve().parents[2] / "wordsFiltered.txt"


def create_filtered_file():
    if not RAW_WORDS.exists():
        raise FileNotFoundError("words.txt not found")

    filtered = {
        w.strip().lower()
        for w in RAW_WORDS.read_text(encoding="utf-8").splitlines()
        if w.isalpha()
        and w.isascii()
        and 3 <= len(w) <= 10
        and len(set(w)) >= 3
    }

    FILTERED_WORDS.write_text("\n".join(sorted(filtered)), encoding="utf-8")
    print(f"Created {FILTERED_WORDS} with {len(filtered)} words")


def load_words(length: int | None = None) -> list[str]:
    # 🔥 ensure file exists
    if not FILTERED_WORDS.exists():
        create_filtered_file()

    words = FILTERED_WORDS.read_text(encoding="utf-8").splitlines()

    if length is not None:
        words = [w for w in words if len(w) == length]

    return words


def get_random_words(number: int, length: int | None = None) -> list[str]:
    words = load_words(length)

    if len(words) < number:
        raise ValueError("Not enough words available")

    return random.sample(words, number)