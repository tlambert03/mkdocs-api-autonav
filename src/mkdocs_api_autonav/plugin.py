"""api-autonav plugin for MkDocs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

import mkdocs
import mkdocs.config
import mkdocs.config.config_options
from mkdocs.config import Config
from mkdocs.config.config_options import Plugins
from mkdocs.config.defaults import get_schema
from mkdocs.plugins import BasePlugin, get_plugin_logger
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Section
from mkdocs.structure.pages import Page

if TYPE_CHECKING:
    from collections.abc import Iterator

    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure import StructureItem
    from mkdocs.structure.nav import Navigation


PLUGIN_NAME = "api-autonav"  # must match [project.entry-points."mkdocs.plugins"]

# empty code block that renders as [mod] symbol
MOD_SYMBOL = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

logger = get_plugin_logger(PLUGIN_NAME)


class PluginConfig(Config):  # type: ignore [no-untyped-call]
    """Our configuration options."""

    modules = mkdocs.config.config_options.ListOfPaths()
    """List of paths to Python modules to include in the navigation."""
    nav_section_title = mkdocs.config.config_options.Type(str, default="API Reference")
    """Title for the API reference section as it appears in the navigation."""
    api_root_uri = mkdocs.config.config_options.Type(str, default="reference")
    """Root folder for api docs in the generated site."""
    nav_item_prefix = mkdocs.config.config_options.Type(str, default=MOD_SYMBOL)
    """A prefix to add to each module name in the navigation."""
    exclude_private = mkdocs.config.config_options.Type(bool, default=True)
    """Exclude modules that start with an underscore."""


class AutoAPIPlugin(BasePlugin[PluginConfig]):  # type: ignore [no-untyped-call]
    """API docs with navigation plugin for MkDocs."""

    nav: _NavNode

    def on_config(self, config: MkDocsConfig) -> MkDocsConfig | None:
        """First event called on build. Run right after the user config is loaded."""
        # ensure that mkdocstrings is in the plugins list
        # if not, add it and log a warning
        if "mkdocstrings" not in config["plugins"]:
            for name, option in get_schema():
                if name == "plugins":
                    plugins_option = cast(Plugins, option)
                    plugins_option.load_plugin_with_namespace("mkdocstrings", {})
                    logger.warning(
                        "'mkdocstrings' wasn't found in the plugins list. "
                        f"It has been added automatically by {PLUGIN_NAME}.\nPlease "
                        "ensure that 'mkdocstrings' is added to the plugins list."
                    )
                    # this adds the mkdocstrings plugin to the config['plugins']
                    # but should we add it to config['plugins'] explicitly?
                    break

        self.nav = _NavNode(name_prefix=self.config.nav_item_prefix)
        return None

    def _module_markdown(self, parts: tuple[str, ...]) -> str:
        """Create the content for the virtual file.

        Example
        -------
        >>> parts = ("top_module", "sub", "sub_sub")
        >>> print(_make_content(parts))
        ---
        title: top_module.sub.sub_sub
        ---

        ::: top_module.sub.sub_sub
        """
        mod_identifier = ".".join(parts)  # top_module.sub.sub_sub
        # create the actual markdown that will go into the virtual file
        return f"---\ntitle: {mod_identifier}\n---\n\n::: {mod_identifier}"

    def on_files(self, files: Files, /, *, config: MkDocsConfig) -> None:
        """Called after the files collection is populated from the `docs_dir`.

        Here we generate the virtual files that will be used to render the API
        (each )
        """
        exclude_private = self.config.exclude_private

        # for each top-level module specified in plugins.api-autonav.modules
        for module in self.config.modules:
            # iterate (recursively) over all modules in the package
            for name_parts, docs_path in _iter_modules(
                module, self.config.api_root_uri
            ):
                # parts looks like -> ('top_module', 'sub', 'sub_sub')
                # docs_path looks like -> api_root_uri/top_module/sub/sub_sub/index.md
                #   and refers to the location in the BUILT site directory
                if exclude_private and any(part.startswith("_") for part in name_parts):
                    continue

                # create the actual markdown that will go into the virtual file
                content = self._module_markdown(name_parts)

                # generate a mkdocs File object and add it to the collection
                logger.info("Writing virtual file: %s", docs_path)
                file = File.generated(config, src_uri=docs_path, content=content)
                files.append(file)

                # update our navigation tree
                self.nav.add_path(name_parts, docs_path)

        # Render the navigation tree to dict and add to config['nav']
        if cfg_nav := config.nav:
            _merge_nav(
                cfg_nav,
                self.config.nav_section_title,
                self.nav.as_dict(),
                self.config.api_root_uri,
            )
        # note, if there is NO existing nav, then mkdocs will
        # find the pages and include them in the nav automatically

    def on_nav(
        self, nav: Navigation, /, *, config: MkDocsConfig, files: Files
    ) -> Navigation:
        """Called after the navigation is created, but before it is rendered."""
        if not config.nav:
            # there was no nav specified in the config.
            # let's correct the autogenerated navigation, which will be lacking
            # titles, have the wrong name, and be missing prefixes.
            ref_section = next(
                item
                for item in nav.items
                if isinstance(item, Section) and item.title == "Reference"
            )

            self._fix_nav_item(ref_section)
            ref_section.title = self.config.nav_section_title
        return nav

    def _fix_nav_item(self, item: StructureItem) -> None:
        """Recursively fix titles of members in section.

        Section(title='Reference')
            Section(title='Module')
                Page(title=[blank], url='/reference/module/')

        Section(title='API Reference')
            Section(title='{prefix}module')
                Page(title='{prefix}module', url='/reference/module/')
        """
        if isinstance(item, Section):
            item.title = f"{self.config.nav_item_prefix}{item.title.lower()}"
            for child in item.children:
                self._fix_nav_item(child)
        elif isinstance(item, Page):
            if not item.title:
                parts = item.url.split("/")
                item.meta["title"] = f"{self.config.nav_item_prefix}{parts[-2]}"


# -----------------------------------------------------------------------------


def _iter_modules(
    root_module: Path | str, docs_root: str
) -> Iterator[tuple[tuple[str, ...], str]]:
    """Recursively collect all modules starting at `module_path`.

    Yields a tuple of parts (e.g. ('top_module', 'sub', 'sub_sub')) and the
    path where the corresponding documentation file should be written.
    """
    root_module = Path(root_module)
    for abs_path in sorted(root_module.rglob("*.py")):
        rel_path = abs_path.relative_to(root_module.parent)
        doc_path = rel_path.with_suffix(".md")
        full_doc_path = Path(docs_root, doc_path)
        parts = tuple(rel_path.with_suffix("").parts)

        if parts[-1] == "__init__":
            parts = parts[:-1]
            doc_path = doc_path.with_name("index.md")
            full_doc_path = full_doc_path.with_name("index.md")

        yield parts, str(full_doc_path)


def _merge_nav(
    cfg_nav: list, nav_section_title: str, nav_dict: dict, root: str
) -> None:
    """Mutate cfg_nav list in place, to add in our own nav_dict.

    nav_dict is (likely) constructed during on_files, and represents the
    navigation structure for the API reference section.
    """
    # look for existing nav items that match the API header
    for position, item in enumerate(list(cfg_nav)):
        if isinstance(item, str) and item == nav_section_title:
            # someone simply placed the string ref... replace with full nav dict
            cfg_nav[position] = {nav_section_title: [nav_dict]}
            return

        if isinstance(item, dict):
            name, value = next(iter(item.items()))
            if name != nav_section_title:
                continue  # pragma: no cover

            # if we get here, it means that the API section already exists
            # we need to merge in our navigation info
            if isinstance(value, str):
                # The section exists and it is a single string, perhaps
                # associated with literate-nav-type items to come later?
                # let's put our stuff here, but assert the name of the directory
                # matches where we expect to put the API docs.
                if value not in {root.rstrip("/"), root.rstrip("/") + "/"}:
                    # unexpected...
                    logger.error(
                        "Encountered pre-existing navigation section %r "
                        "with unexpected value %r (expected %r). "
                        "Skipping...",
                        name,
                        value,
                        root,
                    )
                    return

                # replace the string with our full nav dict
                cfg_nav[position] = {nav_section_title: [nav_dict]}
                return

            if isinstance(value, list):
                # The section exists and it is already a list of items
                # append our new nav to the list
                value.append(nav_dict)
                return

    # we've reached the end of the list without finding the API section
    # add it to the end
    cfg_nav.append({nav_section_title: [nav_dict]})


@dataclass
class _NavNode:
    """Simple helper node used while building the navigation tree."""

    doc_path: str | None = None
    children: dict[str, _NavNode] = field(default_factory=dict)
    name_prefix: str = ""

    def as_dict(self) -> dict:
        return {
            f"{self.name_prefix}{name}": node.as_obj()
            for name, node in self.children.items()
        }

    def add_path(self, parts: tuple[str, ...], doc_path: str) -> None:
        """Add a path to the tree."""
        node = self
        for part in parts:
            if part not in node.children:
                node.children[part] = _NavNode(name_prefix=node.name_prefix)
            node = node.children[part]
        node.doc_path = doc_path

    def as_obj(self) -> list | str:
        """Convert the tree to nested list/dict form."""
        if not self.children:
            return self.doc_path or ""

        # Has children -> return a list
        result: list[str | dict[str, str | list]] = []
        if self.doc_path:
            # Put the doc_path first, if it exists
            result.append(self.doc_path)

        # Then each child is {child_name: child_structure}
        # (in insertion order or sorted—here we just rely on insertion order)
        for child_name, child_node in self.children.items():
            result.append(
                {f"{child_node.name_prefix}{child_name}": child_node.as_obj()}
            )
        return result
