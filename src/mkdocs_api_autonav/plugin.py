from __future__ import annotations

from typing import TYPE_CHECKING, cast

from mkdocs.config import Config
from mkdocs.config.config_options import Plugins
from mkdocs.config.defaults import get_schema
from mkdocs.plugins import BasePlugin, event_priority, get_plugin_logger
from rich import print  # noqa

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig

MOD_SYMBOL = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

# nav = ...
# mod_symbol = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

# ROOT = Path(__file__).parent.parent
# SRC = ROOT / "src"

# for path in sorted(SRC.rglob("*.py")):
#     module_path = path.relative_to(SRC).with_suffix("")
#     doc_path = path.relative_to(SRC).with_suffix(".md")
#     full_doc_path = Path("reference", doc_path)

#     parts = tuple(module_path.parts)

#     if parts[-1] == "__init__":
#         parts = parts[:-1]
#         doc_path = doc_path.with_name("index.md")
#         full_doc_path = full_doc_path.with_name("index.md")
#     if any(part.startswith("_") for part in parts):
#         continue

#     nav_parts = [f"{mod_symbol} {part}" for part in parts]
#     nav[tuple(nav_parts)] = doc_path.as_posix()

#     with mkdocs_gen_files.open(full_doc_path, "w") as fd:
#         ident = ".".join(parts)
#         fd.write(f"---\ntitle: {ident}\n---\n\n::: {ident}")

#     mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path.relative_to(ROOT))

# with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
#     nav_file.writelines(nav.build_literate_nav())

# mkdocs.config.config_options.Plugins
# 1059         def run_validation(self, value: object) -> plugins.PluginCollection:
# 1060             if not isinstance(value, (list, tuple, dict)):
# 1061                 raise ValidationError('Invalid Plugins configuration. Expected a list or dict.')
# 1062             self.plugins = plugins.PluginCollection()
# 1063             self._instance_counter: MutableMapping[str, int] = Counter()
# 1064             for name, cfg in self._parse_configs(value):
# 1065  ->             self.load_plugin_with_namespace(name, cfg)
# 1066             return self.plugins
# (Pdb++)

logger = get_plugin_logger("mkdocs-api-autonav")


class PluginConfig(Config):
    """Our configuration options."""


class AutoAPIPlugin(BasePlugin[PluginConfig]):  # type: ignore [no-untyped-call]
    """Auto API navigation plugin for MkDocs."""

    def on_config(self, config: MkDocsConfig) -> MkDocsConfig | None:
        """First event called on build. Run right after the user config is loaded."""
        # ensure that mkdocstrings is in the plugins list
        # if not, add it and log a warning
        if "mkdocstrings" not in config["plugins"]:
            for name, option in get_schema():
                if name == "plugins":
                    plugins_option = cast(Plugins, option)
                    plugins_option.load_plugin_with_namespace("mkdocstrings", {})
                    logger.info(
                        "'mkdocstrings' wasn't found in the plugins list. "
                        "It has been added automatically."
                    )
                    # this adds the mkdocstrings plugin to the config['plugins']
                    # but should we add it to config['plugins'] explicitly?
                    break
        return None

    @event_priority(-100)  # Run last
    def on_files(self, files: Files, config: MkDocsConfig) -> None:
        # config.nav = resolve_directories_in_nav(
        #     config.nav,
        #     files,
        #     nav_file_name=self.config.nav_file,
        #     implicit_index=self.config.implicit_index,
        #     markdown_config={
        #         'extensions': self.config.markdown_extensions,
        #         'extension_configs': self.config["mdx_configs"],
        #         'tab_length': self.config.tab_length,
        #     },
        # )
        self._files = files
