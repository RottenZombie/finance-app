"""FinanceTerminal backup file (``.ftbackup``): a portable, versioned data format.

The same file is meant to be read and written by the desktop application and by
future phone applications (iOS, Android, HarmonyOS), so it deliberately uses only
things every platform has built in: UTF-8 JSON, SHA-256, PBKDF2-HMAC-SHA256,
AES-256-GCM and base64. It is NOT a copy of the SQLite files, is independent of
the user interface language, and stores numbers as plain decimal strings.

The complete specification (with examples and test vectors) is in
``docs/DATA_FORMAT.md``; keep that document and this module in sync.

This module is Qt-free and never touches the disk: it turns a payload dictionary
into bytes and back, and validates what it reads.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from core.i18n import tr
from features.bist.utils import normalize_symbol
from features.currencies import CURRENCY_INFO, currency_choices, sort_currency_codes

FORMAT = "FinanceTerminal.Backup"
FORMAT_VERSION = 1
FILE_EXTENSION = ".ftbackup"
MAX_FILE_BYTES = 16 * 1024 * 1024
PBKDF2_ITERATIONS = 600_000
MIN_ITERATIONS = 100_000
MAX_ITERATIONS = 5_000_000
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
MIN_PASSWORD_LENGTH = 8
PROFILE_IDS = ("profile1", "profile2", "profile3")
METAL_CODES = ("XAU", "XAG")
MAX_ROWS_PER_SECTION = 10_000
MAX_NAME_LENGTH = 64
# Preferences that make sense on every device. Theme, language, start tab,
# window/tray behaviour and similar settings stay personal to each device.
SHARED_PREFERENCE_KEYS = ("precision", "currency_codes", "calculator_extra_currency")


class BackupError(Exception):
    """Base class; the message is already translated and safe to show to the user."""


class NotABackupError(BackupError):
    pass


class NewerBackupError(BackupError):
    pass


class PasswordRequiredError(BackupError):
    pass


class WrongPasswordError(BackupError):
    pass


class CorruptBackupError(BackupError):
    pass


class EncryptionUnavailableError(BackupError):
    pass


@dataclass(frozen=True)
class BackupInfo:
    encrypted: bool
    format_version: int
    created_at: str
    app_version: str
    platform: str


@dataclass
class CleanProfile:
    id: str
    name: str
    currency: list[dict[str, Any]] = field(default_factory=list)
    metals: list[dict[str, Any]] = field(default_factory=list)
    stocks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def record_count(self) -> int:
        return len(self.currency) + len(self.metals) + len(self.stocks)


@dataclass
class CleanBackup:
    preferences: dict[str, Any]
    profiles: list[CleanProfile]
    skipped: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- passwords
def password_problem(password: str | None) -> str | None:
    """Why a password cannot be used (None when it is fine)."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return tr("Şifre en az {0} karakter olmalıdır.").format(MIN_PASSWORD_LENGTH)
    return None


def _password_bytes(password: str) -> bytes:
    # NFC so that "ş", "ı", "İ"... give the same bytes on every platform/keyboard.
    return unicodedata.normalize("NFC", password).encode("utf-8")


def derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", _password_bytes(password), salt, iterations, dklen=KEY_BYTES)


def _aad(version: int) -> bytes:
    # Binds the ciphertext to the format and version it was written for.
    return f"{FORMAT}/{version}".encode("utf-8")


