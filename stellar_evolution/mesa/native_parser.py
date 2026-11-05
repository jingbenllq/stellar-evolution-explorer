"""
Pure-Python Native MESA Log Parser (Zero External Dependencies)
==============================================================
Provides high-performance, robust parsing of standard MESA ASCII output files:
  - LOGS/history.data
  - LOGS/profiles.index
  - LOGS/profile*.data
Features:
  - Full support for Fortran double-precision 'D+'/ 'D-' exponent notation
  - Automatic handling of missing 'E' exponents (e.g. 1.2345-05)
  - remove_backups() backward-scan algorithm for retry step elimination and deduplication
  - Dual API: both stateful parser instance `NativeMesaParser(logs_dir)` and class calls
  - MesaLogDir high-level interface mimicking py_mesa_reader
  - Automatic linear physical quantity generation (L, Teff, R, Tc, Rhoc)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
import numpy as np

from ..core.schemas import HistoryData, ProfileData, ProfileInfo
from ..core.exceptions import MesaParseError, MesaFormatError

_FORTRAN_EXP_PATTERN = re.compile(r"([0-9])([+-][0-9]+)")
_INT_COLUMNS = {"model_number", "zone", "priority", "profile_number"}


def parse_fortran_float(s: str) -> float:
    """
    Parse a number string that may be in Fortran scientific format.
    Supports:
      - 1.234567D+02, 1.234567d-02
      - 1.234567E+02, 1.234567e-02
      - 1.2345-05 (missing exponent letter)
      - Standard integers and floats
    """
    clean = s.strip().strip('"').strip("'")
    if not clean:
        return 0.0
    clean = clean.replace("D", "E").replace("d", "E")
    if "E" not in clean and "e" not in clean:
        clean = _FORTRAN_EXP_PATTERN.sub(r"\1E\2", clean)
    try:
        return float(clean)
    except ValueError as err:
        raise MesaParseError(f"Cannot parse float token '{s}': {err}") from err


def remove_backups(model_numbers: Union[List[int], np.ndarray]) -> List[int]:
    """
    Remove backup steps caused by MESA restarts / retry convergence backups.
    Retains only the monotonic advancing evolutionary branch, dropping rolled-back steps.
    """
    cleaned: List[int] = []
    for m in model_numbers:
        val = int(m)
        while cleaned and cleaned[-1] >= val:
            cleaned.pop()
        cleaned.append(val)
    return cleaned


class _HybridMethod:
    """Descriptor supporting both instance calls with self and class calls."""
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        if instance is not None:
            def bound_instance(*args, **kwargs):
                return self.func(instance, *args, **kwargs)
            return bound_instance
        else:
            def bound_class(*args, **kwargs):
                return self.func(None, *args, **kwargs)
            return bound_class


class NativeMesaParser:
    """
    Parser for MESA ASCII data files (history.data, profiles.index, profile*.data).
    Requires zero external C/Fortran libraries.
    Can be used both as an instance:
      parser = NativeMesaParser("path/to/LOGS")
      hist = parser.read_history()
    or statically on the class:
      hist = NativeMesaParser.read_history("path/to/LOGS/history.data")
    """

    def __init__(self, logs_dir: Optional[Union[str, Path]] = None):
        self.logs_dir = Path(logs_dir) if logs_dir is not None else None

    @_HybridMethod
    def read_history(
        self_or_none,
        path: Optional[Union[str, Path]] = None,
        remove_backups: bool = True,
    ) -> HistoryData:
        """Parse history.data either using configured logs_dir or provided path."""
        if path is not None:
            target = Path(path)
            if target.is_dir():
                target = target / "history.data"
        elif self_or_none is not None and self_or_none.logs_dir is not None:
            target = self_or_none.logs_dir / "history.data"
        else:
            raise MesaParseError("No history path provided and logs_dir is not configured.")

        return NativeMesaParser._parse_history_file(target, remove_backups=remove_backups)

    @_HybridMethod
    def read_index(
        self_or_none,
        path: Optional[Union[str, Path]] = None,
    ) -> List[ProfileInfo]:
        """Parse profiles.index either using configured logs_dir or provided path."""
        if path is not None:
            target = Path(path)
            if target.is_dir():
                target = target / "profiles.index"
        elif self_or_none is not None and self_or_none.logs_dir is not None:
            target = self_or_none.logs_dir / "profiles.index"
        else:
            raise MesaParseError("No profiles.index path provided and logs_dir is not configured.")

        return NativeMesaParser._parse_index_file(target)

    @_HybridMethod
    def read_profile(
        self_or_none,
        target: Optional[Union[str, Path, int]] = None,
    ) -> ProfileData:
        """Parse profile*.data from integer profile number, file path, or default latest."""
        if isinstance(target, int):
            if self_or_none is None or self_or_none.logs_dir is None:
                raise MesaParseError(f"Cannot resolve profile number {target} without logs_dir.")
            file_path = self_or_none.logs_dir / f"profile{target}.data"
            if not file_path.is_file():
                matches = list(self_or_none.logs_dir.glob(f"profile*{target}.data"))
                if matches:
                    file_path = matches[0]
                else:
                    raise MesaParseError(f"profile{target}.data not found in {self_or_none.logs_dir}")
            return NativeMesaParser._parse_profile_file(file_path)
        elif target is not None:
            return NativeMesaParser._parse_profile_file(Path(target))
        else:
            if self_or_none is None or self_or_none.logs_dir is None:
                raise MesaParseError("No profile target or logs_dir provided.")
            prof_files = sorted(self_or_none.logs_dir.glob("profile*.data"))
            if not prof_files:
                raise MesaParseError(f"No profile*.data files found in {self_or_none.logs_dir}")
            return NativeMesaParser._parse_profile_file(prof_files[-1])

    @classmethod
    def _parse_history_file(cls, path: Path, remove_backups: bool = True) -> HistoryData:
        if not path.is_file():
            raise MesaParseError(f"MESA history file not found: {path}")
        headers, data = cls._parse_mesa_ascii_table(path)
        hist = HistoryData(headers=headers, data=data, file_name=str(path))
        if remove_backups:
            hist.remove_backups()
        return hist

    @classmethod
    def _parse_profile_file(cls, path: Path) -> ProfileData:
        if not path.is_file():
            raise MesaParseError(f"MESA profile file not found: {path}")
        headers, data = cls._parse_mesa_ascii_table(path)
        return ProfileData(headers=headers, data=data, file_name=str(path))

    @classmethod
    def _parse_index_file(cls, path: Path) -> List[ProfileInfo]:
        if not path.is_file():
            raise MesaParseError(f"MESA profiles index file not found: {path}")

        lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        clean_lines = [l for l in lines if l and not l.startswith("!")]
        if not clean_lines:
            return []

        header_idx = -1
        for idx, line in enumerate(clean_lines):
            low = line.lower()
            if "model_number" in low and "profile_number" in low:
                header_idx = idx
                break

        if header_idx == -1:
            if len(clean_lines) >= 2 and any(c.isdigit() for c in clean_lines[1]):
                header_idx = 0
            else:
                header_idx = 1 if len(clean_lines) > 1 else 0

        col_names = clean_lines[header_idx].split()
        m_idx = 0
        p_idx = 1
        pr_idx = 2

        for i, col in enumerate(col_names):
            c_low = col.lower()
            if "model" in c_low:
                m_idx = i
            elif "priority" in c_low:
                p_idx = i
            elif "profile" in c_low:
                pr_idx = i

        profiles: List[ProfileInfo] = []
        for line in clean_lines[header_idx + 1:]:
            tokens = line.split()
            if len(tokens) <= max(m_idx, pr_idx):
                continue
            try:
                m_num = int(tokens[m_idx])
                pri = int(tokens[p_idx]) if p_idx < len(tokens) else 1
                pr_num = int(tokens[pr_idx])
                profiles.append(ProfileInfo(model_number=m_num, priority=pri, profile_number=pr_num))
            except ValueError:
                continue

        return profiles

    @staticmethod
    def _parse_mesa_ascii_table(path: Path) -> Tuple[Dict[str, Any], Dict[str, np.ndarray]]:
        """Internal parser for general MESA ASCII output table files."""
        content = path.read_text(encoding="utf-8", errors="replace")
        raw_lines = content.splitlines()

        lines = []
        for line in raw_lines:
            stripped = line.strip()
            if stripped.startswith("!"):
                continue
            lines.append(stripped)

        headers: Dict[str, Any] = {}
        data: Dict[str, np.ndarray] = {}

        start = 0
        while start < len(lines) and not lines[start]:
            start += 1

        if start >= len(lines):
            return headers, data

        blocks: List[List[str]] = []
        cur_block: List[str] = []

        for line in lines[start:]:
            if not line:
                if cur_block:
                    blocks.append(cur_block)
                    cur_block = []
            else:
                cur_block.append(line)

        if cur_block:
            blocks.append(cur_block)

        if len(blocks) >= 2:
            hdr_block = blocks[0]
            bulk_block = blocks[1]
            headers = NativeMesaParser._parse_header_block(hdr_block)
            data = NativeMesaParser._parse_bulk_block(bulk_block)
        elif len(blocks) == 1:
            data = NativeMesaParser._parse_bulk_block(blocks[0])
        else:
            raise MesaFormatError(f"Empty or unparseable MESA file: {path}")

        return headers, data

    @staticmethod
    def _parse_header_block(lines: List[str]) -> Dict[str, Any]:
        headers: Dict[str, Any] = {}
        if len(lines) < 2:
            return headers

        if len(lines) >= 3 and lines[0].split()[0].isdigit():
            names_line = lines[1]
            values_line = lines[2]
        else:
            names_line = lines[0]
            values_line = lines[1]

        names = names_line.split()
        val_tokens = NativeMesaParser._tokenize_values(values_line)

        for i, name in enumerate(names):
            if i < len(val_tokens):
                raw_val = val_tokens[i]
                try:
                    headers[name] = parse_fortran_float(raw_val)
                except MesaParseError:
                    headers[name] = raw_val.strip('"').strip("'")
            else:
                headers[name] = None

        return headers

    @staticmethod
    def _parse_bulk_block(lines: List[str]) -> Dict[str, np.ndarray]:
        if not lines:
            return {}

        if len(lines) >= 2 and lines[0].split()[0].isdigit():
            names_idx = 1
            data_start = 2
        else:
            names_idx = 0
            data_start = 1

        col_names = lines[names_idx].split()
        n_cols = len(col_names)
        if n_cols == 0:
            return {}

        data_rows: List[List[float]] = []
        for line in lines[data_start:]:
            tokens = line.split()
            if not tokens:
                continue
            if len(tokens) != n_cols:
                if len(tokens) < n_cols:
                    continue
                tokens = tokens[:n_cols]

            row_vals = []
            for tok in tokens:
                row_vals.append(parse_fortran_float(tok))
            data_rows.append(row_vals)

        if not data_rows:
            return {col: np.array([], dtype=float) for col in col_names}

        arr = np.array(data_rows, dtype=float)
        result: Dict[str, np.ndarray] = {}
        for col_i, name in enumerate(col_names):
            col_arr = arr[:, col_i]
            if name.lower() in _INT_COLUMNS:
                result[name] = col_arr.astype(int)
            else:
                result[name] = col_arr

        return result

    @staticmethod
    def _tokenize_values(line: str) -> List[str]:
        tokens = []
        in_quote = False
        quote_char = ""
        cur_tok = []

        for ch in line:
            if in_quote:
                cur_tok.append(ch)
                if ch == quote_char:
                    in_quote = False
                    tokens.append("".join(cur_tok))
                    cur_tok = []
            elif ch in ('"', "'"):
                in_quote = True
                quote_char = ch
                cur_tok.append(ch)
            elif ch.isspace():
                if cur_tok:
                    tokens.append("".join(cur_tok))
                    cur_tok = []
            else:
                cur_tok.append(ch)

        if cur_tok:
            tokens.append("".join(cur_tok))

        return tokens


class MesaLogDir:
    """
    High-level manager for a MESA LOGS directory.
    Replicates py_mesa_reader.MesaLogDir interface with pure Python native parser.
    """

    def __init__(self, log_path: Union[str, Path] = "LOGS", memoize_profiles: bool = True):
        self.log_dir = Path(log_path)
        self.memoize_profiles = memoize_profiles
        self._history: Optional[HistoryData] = None
        self._profiles_index: Optional[List[ProfileInfo]] = None
        self._profile_cache: Dict[int, ProfileData] = {}

    @property
    def history(self) -> HistoryData:
        """Loaded history.data."""
        if self._history is None:
            hist_path = self.log_dir / "history.data"
            self._history = NativeMesaParser._parse_history_file(hist_path, remove_backups=False)
        return self._history

    @property
    def profiles_index(self) -> List[ProfileInfo]:
        """Parsed profiles.index list."""
        if self._profiles_index is None:
            idx_path = self.log_dir / "profiles.index"
            if idx_path.is_file():
                self._profiles_index = NativeMesaParser._parse_index_file(idx_path)
            else:
                self._profiles_index = []
        return self._profiles_index

    @property
    def model_numbers(self) -> np.ndarray:
        """Array of model numbers for which a profile exists."""
        return np.array([p.model_number for p in self.profiles_index], dtype=int)

    @property
    def profile_numbers(self) -> np.ndarray:
        """Array of profile numbers available in the directory."""
        return np.array([p.profile_number for p in self.profiles_index], dtype=int)

    def profile_data(self, model_number: Optional[int] = None, profile_number: Optional[int] = None) -> ProfileData:
        """
        Retrieve ProfileData for a given model_number or profile_number.
        If neither is specified, returns the profile with the largest profile number (last profile).
        """
        target_pr_num = None

        if profile_number is not None:
            target_pr_num = int(profile_number)
        elif model_number is not None:
            target_model = int(model_number)
            for info in self.profiles_index:
                if info.model_number == target_model:
                    target_pr_num = info.profile_number
                    break
            if target_pr_num is None:
                raise ValueError(f"No profile found for model_number={model_number} in {self.log_dir}")
        else:
            if self.profiles_index:
                target_pr_num = max(p.profile_number for p in self.profiles_index)
            else:
                prof_files = sorted(self.log_dir.glob("profile*.data"))
                if not prof_files:
                    raise MesaParseError(f"No profile*.data files found in {self.log_dir}")
                last_file = prof_files[-1]
                m = re.search(r"profile(\d+)\.data", last_file.name)
                target_pr_num = int(m.group(1)) if m else 1

        if self.memoize_profiles and target_pr_num in self._profile_cache:
            return self._profile_cache[target_pr_num]

        file_path = self.log_dir / f"profile{target_pr_num}.data"
        if not file_path.is_file():
            matches = list(self.log_dir.glob(f"profile*{target_pr_num}.data"))
            if matches:
                file_path = matches[0]
            else:
                raise MesaParseError(f"Profile file profile{target_pr_num}.data not found in {self.log_dir}")

        prof = NativeMesaParser._parse_profile_file(file_path)
        if self.memoize_profiles:
            self._profile_cache[target_pr_num] = prof
        return prof

    def select_models(self, predicate: Callable[[np.ndarray], np.ndarray], col_name: str = "star_age") -> np.ndarray:
        """Filter profile model numbers based on a predicate applied to a history column."""
        h = self.history
        valid_models = []
        for m in self.model_numbers:
            try:
                val = h.data_at_model_number(col_name, int(m))
                if predicate(np.array([val]))[0]:
                    valid_models.append(int(m))
            except (KeyError, ValueError):
                continue
        return np.array(valid_models, dtype=int)
