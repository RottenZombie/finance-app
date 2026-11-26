"""Read the application's data into a backup payload and restore one (Qt-free).

Backups are written per profile and contain only portable values (see
``docs/DATA_FORMAT.md``). Restoring never touches anything before the whole file
has been verified and validated, and always saves the current data first.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from core import backup
from core.app_paths import app_data_directory
from core.backup import CleanBackup, PROFILE_IDS, plain
from core.i18n import tr
from core.log_setup import get_logger
from features.bist.database import BistDatabase
from features.currencies import DEFAULT_EXTRA_CURRENCY, asset_display_name
from features.investment_store import InvestmentStore

log = get_logger("backup")

MERGE = "merge"
REPLACE = "replace"
KEEP_SAFETY_BACKUPS = 5
INVESTMENT_DB = "investment_holdings.db"
BIST_DB = "bist_portfolio.db"


def profile_data_dir(profile_id: str, data_root: Path | None = None) -> Path:
    return (data_root or app_data_directory()) / "profiles" / profile_id / "data"


def backups_dir(data_root: Path | None = None) -> Path:
    return (data_root or app_data_directory()) / "backups"


def _profile_names(settings: Mapping[str, Any]) -> dict[str, str]:
    names = settings.get("profile_names")
    names = names if isinstance(names, dict) else {}
    # Profiles 1 and 2 always exist; profile 3 only after the user created it.
    result = {pid: str(names.get(pid) or "") for pid in ("profile1", "profile2")}
    if names.get("profile3"):
        result["profile3"] = str(names["profile3"])
    return result


# ------------------------------------------------------------------ export
def collect_payload(settings: Mapping[str, Any], data_root: Path | None = None) -> dict[str, Any]:
    """Current preferences and every profile's records, in the portable layout."""
    profiles: list[dict[str, Any]] = []
    for profile_id, name in _profile_names(settings).items():
        data_dir = profile_data_dir(profile_id, data_root)
        entry: dict[str, Any] = {"id": profile_id, "name": name, "currency": [], "metals": [], "stocks": []}

        investment_db = data_dir / INVESTMENT_DB
        if investment_db.is_file():  # never create files just by exporting
            store = InvestmentStore(investment_db)
            for group, section in (("currency", "currency"), ("metals", "metals")):
                for row in store.list_holdings(group):
                    entry[section].append({
                        "code": row["asset_code"],
                        "quantity": plain(Decimal(str(row["quantity"]))),
                        "average_cost_try": plain(Decimal(str(row["average_cost_try"]))),
                        "updated_at": row.get("updated_at", ""),
                    })
        bist_db = data_dir / BIST_DB
        if bist_db.is_file():
            for row in BistDatabase(bist_db).list_holdings():
                entry["stocks"].append({
                    "symbol": row["symbol"],
                    "company": row.get("company", ""),
                    "quantity": plain(Decimal(str(row["quantity"]))),
                    "average_cost": plain(Decimal(str(row["average_cost"]))),
                    "sector": row.get("sector", ""),
                    "notes": row.get("notes", ""),
                    "updated_at": row.get("updated_at", ""),
                })
        profiles.append(entry)

    precision = settings.get("precision", 2)
    return {
        "preferences": {
            "precision": precision if isinstance(precision, int) and not isinstance(precision, bool) else 2,
            "currency_codes": list(settings.get("currency_codes") or []),
            "calculator_extra_currency": str(settings.get("calculator_extra_currency") or DEFAULT_EXTRA_CURRENCY),
        },
        "profiles": profiles,
    }


def build_backup_bytes(
    settings: Mapping[str, Any], *, password: str | None, app_version: str,
    data_root: Path | None = None, platform_name: str = "windows",
) -> tuple[bytes, dict[str, int]]:
    """Backup file content plus record counts per section (for the confirmation message)."""
    payload = collect_payload(settings, data_root)
    counts = {
        "profiles": len(payload["profiles"]),
        "currency": sum(len(p["currency"]) for p in payload["profiles"]),
        "metals": sum(len(p["metals"]) for p in payload["profiles"]),
        "stocks": sum(len(p["stocks"]) for p in payload["profiles"]),
    }
    data = backup.create_backup(payload, password=password, app_version=app_version, platform_name=platform_name)
    return data, counts


# ----------------------------------------------------------------- restore
@dataclass
class RestoreReport:
    mode: str
    imported: dict[str, int] = field(default_factory=dict)   # profile id -> number of records
    skipped: list[str] = field(default_factory=list)
    safety_backup: Path | None = None
    settings: dict[str, Any] = field(default_factory=dict)   # updated settings; the caller saves them

    @property
    def total_imported(self) -> int:
        return sum(self.imported.values())


