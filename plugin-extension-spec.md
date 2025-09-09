# Extending mkdocs-api-autonav for C/C++ Documentation Support

## Overview

Extend the `mkdocs-api-autonav` plugin to support documenting C/C++ source files (and potentially other languages) while maintaining complete backward compatibility with existing Python-focused configurations.

## Current State

The plugin currently:

- Only discovers Python files (`.py`)
- Hardcodes Python module logic in `_iter_modules` and `_module_markdown`
- Uses mkdocstrings with Python handler exclusively
- Assumes Python package structure with `__init__.py` files

## Requirements

1. **Support C/C++ file discovery** - Find and document `.c` and `.h` files
2. **Maintain backward compatibility** - All existing configs must work unchanged
3. **Clean abstraction** - Extensible pattern for future language support
4. **Flexible configuration** - Allow mixed language projects (Python + C in same docs)

## Possible other languages we want to support

- shell (with mkdocstrings-shell)

    ```yaml
    plugins:
    - mkdocstrings:
        default_handler: shell  # optional
    ```

    then in markdown:

    ```markdown
    ::: relative/path/to/script
        handler: shell
    ```

- typescript/javascript (with mkdocstrings-typescript)

    ```txt
    📁 ./
    ├── 📁 src/
    │   └── 📁 package1/
    ├──  typedoc.base.json
    └──  typedoc.json
    ```

    then, in markdown:

    ```markdown
    ::: @owner/packageName
        handler: typescript
    ```

## Implementation Strategy (partial?)

### 1. Create Discovery Strategy Abstraction

Create a new file `discovery.py` with the following base classes:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

@runtime_checkable
class FileDiscoveryStrategy(Protocol):
    """Protocol for file discovery strategies."""
    
    def discover(self, root: Path, docs_root: str) -> Iterator[tuple[tuple[str, ...], str]]:
        """
        Discover files and return documentation structure.
        
        Returns:
            Iterator of (name_parts, doc_path) tuples where:
            - name_parts: tuple like ('module', 'submodule') for navigation hierarchy
            - doc_path: string path where the virtual .md file will be created
        """
        ...
    
    def make_content(self, parts: tuple[str, ...], full_path: Path, options: dict) -> str:
        """
        Generate markdown content for the discovered file.
        
        Args:
            parts: Name parts for the file (e.g., ('foo', 'bar') for foo/bar.c)
            full_path: Full path to the actual source file
            options: Module-specific options from config
            
        Returns:
            Markdown content with appropriate mkdocstrings directive
        """
        ...
    
    def get_display_title(self, parts: tuple[str, ...], show_full: bool) -> str:
        """Get the display title for navigation."""
        ...
```

### 2. Implement Python Discovery (Refactor Existing)

Move existing Python logic into `PythonDiscovery` class in `discovery.py`:

```python
class PythonDiscovery:
    """Python module discovery - current implementation."""
    
    def __init__(self, exclude_private: bool = True, 
                 on_implicit_namespace_package: str = "warn"):
        self.exclude_private = exclude_private
        self.on_implicit_namespace_package = on_implicit_namespace_package
    
    def discover(self, root: Path, docs_root: str) -> Iterator[tuple[tuple[str, ...], str]]:
        # Move current _iter_modules logic here
        # Keep the exact same behavior
        pass
    
    def make_content(self, parts: tuple[str, ...], full_path: Path, options: dict) -> str:
        # Move current _module_markdown logic here
        # Returns "::: module.path" for mkdocstrings
        pass
    
    def get_display_title(self, parts: tuple[str, ...], show_full: bool) -> str:
        if show_full:
            return ".".join(parts)
        return parts[-1]
