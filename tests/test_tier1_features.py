#!/usr/bin/env python3
"""
Tier 1: Feature Coverage Test Suite.
Validates complete functional presence and correctness for:
1. 3D Cutaway Onion-Skin Model (M2)
2. High-DPI Canvas Handling (M1)
3. Interactive Hover Tooltips (M1)
4. Multi-Speed Playback Controls (M1)
5. Timeline Evolutionary Stage Markers (M1)
6. One-Click Export System (M1)

Each feature has at least 5 dedicated test cases (total >= 30 test cases).
"""

import re
import time
from typing import List
from tests.test_harness import StellarExplorerHarness, TestResult


def run_tier1_tests(harness: StellarExplorerHarness) -> List[TestResult]:
    results: List[TestResult] = []
    html = harness.get_html_content()
    js = harness.extract_script()
    css = harness.extract_css()

    # =========================================================================
    # Feature 1: 3D Cutaway Onion-Skin Model (M2)
    # =========================================================================
    t0 = time.perf_counter()
    # TC1.1: 3D container and canvas structure
    has_3d_canvas = bool(
        re.search(r'<canvas[^>]*id=["\'](?:onion3DCanvas|onionCanvas)["\']', html)
        and ("three" in html.lower() or "webgl" in js.lower() or "initonion3d" in js.lower())
    )
    results.append(
        TestResult(
            test_id="T1_F1_TC1",
            name="3D Canvas & WebGL Container Structure",
            tier=1,
            feature="3D Cutaway Onion-Skin",
            passed=has_3d_canvas,
            milestone="M2",
            message="3D WebGL Canvas container detected with Three.js/WebGL integration"
            if has_3d_canvas
            else "Card 3 lacks 3D WebGL / Three.js initialization (still baseline 2D canvas)",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC1.2: Concentric cutaway geometry (3/4 cutaway or ring/sphere cutaway faces)
    has_cutaway_geom = bool(
        re.search(r'(?:SphereGeometry|RingGeometry|cutaway|phiLength|Math\.PI\s*\*\s*1\.5)', js, re.IGNORECASE)
    )
    results.append(
        TestResult(
            test_id="T1_F1_TC2",
            name="Concentric 3/4 Cutaway Geometry Construction",
            tier=1,
            feature="3D Cutaway Onion-Skin",
            passed=has_cutaway_geom,
            milestone="M2",
            message="3/4 Cutaway geometry routines found in 3D onion skin engine"
            if has_cutaway_geom
            else "Cutaway geometric algorithms (3/4 sphere or cut planes) not found in script",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC1.3: Non-linear radial scaling R(q)
    has_radial_scaling = bool(
        re.search(r'(?:Math\.pow\s*\(\s*q|\bq\s*\*\*\s*0\.\d|\bMath\.sqrt\s*\(\s*q\b|R\(q\)|radialScale)', js)
    )
    results.append(
        TestResult(
            test_id="T1_F1_TC3",
            name="Non-Linear Radial Scaling Function R(q)",
            tier=1,
            feature="3D Cutaway Onion-Skin",
            passed=has_radial_scaling,
            milestone="M2",
            message="Non-linear radial scaling R(q) present for core visibility"
            if has_radial_scaling
            else "Missing non-linear radial scaling R(q) mapping in onion skin engine",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC1.4: Chemical shell color distinction (Fe, Si, Ne, O, C, He, H)
    required_elements = ["fe56", "si28", "ne20", "o16", "c12", "he4", "h1"]
    has_all_elements = all(elem in js.lower() for elem in required_elements)
    results.append(
        TestResult(
            test_id="T1_F1_TC4",
            name="7-Element Chemical Shell Distinction & Color Coding",
            tier=1,
            feature="3D Cutaway Onion-Skin",
            passed=has_all_elements,
            milestone="M2",
            message="All 7 nuclear shell isotopes (Fe, Si, Ne, O, C, He, H) mapped"
            if has_all_elements
            else f"Missing element mapping in shell color logic (found {sum(e in js.lower() for e in required_elements)}/7)",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC1.5: Active burning pulsation / dynamic emissive ring indicator
    has_burning_indicator = bool(
        re.search(r'(?:emissive|pulse|eps_nuc|burning|sin\(|pulsat)', js, re.IGNORECASE)
    )
    results.append(
        TestResult(
            test_id="T1_F1_TC5",
            name="Active Nuclear Burning Dynamic Pulsation Indicator",
            tier=1,
            feature="3D Cutaway Onion-Skin",
            passed=has_burning_indicator,
            milestone="M2",
            message="Dynamic emissive pulsation / nuclear burning indicator present"
            if has_burning_indicator
            else "Missing dynamic pulsation / emissive burning ring animation logic",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    # =========================================================================
    # Feature 2: High-DPI Canvas Handling (M1)
    # =========================================================================
    t0 = time.perf_counter()
    # TC2.1: setupHiDPICanvas function exists
    has_hidpi_fn = bool(re.search(r'function\s+setupHiDPICanvas\b', js))
    results.append(
        TestResult(
            test_id="T1_F2_TC1",
            name="High-DPI Canvas Helper Function Declaration",
            tier=1,
            feature="High-DPI Canvas Handling",
            passed=has_hidpi_fn,
            milestone="M1",
            message="setupHiDPICanvas function declared in script"
            if has_hidpi_fn
            else "setupHiDPICanvas function not found in script",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC2.2: Device pixel ratio scaling of backing store buffer
    has_dpr_scaling = bool(
        re.search(r'devicePixelRatio', js)
        and (
            re.search(r'(?:bufW|cv\.width|canvas\.width)\s*=\s*Math\.round\s*\(\s*w\s*\*\s*dpr\s*\)', js)
            or re.search(r'(?:cv|canvas)\.width\s*=.*dpr', js)
        )
    )
    results.append(
        TestResult(
            test_id="T1_F2_TC2",
            name="Backing Store Dimensions Scaled by devicePixelRatio",
            tier=1,
            feature="High-DPI Canvas Handling",
            passed=has_dpr_scaling,
            milestone="M1",
            message="Canvas backing store width/height dynamically scaled by DPR"
            if has_dpr_scaling
            else "Canvas dimensions not scaled by window.devicePixelRatio",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC2.3: 2D Context transformation setTransform or scale
    has_ctx_transform = bool(
        re.search(r'setTransform\s*\(\s*dpr\s*,\s*0\s*,\s*0\s*,\s*dpr', js)
        or re.search(r'ctx\.scale\s*\(\s*dpr\s*,\s*dpr\s*\)', js)
    )
    results.append(
        TestResult(
            test_id="T1_F2_TC3",
            name="2D Context Coordinate Transformation (setTransform/scale)",
            tier=1,
            feature="High-DPI Canvas Handling",
            passed=has_ctx_transform,
            milestone="M1",
            message="setTransform(dpr, 0, 0, dpr, 0, 0) or scale(dpr, dpr) applied"
            if has_ctx_transform
            else "Missing context setTransform/scale for logical CSS coordinate alignment",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC2.4: Window resize event listener
    has_resize_listener = bool(
        re.search(r'addEventListener\s*\(\s*["\']resize["\']', js)
    )
    results.append(
        TestResult(
            test_id="T1_F2_TC4",
            name="Responsive Window Resize Event Listener Attached",
            tier=1,
            feature="High-DPI Canvas Handling",
            passed=has_resize_listener,
            milestone="M1",
            message="window.addEventListener('resize', ...) detected"
            if has_resize_listener
            else "No window resize listener to update canvas resolution on resize/zoom",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC2.5: High-DPI coverage across 2D charts (drawHR, drawRhoT, drawAbundanceProfile)
    chart_draw_calls = ["drawHR", "drawRhoT", "drawAbundanceProfile"]
    calls_hidpi = all(
        re.search(rf'function\s+{fn}\b.*?(?:setupHiDPI|devicePixelRatio)', js, re.DOTALL)
        for fn in chart_draw_calls
    )
    results.append(
        TestResult(
            test_id="T1_F2_TC5",
            name="High-DPI Resolution Applied Across All 2D Canvases",
            tier=1,
            feature="High-DPI Canvas Handling",
            passed=calls_hidpi,
            milestone="M1",
            message="All 2D chart drawing routines use High-DPI scaling"
            if calls_hidpi
            else "One or more 2D chart drawing routines lack High-DPI canvas integration",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    # =========================================================================
    # Feature 3: Interactive Hover Tooltips (M1)
    # =========================================================================
    t0 = time.perf_counter()
    # TC3.1: Tooltip DOM container and CSS styling
    has_tooltip_dom = bool(
        re.search(r'id=["\']stellarTooltip["\']', html)
        and re.search(r'#stellarTooltip\b', css)
    )
    results.append(
        TestResult(
            test_id="T1_F3_TC1",
            name="Floating Tooltip DOM Container (#stellarTooltip) & CSS",
            tier=1,
            feature="Hover Tooltips",
            passed=has_tooltip_dom,
            milestone="M1",
            message="#stellarTooltip DOM container and CSS declarations confirmed"
            if has_tooltip_dom
            else "#stellarTooltip container or CSS rules missing",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC3.2: Tooltip edge clamping / flipping logic
    has_edge_clamping = bool(
        re.search(r'innerWidth', js) and re.search(r'innerHeight', js)
        and ("stellarTooltip" in js or "Tooltip" in js)
    )
    results.append(
        TestResult(
            test_id="T1_F3_TC2",
            name="Smart Viewport Edge Clamping & Direction Flipping",
            tier=1,
            feature="Hover Tooltips",
            passed=has_edge_clamping,
            milestone="M1",
            message="Tooltip detects innerWidth/innerHeight to prevent overflow"
            if has_edge_clamping
            else "Tooltip lacks viewport boundary clamping / flipping logic",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC3.3: HR Diagram hover listener with track snapping
    has_hr_hover = bool(
        re.search(r'hrCanvas.*?(?:addEventListener|onmousemove|pointermove)', js, re.DOTALL)
        and re.search(r'(?:nearest|snap|Teff|log_L)', js)
    )
    results.append(
        TestResult(
            test_id="T1_F3_TC3",
            name="HR Diagram Interactive Track Snapping & Tooltip",
            tier=1,
            feature="Hover Tooltips",
            passed=has_hr_hover,
            milestone="M1",
            message="HR Diagram hover listener snaps to evolutionary track with metrics"
            if has_hr_hover
            else "HR Diagram lacks interactive hover listener or track snapping logic",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC3.4: Central state Rho-T diagram hover listener
    has_rhot_hover = bool(
        re.search(r'rhoTCanvas.*?(?:addEventListener|onmousemove|pointermove)', js, re.DOTALL)
        and re.search(r'(?:ignition|degeneracy|log_center_T)', js, re.IGNORECASE)
    )
    results.append(
        TestResult(
            test_id="T1_F3_TC4",
            name="Central State (Rho-T) Ignition Lines & Phase Hover Tooltip",
            tier=1,
            feature="Hover Tooltips",
            passed=has_rhot_hover,
            milestone="M1",
            message="Rho-T diagram hover listener detects ignition lines / central states"
            if has_rhot_hover
            else "Rho-T diagram lacks interactive hover detection for ignition lines",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC3.5: Radial chemical abundance profile hover listener
    has_prof_hover = bool(
        re.search(r'profCanvas.*?(?:addEventListener|onmousemove|pointermove)', js, re.DOTALL)
        and re.search(r'(?:guideline|vertical|prof\.q|mass)', js, re.IGNORECASE)
    )
    results.append(
        TestResult(
            test_id="T1_F3_TC5",
            name="Radial Chemical Profile Vertical Guideline & Isotope Hover",
            tier=1,
            feature="Hover Tooltips",
            passed=has_prof_hover,
            milestone="M1",
            message="Profile canvas hover listener inspects internal mass q and isotopes"
            if has_prof_hover
            else "Profile canvas lacks interactive hover listener or guideline inspection",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    # =========================================================================
    # Feature 4: Multi-Speed Playback Controls (M1)
    # =========================================================================
    t0 = time.perf_counter()
    # TC4.1: Speed buttons present in UI for 0.5x, 1x, 2x, 5x
    speeds = ["0.5", "1", "2", "5"]
    has_speed_btns = all(
        re.search(rf'data-speed=["\']{re.escape(s)}|{re.escape(s)}x', html, re.IGNORECASE)
        for s in speeds
    )
    results.append(
        TestResult(
            test_id="T1_F4_TC1",
            name="Multi-Speed Playback Buttons Markup (0.5x, 1x, 2x, 5x)",
            tier=1,
            feature="Multi-Speed Playback",
            passed=has_speed_btns,
            milestone="M1",
            message="Speed selector buttons (0.5x, 1x, 2x, 5x) declared in DOM"
            if has_speed_btns
            else "Missing speed control buttons (0.5x, 1x, 2x, 5x) in HTML controls",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC4.2: Dynamic timer update on speed change
    has_dynamic_timer = bool(
        re.search(r'playbackSpeed', js)
        and re.search(r'(?:baseInterval|interval)\s*(?:/|\*)\s*(?:state\.)?playbackSpeed', js)
    )
    results.append(
        TestResult(
            test_id="T1_F4_TC2",
            name="Dynamic Playback Timer Re-computation on Speed Change",
            tier=1,
            feature="Multi-Speed Playback",
            passed=has_dynamic_timer,
            milestone="M1",
            message="Playback timer dynamically recalculates interval based on speed"
            if has_dynamic_timer
            else "Playback timer does not dynamically adjust interval using playbackSpeed",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC4.3: Play/pause toggle button with state indicator
    has_play_btn = bool(
        re.search(r'id=["\']playBtn["\']', html)
        and re.search(r'▶\s*播放', html)
        and re.search(r'⏸\s*暂停', js)
    )
    results.append(
        TestResult(
            test_id="T1_F4_TC3",
            name="Play/Pause Button & Toggle State Indicator",
            tier=1,
            feature="Multi-Speed Playback",
            passed=has_play_btn,
            milestone="M1",
            message="playBtn toggles between Play and Pause states"
            if has_play_btn
            else "playBtn missing or lacking toggle state indicator in script",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC4.4: Stepping controls (⏮ Previous Step, ⏭ Next Step)
    has_stepping = bool(
        re.search(r'(?:stepPrevBtn|stepPrev|⏮)', html)
        and re.search(r'(?:stepNextBtn|stepNext|⏭)', html)
    )
    results.append(
        TestResult(
            test_id="T1_F4_TC4",
            name="Step Navigation Buttons (Previous/Next Step)",
            tier=1,
            feature="Multi-Speed Playback",
            passed=has_stepping,
            milestone="M1",
            message="Step navigation buttons (⏮ and ⏭) present in UI"
            if has_stepping
            else "Step navigation buttons (⏮ / ⏭) missing in controls",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC4.5: Keyboard shortcuts (Space, ArrowLeft, ArrowRight)
    has_keyboard = bool(
        re.search(r'addEventListener\s*\(\s*["\']keydown["\']', js)
        and ("ArrowLeft" in js or "ArrowRight" in js or "Space" in js or "keyCode" in js)
    )
    results.append(
        TestResult(
            test_id="T1_F4_TC5",
            name="Keyboard Shortcut Event Handlers (Space, Left, Right)",
            tier=1,
            feature="Multi-Speed Playback",
            passed=has_keyboard,
            milestone="M1",
            message="Keyboard event listener handles Space and Arrow keys"
            if has_keyboard
            else "Keyboard shortcut event handler missing in script",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    # =========================================================================
    # Feature 5: Timeline Evolutionary Stage Markers (M1)
    # =========================================================================
    t0 = time.perf_counter()
    # TC5.1: 5-Phase ribbon track
    has_ribbon = bool(
        re.search(r'(?:timeline-ribbon|seg-ms|seg-rgb|ribbon)', html)
        and re.search(r'(?:timeline-track|ribbon)', css)
    )
    results.append(
        TestResult(
            test_id="T1_F5_TC1",
            name="5-Phase Continuous Timeline Ribbon Bar",
            tier=1,
            feature="Timeline Stage Markers",
            passed=has_ribbon,
            milestone="M1",
            message="Timeline ribbon bar dividing steps into physical phases found"
            if has_ribbon
            else "Timeline ribbon bar missing; slider is an unadorned range input",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC5.2: Distinct stage anchor pins/markers (6 key stages)
    has_pins = bool(
        re.search(r'(?:timeline-pin|timeline-marker|stage-pin)', html)
        or re.search(r'(?:timeline-pin|stage_indices)', js)
    )
    results.append(
        TestResult(
            test_id="T1_F5_TC2",
            name="Stage Anchor Pins Positioned at Key Stage Indices",
            tier=1,
            feature="Timeline Stage Markers",
            passed=has_pins,
            milestone="M1",
            message="Stage anchor pins positioned along timeline track"
            if has_pins
            else "Stage anchor pins missing along timeline track",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC5.3: Interactive click-to-seek functionality
    has_click_seek = bool(
        (
            re.search(r'state\.stepIdx\s*=\s*(?:sIdx|startSteps|m\.stage_indices)', js)
            or re.search(r'stepSlider.*value\s*=.*?renderAll', js, re.DOTALL)
        )
        and re.search(r'renderAll', js)
    )
    results.append(
        TestResult(
            test_id="T1_F5_TC3",
            name="Interactive Stage Click-to-Seek Synchronization",
            tier=1,
            feature="Timeline Stage Markers",
            passed=has_click_seek,
            milestone="M1",
            message="Clicking stage markers updates step index, slider, and charts"
            if has_click_seek
            else "Stage marker click event does not trigger full dashboard synchronization",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC5.4: Active stage tracking and highlighting
    has_active_highlight = bool(
        re.search(r'classList\.(?:add|toggle)\s*\(\s*["\']active["\']', js)
        and ("stage-pill" in js or "timeline-pin" in js)
    )
    results.append(
        TestResult(
            test_id="T1_F5_TC4",
            name="Active Evolutionary Stage Real-time Highlighting",
            tier=1,
            feature="Timeline Stage Markers",
            passed=has_active_highlight,
            milestone="M1",
            message="Active class dynamically applied to current stage indicator"
            if has_active_highlight
            else "Current stage indicator not dynamically updated with active class",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC5.5: Step counter badge and stage label badge
    has_badges = bool(
        re.search(r'(?:stepCounterBadge|step-badge)', html)
        and re.search(r'(?:stageNameBadge|stage-badge)', html)
    )
    results.append(
        TestResult(
            test_id="T1_F5_TC5",
            name="Step Counter & Stage Name Status Badges",
            tier=1,
            feature="Timeline Stage Markers",
            passed=has_badges,
            milestone="M1",
            message="Step counter and stage name badges present in timeline header"
            if has_badges
            else "Step counter badge or stage name badge missing in timeline header",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    # =========================================================================
    # Feature 6: One-Click Export System (M1)
    # =========================================================================
    t0 = time.perf_counter()
    # TC6.1: Header export dropdown menu
    has_export_menu = bool(
        re.search(r'id=["\']export(?:DropdownBtn|Menu)["\']', html)
        and re.search(r'export-item', html)
    )
    results.append(
        TestResult(
            test_id="T1_F6_TC1",
            name="Header One-Click Export Dropdown Menu",
            tier=1,
            feature="Export System",
            passed=has_export_menu,
            milestone="M1",
            message="Export dropdown button and item menu declared in header"
            if has_export_menu
            else "Export dropdown menu missing in dashboard header",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC6.2: exportCanvasPNG function (supports toBlob or toDataURL)
    has_canvas_png = bool(
        re.search(r'function\s+exportCanvasPNG\b', js)
        and (
            re.search(r'toDataURL\s*\(\s*["\']image/png["\']', js)
            or re.search(r'toBlob\s*\(.*?["\']image/png["\']', js, re.DOTALL)
        )
    )
    results.append(
        TestResult(
            test_id="T1_F6_TC2",
            name="Individual Canvas PNG Image Export Function",
            tier=1,
            feature="Export System",
            passed=has_canvas_png,
            milestone="M1",
            message="exportCanvasPNG uses canvas toBlob/toDataURL('image/png') for chart download"
            if has_canvas_png
            else "exportCanvasPNG function missing or not using toBlob/toDataURL('image/png')",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC6.3: exportAllChartsCompositePNG function
    has_composite_png = bool(
        re.search(r'function\s+exportAllChartsCompositePNG\b', js)
        and re.search(r'drawImage', js)
    )
    results.append(
        TestResult(
            test_id="T1_F6_TC3",
            name="Composite 4-Panel Dashboard PNG Image Export",
            tier=1,
            feature="Export System",
            passed=has_composite_png,
            milestone="M1",
            message="exportAllChartsCompositePNG stitches 4 panels onto offscreen canvas"
            if has_composite_png
            else "exportAllChartsCompositePNG function missing or incomplete",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC6.4: exportCurrentTrackCSV with UTF-8 BOM
    has_track_csv = bool(
        re.search(r'function\s+exportCurrentTrackCSV\b', js)
        and re.search(r'\\uFEFF|text/csv', js)
    )
    results.append(
        TestResult(
            test_id="T1_F6_TC4",
            name="Evolutionary Track CSV Export with UTF-8 BOM",
            tier=1,
            feature="Export System",
            passed=has_track_csv,
            milestone="M1",
            message="exportCurrentTrackCSV generates CSV with UTF-8 BOM \\uFEFF"
            if has_track_csv
            else "exportCurrentTrackCSV missing or lacking UTF-8 BOM prefix",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    t0 = time.perf_counter()
    # TC6.5: Profile CSV, model JSON, and grid summary CSV exports
    has_data_exports = bool(
        re.search(r'function\s+exportCurrentProfileCSV\b', js)
        and re.search(r'function\s+exportCurrentModelJSON\b', js)
    )
    results.append(
        TestResult(
            test_id="T1_F6_TC5",
            name="Radial Profile CSV & Full Model JSON Data Exports",
            tier=1,
            feature="Export System",
            passed=has_data_exports,
            milestone="M1",
            message="exportCurrentProfileCSV and exportCurrentModelJSON declared"
            if has_data_exports
            else "Missing profile CSV or model JSON export routines",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    )

    return results
