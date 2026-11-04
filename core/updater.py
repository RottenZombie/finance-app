from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


GITHUB_OWNER = "RottenZombie"
GITHUB_REPOSITORY = "finance-app"
LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases/latest"
)
EXPECTED_ASSET_NAME = "FinanceTerminal.exe"
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
USER_AGENT = "FinanceTerminal-Updater/1.0"


class UpdateError(RuntimeError):
    """Raised when release metadata or an update file cannot be trusted/applied."""


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    version: str
    release_url: str
    download_url: str
    asset_size: int
    digest: str | None
    release_notes: str = ""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(
        r"\s*v?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\s*",
        str(value),
        re.IGNORECASE,
    )
    if not match:
        raise UpdateError(f"Geçersiz sürüm numarası: {value}")
    return tuple(int(part) for part in match.groups())


def is_newer_version(current_version: str, latest_version: str) -> bool:
    """Compare stable numeric version parts, ignoring a local '-dev' suffix."""
    return _version_tuple(latest_version) > _version_tuple(current_version)


def parse_release_payload(payload: dict, current_version: str) -> ReleaseInfo | None:
    if not isinstance(payload, dict):
        raise UpdateError("GitHub sürüm yanıtı beklenen biçimde değil.")
    if payload.get("draft") or payload.get("prerelease"):
        return None

    tag_name = str(payload.get("tag_name") or "").strip()
    version = tag_name.lstrip("vV")
    if not version:
        raise UpdateError("GitHub sürüm etiketi bulunamadı.")
    if not is_newer_version(current_version, version):
        return None

    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("GitHub sürümünde indirilebilir dosya listesi bulunamadı.")

    asset = next(
        (item for item in assets if isinstance(item, dict)
         and str(item.get("name", "")).casefold() == EXPECTED_ASSET_NAME.casefold()),
        None,
    )
    if asset is None:
        raise UpdateError(
            f"Yeni sürüm {version} bulundu ancak {EXPECTED_ASSET_NAME} dosyası eklenmemiş."
        )

    download_url = str(asset.get("browser_download_url") or "")
    parsed_url = urlparse(download_url)
    expected_download_prefix = f"/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases/download/"
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "github.com"
        or not parsed_url.path.startswith(expected_download_prefix)
    ):
        raise UpdateError("Güncelleme bağlantısı beklenen GitHub depo adresinden gelmiyor.")

    try:
        asset_size = int(asset.get("size", 0))
    except (TypeError, ValueError):
        asset_size = 0
    if asset_size < 1024 or asset_size > MAX_DOWNLOAD_BYTES:
        raise UpdateError("Güncelleme dosyasının boyutu geçerli aralıkta değil.")

    digest = asset.get("digest")
    if isinstance(digest, str) and digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1].strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            digest = None
    else:
        digest = None

    release_url = str(payload.get("html_url") or "")
    release_path_prefix = f"/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases"
    parsed_release_url = urlparse(release_url)
    if (
        parsed_release_url.scheme != "https"
        or parsed_release_url.hostname != "github.com"
        or not parsed_release_url.path.startswith(release_path_prefix)
    ):
        release_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases"

    return ReleaseInfo(
        tag_name=tag_name,
        version=version,
        release_url=release_url,
        download_url=download_url,
        asset_size=asset_size,
        digest=digest,
        release_notes=str(payload.get("body") or "").strip(),
    )


