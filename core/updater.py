from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
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
USER_AGENT = "FinanceTerminal-Updater/1.1"
DOWNLOAD_CHUNK_SIZE = 512 * 1024


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


def download_release_asset(
    info: ReleaseInfo,
    timeout: int = 30,
    progress_callback: Callable[[int, int, float], None] | None = None,
) -> Path:
    """Download and verify the release EXE; optionally report bytes and average speed."""
    request = Request(
        info.download_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
    )
    digest = hashlib.sha256()
    fd, temp_name = tempfile.mkstemp(prefix=f"FinanceTerminal_{info.version}_", suffix=".exe")
    temp_path = Path(temp_name)
    total = 0
    started_at = time.monotonic()
    try:
        if progress_callback is not None:
            progress_callback(0, info.asset_size, 0.0)
        with os.fdopen(fd, "wb") as output:
            with urlopen(request, timeout=timeout) as response:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES or total > info.asset_size:
                        raise UpdateError("İndirilen dosya beklenen boyutu aşıyor.")
                    digest.update(chunk)
                    output.write(chunk)
                    if progress_callback is not None:
                        elapsed = max(time.monotonic() - started_at, 0.001)
                        progress_callback(total, info.asset_size, total / elapsed)
            output.flush()
            os.fsync(output.fileno())

        if total != info.asset_size:
            raise UpdateError(
                f"İndirilen dosyanın boyutu uyuşmuyor (beklenen {info.asset_size}, gelen {total})."
            )
        with temp_path.open("rb") as downloaded:
            if downloaded.read(2) != b"MZ":
                raise UpdateError("İndirilen dosya geçerli bir Windows EXE dosyası değil.")
        if info.digest and digest.hexdigest().lower() != info.digest.lower():
            raise UpdateError("İndirilen dosyanın SHA-256 doğrulaması başarısız.")
        if progress_callback is not None:
            elapsed = max(time.monotonic() - started_at, 0.001)
            progress_callback(total, info.asset_size, total / elapsed)
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


