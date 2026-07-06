#!/usr/bin/env python3
"""Python wrapper around the PHP reorg smoke test.

Locates a PHP binary (env PHP -> PATH -> known WinGet path), runs the PHP
smoke script with the workspace root as cwd, streams its stdout, and exits with
the PHP process's return code.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE_ROOT = HERE.parent
PHP_SCRIPT = HERE / "run_reorg_smoke.php"

_KNOWN_PHP = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Microsoft", "WinGet", "Packages",
    "PHP.PHP.8.3_Microsoft.Winget.Source_8wekyb3d8bbwe", "php.exe",
)


def find_php() -> str:
    for cand in (os.environ.get("PHP"), "php", _KNOWN_PHP):
        if not cand:
            continue
        found = shutil.which(cand)
        if found:
            return found
        if Path(cand).exists():
            return cand
    return ""


def main() -> int:
    php = find_php()
    if not php:
        sys.stderr.write("php binary not found\n")
        return 2
    proc = subprocess.run([php, str(PHP_SCRIPT)], cwd=str(WORKSPACE_ROOT))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