```

### 3. Implement C Discovery

Add `CDiscovery` class to `discovery.py`:

```python
class CDiscovery:
    """C/C++ source file discovery."""
    
    def __init__(self, 
                 include_headers: bool = True,
                 include_source: bool = True,
                 group_by_basename: bool = True,
                 file_extensions: list[str] = None):
        """
        Args:
            include_headers: Include .h/.hpp files
            include_source: Include .c/.cpp files  
            group_by_basename: Group foo.c and foo.h as single doc page
            file_extensions: Override default extensions
        """
        self.include_headers = include_headers
        self.include_source = include_source
        self.group_by_basename = group_by_basename
        self.file_extensions = file_extensions or self._get_default_extensions()
    
    def _get_default_extensions(self) -> list[str]:
        extensions = []
        if self.include_source:
            extensions.extend(['.c', '.cpp', '.cc', '.cxx'])
        if self.include_headers:
            extensions.extend(['.h', '.hpp', '.hh', '.hxx'])
        return extensions
    
    def discover(self, root: Path, docs_root: str) -> Iterator[tuple[tuple[str, ...], str]]:
        """
        Discover C/C++ files.
        
        If group_by_basename is True:
            - foo.c and foo.h -> single page at docs_root/foo.md
        Otherwise:
            - foo.c -> docs_root/foo_c.md
            - foo.h -> docs_root/foo_h.md
        """
        # Implementation details:
        # 1. Walk directory tree finding files with correct extensions
        # 2. Group by basename if requested
        # 3. Generate appropriate doc paths
        pass
    
    def make_content(self, parts: tuple[str, ...], full_path: Path, options: dict) -> str:
        """
        Generate mkdocstrings-c directive content.
        
        For grouped files (foo.c + foo.h), include both.
        """
        # Determine handler (mkdocstrings-c uses 'c' handler)
        handler = options.get('handler', 'c')
        
        # Build content based on what files exist
        # If this represents grouped files, include multiple directives
        content = f"""
---
title: {parts[-1]}
---

# {'.'.join(parts)}

::: {full_path}
    handler: {handler}
"""
        return content
    
    def get_display_title(self, parts: tuple[str, ...], show_full: bool) -> str:
        # For C files, might want different display logic
        # e.g., "foo.c" or just "foo" depending on grouping
        if show_full:
            return "/".join(parts)
        return parts[-1]
```

### 4. Update Plugin Configuration

Modify `PluginConfig` class in `plugin.py`:

```python
class SourceConfig(Config):
    """Configuration for a single source directory."""
    path = opt.Type(str, required=True)
    discovery = opt.Choice(choices=['python', 'c', 'auto'], default='auto')
    options = opt.Type(dict, default={})
    module_options = opt.Type(dict, default={})
    exclude = opt.ListOfItems[str](opt.Type(str), default=[])

class PluginConfig(Config):
    # Keep ALL existing options for backward compatibility
    modules = opt.ListOfPaths()  # Keep as-is, not required
    module_options = opt.Type(dict, default={})
    exclude = opt.ListOfItems[str](opt.Type(str), default=[])
    nav_section_title = opt.Type(str, default="API Reference")
    api_root_uri = opt.Type(str, default="reference")
    nav_item_prefix = opt.Type(str, default=MOD_SYMBOL)
    exclude_private = opt.Type(bool, default=True)
    show_full_namespace = opt.Type(bool, default=False)
    on_implicit_namespace_package = opt.Choice(
        default="warn", choices=["raise", "warn", "skip"]
    )
    
    # NEW: Flexible source configuration
    sources = opt.ListOfItems(opt.SubConfig(SourceConfig), default=[])
```

### 5. Create Discovery Registry

Add to `discovery.py`:

```python
# Registry of available discovery strategies
DISCOVERY_STRATEGIES = {
    'python': PythonDiscovery,
    'c': CDiscovery,
    # Future: 'rust': RustDiscovery, etc.
}

def create_discovery_strategy(discovery_type: str, options: dict) -> FileDiscoveryStrategy:
    """Factory function to create discovery strategies."""
    if discovery_type == 'auto':
        # Auto-detection logic could go here
        # For now, default to python
        discovery_type = 'python'
    
    strategy_class = DISCOVERY_STRATEGIES.get(discovery_type)
    if not strategy_class:
        raise ValueError(f"Unknown discovery strategy: {discovery_type}")
    
    return strategy_class(**options)
```

### 6. Update Plugin's on_files Method

Modify the `on_files` method in `AutoAPIPlugin`:

```python
def on_files(self, files: Files, /, *, config: MkDocsConfig) -> None:
    """Called after the files collection is populated from the `docs_dir`."""
    
    # Build unified source list from both old and new config
    sources = self._build_sources_list()
    
    for source_config in sources:
        # Create appropriate discovery strategy
        strategy = create_discovery_strategy(
            source_config.discovery, 
            source_config.options
        )
        
        # Process exclusions (both global and per-source)
        exclude_patterns, exclude_paths = self._process_exclusions(
            self.config.exclude + source_config.exclude
        )
        
        # Discover and document files
        for name_parts, docs_path in strategy.discover(
            Path(source_config.path), 
            self.config.api_root_uri
        ):
            # Check exclusions
            if self._should_exclude(name_parts, exclude_patterns, exclude_paths):
                logger.info("Excluding %r due to config.exclude", ".".join(name_parts))
                continue
            
            # Generate content
            full_path = self._resolve_full_path(source_config.path, name_parts)
            content = strategy.make_content(
                name_parts, 
                full_path,
                source_config.module_options
            )
            
            # Create virtual file
            logger.info("Documenting %r in virtual file: %s", 
                       ".".join(name_parts), docs_path)
            file = File.generated(config, src_uri=docs_path, content=content)
            if file.src_uri in files.src_uris:
                files.remove(file)
            files.append(file)
            
            # Update navigation
            display_title = strategy.get_display_title(
                name_parts, 
                self.config.show_full_namespace
            )
            self.nav.add_path(name_parts, docs_path, file=file)

