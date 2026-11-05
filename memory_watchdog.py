#!python
"""
memory_watchdog.py - Real-Time Host Memory Safety Guard for Stellar Evolution & MESA Pipelines

Enforces strict memory guardrails so host RAM usage never exceeds 85%:
- Warning threshold: 80.0%
- Emergency throttle / pause ceiling: 84.0%
- Peak memory tracker and detailed telemetry audit log
- Safe streaming chunked download manager (1MB chunks) with socket timeouts and MD5 verification
"""

import os
import sys
import time
import socket
import hashlib
import logging
import threading
import subprocess
import urllib.request
from typing import Optional, Callable, Dict, Any, Tuple

# Socket timeout mandatory across all network operations
DEFAULT_SOCKET_TIMEOUT = 15.0
socket.setdefaulttimeout(DEFAULT_SOCKET_TIMEOUT)

try:
    import psutil
except ImportError:
    psutil = None

# Safety thresholds (percentage of total physical RAM)
WARNING_THRESHOLD_PERCENT = 80.0
EMERGENCY_CEILING_PERCENT = 84.0
ABSOLUTE_MAX_PERCENT = 85.0
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MB streaming buffer


class MemoryCeilingExceeded(RuntimeError):
    """Raised when physical system memory exceeds emergency safety threshold."""
    pass