def check_latest_release(current_version: str, timeout: int = 12) -> ReleaseInfo | None:
    request = Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise UpdateError(f"GitHub güncelleme kontrolü başarısız (HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise UpdateError("Güncelleme sunucusuna ulaşılamadı. İnternet bağlantınızı kontrol edin.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("GitHub'dan gelen sürüm bilgisi okunamadı.") from exc
    return parse_release_payload(payload, current_version)


def download_release_asset(info: ReleaseInfo, timeout: int = 30) -> Path:
    """Download the release EXE to a temporary file and validate it before use."""
    request = Request(
        info.download_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
    )
    digest = hashlib.sha256()
    fd, temp_name = tempfile.mkstemp(prefix=f"FinanceTerminal_{info.version}_", suffix=".exe")
    temp_path = Path(temp_name)
    total = 0
    try:
        with os.fdopen(fd, "wb") as output:
            with urlopen(request, timeout=timeout) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES or total > info.asset_size:
                        raise UpdateError("İndirilen dosya beklenen boyutu aşıyor.")
                    digest.update(chunk)
                    output.write(chunk)
        if total != info.asset_size:
            raise UpdateError(
                f"İndirilen dosyanın boyutu uyuşmuyor (beklenen {info.asset_size}, gelen {total})."
            )
        with temp_path.open("rb") as downloaded:
            if downloaded.read(2) != b"MZ":
                raise UpdateError("İndirilen dosya geçerli bir Windows EXE dosyası değil.")
        if info.digest and digest.hexdigest().lower() != info.digest.lower():
            raise UpdateError("İndirilen dosyanın SHA-256 doğrulaması başarısız.")
        return temp_path
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def current_executable_path() -> Path:
    if not getattr(sys, "frozen", False):
        raise UpdateError("Otomatik kurulum yalnızca yayımlanmış Windows EXE sürümünde kullanılabilir.")
    executable = Path(sys.executable).resolve()
    if executable.suffix.lower() != ".exe" or not executable.is_file():
        raise UpdateError("Çalışan FinanceTerminal.exe yolu belirlenemedi.")
    return executable


def ensure_install_directory_writable(executable: Path) -> None:
    directory = executable.parent
    try:
        fd, probe = tempfile.mkstemp(prefix=".financeterminal_write_test_", dir=str(directory))
        os.close(fd)
        Path(probe).unlink(missing_ok=True)
    except OSError as exc:
        raise UpdateError(
            "Uygulamanın bulunduğu klasöre yazma izni yok. EXE'yi yazma izniniz olan "
            "bir klasöre taşıyın veya güncellemeyi GitHub'dan elle indirin."
        ) from exc


def launch_windows_update_helper(downloaded_exe: Path, executable: Path) -> None:
    """Start a detached PowerShell helper which waits for this app to exit, replaces it and restarts it."""
    if os.name != "nt":
        raise UpdateError("Otomatik EXE değiştirme yalnızca Windows'ta kullanılabilir.")
    ensure_install_directory_writable(executable)

    def ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    script = f"""$ErrorActionPreference = 'Stop'
$targetPid = {os.getpid()}
$source = {ps_quote(str(downloaded_exe.resolve()))}
$destination = {ps_quote(str(executable.resolve()))}
$staged = $destination + '.new'
try {{
    while (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) {{ Start-Sleep -Milliseconds 500 }}
    Copy-Item -LiteralPath $source -Destination $staged -Force
    Move-Item -LiteralPath $staged -Destination $destination -Force
    Remove-Item -LiteralPath $source -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $destination
}} catch {{
    Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue
    [System.Windows.MessageBox]::Show(
        ('FinanceTerminal güncellenemedi. Eski sürüm korunmuştur.`n`n' + $_.Exception.Message),
        'FinanceTerminal güncelleme hatası'
    ) | Out-Null
    if (Test-Path -LiteralPath $staged) {{ Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue }}
}}
Start-Sleep -Seconds 2
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
"""
    script_fd, script_name = tempfile.mkstemp(prefix="FinanceTerminal_Update_", suffix=".ps1")
    script_path = Path(script_name)
    with os.fdopen(script_fd, "w", encoding="utf-8-sig") as script_file:
        script_file.write(script)

    creationflags = 0
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    try:
        subprocess.Popen(
            [
                "powershell.exe", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
                "-File", str(script_path),
            ],
            close_fds=True,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        script_path.unlink(missing_ok=True)
        raise UpdateError(f"Güncelleme yardımcısı başlatılamadı: {exc}") from exc
