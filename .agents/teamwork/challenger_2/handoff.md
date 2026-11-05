# Handoff Report — challenger_2 (Adversarial & Empirical Challenger)

## 1. Observation

### Obs 1. Artifact Parity & Compilation
- **Command**: `py -3 build_explorer_html.py`
  - Output:
    ```
    Built C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\index.html (208.1 KB)
    Built C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\stellar_explorer.html (208.1 KB)
    ```
- **Command**: `Compare-Object (Get-Content index.html) (Get-Content stellar_explorer.html)`
  - Output: *Completely empty (zero differences).*
- **Command**: `Get-FileHash index.html, stellar_explorer.html`
  - Output:
    ```
    Algorithm Hash                                                             Path
    SHA256    D0BC0B4767A3DF63933EE481D844A9C1FC85C5DB0D3B208D578FF189F706EF9D index.html
    SHA256    D0BC0B4767A3DF63933EE481D844A9C1FC85C5DB0D3B208D578FF189F706EF9D stellar_explorer.html
    ```

### Obs 2. JavaScript Syntax Validation
- **Command**: `node -c "$env:TEMP\stellar_explorer_extracted.js"`
  - Output: *Exit code 0 (clean parse, 0 syntax errors across all 142,642 characters of embedded JavaScript).*

### Obs 3. Onion-Skin Diagram Shell Generation (25 $M_\odot$ and 15 $M_\odot$)
- **File**: `stellar_evolution/physics/abundance.py:187-200`
  ```python
  s_fe = 1.0 - w_fe
  s_si = w_fe * (1.0 - w_si)
  s_one = w_si * (1.0 - w_one)
  s_co = w_one * (1.0 - w_co)
  s_he = w_co * (1.0 - w_he)
  s_env = w_he

  H1 = (X_init - 0.06) * s_env
  He4 = (1.0 - z) * s_he + (Y_init + 0.06) * s_env
  C12 = 0.08 * s_one + 0.36 * s_co + c_init * (s_he + s_env)
  O16 = 0.14 * s_si + 0.66 * s_one + (0.64 - z) * s_co + o_init * (s_he + s_env)
  Ne20 = 0.24 * s_one + ne_init * (s_co + s_he + s_env)
  Si28 = 0.08 * s_fe + 0.78 * s_si + 0.02 * s_one + si_init * (s_co + s_he + s_env)
  Fe56 = 0.92 * s_fe + 0.08 * s_si + fe_init * (s_one + s_co + s_he + s_env)
  ```
- **File**: `stellar_explorer.html:3045-3065` (`getDetailedOnionShells`)
  ```javascript
  for (let i = 0; i < qArr.length; i++) {
    let bestSp = "H1";
    let bestVal = -1;
    for (const sp of speciesOrder) {
      if (prof[sp] && prof[sp][i] > bestVal) {
        bestVal = prof[sp][i];
        bestSp = sp;
      }
    }
    if (bestSp !== prevDom && prevDom !== null) {
      rawShells.push({ sp: prevDom, q0: startQ, q1: qArr[i] });
      startQ = qArr[i];
    }
    prevDom = bestSp;
  }
  ```
- **Node.js VM Evaluation Result** for `getDetailedOnionShells` at Step 199 (Stage 5):
  - **25 $M_\odot$ Shell Count**: **5** (Expected: **7**)
    - Identified Shells: `Fe56 (q: 0.0 -> 0.161)`, `Si28 (q: 0.161 -> 0.245)`, `O16 (q: 0.245 -> 0.581)`, `He4 (q: 0.581 -> 0.799)`, `H1 (q: 0.799 -> 1.0)`.
    - **Missing Shells**: `Ne20` and `C12` are missing completely.
  - **15 $M_\odot$ Shell Count**: **5** (Expected: **7**)
    - Identified Shells: `Fe56 (q: 0.0 -> 0.144)`, `Si28 (q: 0.144 -> 0.211)`, `O16 (q: 0.211 -> 0.463)`, `He4 (q: 0.463 -> 0.648)`, `H1 (q: 0.648 -> 1.0)`.
    - **Missing Shells**: `Ne20` and `C12` are missing completely.
- **Active Burning Ring Glow Status in 25 $M_\odot$**:
  - `Fe56`: `burn: false`
  - `Si28`: `burn: true` (`reaction: ²⁸Si + 7α ⇌ ⁵⁶Ni → ⁵⁶Co → ⁵⁶Fe`)
  - `O16`: `burn: false` (`reaction: 核反应微弱或已熄灭`, condition `qMid <= 0.30` failed because $q_{\text{mid}} = 0.4127$)
  - `He4`: `burn: false`
  - `H1`: `burn: false`
  - Out of all pre-supernova shells in 25 $M_\odot$, only a single burning ring (`Si28`) is rendered active.

