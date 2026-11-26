"""Regenerate the published backup test vectors in docs/test-vectors/.

The vectors use a fixed salt, nonce and timestamp so the output is reproducible.
Other platforms (phones) can use them to check that they read and write the same
format: decrypt ``encrypted.ftbackup`` with the password in ``README.md`` and you
must obtain exactly the payload that ``plain.ftbackup`` contains.

    python tools/make_backup_vectors.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import backup  # noqa: E402

PASSWORD = "Şifre-123-ığüİ"          # Turkish letters on purpose (NFC normalisation)
SALT = bytes(range(16))
NONCE = bytes(range(12))
MOMENT = datetime(2026, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
PAYLOAD = {
    "preferences": {"precision": 2, "currency_codes": ["USD", "EUR", "SEK"], "calculator_extra_currency": "SEK"},
    "profiles": [
        {
            "id": "profile1", "name": "Ana Profil",
            "currency": [{"code": "USD", "quantity": "100.5", "average_cost_try": "30.25", "updated_at": "2026-01-10T08:00:00+00:00"}],
            "metals": [{"code": "XAU", "quantity": "10", "average_cost_try": "2800", "updated_at": "2026-01-11T08:00:00+00:00"}],
            "stocks": [{"symbol": "ASELS", "company": "Aselsan Elektronik", "quantity": "10", "average_cost": "75.50",
                        "sector": "Savunma", "notes": "Şirket notu: çeşitli ığüşöç", "updated_at": "2026-01-12T08:00:00+00:00"}],
        }
    ],
}


def generate() -> dict[str, bytes]:
    common = dict(app_version="2.6.0", platform_name="windows", now=MOMENT)
    return {
        "plain.ftbackup": backup.create_backup(PAYLOAD, **common),
        "encrypted.ftbackup": backup.create_backup(PAYLOAD, password=PASSWORD, salt=SALT, nonce=NONCE, **common),
    }


def main() -> None:
    folder = ROOT / "docs" / "test-vectors"
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in generate().items():
        (folder / name).write_bytes(data)
        print("wrote", folder / name)
    key = backup.derive_key(PASSWORD, SALT, backup.PBKDF2_ITERATIONS).hex()
    print("derived key (hex):", key)


if __name__ == "__main__":
    main()
