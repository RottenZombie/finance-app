# FinanceTerminal backup file format (`.ftbackup`), version 1

This document is the contract between every FinanceTerminal application: the
Windows desktop app today, and the iOS, Android and HarmonyOS apps later. A backup
written by one of them **must** be readable by all of them, in either direction.
The reference implementation is `core/backup.py` (format, encryption, validation)
and `features/backup_data.py` (reading and restoring the data). If this document and
the code disagree, fix the code or the document in the same change.

## Design rules

- **Portable:** UTF-8 JSON plus SHA-256, PBKDF2-HMAC-SHA256, AES-256-GCM and base64.
  All of these are built into iOS, Android and HarmonyOS.
- **Not a database copy.** The SQLite files are an internal detail of the desktop app.
- **Language independent:** field names are English identifiers; nothing depends on
  the interface language. Excel exports (human readable, localised) are a different feature.
- **Exact numbers:** quantities and prices are plain decimal *strings* (`"75.50"`),
  never floating-point JSON numbers, never locale formats (`"75,50"`, `"1.250,00"`),
  never scientific notation (`1E+3`). `"1.250"` means 1.25.
- **Personal settings are not shared.** Theme, interface language, start tab,
  tray/window behaviour and similar settings stay on each device. Only the *shared
  preferences* listed below travel.
- **Forward compatible:** readers ignore fields they do not know. A reader that meets
  a `format_version` newer than it supports refuses the file with a clear message.

## File

A backup is one UTF-8 JSON object (a UTF-8 BOM is tolerated when reading; do not write one).
Recommended extension `.ftbackup`, media type `application/json`. Maximum accepted size: 16 MiB.

### Envelope (always present)

| Field | Type | Meaning |
| --- | --- | --- |
| `format` | string | Always `"FinanceTerminal.Backup"` |
| `format_version` | integer | `1` |
| `created_at` | string | UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| `app_version` | string | Version of the app that wrote the file (informational) |
| `platform` | string | `windows`, `ios`, `android`, `harmonyos` (informational) |
| `encrypted` | boolean | Whether `payload` is encrypted |
| `payload` | string | See below |

### Unencrypted file (`encrypted: false`)

- `payload` is the **JSON text** of the data object (a string, not a nested object).
- `sha256` is the lowercase hex SHA-256 of the UTF-8 bytes of that exact string.
  Because the checksum covers the string as written, no JSON canonicalisation is
  needed and platforms may serialise the payload however they like. It detects
  accidental damage, not deliberate changes.

### Encrypted file (`encrypted: true`)

Extra fields:

```json
"kdf":    { "name": "PBKDF2-HMAC-SHA256", "iterations": 600000, "salt": "<base64, 16 bytes>" },
"cipher": { "name": "AES-256-GCM", "nonce": "<base64, 12 bytes>" },
"payload": "<base64 of ciphertext followed by the 16-byte GCM tag>"
```

- **Key:** `PBKDF2-HMAC-SHA256(password, salt, iterations, 32 bytes)`.
- **Password bytes:** the password after Unicode **NFC** normalisation, encoded as UTF-8.
  (Turkish letters such as ş, ı, İ can otherwise differ between keyboards and platforms.)
  Minimum length when *creating* a backup: 8 characters.
- **Cipher:** AES-256-GCM, 12-byte random nonce, 128-bit tag appended to the ciphertext.
- **Associated data (AAD):** the UTF-8 bytes of `FinanceTerminal.Backup/<format_version>`,
  i.e. `FinanceTerminal.Backup/1`.
- **Plaintext:** the UTF-8 JSON text of the data object.
- Use a fresh random salt and nonce for every file. `iterations` must be read from the
  file; readers must reject values outside 100 000 – 5 000 000 (protects against
  files crafted to burn CPU). Writers use 600 000.
- A wrong password and a modified file both fail GCM authentication; they cannot be told apart.
- **There is no password recovery.** Nothing is stored anywhere except the file. The
  application warns users about this before creating an encrypted backup.

## Data object

```json
{
  "preferences": {
    "precision": 2,
    "currency_codes": ["USD", "EUR", "SEK"],
    "calculator_extra_currency": "SEK"
  },
  "profiles": [
    {
      "id": "profile1",
      "name": "Main",
      "currency": [ { "code": "USD", "quantity": "100.5", "average_cost_try": "30.25", "updated_at": "2026-01-10T08:00:00+00:00" } ],
      "metals":   [ { "code": "XAU", "quantity": "10", "average_cost_try": "2800" } ],
      "stocks":   [ { "symbol": "ASELS", "company": "Aselsan Elektronik", "quantity": "10",
                      "average_cost": "75.50", "sector": "Defense", "notes": "", "updated_at": "..." } ]
    }
  ]
}
```