### Obs 4. Low-Mass Fully Convective Star ($0.3\,M_\odot$)
- Across all 200 evolutionary steps in `GRID_DATA.models['0.014']['0.3']`:
  - `is_convective` is `true` for 100% of shells.
  - Exactly 0 false radiative shells observed.

### Obs 5. Coordinate Mapping & Geometry Monotonicity
- **Function**: `coordTransform(q, coordMode, mass, sVal)` tested across dense grid of $q \in [0, 1]$ (200 sample points), 11 stage slices $s \in [0, 5]$, and all 3 modes (`q`, `r_norm`, `log_r`):
  - Values remain strictly bounded in $[0.0, 1.0]$.
  - Zero `NaN`, zero `Infinity`, zero division by zero, zero $\log(0)$.
  - Strict monotonicity: $f(q_1) \le f(q_2)$ for all $q_1 \le q_2$.
  - All concentric shell boundaries across 28 models satisfy $u_0 \le u_1$ and non-inverted concentric ordering.

### Obs 6. Memory Watchdog Stress Harness
- Tested `memory_watchdog.py` across 8 simulated scenarios with mocked `psutil`:
  - $50.0\%$ (Normal): `safe=True`, `warning=False`, 0s delay.
  - $80.0\%$ (Warn threshold): `safe=True`, `warning=True`, logs `[WARNING_THROTTLE]`, 0.05s micro-backoff applied.
  - $83.9\%$ (Warn ceiling): `safe=True`, `warning=True`, returns cleanly.
  - $84.0\%$ (Emergency threshold, `auto_pause=False`): Immediately raises `MemoryCeilingExceeded`, logs `[EMERGENCY_PAUSE]` and `[EMERGENCY_HALT]`.
  - $84.5\%$ (Emergency pause timeout): Automatically pauses and raises `MemoryCeilingExceeded` after `max_pause_sec`.
  - $84.2\% \to 70.0\%$ (Emergency pause recovery): Logs `[EMERGENCY_PAUSE]`, recovers, logs `[RESUMED]`, returns cleanly without crashing.
  - $90.0\%$ (Hard ceiling breach): Immediately halts.
  - Peak tracking: monotonically records historical peak usage.
  - All 8 stress tests passed.

### Obs 7. Unit & Multi-Tier Test Suite
- **Command**: `cd C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project; py -3 -m unittest discover tests`
  - Output: `Ran 71 tests in 4.682s, OK` (100% pass rate).

---

## 2. Logic Chain

1. **Premise**: PROJECT.md Feature F14, ORIGINAL_REQUEST.md §R4, and the task dispatch explicitly require the Onion-Skin diagram to model and render all 7 concentric nuclear burning shells ($\text{H} \to \text{He} \to \text{C} \to \text{Ne} \to \text{O} \to \text{Si} \to \text{Fe}$) for massive stars ($25\,M_\odot$ and $15\,M_\odot$) at pre-supernova core-collapse stage.
2. **Observation Obs 3**: In `stellar_evolution/physics/abundance.py`, the abundance profiles for stage 5 set:
   - In the O/Ne shell slice ($s_{\text{one}}$): $X(^{16}\text{O}) = 0.66$ and $X(^{20}\text{Ne}) = 0.24$.
   - In the C/O shell slice ($s_{\text{co}}$): $X(^{16}\text{O}) = 0.64$ and $X(^{12}\text{C}) = 0.36$.
3. **Inference**: Because $X(^{16}\text{O}) > X(^{20}\text{Ne})$ and $X(^{16}\text{O}) > X(^{12}\text{C})$, $^{16}\text{O}$ has the mathematical plurality/maximum across both adjacent radial zones ($q \approx 0.24$ to $0.58$).
4. **Inference**: The dominant-element segmentation algorithm in `getDetailedOnionShells` (JS) and `generate_onion_shells` (Python) evaluates $\arg\max_i X_i(q)$ at each zone. Because $^{16}\text{O}$ dominates continuously across the entire span, neither $^{20}\text{Ne}$ nor $^{12}\text{C}$ is ever identified as the dominant element.
5. **Inference**: Consequently, the generated onion skin diagram contains only 5 shells (`Fe56`, `Si28`, `O16`, `He4`, `H1`) instead of the specified 7 shells ($\text{H} \to \text{He} \to \text{C} \to \text{Ne} \to \text{O} \to \text{Si} \to \text{Fe}$). The green $^{12}\text{C}$ shell and cyan $^{20}\text{Ne}$ shell never appear in the visualizer for massive star late stages.
6. **Inference**: Furthermore, because the merged $^{16}\text{O}$ shell is abnormally wide ($q \in [0.24, 0.58]$, $q_{\text{mid}} = 0.4127$), the hardcoded burning ignition test `qMid <= 0.30` in `getDetailedOnionShells` evaluates to false, extinguishing the active burning glow ring for Oxygen.
7. **Conclusion**: While all other aspects (HTML parity, JS syntax, coordinate geometry, watchdog, 0.3 $M_\odot$ convection, unit tests) pass with 100% compliance, the Onion-Skin diagram fails the 7-shell nuclear burning requirement for $25\,M_\odot$ and $15\,M_\odot$.