def launch_windows_update_helper(
    downloaded_exe: Path,
    executable: Path,
    expected_size: int | None = None,
) -> None:
    """Launch a detached helper that waits for both PyInstaller one-file processes.

    PyInstaller one-file builds use a bootloader parent and a Python child process.
    Waiting for only os.getpid() can leave the parent holding the EXE open.
    """
    if os.name != "nt":
        raise UpdateError("Otomatik EXE değiştirme yalnızca Windows'ta kullanılabilir.")
    ensure_install_directory_writable(executable)

    def ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    size_literal = int(expected_size or downloaded_exe.stat().st_size)
    target_pid = os.getpid()
    parent_pid = os.getppid()
    pids = sorted({pid for pid in (target_pid, parent_pid) if isinstance(pid, int) and pid > 0})
    pid_array = ", ".join(str(pid) for pid in pids)

    script = f"""$ErrorActionPreference = 'Stop'
$targetProcessIds = @({pid_array})
$source = {ps_quote(str(downloaded_exe.resolve()))}
$destination = {ps_quote(str(executable.resolve()))}
$expectedSize = {size_literal}
$installDirectory = Split-Path -Parent $destination
$staged = $destination + '.new'
$backup = $destination + '.previous-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff')
$logDirectory = Join-Path $env:APPDATA 'FinanceTerminal\\logs'
if ([string]::IsNullOrWhiteSpace($env:APPDATA)) {{ $logDirectory = Join-Path $env:TEMP 'FinanceTerminal\\logs' }}
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$logPath = Join-Path $logDirectory 'updater.log'
function Write-UpdateLog([string]$message) {{
    $line = ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + $message)
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}}
$backupCreated = $false
$updateSucceeded = $false
try {{
    Write-UpdateLog ('Güncelleme yardımcısı başladı. Hedef: ' + $destination)
    if (!(Test-Path -LiteralPath $source -PathType Leaf)) {{ throw 'İndirilen geçici EXE bulunamadı.' }}
    $sourceInfo = Get-Item -LiteralPath $source
    if ($sourceInfo.Length -ne $expectedSize) {{ throw ('İndirilen EXE boyutu uyuşmuyor. Beklenen: ' + $expectedSize + ', bulunan: ' + $sourceInfo.Length) }}

    if (Test-Path -LiteralPath $staged) {{ Remove-Item -LiteralPath $staged -Force }}
    Copy-Item -LiteralPath $source -Destination $staged -Force
    $stagedInfo = Get-Item -LiteralPath $staged
    if ($stagedInfo.Length -ne $expectedSize) {{ throw 'Kurulum klasörüne kopyalanan EXE boyut doğrulamasından geçemedi.' }}
    $fileStream = [System.IO.File]::OpenRead($staged)
    try {{
        $header = New-Object byte[] 2
        if ($fileStream.Read($header, 0, 2) -ne 2 -or $header[0] -ne 77 -or $header[1] -ne 90) {{ throw 'Yeni dosya geçerli bir Windows EXE değil (MZ imzası yok).' }}
    }} finally {{ $fileStream.Dispose() }}
    Write-UpdateLog 'Yeni EXE geçici kurulum dosyasına kopyalandı ve doğrulandı.'

    # Wait for both the Python child and PyInstaller one-file bootloader parent.
    $deadline = (Get-Date).AddSeconds(90)
    foreach ($appProcessId in $targetProcessIds) {{
        while (Get-Process -Id $appProcessId -ErrorAction SilentlyContinue) {{
            if ((Get-Date) -gt $deadline) {{ throw ('Uygulama işlemi kapanmadı (PID ' + $appProcessId + ').') }}
            Start-Sleep -Milliseconds 400
        }}
    }}
    # Give the Windows loader and PyInstaller bootloader time to release the image file.
    Start-Sleep -Seconds 2
    Write-UpdateLog 'Uygulamanın iki süreci de kapandı; EXE değiştiriliyor.'

    $replaceDeadline = (Get-Date).AddSeconds(60)
    $lastReplaceError = ''
    while ((Get-Date) -lt $replaceDeadline) {{
        try {{
            [System.IO.File]::Replace($staged, $destination, $backup, $true)
            $backupCreated = $true
            break
        }} catch {{
            $lastReplaceError = $_.Exception.Message
            Start-Sleep -Milliseconds 750
        }}
    }}
    if (!$backupCreated) {{ throw ('Eski EXE değiştirilemedi. Son hata: ' + $lastReplaceError) }}
    Write-UpdateLog 'Yeni EXE hedef konuma atomik olarak yerleştirildi; eski dosya yedeklendi.'

    Remove-Item -LiteralPath $source -Force -ErrorAction SilentlyContinue
    $newProcess = Start-Process -FilePath $destination -WorkingDirectory $installDirectory -PassThru
    Start-Sleep -Seconds 10
    $newProcess.Refresh()
    if ($newProcess.HasExited) {{
        throw ('Yeni sürüm başlatıldıktan hemen sonra kapandı. Çıkış kodu: ' + $newProcess.ExitCode)
    }}
    Write-UpdateLog 'Yeni FinanceTerminal süreci çalışır durumda; güncelleme başarılı.'
    $updateSucceeded = $true
    Start-Sleep -Seconds 2
    Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
}} catch {{
    $errorMessage = $_.Exception.Message
    Write-UpdateLog ('GÜNCELLEME HATASI: ' + $errorMessage)
    if ($backupCreated -and (Test-Path -LiteralPath $backup)) {{
        try {{
            if (Test-Path -LiteralPath $destination) {{ Remove-Item -LiteralPath $destination -Force }}
            [System.IO.File]::Move($backup, $destination)
            Write-UpdateLog 'Geri alma başarılı; önceki EXE geri yüklendi.'
            Start-Process -FilePath $destination -WorkingDirectory $installDirectory
        }} catch {{
            Write-UpdateLog ('GERİ ALMA HATASI: ' + $_.Exception.Message)
        }}
    }}
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    [System.Windows.Forms.MessageBox]::Show(
        ('FinanceTerminal güncellenemedi. Önceki sürüm korunmaya/geri yüklenmeye çalışıldı.' + [Environment]::NewLine + [Environment]::NewLine + $errorMessage + [Environment]::NewLine + [Environment]::NewLine + 'Ayrıntılı günlük: ' + $logPath),
        'FinanceTerminal güncelleme hatası',
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
}} finally {{
    if (Test-Path -LiteralPath $staged) {{ Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue }}
    if ($updateSucceeded) {{ Write-UpdateLog 'Güncelleme yardımcısı tamamlandı.' }}
}}
Start-Sleep -Seconds 1
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
"""

    script_fd, script_name = tempfile.mkstemp(prefix="FinanceTerminal_Update_", suffix=".ps1")
    script_path = Path(script_name)
    with os.fdopen(script_fd, "w", encoding="utf-8-sig") as script_file:
        script_file.write(script)

    
    # Create the log directory before starting PowerShell.
    log_root = Path(os.environ.get("APPDATA") or tempfile.gettempdir())
    log_directory = log_root / "FinanceTerminal" / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / "updater.log"

    def write_launcher_log(message: str) -> None:
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] {message}\n")
        except OSError:
            pass

    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    powershell_path = (
        system_root
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )

    powershell_command = (
        str(powershell_path)
        if powershell_path.is_file()
        else "powershell.exe"
    )

    command = [
        powershell_command,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]

    # Use CREATE_NO_WINDOW without DETACHED_PROCESS.
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    write_launcher_log(
        "Python güncelleyici PowerShell yardımcısını başlatıyor."
    )

    try:
        helper_process = subprocess.Popen(
            command,
            cwd=str(executable.parent),
            close_fds=True,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        write_launcher_log(
            f"PowerShell yardımcısı başlatılamadı: {exc}"
        )
        script_path.unlink(missing_ok=True)
        raise UpdateError(
            f"Güncelleme yardımcısı başlatılamadı: {exc}"
        ) from exc

    write_launcher_log(
        f"PowerShell yardımcısı başlatıldı. PID: {helper_process.pid}"
    )

    time.sleep(0.75)
    exit_code = helper_process.poll()

    if exit_code is not None:
        write_launcher_log(
            f"PowerShell yardımcısı erken kapandı. Çıkış kodu: {exit_code}"
        )
        raise UpdateError(
            "Güncelleme yardımcısı başlatıldı ancak hemen kapandı. "
            f"Ayrıntılı günlük: {log_path}"
        )
