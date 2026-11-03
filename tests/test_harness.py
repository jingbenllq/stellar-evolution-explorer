#!/usr/bin/env python3
"""
Test Harness for Stellar Evolution Explorer E2E Test Suite.
Provides headless DOM parsing, JSON data inspection, and Node.js-based JavaScript
runtime simulation to test both static structure and dynamic behavior.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRID_DATA_PATH = PROJECT_ROOT / "stellar_grid_data.json"
BUILD_SCRIPT_PATH = PROJECT_ROOT / "build_explorer_html.py"
EXPLORER_HTML_PATH = PROJECT_ROOT / "stellar_explorer.html"


@dataclass
class TestResult:
    test_id: str
    name: str
    tier: int
    feature: str
    passed: bool
    milestone: str  # "M1", "M2", "M3"
    message: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class StellarExplorerHarness:
    """Headless test harness for inspecting data, DOM, and executing JavaScript."""

    def __init__(self) -> None:
        self.project_root = PROJECT_ROOT
        self.grid_data: Optional[Dict[str, Any]] = None
        self._cached_html: Optional[str] = None

    def load_grid_data(self) -> Dict[str, Any]:
        """Loads and caches the 28-model grid data."""
        if self.grid_data is None:
            if not GRID_DATA_PATH.exists():
                raise FileNotFoundError(f"Missing stellar grid dataset: {GRID_DATA_PATH}")
            with open(GRID_DATA_PATH, "r", encoding="utf-8") as f:
                self.grid_data = json.load(f)
        return self.grid_data

    def get_html_content(self) -> str:
        """Reads stellar_explorer.html if present, else extracts HTML_TEMPLATE from build script."""
        if self._cached_html is not None:
            return self._cached_html

        if EXPLORER_HTML_PATH.exists() and EXPLORER_HTML_PATH.stat().st_size > 50000:
            with open(EXPLORER_HTML_PATH, "r", encoding="utf-8", errors="replace") as f:
                self._cached_html = f.read()
            return self._cached_html

        if BUILD_SCRIPT_PATH.exists():
            content = BUILD_SCRIPT_PATH.read_text(encoding="utf-8", errors="replace")
            # Extract HTML_TEMPLATE = """..."""
            match = re.search(r'HTML_TEMPLATE\s*=\s*"""(.*?)"""', content, re.DOTALL)
            if match:
                self._cached_html = match.group(1)
                return self._cached_html

        raise FileNotFoundError("Neither stellar_explorer.html nor build_explorer_html.py could be found.")

    def extract_script(self) -> str:
        """Extracts the client-side JavaScript code embedded inside <script> tags."""
        html = self.get_html_content()
        # Find all script blocks
        scripts = re.findall(r"<script(?:\s+[^>]*)?>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
        # Join non-empty scripts, but strip out the massive raw JSON if present to keep evaluations fast
        script_parts = []
        for s in scripts:
            if "__GRID_DATA_JSON__" in s:
                # Mock or leave as placeholder
                script_parts.append(s)
            else:
                script_parts.append(s)
        return "\n\n".join(script_parts)

    def extract_css(self) -> str:
        """Extracts embedded CSS from <style> blocks."""
        html = self.get_html_content()
        styles = re.findall(r"<style(?:\s+[^>]*)?>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
        return "\n\n".join(styles)

    def run_node_js(self, js_code: str, timeout_sec: float = 10.0) -> Dict[str, Any]:
        """
        Executes a JavaScript snippet via Node.js in a mock headless browser environment.
        Returns a dict containing standard output, parsed JSON result, stderr, and exit code.
        """
        mock_env_header = """
// Mock Minimal Browser Environment
global.window = global;
global.document = {
    getElementById: function(id) {
        return {
            id: id,
            width: 600,
            height: 380,
            clientWidth: 600,
            clientHeight: 380,
            getBoundingClientRect: function() { return { left: 0, top: 0, width: 600, height: 380 }; },
            getContext: function(type) {
                return {
                    clearRect: function() {},
                    fillRect: function() {},
                    beginPath: function() {},
                    arc: function() {},
                    fill: function() {},
                    stroke: function() {},
                    moveTo: function() {},
                    lineTo: function() {},
                    closePath: function() {},
                    fillText: function() {},
                    strokeText: function() {},
                    setTransform: function(a,b,c,d,e,f) { this.transform = [a,b,c,d,e,f]; },
                    setLineDash: function() {},
                    drawImage: function() {},
                    font: '',
                    fillStyle: '',
                    strokeStyle: '',
                    lineWidth: 1,
                    textAlign: '',
                    textBaseline: ''
                };
            },
            style: {},
            classList: {
                _classes: new Set(),
                add: function(c) { this._classes.add(c); },
                remove: function(c) { this._classes.delete(c); },
                contains: function(c) { return this._classes.has(c); },
                toggle: function(c) { if (this._classes.has(c)) this._classes.delete(c); else this._classes.add(c); }
            },
            innerHTML: '',
            textContent: '',
            dataset: {},
            value: 0,
            addEventListener: function() {},
            querySelectorAll: function() { return []; }
        };
    },
    querySelectorAll: function() { return []; },
    createElement: function(tag) {
        return {
            tagName: tag,
            style: {},
            classList: { add: function(){}, remove: function(){} },
            setAttribute: function(){},
            getAttribute: function(){},
            appendChild: function(){},
            click: function(){}
        };
    },
    body: { appendChild: function(){}, removeChild: function(){} },
    addEventListener: function() {}
};
global.window.devicePixelRatio = 2.0;
global.window.innerWidth = 1440;
global.window.innerHeight = 900;
global.window.addEventListener = function() {};
global.Blob = function(parts, options) { this.parts = parts; this.options = options; };
global.URL = { createObjectURL: function(blob) { return 'blob:mock-url'; }, revokeObjectURL: function() {} };
"""
        full_code = mock_env_header + "\n" + js_code
        try:
            res = subprocess.run(
                ["node", "-e", full_code],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(self.project_root)
            )
            parsed_data = None
            for line in res.stdout.strip().split("\n"):
                if line.startswith("__TEST_OUT__:"):
                    try:
                        parsed_data = json.loads(line[len("__TEST_OUT__:") :])
                    except Exception:
                        pass
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "data": parsed_data,
                "success": res.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_sec}s",
                "data": None,
                "success": False
            }
        except Exception as e:
            return {
                "exit_code": -2,
                "stdout": "",
                "stderr": str(e),
                "data": None,
                "success": False
            }

    def check_element_exists(self, element_id: str) -> bool:
        """Checks if an element with the given ID exists in the HTML."""
        html = self.get_html_content()
        pattern = rf'id=["\']{re.escape(element_id)}["\']'
        return bool(re.search(pattern, html))

    def check_pattern_in_html(self, pattern: str, regex: bool = False) -> bool:
        """Checks if a pattern exists in the HTML."""
        html = self.get_html_content()
        if regex:
            return bool(re.search(pattern, html, re.DOTALL))
        return pattern in html

    def check_pattern_in_js(self, pattern: str, regex: bool = False) -> bool:
        """Checks if a pattern exists in the JavaScript code."""
        js = self.extract_script()
        if regex:
            return bool(re.search(pattern, js, re.DOTALL))
        return pattern in js

    def check_pattern_in_css(self, pattern: str, regex: bool = False) -> bool:
        """Checks if a pattern exists in CSS styles."""
        css = self.extract_css()
        if regex:
            return bool(re.search(pattern, css, re.DOTALL))
        return pattern in css
