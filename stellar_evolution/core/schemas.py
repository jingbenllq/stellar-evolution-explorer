"""
Data Schemas and Unified Models for Stellar Evolution Simulation
================================================================
Defines strict dataclass models for:
  - OnionShellModel: interior shell boundary and physical conditions
  - StageModel: evolutionary stage state and concentric shells
  - StellarModel: unified model representation across MESA and grid
  - ProfileInfo: mapping from model_number to profile_number
  - HistoryData & ProfileData: container interfaces for MESA ASCII logs
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import numpy as np


@dataclass
class OnionShellModel:
    name: str
    dominant_element: str
    q_inner: float
    q_outer: float
    r_inner_norm: float
    r_outer_norm: float
    is_convective: bool
    burning_active: bool
    burning_reaction: str
    temperature_K: float
    density_cgs: float
    abundances: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OnionShellModel":
        return cls(
            name=str(d.get("name", "")),
            dominant_element=str(d.get("dominant_element", "")),
            q_inner=float(d.get("q_inner", 0.0)),
            q_outer=float(d.get("q_outer", 1.0)),
            r_inner_norm=float(d.get("r_inner_norm", 0.0)),
            r_outer_norm=float(d.get("r_outer_norm", 1.0)),
            is_convective=bool(d.get("is_convective", False)),
            burning_active=bool(d.get("burning_active", False)),
            burning_reaction=str(d.get("burning_reaction", "None")),
            temperature_K=float(d.get("temperature_K", 0.0)),
            density_cgs=float(d.get("density_cgs", 0.0)),
            abundances=dict(d.get("abundances", {})),
        )


@dataclass
class StageModel:
    name: str
    age_yr: float
    log_L: float
    log_Teff: float
    radius_Rsun: float
    onion_shells: List[OnionShellModel] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "age_yr": self.age_yr,
            "log_L": self.log_L,
            "log_Teff": self.log_Teff,
            "radius_Rsun": self.radius_Rsun,
            "onion_shells": [s.to_dict() for s in self.onion_shells],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StageModel":
        shells = [OnionShellModel.from_dict(s) for s in d.get("onion_shells", [])]
        return cls(
            name=str(d.get("name", "")),
            age_yr=float(d.get("age_yr", 0.0)),
            log_L=float(d.get("log_L", 0.0)),
            log_Teff=float(d.get("log_Teff", 0.0)),
            radius_Rsun=float(d.get("radius_Rsun", 1.0)),
            onion_shells=shells,
        )


@dataclass
class StellarModel:
    mass: float
    metallicity: float
    stages: List[StageModel] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "mass": self.mass,
            "metallicity": self.metallicity,
            "stages": [s.to_dict() for s in self.stages],
        }
        if self.metadata:
            res["metadata"] = self.metadata
        return res

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StellarModel":
        stages = [StageModel.from_dict(s) for s in d.get("stages", [])]
        return cls(
            mass=float(d.get("mass", 1.0)),
            metallicity=float(d.get("metallicity", 0.014)),
            stages=stages,
            metadata=dict(d.get("metadata", {})),
        )


@dataclass
class ProfileInfo:
    model_number: int
    priority: int
    profile_number: int


class HistoryData:
    """Container for MESA history.data output with column and header access."""

    def __init__(self, headers: Dict[str, Any], data: Dict[str, np.ndarray], file_name: str = ""):
        self.headers = headers
        self.data_dict = data
        self.file_name = file_name
        self._bulk_names = tuple(data.keys())
        self._header_names = tuple(headers.keys())

    @property
    def bulk_names(self) -> Tuple[str, ...]:
        return self._bulk_names

    @property
    def header_names(self) -> Tuple[str, ...]:
        return self._header_names

    def in_data(self, name: str) -> bool:
        return name in self.data_dict

    def data(self, name: str) -> np.ndarray:
        if name not in self.data_dict:
            raise KeyError(f"Column '{name}' not found in history data. Available: {self._bulk_names}")
        return self.data_dict[name]

    def header(self, name: str) -> Any:
        return self.headers.get(name)

    def __getitem__(self, name: str) -> np.ndarray:
        return self.data(name)

    def __contains__(self, name: str) -> bool:
        return self.in_data(name)

    def __getattr__(self, name: str) -> Any:
        if name in self.data_dict:
            return self.data_dict[name]
        # Convenience linear attributes
        if name == "L" and "log_L" in self.data_dict:
            return 10.0 ** self.data_dict["log_L"]
        if name == "Teff" and "log_Teff" in self.data_dict:
            return 10.0 ** self.data_dict["log_Teff"]
        if name == "R" and "log_R" in self.data_dict:
            return 10.0 ** self.data_dict["log_R"]
        if name == "Tc" and "log_center_T" in self.data_dict:
            return 10.0 ** self.data_dict["log_center_T"]
        if name == "Rhoc" and "log_center_Rho" in self.data_dict:
            return 10.0 ** self.data_dict["log_center_Rho"]
        raise AttributeError(f"'HistoryData' object has no attribute or data column '{name}'")

    def data_at_model_number(self, col: str, model_num: int) -> float:
        if "model_number" not in self.data_dict:
            raise KeyError("No 'model_number' column found in history data.")
        mn = self.data_dict["model_number"]
        matches = np.where(np.isclose(mn, float(model_num)))[0]
        if len(matches) == 0:
            raise ValueError(f"Model number {model_num} not found in history data.")
        return float(self.data(col)[matches[-1]])

    def remove_backups(self) -> "HistoryData":
        """
        Remove backup steps caused by MESA restarts / retry convergence backups.
        Keeps the latest valid timeline by scanning backwards so model_number
        is strictly monotonically increasing.
        """
        if "model_number" not in self.data_dict or len(self.data_dict["model_number"]) == 0:
            return self

        mn = self.data_dict["model_number"]
        n = len(mn)
        valid_indices = []
        current_min = float("inf")

        for i in range(n - 1, -1, -1):
            val = mn[i]
            if val < current_min:
                valid_indices.append(i)
                current_min = val

        valid_indices.reverse()
        idx_arr = np.array(valid_indices, dtype=int)

        new_data = {k: v[idx_arr] for k, v in self.data_dict.items()}
        self.data_dict = new_data
        return self


class ProfileData:
    """Container for MESA profile*.data with radial column and header access."""

    def __init__(self, headers: Dict[str, Any], data: Dict[str, np.ndarray], file_name: str = ""):
        self.headers = headers
        self.data_dict = data
        self.file_name = file_name
        self._bulk_names = tuple(data.keys())
        self._header_names = tuple(headers.keys())

    @property
    def bulk_names(self) -> Tuple[str, ...]:
        return self._bulk_names

    @property
    def header_names(self) -> Tuple[str, ...]:
        return self._header_names

    def in_data(self, name: str) -> bool:
        return name in self.data_dict

    def data(self, name: str) -> np.ndarray:
        if name not in self.data_dict:
            raise KeyError(f"Column '{name}' not found in profile data. Available: {self._bulk_names}")
        return self.data_dict[name]

    def header(self, name: str) -> Any:
        return self.headers.get(name)

    def __getitem__(self, name: str) -> np.ndarray:
        return self.data(name)

    def __contains__(self, name: str) -> bool:
        return self.in_data(name)

    def __getattr__(self, name: str) -> Any:
        if name in self.data_dict:
            return self.data_dict[name]
        # Convenience linear attributes
        if name == "T" and "logT" in self.data_dict:
            return 10.0 ** self.data_dict["logT"]
        if name == "Rho" and "logRho" in self.data_dict:
            return 10.0 ** self.data_dict["logRho"]
        if name == "P" and "logP" in self.data_dict:
            return 10.0 ** self.data_dict["logP"]
        if name == "R" and "logR" in self.data_dict:
            return 10.0 ** self.data_dict["logR"]
        raise AttributeError(f"'ProfileData' object has no attribute or data column '{name}'")