def _aesgcm_class():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:  # unencrypted backups keep working without it
        raise EncryptionUnavailableError(
            tr("Şifreleme bileşeni bulunamadı; şifreli yedek bu kurulumda kullanılamıyor.")
        ) from exc
    return AESGCM


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: object) -> bytes:
    try:
        return base64.b64decode(str(text), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CorruptBackupError(tr("Yedek dosyası bozuk.")) from exc


# --------------------------------------------------------------- writing
def payload_to_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def utc_timestamp(moment: datetime | None = None) -> str:
    return (moment or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_backup(
    payload: dict[str, Any],
    *,
    password: str | None = None,
    app_version: str,
    platform_name: str = "windows",
    now: datetime | None = None,
    salt: bytes | None = None,
    nonce: bytes | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> bytes:
    """Serialise ``payload`` into a backup file; encrypted when a password is given.

    ``salt``/``nonce`` exist only so the published test vectors are reproducible;
    real backups always use fresh random values.
    """
    text = payload_to_text(payload)
    envelope: dict[str, Any] = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "created_at": utc_timestamp(now),
        "app_version": str(app_version),
        "platform": str(platform_name),
    }
    if not password:
        envelope["encrypted"] = False
        envelope["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        envelope["payload"] = text
    else:
        problem = password_problem(password)
        if problem:
            raise BackupError(problem)
        salt = salt or os.urandom(SALT_BYTES)
        nonce = nonce or os.urandom(NONCE_BYTES)
        key = derive_key(password, salt, iterations)
        ciphertext = _aesgcm_class()(key).encrypt(nonce, text.encode("utf-8"), _aad(FORMAT_VERSION))
        envelope["encrypted"] = True
        envelope["kdf"] = {"name": "PBKDF2-HMAC-SHA256", "iterations": iterations, "salt": _b64(salt)}
        envelope["cipher"] = {"name": "AES-256-GCM", "nonce": _b64(nonce)}
        envelope["payload"] = _b64(ciphertext)  # ciphertext followed by the 16-byte tag
    return json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")


# --------------------------------------------------------------- reading
def _parse_envelope(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_FILE_BYTES:
        raise NotABackupError(tr("Bu dosya bir FinanceTerminal yedeği değil."))
    try:
        envelope = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NotABackupError(tr("Bu dosya bir FinanceTerminal yedeği değil.")) from exc
    if not isinstance(envelope, dict) or envelope.get("format") != FORMAT:
        raise NotABackupError(tr("Bu dosya bir FinanceTerminal yedeği değil."))
    version = envelope.get("format_version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise CorruptBackupError(tr("Yedek dosyası bozuk."))
    if version > FORMAT_VERSION:
        raise NewerBackupError(
            tr("Bu yedek FinanceTerminal'in daha yeni bir sürümüyle oluşturulmuş. Uygulamayı güncelleyip tekrar deneyin.")
        )
    return envelope


def inspect_backup(data: bytes) -> BackupInfo:
    """Read the header only (works for encrypted files without a password)."""
    envelope = _parse_envelope(data)
    return BackupInfo(
        encrypted=bool(envelope.get("encrypted")),
        format_version=int(envelope["format_version"]),
        created_at=str(envelope.get("created_at") or ""),
        app_version=str(envelope.get("app_version") or ""),
        platform=str(envelope.get("platform") or ""),
    )


def read_backup(data: bytes, password: str | None = None) -> tuple[BackupInfo, dict[str, Any]]:
    """Verify and decode a backup; returns (header, raw payload dictionary)."""
    envelope = _parse_envelope(data)
    info = inspect_backup(data)
    raw = envelope.get("payload")
    if not isinstance(raw, str):
        raise CorruptBackupError(tr("Yedek dosyası bozuk."))

    if not info.encrypted:
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != str(envelope.get("sha256", "")).lower():
            raise CorruptBackupError(tr("Yedek dosyası bozuk (sağlama toplamı uyuşmuyor)."))
        text = raw
    else:
        if not password:
            raise PasswordRequiredError(tr("Bu yedek şifreli; şifreyi girin."))
        kdf = envelope.get("kdf") if isinstance(envelope.get("kdf"), dict) else {}
        cipher = envelope.get("cipher") if isinstance(envelope.get("cipher"), dict) else {}
        iterations = kdf.get("iterations")
        if (
            kdf.get("name") != "PBKDF2-HMAC-SHA256" or cipher.get("name") != "AES-256-GCM"
            or isinstance(iterations, bool) or not isinstance(iterations, int)
            or not MIN_ITERATIONS <= iterations <= MAX_ITERATIONS
        ):
            raise CorruptBackupError(tr("Yedek dosyası bozuk."))
        salt, nonce, ciphertext = _unb64(kdf.get("salt")), _unb64(cipher.get("nonce")), _unb64(raw)
        if len(nonce) != NONCE_BYTES or len(salt) < 8 or len(ciphertext) < 16:
            raise CorruptBackupError(tr("Yedek dosyası bozuk."))
        aesgcm = _aesgcm_class()
        from cryptography.exceptions import InvalidTag

        try:
            plain = aesgcm(derive_key(password, salt, iterations)).decrypt(nonce, ciphertext, _aad(info.format_version))
            text = plain.decode("utf-8")
        except InvalidTag as exc:
            raise WrongPasswordError(tr("Şifre yanlış ya da dosya bozulmuş.")) from exc
        except UnicodeDecodeError as exc:
            raise CorruptBackupError(tr("Yedek dosyası bozuk.")) from exc

    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise CorruptBackupError(tr("Yedek dosyası bozuk.")) from exc
    if not isinstance(payload, dict):
        raise CorruptBackupError(tr("Yedek dosyasındaki veri beklenen biçimde değil."))
    return info, payload


# ------------------------------------------------------------ validation
_DECIMAL_TEXT = re.compile(r"[+-]?\d+(?:\.\d+)?")


def canonical_decimal(value: object) -> Decimal | None:
    """Parse a plain decimal ("75.50"); None when it is anything else.

    The format never uses locale-dependent separators, so "1.250" means 1.25 here
    (unlike the lenient parser used for typed input).
    """
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip()
    if not _DECIMAL_TEXT.fullmatch(text):
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def plain(number: Decimal) -> str:
    """Decimal as plain text, never scientific notation ("1E+3" -> "1000")."""
    return format(number, "f")


def _clean_rows(rows: object, section: str, profile_id: str, kind: str, skipped: list[str]) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if not isinstance(rows, list):
        skipped.append(tr("{0} / {1}: bir satır atlandı — {2}").format(profile_id, section, tr("satır okunamadı")))
        return []
    if len(rows) > MAX_ROWS_PER_SECTION:
        skipped.append(tr("{0} / {1}: bir satır atlandı — {2}").format(
            profile_id, section, tr("çok fazla kayıt (en çok {0})").format(MAX_ROWS_PER_SECTION)))
        rows = rows[:MAX_ROWS_PER_SECTION]

    def skip(reason: str) -> None:
        skipped.append(tr("{0} / {1}: bir satır atlandı — {2}").format(profile_id, section, reason))

    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            skip(tr("satır okunamadı"))
            continue
        if kind == "stock":
            try:
                code = normalize_symbol(row.get("symbol"))
            except ValueError:
                skip(tr("desteklenmeyen kod: {0}").format(row.get("symbol")))
                continue
            cost_key = "average_cost"
        else:
            code = str(row.get("code", "")).strip().upper()
            allowed = set(CURRENCY_INFO) if kind == "currency" else set(METAL_CODES)
            if code not in allowed:
                skip(tr("desteklenmeyen kod: {0}").format(row.get("code")))
                continue
            cost_key = "average_cost_try"
        quantity = canonical_decimal(row.get("quantity"))
        cost = canonical_decimal(row.get(cost_key))
        if quantity is None or quantity <= 0:
            skip(tr("geçersiz miktar"))
            continue
        if cost is None or cost < 0:
            skip(tr("geçersiz ortalama maliyet"))
            continue
        if code in seen:
            skip(tr("aynı kod birden fazla kez geçiyor: {0}").format(code))
            continue
        seen.add(code)
        item: dict[str, Any] = {"quantity": quantity, cost_key: cost}
        if kind == "stock":
            item["symbol"] = code
            for key in ("company", "sector", "notes"):
                item[key] = str(row.get(key) or "").strip()[:500]
        else:
            item["code"] = code
        cleaned.append(item)
    return cleaned


def validate_payload(payload: object) -> CleanBackup:
    """Turn untrusted payload data into safe values; bad rows are skipped, not fatal."""
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), list):
        raise CorruptBackupError(tr("Yedek dosyasındaki veri beklenen biçimde değil."))

    skipped: list[str] = []
    profiles: list[CleanProfile] = []
    for entry in payload["profiles"]:
        if not isinstance(entry, dict):
            continue
        profile_id = str(entry.get("id", "")).strip().lower()
        if profile_id not in PROFILE_IDS or any(p.id == profile_id for p in profiles):
            continue
        name = str(entry.get("name") or "").strip()[:MAX_NAME_LENGTH]
        profiles.append(CleanProfile(
            id=profile_id,
            name=name,
            currency=_clean_rows(entry.get("currency"), "currency", profile_id, "currency", skipped),
            metals=_clean_rows(entry.get("metals"), "metals", profile_id, "metal", skipped),
            stocks=_clean_rows(entry.get("stocks"), "stocks", profile_id, "stock", skipped),
        ))

    return CleanBackup(
        preferences=_clean_preferences(payload.get("preferences")),
        profiles=profiles,
        skipped=skipped,
    )


def _clean_preferences(raw: object) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    if not isinstance(raw, dict):
        return clean
    precision = raw.get("precision")
    if isinstance(precision, int) and not isinstance(precision, bool) and 0 <= precision <= 6:
        clean["precision"] = precision
    codes = raw.get("currency_codes")
    if isinstance(codes, list):
        supported = [str(code).strip().upper() for code in codes if str(code).strip().upper() in CURRENCY_INFO]
        if supported:
            clean["currency_codes"] = sort_currency_codes(supported)
    extra = str(raw.get("calculator_extra_currency") or "").strip().upper()
    if extra in currency_choices(exclude=("USD", "EUR")):
        clean["calculator_extra_currency"] = extra
    return clean
