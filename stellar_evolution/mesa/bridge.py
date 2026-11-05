"""
Unified Data Model Bridge: MESA Simulation & Grid Engine Integration
====================================================================
Bridges disparate simulation outputs (MESA history/profile logs and calibrated
28-model semi-analytical evolutionary tracks) into the unified, strongly typed
StellarModel data representation conforming to PROJECT.md § Interface Contracts.
"""

import math
from typing import Dict, List, Optional, Any, Union
import numpy as np

from ..core.schemas import StellarModel, StageModel, OnionShellModel, HistoryData, ProfileData
from ..core.exceptions import ValidationError
from ..physics.nucleosynthesis import generate_onion_shells, identify_dominant_element
from .native_parser import MesaLogDir, NativeMesaParser

STAGE_NAME_MAP = {
    0: "ZAMS",
    1: "TAMS",
    2: "RGB",
    3: "CHeB",
    4: "AGB",
    5: "Remnant",
}


class MesaBridge:
    """
    Bridge converting between MESA raw simulation logs, analytical grid models,
    and the unified StellarModel contract.
    """

    @staticmethod
    def grid_model_to_stellar_model(model_dict: Dict[str, Any]) -> StellarModel:
        """
        Convert a model dictionary from generate_track(mass, z) or stellar_grid_data.json
        into a unified StellarModel dataclass instance.
        """
        mass = float(model_dict.get("mass_init", 1.0))
        z = float(model_dict.get("z_init", 0.014))
        track = model_dict.get("track", {})
        profiles = model_dict.get("profiles", {})
        stage_step_indices = model_dict.get("stage_step_indices", [0, 40, 80, 120, 160, 199])

        stages: List[StageModel] = []

        for st_idx in range(6):
            st_name = STAGE_NAME_MAP.get(st_idx, f"Stage_{st_idx}")
            step_i = stage_step_indices[st_idx] if st_idx < len(stage_step_indices) else st_idx * 40
            step_i = min(step_i, len(track.get("s", [])) - 1)

            age = float(track["age_yr"][step_i]) if "age_yr" in track else 0.0
            log_L = float(track["log_L"][step_i]) if "log_L" in track else 0.0
            log_Teff = float(track["log_Teff"][step_i]) if "log_Teff" in track else 3.76
            log_R = float(track["log_R"][step_i]) if "log_R" in track else 0.0
            radius = 10.0 ** log_R

            track_point = {
                "log_L": log_L,
                "log_Teff": log_Teff,
                "log_R": log_R,
                "log_Tc": float(track["log_Tc"][step_i]) if "log_Tc" in track else 7.15,
                "log_Rhoc": float(track["log_Rhoc"][step_i]) if "log_Rhoc" in track else 1.95,
            }

            prof_dict = profiles.get(str(st_idx), {})
            if prof_dict and "q" in prof_dict:
                shells = generate_onion_shells(mass, z, st_idx, track_point, prof_dict)
            else:
                # Default single envelope shell if no profile
                shells = [
                    OnionShellModel(
                        name="envelope",
                        dominant_element="H",
                        q_inner=0.0,
                        q_outer=1.0,
                        r_inner_norm=0.0,
                        r_outer_norm=1.0,
                        is_convective=False,
                        burning_active=True,
                        burning_reaction="pp-chain",
                        temperature_K=10.0 ** track_point["log_Tc"],
                        density_cgs=10.0 ** track_point["log_Rhoc"],
                        abundances={"H1": 0.70, "He4": 0.28, "Z": 0.02},
                    )
                ]

            stage = StageModel(
                name=st_name,
                age_yr=age,
                log_L=log_L,
                log_Teff=log_Teff,
                radius_Rsun=radius,
                onion_shells=shells,
            )
            stages.append(stage)

        meta = {
            "source": "stellar_evolution_grid",
            "pathway": model_dict.get("pathway", {}),
            "zams": model_dict.get("zams", {}),
        }

        return StellarModel(mass=mass, metallicity=z, stages=stages, metadata=meta)

    @staticmethod
    def mesa_logs_to_stellar_model(
        logs_or_dir: Union[str, MesaLogDir],
        mass: Optional[float] = None,
        metallicity: Optional[float] = None,
    ) -> StellarModel:
        """
        Convert MESA simulation logs (history.data and profile*.data files)
        into the unified StellarModel contract.
        """
        if isinstance(logs_or_dir, str):
            logs = MesaLogDir(logs_or_dir)
        else:
            logs = logs_or_dir

        h = logs.history
        h.remove_backups()

        # Infer initial mass and metallicity if not provided
        star_mass = mass if mass is not None else float(h.star_mass[0]) if "star_mass" in h else 1.0
        z_init = metallicity if metallicity is not None else 0.014

        # Sample stages from history: ZAMS (min age or model 1), TAMS (center_h1 ~ 0.01),
        # intermediate profiles, and final model
        n_hist = len(h.star_age)
        stages: List[StageModel] = []

        # Find available profiles
        pr_infos = logs.profiles_index
        if pr_infos:
            for info in pr_infos:
                m_num = info.model_number
                pr_num = info.profile_number
                try:
                    prof = logs.profile_data(profile_number=pr_num)
                except Exception:
                    continue

                # Get history conditions at this model number
                try:
                    age = h.data_at_model_number("star_age", m_num)
                    log_L = h.data_at_model_number("log_L", m_num)
                    log_Teff = h.data_at_model_number("log_Teff", m_num)
                    log_R = h.data_at_model_number("log_R", m_num) if "log_R" in h else 0.5 * log_L - 2.0 * (log_Teff - 3.7613)
                except Exception:
                    age = float(prof.header("star_age")) if prof.header("star_age") else 0.0
                    log_L = float(prof.header("log_L")) if prof.header("log_L") else 0.0
                    log_Teff = float(prof.header("log_Teff")) if prof.header("log_Teff") else 3.76
                    log_R = 0.5 * log_L - 2.0 * (log_Teff - 3.7613)

                shells = MesaBridge._build_shells_from_profile(prof)
                st_name = f"Model_{m_num}"
                if len(stages) == 0:
                    st_name = "ZAMS"
                elif pr_num == max(p.profile_number for p in pr_infos):
                    st_name = "Remnant" if age > 1e10 or star_mass < 0.5 else "Advanced"

                stage = StageModel(
                    name=st_name,
                    age_yr=float(age),
                    log_L=float(log_L),
                    log_Teff=float(log_Teff),
                    radius_Rsun=float(10.0 ** log_R),
                    onion_shells=shells,
                )
                stages.append(stage)
        else:
            # Fallback if no profiles present: construct ZAMS and Final from history
            stage_indices = [0, n_hist - 1]
            names = ["ZAMS", "Final"]
            for i, st_name in zip(stage_indices, names):
                age = float(h.star_age[i])
                log_L = float(h.log_L[i])
                log_Teff = float(h.log_Teff[i])
                log_R = float(h.log_R[i]) if "log_R" in h else 0.5 * log_L - 2.0 * (log_Teff - 3.7613)
                stage = StageModel(
                    name=st_name,
                    age_yr=age,
                    log_L=log_L,
                    log_Teff=log_Teff,
                    radius_Rsun=10.0 ** log_R,
                    onion_shells=[],
                )
                stages.append(stage)

        meta = {
            "source": "MESA_LOGS",
            "log_dir": str(logs.log_dir),
            "total_models": n_hist,
        }

        return StellarModel(mass=star_mass, metallicity=z_init, stages=stages, metadata=meta)

    @staticmethod
    def _build_shells_from_profile(prof: ProfileData) -> List[OnionShellModel]:
        """Convert a MESA ProfileData object into segmented OnionShellModel shells."""
        # Standardize radial coordinate q
        if "q" in prof:
            q_arr = np.array(prof["q"])
        elif "mass" in prof and len(prof["mass"]) > 0:
            m_tot = max(prof["mass"])
            q_arr = np.array(prof["mass"]) / (m_tot if m_tot > 0 else 1.0)
        else:
            q_arr = np.linspace(1.0, 0.0, len(prof.data(prof.bulk_names[0])))

        # Sort so q increases from center (0) to surface (1)
        sort_order = np.argsort(q_arr)
        q_sorted = q_arr[sort_order]

        n_pts = len(q_sorted)
        if n_pts == 0:
            return []

        # Find dominant species per zone
        iso_candidates = ["h1", "he4", "c12", "o16", "ne20", "si28", "fe56"]
        avail_isos = [iso for iso in iso_candidates if iso in prof]
        if not avail_isos:
            # Check for x_mass_fraction_H, y_mass_fraction_He, etc.
            if "x_mass_fraction_H" in prof:
                avail_isos = ["x_mass_fraction_H", "y_mass_fraction_He", "z_mass_fraction_metals"]

        dom_per_zone = []
        for idx in sort_order:
            best_sp = "H"
            best_val = -1.0
            for sp in avail_isos:
                val = prof.data(sp)[idx]
                if val > best_val:
                    best_val = val
                    best_sp = sp
            dom_elem = identify_dominant_element({best_sp: 1.0})
            dom_per_zone.append(dom_elem)

        # Segment into concentric shells
        segments = []
        cur_dom = dom_per_zone[0]
        start_i = 0
        for i in range(1, n_pts):
            if dom_per_zone[i] != cur_dom:
                segments.append({"dom": cur_dom, "start": start_i, "end": i})
                cur_dom = dom_per_zone[i]
                start_i = i
        segments.append({"dom": cur_dom, "start": start_i, "end": n_pts})

        shells: List[OnionShellModel] = []
        n_segs = len(segments)

        for s_idx, seg in enumerate(segments):
            i_s = seg["start"]
            i_e = seg["end"] - 1
            elem = seg["dom"]
            q_in = 0.0 if s_idx == 0 else float(q_sorted[i_s])
            q_out = 1.0 if s_idx == n_segs - 1 else float(q_sorted[i_e])

            mid_i = sort_order[(i_s + i_e) // 2]
            T_val = float(prof.T[mid_i]) if "T" in dir(prof) and "logT" in prof else 1.0e7
            rho_val = float(prof.Rho[mid_i]) if "Rho" in dir(prof) and "logRho" in prof else 1.0

            abund_map = {}
            for sp in avail_isos:
                clean_k = sp.replace("x_mass_fraction_", "").replace("y_mass_fraction_", "").replace("z_mass_fraction_", "")
                abund_map[clean_k] = float(prof.data(sp)[mid_i])

            is_conv = False
            if "mixing_type" in prof:
                is_conv = bool(prof.data("mixing_type")[mid_i] == 1)

            eps = float(prof.data("eps_nuc")[mid_i]) if "eps_nuc" in prof else 0.0
            burning_active = eps > 1.0e-2

            shell_name = f"{elem}_core" if q_in == 0.0 else (f"{elem}_envelope" if q_out >= 0.98 else f"{elem}_shell")

            shells.append(
                OnionShellModel(
                    name=shell_name,
                    dominant_element=elem,
                    q_inner=round(q_in, 4),
                    q_outer=round(q_out, 4),
                    r_inner_norm=round(float(q_in ** 0.45), 4),
                    r_outer_norm=round(float(q_out ** 0.45), 4),
                    is_convective=is_conv,
                    burning_active=burning_active,
                    burning_reaction=f"{elem}-burning" if burning_active else "None",
                    temperature_K=round(T_val, 1),
                    density_cgs=round(rho_val, 4),
                    abundances=abund_map,
                )
            )

        return shells

    @staticmethod
    def validate_stellar_model(model: StellarModel) -> bool:
        """
        Validate that a StellarModel instance complies with physical and schema invariants:
          1. mass > 0 and metallicity > 0
          2. At least 1 stage
          3. Stage onion_shells cover [0, 1] in relative mass q
          4. Inner shell boundaries <= outer boundaries
        """
        if model.mass <= 0.0:
            raise ValidationError(f"Invalid stellar mass: {model.mass} <= 0")
        if model.metallicity <= 0.0 or model.metallicity > 0.1:
            raise ValidationError(f"Invalid metallicity: {model.metallicity}")
        if not model.stages:
            raise ValidationError("StellarModel contains no evolutionary stages.")

        for st in model.stages:
            if not st.onion_shells:
                continue
            # Check concentric monotonicity
            for shell in st.onion_shells:
                if shell.q_inner > shell.q_outer:
                    raise ValidationError(f"Shell {shell.name} has q_inner ({shell.q_inner}) > q_outer ({shell.q_outer})")
                if shell.r_inner_norm > shell.r_outer_norm:
                    raise ValidationError(f"Shell {shell.name} has r_inner ({shell.r_inner_norm}) > r_outer ({shell.r_outer_norm})")

            # Check coverage
            min_q = min(s.q_inner for s in st.onion_shells)
            max_q = max(s.q_outer for s in st.onion_shells)
            if not (math.isclose(min_q, 0.0, abs_tol=0.05) and math.isclose(max_q, 1.0, abs_tol=0.05)):
                raise ValidationError(f"Stage {st.name} onion shells do not span [0, 1] (min={min_q}, max={max_q})")

        return True
