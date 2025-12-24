import json
from pathlib import Path
from typing import Any, List

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOANS_FILE = DATA_DIR / "loans.json"
PAYMENTS_FILE = DATA_DIR / "payments.json"


def _read_json(path: Path) -> List[Any]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")
        return []

    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_json(path: Path, data: List[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class JSONStorage:
    """Tiny JSON file storage layer used for dev/demo purposes."""

    def load_loans(self) -> List[Any]:
        return _read_json(LOANS_FILE)

    def save_loans(self, loans: List[Any]) -> None:
        _write_json(LOANS_FILE, loans)

    def load_payments(self) -> List[Any]:
        return _read_json(PAYMENTS_FILE)

    def save_payments(self, payments: List[Any]) -> None:
        _write_json(PAYMENTS_FILE, payments)
