import pytest

from mkdocs_api_autonav.plugin import AutoAPIPlugin, PluginConfig


def make_plugin(show_full_namespace: bool) -> AutoAPIPlugin:
    plugin = AutoAPIPlugin()
    cfg = PluginConfig()
    cfg.show_full_namespace = show_full_namespace  # pyright: ignore
    object.__setattr__(plugin, "config", cfg)
    return plugin


@pytest.mark.parametrize("show_full_namespace", [True, False])
def test_nav_title_namespace(show_full_namespace: bool) -> None:
    # Simulate a module path
    parts = ("vllm", "distributed", "device_communicators", "cpu_communicator")
    plugin = make_plugin(show_full_namespace)
    md = plugin._module_markdown(parts)
    # Parse YAML front-matter
    title = md.split("---\n")[1].split("\n")[0].replace("title: ", "")
    expect = (
        "vllm.distributed.device_communicators.cpu_communicator"
        if show_full_namespace
        else "cpu_communicator"
    )
    assert title == expect