### `preferences` (shared preferences, all optional)

| Field | Rule |
| --- | --- |
| `precision` | integer 0–6: decimals shown for amounts |
| `currency_codes` | currencies shown as rate cards; unsupported codes are dropped |
| `calculator_extra_currency` | the calculator's freely chosen currency; any supported code except `USD`/`EUR` |

Anything else in `preferences` (for example a theme or language) is ignored when reading.

### `profiles` (1–3 entries)

- `id`: `profile1`, `profile2` or `profile3` (a profile exists in the file only if it exists on the device; `profile3` is optional). Unknown ids and repeated ids are ignored.
- `name`: display name, at most 64 characters. A name that is still a default (`Profil 1`, `Profile 1`, …) is shown in the reader's own language.
- Each of `currency`, `metals`, `stocks` is a list of at most 10 000 rows.

| Section | Row fields | Rules |
| --- | --- | --- |
| `currency` | `code`, `quantity`, `average_cost_try` | ISO 4217 code from the supported list (`USD`, `EUR`, `SEK`, `RON`, … never `TRY`); quantity > 0; cost ≥ 0 (TRY per unit) |
| `metals` | `code`, `quantity`, `average_cost_try` | `XAU` (gold) or `XAG` (silver); quantity in **grams**; cost = TRY per gram |
| `stocks` | `symbol`, `quantity`, `average_cost`, `company`, `sector`, `notes` | BIST ticker, 2–12 letters/digits; quantity = number of shares; cost = TRY per share |

`updated_at` (ISO 8601 UTC) is informational and may be ignored. **One row per code** within
a section; a repeated code is skipped. Unknown fields in a row are ignored.

## Reading a file

1. Parse the envelope; reject anything that is not `FinanceTerminal.Backup`; reject
   `format_version` greater than the reader supports ("update the app").
2. Verify the checksum, or decrypt (ask for the password only if `encrypted` is true).
3. **Validate before changing anything.** Bad rows (unsupported code, quantity ≤ 0,
   negative cost, malformed number, duplicate code) are skipped and *reported to the
   user*; they never abort the restore. A malformed structure (no `profiles` list) does.
4. Save a safety copy of the device's current data, then apply.

### Restore modes

- **Merge:** every row in the file is added or replaces the row with the same code; rows
  that exist only on the device are kept. Device preferences and profile names are kept
  (a profile that does not exist on the device yet is created with the file's name).
- **Replace:** for each profile *that is in the file*, the device's records are removed
  first and the file's records loaded; the shared preferences and profile names are taken
  from the file. Profiles that are not in the file are left untouched.

There is no automatic two-way synchronisation; the user chooses the mode. A newer
`updated_at` never wins automatically.

## Versioning

- `format_version` changes only for incompatible changes (renamed or removed required
  fields, different cryptography). Adding optional fields does **not** change it.
- A version-1 reader must keep working with files that contain extra fields.
- Test vectors in `docs/test-vectors/` pin the format. They are regenerated with
  `python tools/make_backup_vectors.py`; a unit test fails if the bytes ever change.

## Test vectors

`docs/test-vectors/plain.ftbackup` and `encrypted.ftbackup` hold the same data object.
Parameters of `encrypted.ftbackup`:

| | |
| --- | --- |
| Password (NFC, UTF-8) | `Şifre-123-ığüİ` |
| Salt | `000102030405060708090a0b0c0d0e0f` (hex, 16 bytes) |
| Nonce | `000102030405060708090a0b` (hex, 12 bytes) |
| Iterations | 600 000 |
| Derived key (hex) | `fcc658c5dce27e886bd793530687ee68a6a08f08ddc2bee82e77cade71c79a7c` |

A new implementation is correct when it (1) derives that key, (2) decrypts
`encrypted.ftbackup` to the exact payload text found in `plain.ftbackup`, and (3) writes files
that the reference implementation reads.

## Security notes

- An unencrypted backup contains the user's holdings in clear text; the app says so when
  it is created. An encrypted one is only as strong as its password.
- The password is never stored, logged or sent anywhere.
- Backups never contain API keys, tokens, theme/language settings or file paths.
