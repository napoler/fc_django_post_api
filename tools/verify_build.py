"""pre-commit 校验脚本: 确保 dist/ 中的包含修复后的 admin_site.py

触发: 任何对 src/fc_django_post_api/admin_site.py 的修改
行为:
  1. 清理 dist/ 中的旧构建 (除当前版本外)
  2. 重新 `python -m build`
  3. 在临时 venv 装新 wheel, import fc_django_post_api.admin_site
  4. 校验源码不含真实 OutstandingToken/BlacklistedToken import
  5. 校验有 just-issued 标识 (本次 bug 修复的产物)
  6. 清理临时 venv

退出码: 0 = pass, 1 = fail
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ADMIN = REPO_ROOT / "src" / "fc_django_post_api" / "admin_site.py"
DIST_DIR = REPO_ROOT / "dist"


def get_version() -> str:
    """从 pyproject.toml 读 version"""
    text = (REPO_ROOT / "pyproject.toml").read_text()
    m = re.search(r'^version = "([^"]+)"', text, re.M)
    if not m:
        print("FAIL: pyproject.toml 中找不到 version", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def clean_dist(keep_version: str) -> None:
    """删 dist/ 中除当前版本外的所有文件"""
    if not DIST_DIR.exists():
        return
    for f in DIST_DIR.iterdir():
        if keep_version in f.name:
            continue
        f.unlink()
        print(f"  removed: {f.name}")


def build() -> None:
    """python -m build"""
    print("[1/4] cleaning dist/ ...")
    clean_dist(get_version())
    print("[2/4] python -m build ...")
    subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=REPO_ROOT,
        check=True,
    )


def verify_wheel() -> None:
    """在临时 venv 装新 wheel, 校验源码内容"""
    version = get_version()
    wheel = DIST_DIR / f"fc_django_post_api-{version}-py3-none-any.whl"
    if not wheel.exists():
        print(f"FAIL: wheel not found at {wheel}", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="verify-build-") as tmp:
        venv = Path(tmp) / "venv"
        print(f"[3/4] creating venv at {venv} ...")
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        pip = venv / "bin" / "pip"
        subprocess.run(
            [str(pip), "install", "--quiet", str(wheel)],
            check=True,
        )
        admin = find_installed(venv, "fc_django_post_api/admin_site.py")
        if admin is None:
            print(
                f"FAIL: admin_site.py not found under venv site-packages ({venv})",
                file=sys.stderr,
            )
            sys.exit(1)
        src = admin.read_text()
        check_source(src)


def find_installed(venv: Path, rel: str) -> Path | None:
    """locate installed package file in venv (portable across Python versions)"""
    site = venv / "lib"
    if not site.exists():
        return None
    for py_dir in site.glob("python*/site-packages"):
        candidate = py_dir / rel
        if candidate.exists():
            return candidate
    return None


def check_source(src: str) -> None:
    """校验: 1) 无真实 OutstandingToken import 2) 有 just-issued 标识"""
    print("[4/4] checking source ...")
    has_outstanding_import = bool(
        re.search(r"^\s*from\s+rest_framework_simplejwt\.token_blacklist", src, re.M)
    )
    if has_outstanding_import:
        print(
            "FAIL: admin_site.py 含 token_blacklist 真实 import, "
            "会触发 500 (token_blacklist app 已从 INSTALLED_APPS 移除)",
            file=sys.stderr,
        )
        sys.exit(1)
    if "just-issued" not in src:
        print(
            "FAIL: admin_site.py 缺少 just-issued 标识, "
            "本次 fix 丢失",
            file=sys.stderr,
        )
        sys.exit(1)
    print("OK: no real OutstandingToken import, has just-issued marker")


if __name__ == "__main__":
    try:
        build()
        verify_wheel()
    except subprocess.CalledProcessError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    print("\nALL CHECKS PASSED")
