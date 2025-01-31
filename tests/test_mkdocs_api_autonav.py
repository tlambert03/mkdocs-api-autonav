from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from mkdocs.__main__ import build_command
from pytest import CaptureFixture, MonkeyPatch

from mkdocs_api_autonav.plugin import PluginConfig

FIXTURES = Path(__file__).parent / "fixtures"
REPO1 = FIXTURES / "repo1"

NAV_SECTION = PluginConfig.nav_section_title.default
API_URI = PluginConfig.api_root_uri.default


@pytest.fixture
def cfg() -> dict:
    return {
        "site_name": "My Library",
        "plugins": [
            "search",
            {"mkdocstrings": {}},
            {"api-autonav": {"modules": ["src/my_library"]}},
        ],
    }


@pytest.fixture
def repo1(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(REPO1, repo)
    monkeypatch.syspath_prepend(str(repo / "src"))
    return repo


def test_build(repo1: Path, cfg: dict) -> None:
    site = repo1.parent / "site"
    cfg_path = repo1 / "mkdocs.yml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(SystemExit) as e:
        build_command.main(["-f", str(cfg_path), "-d", str(site)])

    assert e.value.code == 0

    assert (ref := site / "reference").is_dir()
    assert (lib := ref / "my_library").is_dir()
    assert (lib / "index.html").is_file()
    assert (sub_mod := lib / "submod").is_dir()
    assert (sub_mod / "index.html").is_file()
    assert (sub_sub := sub_mod / "sub_submod").is_dir()
    assert (sub_sub / "index.html").is_file()


def test_build_without_mkdocstrings(
    repo1: Path, cfg: dict, capsys: CaptureFixture
) -> None:
    cfg["plugins"].remove({"mkdocstrings": {}})
    site = repo1.parent / "site"
    cfg_path = repo1 / "mkdocs.yml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(SystemExit) as e:
        build_command.main(["-f", str(cfg_path), "-d", str(site)])

    assert e.value.code == 0
    captured = capsys.readouterr()
    assert "'mkdocstrings' wasn't found in the plugins list" in captured.err

    # strict mode should error out
    cfg["strict"] = True
    site = repo1.parent / "site"
    cfg_path = repo1 / "mkdocs.yml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(SystemExit) as e:
        build_command.main(["-f", str(cfg_path), "-d", str(site)])

    assert e.value.code == 1


@pytest.mark.parametrize(
    "nav",
    [
        {"nav": ["index.md"]},
        {"nav": ["index.md", NAV_SECTION]},
        {"nav": ["index.md", {NAV_SECTION: API_URI}]},
        {"nav": ["index.md", {NAV_SECTION: "differentname/"}]},
        {"nav": ["index.md", {NAV_SECTION: ["some_file.md"]}]},
    ],
)
def test_build_with_nav(repo1: Path, cfg: dict, nav: dict) -> None:
    cfg_with_nav = {**cfg, **nav}
    cfg["strict"] = True
    site = repo1.parent / "site"
    cfg_path = repo1 / "mkdocs.yml"
    cfg_path.write_text(yaml.safe_dump(cfg_with_nav))
    with pytest.raises(SystemExit) as e:
        build_command.main(["-f", str(cfg_path), "-d", str(site)])

    assert e.value.code == 0

    assert (ref := site / "reference").is_dir()
    assert (lib := ref / "my_library").is_dir()
    assert (lib / "index.html").is_file()
    assert (sub_mod := lib / "submod").is_dir()
    assert (sub_mod / "index.html").is_file()
    assert (sub_sub := sub_mod / "sub_submod").is_dir()
    assert (sub_sub / "index.html").is_file()


def test_build_with_nav_conflict(repo1: Path, cfg: dict) -> None:
    cfg["strict"] = True
    cfg_with_nav = {**cfg, "nav": ["index.md", {NAV_SECTION: "differentname/"}]}
    site = repo1.parent / "site"
    cfg_path = repo1 / "mkdocs.yml"
    cfg_path.write_text(yaml.safe_dump(cfg_with_nav))
    with pytest.raises(SystemExit) as e:
        build_command.main(["-f", str(cfg_path), "-d", str(site)])

    assert e.value.code == 1