def write_safety_backup(settings: Mapping[str, Any], app_version: str, data_root: Path | None = None) -> Path:
    """Save the current data (unencrypted, local only) before it is modified."""
    folder = backups_dir(data_root)
    folder.mkdir(parents=True, exist_ok=True)
    data, _counts = build_backup_bytes(settings, password=None, app_version=app_version, data_root=data_root)
    target = folder / f"before-restore-{time.strftime('%Y%m%d-%H%M%S')}{backup.FILE_EXTENSION}"
    counter = 1
    while target.exists():
        counter += 1
        target = folder / f"before-restore-{time.strftime('%Y%m%d-%H%M%S')}-{counter}{backup.FILE_EXTENSION}"
    target.write_bytes(data)
    older = sorted(folder.glob(f"before-restore-*{backup.FILE_EXTENSION}"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in older[KEEP_SAFETY_BACKUPS:]:
        try:
            stale.unlink()
        except OSError:
            pass
    return target


def summarize(clean: CleanBackup) -> dict[str, int]:
    return {
        "profiles": len(clean.profiles),
        "currency": sum(len(p.currency) for p in clean.profiles),
        "metals": sum(len(p.metals) for p in clean.profiles),
        "stocks": sum(len(p.stocks) for p in clean.profiles),
    }


def apply_backup(
    clean: CleanBackup,
    mode: str,
    settings: Mapping[str, Any],
    *,
    app_version: str,
    data_root: Path | None = None,
) -> RestoreReport:
    """Write a validated backup into the data folders.

    ``merge`` keeps every record that is not in the file and lets the file win for
    codes that exist in both; local preferences and profile names are kept.
    ``replace`` first clears each profile that is in the file, then loads it, and
    also takes over the shared preferences and profile names.
    """
    if mode not in (MERGE, REPLACE):
        raise ValueError(mode)
    new_settings = dict(settings)
    report = RestoreReport(mode=mode, skipped=list(clean.skipped), settings=new_settings)

    try:
        report.safety_backup = write_safety_backup(settings, app_version, data_root)
    except OSError as exc:
        raise backup.BackupError(tr("Mevcut verilerin güvenlik yedeği alınamadı: {0}").format(exc)) from exc

    names = dict(_profile_names(settings))
    try:
        for profile in clean.profiles:
            data_dir = profile_data_dir(profile.id, data_root)
            data_dir.mkdir(parents=True, exist_ok=True)
            store = InvestmentStore(data_dir / INVESTMENT_DB)
            bist = BistDatabase(data_dir / BIST_DB)
            if mode == REPLACE:
                store.delete_all("currency")
                store.delete_all("metals")
                bist.delete_all()

            imported = 0
            for section, group, unit_of in (
                (profile.currency, "currency", lambda code: code),
                (profile.metals, "metals", lambda code: "gr"),
            ):
                for row in section:
                    try:
                        store.set_holding(
                            group, row["code"], row["quantity"], row["average_cost_try"],
                            display_name=asset_display_name(group, row["code"]), unit=unit_of(row["code"]),
                        )
                        imported += 1
                    except ValueError as exc:
                        report.skipped.append(f"{profile.id} / {row['code']}: {exc}")
            for row in profile.stocks:
                try:
                    bist.upsert_holding(
                        row["symbol"], row["quantity"], row["average_cost"],
                        row["company"], row["sector"], row["notes"],
                    )
                    imported += 1
                except ValueError as exc:
                    report.skipped.append(f"{profile.id} / {row['symbol']}: {exc}")
            report.imported[profile.id] = imported

            if profile.name and (mode == REPLACE or profile.id not in names):
                names[profile.id] = profile.name
            elif profile.id not in names:
                names[profile.id] = tr("Profil 3")
    except Exception as exc:
        log.error("Yedek geri yüklenemedi", exc_info=True)
        raise backup.BackupError(
            tr("Yedek geri yüklenirken bir hata oluştu: {0}\n\nGeri yüklemeden önceki verileriniz şu dosyada saklandı: {1}")
            .format(exc, report.safety_backup)
        ) from exc

    new_settings["profile_names"] = names
    if mode == REPLACE:
        new_settings.update(clean.preferences)
    return report


def load_clean(data: bytes, password: str | None = None) -> tuple[backup.BackupInfo, CleanBackup]:
    """Verify, decrypt and validate a backup file's bytes."""
    info, payload = backup.read_backup(data, password)
    return info, backup.validate_payload(payload)