---

## 3. Caveats

- **No live GPU rendering**: Tests were run via headless Node.js AST/VM parsing and Python CLI/matrix analysis. WebGL shaders and canvas drawing calls were verified syntactically and logically, but not on physical display hardware.
- **Existing unit tests passed**: Existing unit tests in `tests/test_e2e_stellar_evolution.py` passed because they only asserted `max(X_i) > threshold` (e.g. `max(C12) > 0.20`), without asserting that $X(^{12}\text{C})$ or $X(^{20}\text{Ne})$ ever achieves local dominance over $X(^{16}\text{O})$ to form independent segmented onion shells.

---

## 4. Conclusion

**Verdict**: **`REQUEST_CHANGES`**

### Summary of Passed Elements
1. **HTML Artifact Parity**: `build_explorer_html.py` compiles `index.html` and `stellar_explorer.html` with 100% identical byte contents (SHA256: `D0BC0B4767A3DF63933EE481D844A9C1FC85C5DB0D3B208D578FF189F706EF9D`).
2. **JavaScript Syntax**: Clean parse with `node -c` (exit code 0).
3. **Coordinate Transformation**: $q$, $r/R_\star$, and $\log r$ are non-negative, bounded in $[0, 1]$, and strictly monotonic with zero radial inversions.
4. **Low-Mass Convection**: $0.3\,M_\odot$ maintains 100% convective shells across all 200 steps with 0 false radiative shells.
5. **Memory Safety Guard**: `memory_watchdog.py` correctly handles 80% warning throttle, 84% emergency pause, 85% ceiling halt, and recovery transitions.
6. **Unit Test Discovery**: `py -3 -m unittest discover tests` runs 71 tests in 4.68s with 100% pass rate.

### Specific Changes Requested
1. **Fix Abundance Profiles for Massive Stars Stage 5 (`stellar_evolution/physics/abundance.py`)**:
   - In lines 187–200, ensure the Neon-burning shell slice ($s_{\text{one}}$) has $^{20}\text{Ne}$ as the plurality element (e.g., $X(^{20}\text{Ne}) \approx 0.48$, $X(^{16}\text{O}) \approx 0.38$).
   - Ensure the Carbon-burning shell slice ($s_{\text{co}}$) has $^{12}\text{C}$ as the plurality element (e.g., $X(^{12}\text{C}) \approx 0.52$, $X(^{16}\text{O}) \approx 0.38$).
   - This will allow the dominant-species segmenter to cleanly produce all 7 canonical shells: $\text{Fe56} \to \text{Si28} \to \text{O16} \to \text{Ne20} \to \text{C12} \to \text{He4} \to \text{H1}$.
2. **Re-align Active Burning Midpoint Thresholds in UI (`build_explorer_html.py` & `stellar_explorer.html`)**:
   - Ensure the active burning checks in `getDetailedOnionShells` for `O16`, `Ne20`, and `C12` match the radial bounds of the newly segmented shells so their respective volumetric glow rings activate at stage 5.
3. **Rebuild Grid and Web Artifacts**:
   - Run `py -3 stellar_grid_engine.py` and `py -3 build_explorer_html.py`.

---

## 5. Verification Method

To independently reproduce this finding:

1. **Run the Onion Shell Inspection Script**:
   ```powershell
   cd C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project
   py -3 -c "
   import json
   data = json.load(open('stellar_grid_data.json', encoding='utf-8'))
   m25 = data['models']['0.014']['25.0']
   p5 = m25['profiles']['5']
   species = ['Fe56', 'Si28', 'Ne20', 'O16', 'C12', 'He4', 'H1']
   best = [max(species, key=lambda s: p5[s][i]) for i in range(len(p5['q']))]
   from itertools import groupby
   shells = [k for k, _ in groupby(best)]
   print('Observed 25 M_sun Stage 5 Shells:', shells)
   print('Count:', len(shells))
   assert len(shells) == 7, f'Expected 7 shells, found {len(shells)}: {shells}'
   "
   ```
   *Expected result*: Script will raise `AssertionError: Expected 7 shells, found 5: ['Fe56', 'Si28', 'O16', 'He4', 'H1']`.

2. **Verify Memory Watchdog Stress Suite**:
   ```powershell
   cd C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project
   py -3 -c "
   from unittest.mock import MagicMock, patch
   import memory_watchdog as mw
   dog = mw.MemoryWatchdog(emergency_threshold=84.0)
   with patch('psutil.virtual_memory', return_value=MagicMock(percent=84.5)):
       try:
           dog.check_memory(auto_pause=False)
           print('FAIL: Did not raise')
       except mw.MemoryCeilingExceeded:
           print('PASS: MemoryCeilingExceeded raised on 84.5%')
   "
   ```
