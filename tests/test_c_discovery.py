"""Tests for C/C++ discovery functionality."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from mkdocs import config

from mkdocs_api_autonav.discovery import CDiscovery
from mkdocs_api_autonav.plugin import AutoAPIPlugin, PluginConfig

FIXTURES = Path(__file__).parent / "fixtures"
C_PROJECT = FIXTURES / "c_project"


def cfg_dict_c(**kwargs: Any) -> dict:
    """Configuration dictionary for C project testing."""
    return {
        "site_name": "C Project Test",
        "plugins": [
            {
                "mkdocstrings": {
                    "handlers": {
                        "c": {}  # C handler configuration
                    }
                }
            },
            {
                "api-autonav": {
                    "sources": [
                        {
                            "path": "src/arv",
                            "discovery": "c",
                            "options": {
                                "group_by_basename": True,
                                "include_headers": True,
                                "include_source": True,
                            },
                            "module_options": {"handler": "c"},
                        }
                    ],
                    **kwargs,
                }
            },
        ],
    }


@pytest.fixture
def c_project(tmp_path: Path) -> Path:
    """Copy the C project fixture to a temporary directory."""
    project = tmp_path / "c_project"
    shutil.copytree(C_PROJECT, project)
    return project


def test_c_discovery_grouped() -> None:
    """Test C file discovery with grouping by basename."""
    discovery = CDiscovery(
        include_headers=True,
        include_source=True,
        group_by_basename=True,
    )

    # Test with our fixture directory
    root = C_PROJECT / "src" / "arv"
    docs_root = "reference"

    discovered = list(discovery.discover(root, docs_root))

    # Should find arv and device (grouped)
    expected = [
        (("arv",), "reference/arv.md"),
        (("device",), "reference/device.md"),
    ]

    assert discovered == expected


def test_c_discovery_individual() -> None:
    """Test C file discovery without grouping."""
    discovery = CDiscovery(
        include_headers=True,
        include_source=True,
        group_by_basename=False,
    )

    root = C_PROJECT / "src" / "arv"
    docs_root = "reference"

    discovered = list(discovery.discover(root, docs_root))

    # Should find individual files
    # Files: arv.c, arv.h, device.c, device.h
    expected_files = ["arv_c", "arv_h", "device_c", "device_h"]
    discovered_names = [parts[0] for parts, _ in discovered]

    assert len(discovered) == 4
    assert all(name in expected_files for name in discovered_names)


def test_c_discovery_headers_only() -> None:
    """Test C file discovery with headers only."""
    discovery = CDiscovery(
        include_headers=True,
        include_source=False,
        group_by_basename=True,
    )

    root = C_PROJECT / "src" / "arv"
    docs_root = "reference"

    discovered = list(discovery.discover(root, docs_root))

    # Should still find grouped entries but only for headers
    expected = [
        (("arv",), "reference/arv.md"),
        (("device",), "reference/device.md"),
    ]

    assert discovered == expected


def test_c_make_content_grouped() -> None:
    """Test C content generation for grouped files."""
    discovery = CDiscovery(group_by_basename=True)

    # Test with the actual file structure we have
    parts = ("arv",)
    # The full_path needs to be set up so that parent gives us the right directory
    full_path = C_PROJECT / "src" / "arv" / "dummy"  # parent will be src/arv
    options = {"handler": "c"}

    content = discovery.make_content(parts, full_path, options)

    assert "title: arv" in content
    assert "# arv" in content
    # The content should include references to the found files
    lines = content.strip().split("\n")
    header_lines = [line for line in lines if line.startswith(":::")]
    assert len(header_lines) >= 1  # Should find at least arv.c or arv.h
    assert "handler: c" in content


def test_c_make_content_individual() -> None:
    """Test C content generation for individual files."""
    discovery = CDiscovery(group_by_basename=False)

    parts = ("arv_c",)
    full_path = C_PROJECT / "src" / "arv" / "arv.c"
    options = {"handler": "c"}

    content = discovery.make_content(parts, full_path, options)

    assert "title: arv_c" in content
    assert "# arv_c" in content
    assert str(full_path) in content
    assert "handler: c" in content


def test_c_display_title() -> None:
    """Test C display title generation."""
    discovery = CDiscovery()

    parts = ("path", "to", "file")

    # Test show_full = True
    title_full = discovery.get_display_title(parts, show_full=True)
    assert title_full == "path/to/file"

    # Test show_full = False
    title_short = discovery.get_display_title(parts, show_full=False)
    assert title_short == "file"


def test_c_custom_extensions() -> None:
    """Test C discovery with custom file extensions."""
    discovery = CDiscovery(
        include_headers=True,
        include_source=True,
        group_by_basename=True,
        file_extensions=[".h", ".c"],  # Only basic extensions
    )

    root = C_PROJECT / "src" / "arv"
    docs_root = "reference"

    discovered = list(discovery.discover(root, docs_root))

    # Should still find the same files since our fixture uses .h and .c
    expected = [
        (("arv",), "reference/arv.md"),
        (("device",), "reference/device.md"),
    ]

    assert discovered == expected


def test_build_c_project_integration(c_project: Path) -> None:
    """Integration test: build C project documentation."""
    mkdocs_yml = c_project / "mkdocs.yml"

    # Note: This test will only work if mkdocstrings-c is installed
    # For now, we'll just test the configuration loading
    try:
        cfg = config.load_config(str(mkdocs_yml))

        # Verify our plugin is loaded
        plugin_names = [p for p in cfg.plugins if isinstance(p, str)]
        assert "api-autonav" in plugin_names or any(
            "api-autonav" in str(p) for p in cfg.plugins
        )

    except ImportError:
        pytest.skip("MkDocs not available for integration testing")


def test_backwards_compatibility_python() -> None:
    """Test that existing Python configurations still work."""
    # This should use the legacy modules configuration

    # Should not raise any validation errors

    plugin_config = PluginConfig()
    plugin_config.load_dict(
        {
            "modules": ["src/my_library"],
            "exclude_private": True,
        }
    )

    # Verify that the plugin can build sources list correctly
    plugin = AutoAPIPlugin()
    plugin.config = plugin_config

    sources = plugin._build_sources_list()

    assert len(sources) == 1
    assert sources[0]["path"] == "src/my_library"
    assert sources[0]["discovery"] == "python"
    assert sources[0]["options"]["exclude_private"] is True
