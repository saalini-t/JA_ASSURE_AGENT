"""
Robust, cross-machine FFmpeg/ffprobe executable discovery.

Why this exists: shutil.which() only searches the CURRENT PROCESS's inherited PATH
environment variable. On Windows, installing FFmpeg via `winget install Gyan.FFmpeg`
updates the PATH registry key, but any already-running process (a backend server
started before the install, an IDE's integrated terminal, a service) keeps its OLD
PATH snapshot until restarted -- so `where.exe ffmpeg` in a fresh terminal succeeding
does NOT guarantee the backend process itself can see it. This module adds a
Windows-specific fallback search so the backend doesn't depend on every process
happening to be started after PATH was refreshed.

Resolution order (first match wins) -- see resolve_ffmpeg()/resolve_ffprobe():
1. Explicit env var override (FFMPEG_PATH / FFPROBE_PATH), validated to exist.
2. Normal PATH lookup (shutil.which) -- always tried first among discovery methods.
3. Windows only: well-known FFmpeg install locations, found via glob patterns rooted
   at %LOCALAPPDATA%/%ProgramFiles%/etc -- NEVER a hard-coded username or a specific
   FFmpeg version/build hash, so this works on any machine/any WinGet update.

Never silently substitutes a fake/placeholder path: if nothing resolves,
resolve_ffmpeg()/resolve_ffprobe() raise FFmpegNotFoundError with the exact list of
locations checked and how to fix it (install, or set the *_PATH env var).
"""
import glob
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("ja_assure.video.ffmpeg_locator")


class FFmpegNotFoundError(Exception):
    def __init__(self, base_name: str, checked: List[str]):
        self.base_name = base_name
        self.checked = checked
        env_var = f"{base_name.upper()}_PATH"
        checked_list = "\n".join(f"  - {c}" for c in checked) if checked else "  (nothing to check)"
        message = (
            f"Could not locate '{base_name}' on this machine.\n"
            f"Checked:\n{checked_list}\n\n"
            f"Fix options:\n"
            f"  1. Install FFmpeg and restart your terminal/IDE so PATH updates take effect:\n"
            f"     Windows: winget install Gyan.FFmpeg\n"
            f"     macOS:   brew install ffmpeg\n"
            f"     Linux:   apt install ffmpeg\n"
            f"  2. Or set {env_var} to the full path of your {base_name} executable "
            f"(e.g. in backend/.env)."
        )
        super().__init__(message)


def _is_executable_file(path: Optional[str]) -> bool:
    if not path:
        return False
    p = Path(path)
    if not p.is_file():
        return False
    # os.access(X_OK) is not a reliable executable-bit check on Windows (there is no
    # POSIX exec bit), but it's harmless there and meaningful on macOS/Linux.
    return os.access(str(p), os.X_OK)


def _binary_filename(base_name: str) -> str:
    return f"{base_name}.exe" if os.name == "nt" else base_name


def _windows_install_candidates(filename: str) -> List[str]:
    """
    Glob-based search of common Windows FFmpeg install locations. Every root comes
    from an environment variable that Windows sets per-user/per-machine
    (%LOCALAPPDATA%, %ProgramFiles%, %ProgramFiles(x86)%) -- never a literal
    "C:\\Users\\<name>\\..." path -- and every WinGet package/version/build-hash
    segment is a `*` wildcard, so this survives FFmpeg version bumps and works
    identically on any machine.
    """
    if os.name != "nt":
        return []

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "C:/Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")

    patterns: List[str] = []
    if local_app_data:
        # Covers Gyan.FFmpeg, BtbN.FFmpeg.GPL*, and similar WinGet-packaged builds,
        # regardless of version/build-hash in the package or extracted-folder name.
        patterns.append(f"{local_app_data}/Microsoft/WinGet/Packages/*ffmpeg*/**/{filename}")
        # WinGet's shim/link directory -- normally already on PATH, checked here too
        # as a cheap defensive extra in case PATH propagation itself is the problem.
        patterns.append(f"{local_app_data}/Microsoft/WinGet/Links/{filename}")
    patterns.append(f"{program_files}/ffmpeg/bin/{filename}")
    patterns.append(f"{program_files}/FFmpeg/bin/{filename}")
    patterns.append(f"{program_files_x86}/ffmpeg/bin/{filename}")
    patterns.append(f"C:/ffmpeg/bin/{filename}")

    matches: List[str] = []
    for pattern in patterns:
        try:
            matches.extend(glob.glob(pattern, recursive=True))
        except Exception:
            continue
    return matches


def _get_imageio_ffmpeg_exe() -> Optional[str]:
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if _is_executable_file(exe):
            return exe
    except Exception:
        pass
    return None


def _resolve(base_name: str) -> str:
    env_var = f"{base_name.upper()}_PATH"
    checked: List[str] = []

    # 1. Explicit environment variable override
    configured = os.environ.get(env_var)
    if configured:
        checked.append(f"env var {env_var}={configured}")
        if _is_executable_file(configured):
            return str(Path(configured).resolve())
        logger.warning(f"{env_var} is set to '{configured}' but that file doesn't exist or isn't executable.")

    # 2. Normal PATH lookup (shutil.which is PATHEXT-aware on Windows already,
    # so plain "ffmpeg" correctly finds "ffmpeg.exe" without extra handling here)
    which_result = shutil.which(base_name)
    checked.append(f"PATH lookup for '{base_name}'")
    if which_result and _is_executable_file(which_result):
        return str(Path(which_result).resolve())

    # 3. imageio_ffmpeg package lookup (for ffmpeg)
    if base_name == "ffmpeg":
        imgio_exe = _get_imageio_ffmpeg_exe()
        if imgio_exe:
            checked.append(f"imageio_ffmpeg: {imgio_exe}")
            return str(Path(imgio_exe).resolve())

    # 4. Windows-only fallback: known install locations, globbed (no hard-coded paths)
    filename = _binary_filename(base_name)
    for candidate in _windows_install_candidates(filename):
        checked.append(candidate)
        if _is_executable_file(candidate):
            return str(Path(candidate).resolve())

    raise FFmpegNotFoundError(base_name, checked)


def resolve_ffmpeg() -> str:
    path = _resolve("ffmpeg")
    logger.info(f"FFmpeg: {path}")
    return path


def resolve_ffprobe() -> str:
    path = _resolve("ffprobe")
    logger.info(f"FFprobe: {path}")
    return path


