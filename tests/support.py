from pathlib import Path

BASE = "https://manaba.example.ac.jp"

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    """Anonymized manaba HTML: structure copied from the live site, all data fake."""
    return (FIXTURES / name).read_text(encoding="utf-8")