def _build_sources_list(self) -> list:
    """Combine legacy 'modules' config with new 'sources' config."""
    sources = []
    
    # Convert legacy modules to source configs
    for module_path in self.config.modules:
        sources.append(SourceConfig(
            path=module_path,
            discovery='python',  # Legacy modules are always Python
            options={
                'exclude_private': self.config.exclude_private,
                'on_implicit_namespace_package': self.config.on_implicit_namespace_package
            },
            module_options=self.config.module_options,
            exclude=[]  # Use global exclude for legacy
        ))
    
    # Add new sources
    sources.extend(self.config.sources)
    
    return sources

def _process_exclusions(self, exclude_list):
    """Process exclusion patterns."""
    exclude_patterns = []
    exclude_paths = []
    
    for pattern in exclude_list:
        if pattern.startswith("re:"):
            try:
                exclude_patterns.append(re.compile(pattern[3:]))
            except re.error:
                logger.error("Invalid regex pattern: %s", pattern[3:])
        else:
            exclude_paths.append(pattern)
    
    return exclude_patterns, exclude_paths

def _should_exclude(self, name_parts, exclude_patterns, exclude_paths):
    """Check if a path should be excluded."""
    path_str = ".".join(name_parts)
    
    # Check direct path exclusions
    if any(path_str == x or path_str.startswith(x + ".") for x in exclude_paths):
        return True
    
    # Check regex exclusions
    if any(pattern.search(path_str) for pattern in exclude_patterns):
        return True
    
    return False
```

## Usage Examples

### Example 1: Mixed Python and C Project

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          import:
            - https://docs.python.org/3/objects.inv
        c:  # Requires mkdocstrings-c to be installed
          # C-specific options
  
  - api-autonav:
      sources:
        # Python bindings
        - path: 'src/pyarv'
          discovery: python
          
        # C library
        - path: 'src/arv'
          discovery: c
          options:
            group_by_basename: true
            include_headers: true
            include_source: true
          module_options:
            handler: c
            # Any mkdocstrings-c specific options
```

### Example 2: Backward Compatible Python-Only

```yaml
# This still works exactly as before
plugins:
  - api-autonav:
      modules: ['src/my_library']
      exclude_private: true
```

### Example 3: Advanced C Configuration

```yaml
plugins:
  - api-autonav:
      sources:
        - path: 'src/arv'
          discovery: c
          options:
            group_by_basename: false  # Separate pages for .c and .h
            file_extensions: ['.c', '.h', '.cpp', '.hpp']
          exclude:
            - 're:.*_internal\.c'  # Exclude internal C files
            - 'test_'  # Exclude test files
```

## Testing Plan

1. **Backward Compatibility Tests**
   - Ensure all existing Python configurations work unchanged
   - Test with various `modules` configurations
   - Verify navigation generation is identical

2. **C Discovery Tests**
   - Test discovery of .c and .h files
   - Test grouping by basename
   - Test exclusion patterns for C files

3. **Mixed Language Tests**
   - Test projects with both Python and C sources
   - Verify navigation structure for mixed projects

4. **Edge Cases**
   - Empty directories
   - Files with no extensions
   - Deeply nested C source trees
   - Name conflicts (foo.py and foo.c in different directories)

## Migration Guide for Users

### For Existing Users

No changes needed! Your current configuration will continue to work.

### For C/C++ Projects

1. Install `mkdocstrings-c` handler
2. Add C sources using the new `sources` configuration
3. Configure C-specific options as needed

### For Mixed Projects

Use the `sources` list to specify different discovery strategies for different directories.

## Implementation Notes

1. **Import Discovery Strategies Lazily** - Only import when needed to avoid dependencies
2. **Maintain Existing Code Paths** - Keep `_iter_modules` and `_module_markdown` as private methods that delegate to `PythonDiscovery`
3. **Preserve Navigation Behavior** - The navigation tree building should work identically for Python files
4. **Documentation** - Update README.md with new configuration options and examples

## Future Extensions

This pattern makes it easy to add support for:

- Rust (using mkdocstrings-rust)
- Go
- JavaScript/TypeScript
- Any language with a mkdocstrings handler

Just add a new discovery strategy class and register it in `DISCOVERY_STRATEGIES`.
