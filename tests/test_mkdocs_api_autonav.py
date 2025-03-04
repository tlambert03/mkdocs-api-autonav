from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from mkdocs.exceptions import Abort
from pytest import MonkeyPatch

from mkdocs_api_autonav.plugin import PluginConfig, _iter_modules

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

FIXTURES = Path(__file__).parent / "fixtures"
REPO1 = FIXTURES / "repo1"

NAV_SECTION = PluginConfig.nav_section_title.default
API_URI = PluginConfig.api_root_uri.default


def _build_command(config_file: str) -> None:
    from mkdocs import config
    from mkdocs.commands import build

    cfg = config.load_config(config_file)
    cfg.plugins.on_startup(command="build", dirty=False)
    try:
        build.build(cfg, dirty=False)
    finally:
        cfg.plugins.on_shutdown()


def cfg_dict(strict: bool = False) -> dict:
    return {
        "site_name": "My Library",
        "strict": strict,
        "plugins": [
            "search",
            {"mkdocstrings": {}},
            {
                "api-autonav": {
                    "modules": ["src/my_library"],
                    "exclude": ["my_library.exclude_me"],
                }
            },
        ],
    }


@pytest.fixture
def repo1(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(REPO1, repo)
    monkeypatch.syspath_prepend(str(repo / "src"))
    return repo


def test_build(repo1: Path) -> None:
    mkdocs_yml = repo1 / "mkdocs.yml"
    mkdocs_yml.write_text(yaml.safe_dump(cfg_dict()))
    _build_command(str(mkdocs_yml))

    assert (ref := repo1 / "site" / "reference").is_dir()
    assert (lib := ref / "my_library").is_dir()
    assert (lib / "index.html").is_file()
    assert (sub_mod := lib / "submod").is_dir()
    assert (sub_mod / "index.html").is_file()
    assert (sub_sub := sub_mod / "sub_submod").is_dir()
    assert (sub_sub / "index.html").is_file()
    assert not any(lib.rglob("*exclude_me*"))


def test_build_exclude_re(repo1: Path) -> None:
    mkdocs_yml = repo1 / "mkdocs.yml"
    cfg = cfg_dict()
    cfg["plugins"][2]["api-autonav"]["exclude"] = ["re:.*xcl.*"]
    mkdocs_yml.write_text(yaml.safe_dump(cfg))
    _build_command(str(mkdocs_yml))

    assert (ref := repo1 / "site" / "reference").is_dir()
    assert (lib := ref / "my_library").is_dir()
    assert not any(lib.rglob("*exclude_me*"))


def test_sorting(repo1: Path) -> None:
    package = repo1 / "src" / "my_library"
    (package / "z_submod.py").touch()
    (package / "a_submod.py").touch()
    modules = [
        x
        for x, *_ in _iter_modules(repo1 / "src" / "my_library", str(repo1), "skip")
        if not any(part.startswith("_") for part in x)
    ]
    assert modules == [
        ("my_library",),
        ("my_library", "a_submod"),
        ("my_library", "exclude_me"),
        ("my_library", "submod"),
        ("my_library", "submod", "sub_submod"),
        ("my_library", "z_submod"),
    ]


def test_build_without_mkdocstrings(repo1: Path, caplog: LogCaptureFixture) -> None:
    cfg = cfg_dict()
    cfg["plugins"].remove({"mkdocstrings": {}})
    mkdocs_yml = repo1 / "mkdocs.yml"
    mkdocs_yml.write_text(yaml.safe_dump(cfg))
    _build_command(str(mkdocs_yml))

    assert any(
        "api-autonav: 'mkdocstrings' wasn't found in the plugins list" in line
        for line in caplog.messages
    )

    # strict mode should error out
    cfg["strict"] = True
    mkdocs_yml.write_text(yaml.safe_dump(cfg))

    with pytest.raises(Abort):
        _build_command(str(mkdocs_yml))


NAV_CASES: list[tuple[bool, dict]] = [
    (True, {"nav": ["index.md"]}),
    (True, {"nav": [{"Home": "index.md"}]}),
    (True, {"nav": ["index.md", NAV_SECTION]}),
    (True, {"nav": ["index.md", {NAV_SECTION: API_URI}]}),
    (False, {"nav": ["index.md", {NAV_SECTION: "differentname/"}]}),
    (False, {"nav": ["index.md", {NAV_SECTION: ["some_file.md"]}]}),
]


@pytest.mark.parametrize("strict, nav", NAV_CASES)
def test_build_with_nav(
    repo1: Path, strict: bool, nav: dict, caplog: LogCaptureFixture
) -> None:
    cfg_with_nav = {**cfg_dict(strict=strict), **nav}
    mkdocs_yml = repo1 / "mkdocs.yml"
    mkdocs_yml.write_text(yaml.safe_dump(cfg_with_nav))
    _build_command(str(mkdocs_yml))

    expect_message = bool(
        isinstance(nav_dict := nav["nav"][-1], dict)
        and (nav_sec := nav_dict.get(NAV_SECTION))
        and nav_sec != API_URI
    )
    assert bool(caplog.messages) == expect_message

    assert (ref := repo1 / "site" / "reference").is_dir()
    assert (lib := ref / "my_library").is_dir()
    assert (lib / "index.html").is_file()
    assert (sub_mod := lib / "submod").is_dir()
    assert (sub_mod / "index.html").is_file()
    assert (sub_sub := sub_mod / "sub_submod").is_dir()
    assert (sub_sub / "index.html").is_file()


def test_build_with_nav_conflict(repo1: Path, caplog: LogCaptureFixture) -> None:
    cfg = cfg_dict(strict=True)
    cfg_with_nav = {**cfg, "nav": ["index.md", {NAV_SECTION: "differentname/"}]}
    mkdocs_yml = repo1 / "mkdocs.yml"
    mkdocs_yml.write_text(yaml.safe_dump(cfg_with_nav))
    with pytest.raises(Abort):
        _build_command(str(mkdocs_yml))

    assert caplog.messages[0].startswith(
        "api-autonav: Encountered pre-existing navigation section"
    )


def test_warns_on_bad_structure(repo1: Path, caplog: LogCaptureFixture) -> None:
    cfg = cfg_dict(strict=True)
    cfg["plugins"][2]["api-autonav"]["on_implicit_namespace_packge"] = "raise"
    mkdocs_yml = repo1 / "mkdocs.yml"
    mkdocs_yml.write_text(yaml.safe_dump(cfg))
    # add a submodule that doesn't have an __init__.py
    bad_sub = repo1 / "src" / "my_library" / "bad_submod"
    bad_sub.mkdir(parents=True)
    (bad_sub / "misses_init.py").touch()

    # by default, should raise a helpful error
    with pytest.raises(RuntimeError, match="Implicit namespace package"):
        _build_command(str(mkdocs_yml))

    caplog.clear()
    cfg["plugins"][2]["api-autonav"]["on_implicit_namespace_packge"] = "warn"
    mkdocs_yml.write_text(yaml.safe_dump(cfg))
    with pytest.raises(Abort):
        _build_command(str(mkdocs_yml))
    assert any(
        "api-autonav: Skipping implicit namespace package" in line
        for line in caplog.messages
    )

    caplog.clear()
    caplog.set_level("INFO")
    cfg["plugins"][2]["api-autonav"]["on_implicit_namespace_packge"] = "skip"
    mkdocs_yml.write_text(yaml.safe_dump(cfg))
    _build_command(str(mkdocs_yml))
    assert any(
        "api-autonav: Skipping implicit namespace package" in line
        for line in caplog.messages
    )


@pytest.mark.parametrize("strict, nav", NAV_CASES)
# duplicate my_library to my_library2 and add two top level submodules to config
def test_multi_package(repo1: Path, strict: bool, nav: dict) -> None:
    cfg_with_nav = {**cfg_dict(strict=strict), **nav}

    # add another package
    shutil.copytree(repo1 / "src" / "my_library", repo1 / "src" / "my_library2")
    cfg_with_nav["plugins"][2]["api-autonav"]["modules"].append("src/my_library2")

    # this is important to trigger a possible bug:
    mkdocs_yml = repo1 / "mkdocs.yml"
    mkdocs_yml.write_text(yaml.safe_dump(cfg_with_nav))
    _build_command(str(mkdocs_yml))
    assert (ref := repo1 / "site" / "reference").is_dir()


def test_index_py_module(repo1: Path) -> None:
    """Test the edge case of a module named index.py"""
    cfg = cfg_dict()
    repo1.joinpath("src", "my_library", "index.py").touch()
    mkdocs_yml = repo1 / "mkdocs.yml"
    mkdocs_yml.write_text(yaml.safe_dump(cfg))
    _build_command(str(mkdocs_yml))

    assert (ref := repo1 / "site" / "reference").is_dir()
    assert (lib := ref / "my_library").is_dir()
    assert (lib / "index.html").is_file()
    assert (sub_mod := lib / "index_py").is_dir()
    assert (sub_mod / "index.html").is_file()
