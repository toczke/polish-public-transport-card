"""Keep the provider capability table in README.md in sync with the code."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- provider-capabilities:start -->"
END = "<!-- provider-capabilities:end -->"


def _module():
    spec = importlib.util.spec_from_file_location(
        "provider_capabilities", ROOT / "scripts" / "provider_capabilities.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_readme_provider_capability_table_is_current():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert START in text and END in text
    section = text.split(START, 1)[1].split(END, 1)[0].strip()
    assert section == _module().render_markdown().strip()


def test_capability_table_covers_all_offered_providers():
    from mzkzg_transport.config_flow import PROVIDER_OPTIONS

    table = _module().render_markdown()
    for label in PROVIDER_OPTIONS.values():
        assert f"| {label} |" in table
    assert "| Gmina Czernica |" in table
