"""Discovery strategies for different programming languages."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

import yaml
from mkdocs.plugins import get_plugin_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    WarnRaiseSkip = Literal["warn", "raise", "skip"]

logger = get_plugin_logger("api-autonav")


@runtime_checkable
class FileDiscoveryStrategy(Protocol):
    """Protocol for file discovery strategies."""

    def discover(
        self, root: Path, docs_root: str
    ) -> Iterator[tuple[tuple[str, ...], str]]:
        """
        Discover files and return documentation structure.

        Returns
        -------
            Iterator of (name_parts, doc_path) tuples where:
            - name_parts: tuple like ('module', 'submodule') for navigation hierarchy
            - doc_path: string path where the virtual .md file will be created
        """
        ...

    def make_content(
        self, parts: tuple[str, ...], full_path: Path, options: dict
    ) -> str:
        """
        Generate markdown content for the discovered file.

        Parameters
        ----------
        parts : tuple[str, ...]
            Name parts for the file (e.g., ('foo', 'bar') for foo/bar.c)
        full_path : Path
            Full path to the actual source file
        options : dict
            Module-specific options from config

        Returns
        -------
            Markdown content with appropriate mkdocstrings directive
        """
        ...

    def get_display_title(self, parts: tuple[str, ...], show_full: bool) -> str:
        """Get the display title for navigation."""
        ...


class PythonDiscovery:
    """Python module discovery - current implementation."""

    def __init__(
        self,
        exclude_private: bool = True,
        on_implicit_namespace_package: WarnRaiseSkip = "warn",
    ):
        self.exclude_private = exclude_private
        if on_implicit_namespace_package not in ("warn", "raise", "skip"):
            raise ValueError(
                "on_implicit_namespace_package must be one of 'warn', 'raise' or 'skip'"
            )
        self.on_implicit_namespace_package: WarnRaiseSkip = (
            on_implicit_namespace_package
        )

    def discover(
        self, root: Path, docs_root: str
    ) -> Iterator[tuple[tuple[str, ...], str]]:
        """Discover Python modules using the existing logic."""
        for abs_path in sorted(
            self._iter_py_files(root, self.on_implicit_namespace_package)
        ):
            rel_path = abs_path.relative_to(root.parent)
            doc_path = rel_path.with_suffix(".md")
            full_doc_path = Path(docs_root, doc_path)
            parts = tuple(rel_path.with_suffix("").parts)

            if parts[-1] == "__init__":
                parts = parts[:-1]
                doc_path = doc_path.with_name("index.md")
                full_doc_path = full_doc_path.with_name("index.md")
            if parts[-1] == "index":
                # deal with the special case of a module named 'index.py'
                # we don't want to name it index.md, since that is a special
                # name for a directory index
                full_doc_path = full_doc_path.with_name("index_py.md")

            yield parts, str(full_doc_path)

    def make_content(
        self, parts: tuple[str, ...], full_path: Path, options: dict
    ) -> str:
        """Generate Python mkdocstrings content."""
        mod_identifier = ".".join(parts)  # top_module.sub.sub_sub
        # very useful default... but can be overridden
        content_options = {"heading_level": 1}

        for option in options:
            if re.match(option, mod_identifier):
                # if the option is a regex, it matches the module identifier
                content_options.update(options[option])

        # create the actual markdown that will go into the virtual file
        if int(content_options.get("heading_level", 1)) > 1:
            h1 = f"# {mod_identifier}"
        else:
            h1 = ""
            content_options.setdefault("show_root_heading", True)

        md = f"""
        ---
        title: {self.get_display_title(parts, False)}
        ---
        {h1}

        ::: {mod_identifier}
        """

        options_str = yaml.dump({"options": content_options}, default_flow_style=False)
        md = dedent(md).lstrip() + indent(options_str, "    ")
        return md

    def get_display_title(self, parts: tuple[str, ...], show_full: bool) -> str:
        """Get the display title for navigation."""
        if show_full:
            return ".".join(parts)
        return parts[-1]

    def _iter_py_files(
        self, root_module: Path, on_implicit_namespace_package: WarnRaiseSkip
    ) -> Iterator[Path]:
        """Recursively collect all Python files starting at `root_module`."""
        root_path = Path(root_module)

        # Skip this directory entirely if it isn't an explicit package.
        if self._is_implicit_namespace_package(root_path):
            if on_implicit_namespace_package == "raise":
                raise RuntimeError(
                    f"Implicit namespace package (without an __init__.py file) "
                    f"detected at {root_path}.\nThis will likely cause a collection "
                    "error in mkdocstrings.  Set 'on_implicit_namespace_package' "
                    "to 'skip' to omit this package from the documentation, or "
                    "'warn' to include it anyway but log a warning."
                )
            else:
                if on_implicit_namespace_package == "skip":
                    logger.info(
                        "Skipping implicit namespace package (without an "
                        "__init__.py file) at %s",
                        root_path,
                    )
                else:  # on_implicit_namespace_package == "warn":
                    logger.warning(
                        "Skipping implicit namespace package (without an "
                        "__init__.py file) at %s. Set 'on_implicit_namespace_package' "
                        "to 'skip' to omit it without warning.",
                        root_path,
                    )
                return

        # Yield .py files in the current directory.
        for item in root_path.iterdir():
            if item.is_file() and item.suffix == ".py":
                yield item
            elif item.is_dir():
                yield from self._iter_py_files(item, on_implicit_namespace_package)

    def _is_implicit_namespace_package(self, path: Path) -> bool:
        """Return True if the given path is an implicit namespace package."""
        return not (path / "__init__.py").is_file() and any(path.glob("*.py"))


class CDiscovery:
    """C/C++ source file discovery."""

    def __init__(
        self,
        include_headers: bool = True,
        include_source: bool = True,
        group_by_basename: bool = True,
        file_extensions: list[str] | None = None,
    ):
        """Configure C discovery strategy.

        Parameters
        ----------
        include_headers : bool, optional
            Include header files (.h, .hpp, etc.), by default True
        include_source : bool, optional
            Include source files (.c, .cpp, etc.), by default True
        group_by_basename : bool, optional
            Group files with the same basename (e.g., foo.c and foo.h) into a
            single documentation page, by default True
        file_extensions : list[str] | None, optional
            Override default extensions, by default None which uses
            ['.c', '.cpp', '.cc', '.cxx'] for source and
            ['.h', '.hpp', '.hh', '.hxx'] for headers
        """
        self.include_headers = include_headers
        self.include_source = include_source
        self.group_by_basename = group_by_basename
        self.file_extensions = file_extensions or self._get_default_extensions()

    def _get_default_extensions(self) -> list[str]:
        extensions = []
        if self.include_source:
            extensions.extend([".c", ".cpp", ".cc", ".cxx"])
        if self.include_headers:
            extensions.extend([".h", ".hpp", ".hh", ".hxx"])
        return extensions

    def discover(
        self, root: Path, docs_root: str
    ) -> Iterator[tuple[tuple[str, ...], str]]:
        """
        Discover C/C++ files.

        If group_by_basename is True:
            - foo.c and foo.h -> single page at docs_root/foo.md
        Otherwise:
            - foo.c -> docs_root/foo_c.md
            - foo.h -> docs_root/foo_h.md
        """
        # Find all relevant files
        all_files: list[Path] = []
        for ext in self.file_extensions:
            all_files.extend(root.rglob(f"*{ext}"))

        # Group by basename if requested
        if self.group_by_basename:
            # Group files by their basename (without extension)
            groups: dict[tuple[str, ...], list[Path]] = {}
            for file_path in sorted(all_files):
                rel_path = file_path.relative_to(root)
                # Create parts from the directory structure + basename
                parts = (*rel_path.parent.parts, rel_path.stem)
                if parts not in groups:
                    groups[parts] = []
                groups[parts].append(file_path)

            # Yield one entry per group
            for parts, _file_paths in groups.items():
                doc_path = Path(docs_root) / Path(*parts[:-1]) / f"{parts[-1]}.md"
                yield parts, str(doc_path)
        else:
            # Individual files
            for file_path in sorted(all_files):
                rel_path = file_path.relative_to(root)
                # Create parts from the full path including extension
                parts = (*rel_path.parent.parts, rel_path.name.replace(".", "_"))
                doc_path = Path(docs_root) / Path(*parts[:-1]) / f"{parts[-1]}.md"
                yield parts, str(doc_path)

    def make_content(
        self, parts: tuple[str, ...], full_path: Path, options: dict
    ) -> str:
        """
        Generate mkdocstrings-c directive content.

        For grouped files (foo.c + foo.h), include both.
        """
        handler = options.get("handler", "c")
        basename = parts[-1] if parts else ""

        # Determine title and file paths based on grouping mode
        if self.group_by_basename:
            # Find all files with the same basename
            root = full_path.parent
            base_dir = root if len(parts) <= 1 else root / Path(*parts[:-1])

            file_paths = []
            if base_dir.exists():
                for ext in self.file_extensions:
                    candidate = base_dir / f"{basename}{ext}"
                    if candidate.exists():
                        file_paths.append(candidate)

            title = basename
            heading = ".".join(parts)
        else:
            # Single file
            file_paths = [full_path]
            title = basename
            heading = "/".join(parts)

        # Generate content using common template
        header = dedent(f"""
        ---
        title: {title}
        ---

        # {heading}
        """).strip()

        blocks = [header]
        for file_path in sorted(file_paths):
            block = dedent(f"""
            ::: {file_path!s}
                handler: {handler}
            """).strip()
            blocks.append(block)

        return "\n\n".join(blocks) + ("\n" if not self.group_by_basename else "")

    def get_display_title(self, parts: tuple[str, ...], show_full: bool) -> str:
        """Get the display title for navigation."""
        if show_full:
            return "/".join(parts)
        return parts[-1]


# Registry of available discovery strategies
DISCOVERY_STRATEGIES: dict[str, type[FileDiscoveryStrategy]] = {
    "python": PythonDiscovery,
    "c": CDiscovery,
    # Future: 'rust': RustDiscovery, etc.
}


def create_discovery_strategy(
    discovery_type: str, options: dict
) -> FileDiscoveryStrategy:
    """Factory function to create discovery strategies."""
    if discovery_type == "auto":
        # Auto-detection logic could go here
        # For now, default to python
        discovery_type = "python"

    strategy_class = DISCOVERY_STRATEGIES.get(discovery_type)
    if not strategy_class:
        raise ValueError(f"Unknown discovery strategy: {discovery_type}")

    return strategy_class(**options)
