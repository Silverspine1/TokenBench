import zipfile
from pathlib import Path

import pytest

from tokenbench.manual.bundles import _is_unsafe_member, safe_extract


def test_unsafe_member_detection():
    assert _is_unsafe_member("../escape.txt")
    assert _is_unsafe_member("a/../../escape.txt")
    assert _is_unsafe_member("/etc/passwd")
    assert _is_unsafe_member("C:/Windows/x")
    assert _is_unsafe_member("C:\\Windows\\x")
    assert not _is_unsafe_member("workspace/demo/app.py")
    assert not _is_unsafe_member("a/b/c.txt")


def test_safe_extract_rejects_traversal_zip(tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("workspace/ok.txt", "fine")
        zf.writestr("../escape.txt", "evil")

    dest = tmp_path / "out"
    with pytest.raises(ValueError):
        safe_extract(bad, dest)
    # Nothing was extracted outside the destination.
    assert not (tmp_path / "escape.txt").exists()


def test_safe_extract_accepts_clean_zip(tmp_path):
    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("workspace/demo/app.py", "x")
    dest = tmp_path / "out"
    safe_extract(good, dest)
    assert (dest / "workspace" / "demo" / "app.py").exists()
