#!python
"""
sync_workspace.py - Bidirectional Synchronization between D:\\天体物理导论 and mesa_configs

Synchronizes:
1. MESA Inlist templates and run scripts
2. Simulation output logs (LOGS/history.data, profiles.index, profile*.data)
3. Pipeline verification suites and audit logs
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_CONFIGS = REPO_ROOT / "mesa_configs"
REPO_LOGS = REPO_CONFIGS / "LOGS"

D_ROOT = Path(r"D:\天体物理导论")
D_WORK = D_ROOT / "mesa_work"
D_LOGS = D_ROOT / "LOGS"
D_CONFIGS = D_ROOT / "mesa_configs"


def compute_file_hash(path: Path) -> str:
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def sync_file(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and compute_file_hash(src) == compute_file_hash(dst):
        return False  # Already identical
    shutil.copy2(src, dst)
    return True


def sync_directory(src_dir: Path, dst_dir: Path, pattern: str = "*") -> int:
    if not src_dir.exists():
        return 0
    dst_dir.mkdir(parents=True, exist_ok=True)
    synced_count = 0
    for src_file in src_dir.glob(pattern):
        if src_file.is_file():
            dst_file = dst_dir / src_file.name
            if sync_file(src_file, dst_file):
                synced_count += 1
    return synced_count


def sync_tree(src_dir: Path, dst_dir: Path, ignore_dirs: set = None) -> int:
    if not src_dir.exists():
        return 0
    if ignore_dirs is None:
        ignore_dirs = {".git", ".agents", "__pycache__", ".pytest_cache"}
    dst_dir.mkdir(parents=True, exist_ok=True)
    synced_count = 0
    for root, dirs, files in os.walk(src_dir):
        # Exclude ignored dirs in-place
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        rel_path = Path(root).relative_to(src_dir)
        target_root = dst_dir / rel_path
        target_root.mkdir(parents=True, exist_ok=True)
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                continue
            src_f = Path(root) / f
            dst_f = target_root / f
            if sync_file(src_f, dst_f):
                synced_count += 1
    return synced_count


def sync_all(direction: str = "both"):
    print(f"=== Running Full Workspace Synchronization ({direction}) ===")
    
    # 1. Sync simulation logs and watchdog from D: drive to repo
    d_logs_source = D_LOGS if any(D_LOGS.glob("*.data")) else (D_WORK / "1Msun_test" / "LOGS")
    n_logs = sync_directory(d_logs_source, REPO_LOGS, "*")
    print(f"  Synchronized {n_logs} simulation log files from D: to repo/mesa_configs/LOGS")
    
    if (D_ROOT / "memory_watchdog.log").exists():
        sync_file(D_ROOT / "memory_watchdog.log", REPO_ROOT / "memory_watchdog.log")
        print(f"  Synchronized memory watchdog audit log")
        
    if (D_ROOT / "verify_mesa_logs.py").exists():
        sync_file(D_ROOT / "verify_mesa_logs.py", REPO_CONFIGS / "verify_mesa_logs.py")
        sync_file(D_ROOT / "verify_mesa_logs.py", REPO_ROOT / "verify_mesa_logs.py")

    # 2. Sync refactored code modules, tests, figures, and docs from repo to D:
    modules_to_sync = ["stellar_evolution", "tests", "figures", "mesa_configs", ".github"]
    for mod in modules_to_sync:
        src_m = REPO_ROOT / mod
        dst_m = D_ROOT / mod
        n = sync_tree(src_m, dst_m)
        print(f"  Synchronized tree {mod} -> D:\\天体物理导论\\{mod} ({n} files updated)")

    # 3. Standalone code and docs files to D:
    files_to_sync = [
        "build_explorer_html.py",
        "generate_figures.py",
        "stellar_grid_engine.py",
        "run_tests.py",
        "generate_standard_mesa_logs.py",
        "index.html",
        "stellar_explorer.html",
        "stellar_grid_data.json",
        "parameter_space_summary.csv",
        "PROJECT.md",
        "README.md",
        "report.md",
        "TEST_INFRA.md",
        "TEST_READY.md",
        "memory_watchdog.py",
    ]
    synced_files = 0
    for fname in files_to_sync:
        src_f = REPO_ROOT / fname
        dst_f = D_ROOT / fname
        if sync_file(src_f, dst_f):
            synced_files += 1
    print(f"  Synchronized {synced_files} root scripts and doc files to D:\\天体物理导论")

    # 4. Sync self to D:\天体物理导论\sync_workspace.py
    self_path = Path(__file__).resolve()
    sync_file(self_path, D_ROOT / "sync_workspace.py")
    sync_file(self_path, REPO_ROOT / "sync_workspace.py")

    print("Synchronization complete.\n")


if __name__ == "__main__":
    direction = sys.argv[1] if len(sys.argv) > 1 else "both"
    sync_all(direction)