class MemoryWatchdog:
    """
    Monitors host RAM utilization in real-time.
    Tracks peak usage, triggers warnings at 80%, and halts/throttles before 85%.
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        poll_interval: float = 0.5,
        warn_threshold: float = WARNING_THRESHOLD_PERCENT,
        emergency_threshold: float = EMERGENCY_CEILING_PERCENT,
    ):
        self.poll_interval = poll_interval
        self.warn_threshold = warn_threshold
        self.emergency_threshold = emergency_threshold
        self.log_file = log_file or os.path.join(os.path.dirname(__file__), "memory_watchdog.log")
        self.peak_percent = 0.0
        self.peak_used_bytes = 0
        self.total_bytes = 0
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._history = []

        self._init_memory_info()

    def _init_memory_info(self):
        if psutil is not None:
            vm = psutil.virtual_memory()
            self.total_bytes = vm.total
            self.peak_percent = vm.percent
            self.peak_used_bytes = vm.used

    def get_status(self) -> Dict[str, Any]:
        """Returns current host memory snapshot."""
        if psutil is None:
            return {
                "available": False,
                "error": "psutil not installed",
                "percent": 0.0,
                "total_gb": 0.0,
                "used_gb": 0.0,
            }
        vm = psutil.virtual_memory()
        percent = vm.percent
        used = vm.used
        total = vm.total
        if percent > self.peak_percent:
            self.peak_percent = percent
            self.peak_used_bytes = used
        return {
            "percent": percent,
            "total_bytes": total,
            "used_bytes": used,
            "available_bytes": vm.available,
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "peak_percent": round(self.peak_percent, 2),
            "peak_used_gb": round(self.peak_used_bytes / (1024**3), 2),
            "safe": percent < self.emergency_threshold,
            "warning": percent >= self.warn_threshold,
        }

    def _trim_wsl_memory(self):
        """Trims WSL2 Linux pagecache to immediately return memory pages to the Windows host."""
        try:
            subprocess.run(
                ["wsl", "-d", "Ubuntu", "-u", "root", "-e", "bash", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
            )
        except Exception:
            pass

    def check_memory(self, auto_pause: bool = True, max_pause_sec: float = 120.0) -> float:
        """
        Check current memory usage and log telemetry.
        - Warning (>= 80%): logs warning, trims WSL cache, and applies micro-throttle (0.05s backoff).
        - Emergency (>= 84%): logs emergency, trims WSL cache, and pauses execution until memory recovers,
          or raises MemoryCeilingExceeded if memory remains >= 84% after max_pause_sec.
        """
        pause_start = None
        while True:
            status = self.get_status()
            pct = status["percent"]
            msg = (
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"RAM: {pct:.1f}% (Used: {status.get('used_gb', 0)}GB / {status.get('total_gb', 0)}GB, "
                f"Peak: {self.peak_percent:.1f}%)"
            )
            if pct >= self.emergency_threshold:
                self._trim_wsl_memory()
                if pause_start is None:
                    pause_start = time.time()
                    self._log_entry("EMERGENCY_PAUSE", f"Ceiling reached ({pct:.1f}% >= {self.emergency_threshold}%). Pausing execution to prevent OOM...")
                
                if not auto_pause or (time.time() - pause_start) > max_pause_sec:
                    self._log_entry("EMERGENCY_HALT", f"Memory remained above emergency ceiling for {max_pause_sec}s: {msg}")
                    raise MemoryCeilingExceeded(
                        f"Emergency memory ceiling breached: {pct:.1f}% >= {self.emergency_threshold}%! "
                        f"Halting operation to prevent system OOM."
                    )
                time.sleep(2.0)
                continue
            elif pct >= self.warn_threshold:
                self._trim_wsl_memory()
                self._log_entry("WARNING_THROTTLE", f"Approaching limit: {msg}. Applying throttle backoff.")
                time.sleep(0.05)
                return pct
            else:
                if pause_start is not None:
                    self._log_entry("RESUMED", f"Memory recovered to {pct:.1f}%. Resuming operation.")
                return pct

    def _log_entry(self, level: str, msg: str):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{level}] {msg}\n")
        except Exception:
            pass

    def start_background_monitoring(self):
        """Starts a background daemon thread that polls memory periodically."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_background_monitoring(self):
        """Stops the background monitoring thread."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                self.check_memory()
            except MemoryCeilingExceeded as e:
                self._log_entry("CRITICAL", str(e))
            self._stop_event.wait(self.poll_interval)

    def run_command_guarded(
        self,
        command: list,
        cwd: Optional[str] = None,
        timeout: Optional[float] = 600.0,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str]:
        """
        Executes a subprocess while actively checking memory usage.
        If host memory reaches emergency ceiling, process is terminated.
        """
        self.check_memory()
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)
        # Enforce conservative thread allocation
        if "OMP_NUM_THREADS" not in proc_env:
            proc_env["OMP_NUM_THREADS"] = "4"

        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=proc_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout_chunks = []
        stderr_chunks = []
        start_time = time.time()

        try:
            while proc.poll() is None:
                # Poll memory
                self.check_memory()
                if timeout and (time.time() - start_time) > timeout:
                    proc.kill()
                    raise TimeoutError(f"Command timed out after {timeout} seconds: {' '.join(command)}")
                time.sleep(self.poll_interval)

            stdout, stderr = proc.communicate()
            return proc.returncode, stdout, stderr
        except Exception:
            proc.kill()
            raise


def stream_download_file(
    url: str,
    target_path: str,
    expected_md5: Optional[str] = None,
    expected_size: Optional[int] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    watchdog: Optional[MemoryWatchdog] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> bool:
    """
    Downloads a large file using streaming chunked I/O with 1MB buffer.
    Never buffers entire file in memory. Continuously enforces memory watchdog.
    Verifies MD5 checksum and final file size.
    """
    if watchdog is None:
        watchdog = MemoryWatchdog()

    watchdog.check_memory()
    req_headers = {"User-Agent": "curl/7.81.0"}
    if headers:
        req_headers.update(headers)

    temp_path = target_path + ".downloading"
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    # Resume support: check if partial download exists
    downloaded_bytes = 0
    if os.path.exists(temp_path):
        downloaded_bytes = os.path.getsize(temp_path)
        if downloaded_bytes > 0:
            req_headers["Range"] = f"bytes={downloaded_bytes}-"

    req = urllib.request.Request(url, headers=req_headers)
    hasher = hashlib.md5()

    # If resuming, update hasher with already downloaded data (streaming 1MB chunks)
    if downloaded_bytes > 0:
        with open(temp_path, "rb") as existing_file:
            while True:
                buf = existing_file.read(chunk_size)
                if not buf:
                    break
                hasher.update(buf)

    mode = "ab" if downloaded_bytes > 0 else "wb"

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT) as response, open(temp_path, mode) as out_file:
            content_length = response.headers.get("Content-Length")
            total_size = int(content_length) + downloaded_bytes if content_length else expected_size

            while True:
                # Memory check before each chunk read
                watchdog.check_memory()

                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                hasher.update(chunk)
                downloaded_bytes += len(chunk)

                if progress_callback:
                    progress_callback(downloaded_bytes, total_size or 0)

        # Verification
        final_md5 = hasher.hexdigest().lower()
        if expected_md5 and final_md5 != expected_md5.lower().strip():
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError(
                f"MD5 mismatch for {target_path}: expected {expected_md5}, got {final_md5}"
            )

        if expected_size and downloaded_bytes != expected_size:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError(
                f"Size mismatch for {target_path}: expected {expected_size} bytes, got {downloaded_bytes} bytes"
            )

        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)
        return True

    except Exception:
        # Check memory on failure as well
        watchdog.get_status()
        raise


if __name__ == "__main__":
    dog = MemoryWatchdog()
    status = dog.get_status()
    print("=== Memory Safety Guard Status ===")
    print(f"Total Physical RAM : {status.get('total_gb')} GB")
    print(f"Current Used RAM   : {status.get('used_gb')} GB ({status.get('percent')}%)")
    print(f"Peak RAM Recorded  : {status.get('peak_percent')}%")
    print(f"Warning Ceiling    : {dog.warn_threshold}%")
    print(f"Emergency Ceiling  : {dog.emergency_threshold}%")
    print(f"Safety Status      : {'SAFE' if status.get('safe') else 'ALERT'}")

    if "--monitor" in sys.argv:
        print("\nStarting 10-second memory test monitor...")
        dog.start_background_monitoring()
        time.sleep(10)
        dog.stop_background_monitoring()
        print("Monitor completed cleanly.")
