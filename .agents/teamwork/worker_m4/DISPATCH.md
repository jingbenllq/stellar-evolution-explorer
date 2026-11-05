## 2026-11-04T23:49:56Z
[Message] timestamp=2026-11-04T23:49:56Z sender=28088124-758e-4368-81c8-9e195f03aa12 priority=MESSAGE_PRIORITY_HIGH content=You are worker_m4, a teamwork_worker subagent.
Your Working Directory: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\.agents\teamwork\worker_m4
Original Request Path: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\.agents\teamwork\ORIGINAL_REQUEST.md
Project Scope Document: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\PROJECT.md
Explorer Survey 3 Reference: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\.agents\teamwork\explorer_survey_3\handoff.md
Worker M3 Handoff Reference: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\.agents\teamwork\worker_m3\handoff.md

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md and PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Write Ownership:
You exclusively own:
- `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\build_explorer_html.py`
- `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\index.html`
- `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\stellar_explorer.html`
DO NOT modify `D:\天体物理导论/*`, `memory_watchdog.py`, `stellar_evolution/*`, or `tests/*`.

Milestone 4 Scope (Features F14, F15, F16, F17, F18, F19) — Stellar Interior Onion-Skin Diagram (洋葱图) Complete Overhaul:
1. Complete Scientific & Visual Redesign of the Onion-Skin Diagram:
   - Provide a clear, aesthetically refined, scientifically accurate cutaway/cross-section visual of the concentric nuclear burning shells:
     $\text{H} \to \text{He} \to \text{C} \to \text{Ne} \to \text{O} \to \text{Si} \to \text{Fe}$
     across all stellar masses ($0.3 - 25\,M_\odot$) and evolutionary stages (ZAMS, TAMS, RGB, CHeB, AGB, SN/Remnant).
   - Render internal zones distinguishing convective mixing regions (e.g. convective core or convective envelope with subtle churn / radial flow cues) from radiative regions (smooth stratification).
   - Add volumetric active nuclear burning ring glows ($\epsilon_{\text{nuc}}$ interfaces) with subtle pulsation animation at active burning boundaries (e.g. hydrogen burning shell, helium burning shell).
   - Tri-coordinate mapping toggle:
     * Normalized Mass fraction: $q = m/M_\star$
     * True physical radius: $r/R_\star$
     * Balanced logarithmic radius: $\log r$
   - 3D `THREE.Raycaster` mouse hover / click layer inspection on `#onionCanvas`:
     * When user hovers over layers or rings in the 3D cutaway sphere, display an interactive HUD / diagnostic tooltip with:
       - Layer name and dominant chemical isotope
       - Temperature ($T$), density ($\rho$), and pressure ($P$)
       - Mass fraction coordinate ($q$) and radial boundary
       - Dominant nuclear burning reaction (e.g., $4\text{H} \to \text{He}$, $3\alpha \to \text{C}$, ${}^{12}\text{C} + {}^{12}\text{C} \to {}^{20}\text{Ne} + \alpha$, etc.)
       - Local chemical abundance breakdown
   - 2D / 3D Dual-View Presentation Toggle:
     * Add a control toggle allowing the spectator to switch between the 3D interactive rotatable cutaway sphere and a 2D publication-grade cross-section schematic with concentric labeled rings and callout lines.
2. Build & Validate:
   - Implement all changes directly inside `build_explorer_html.py`.
   - Run `py -3 build_explorer_html.py` to regenerate `index.html` and `stellar_explorer.html`.
   - Verify both files are 100% byte-identical (`Compare-Object (Get-Content index.html) (Get-Content stellar_explorer.html)` is empty).
   - Verify embedded JavaScript has no syntax errors using `node -c`.
   - Run `py -3 -m unittest discover tests` and ensure all tests pass.

Write your report to `handoff.md` and notify orchestrator via send_message.
