# mkdocs-api-autonav

[![License](https://img.shields.io/pypi/l/mkdocs-api-autonav.svg?color=green)](https://github.com/tlambert03/mkdocs-api-autonav/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/mkdocs-api-autonav.svg?color=green)](https://pypi.org/project/mkdocs-api-autonav)
[![Python Version](https://img.shields.io/pypi/pyversions/mkdocs-api-autonav.svg?color=green)](https://python.org)
[![CI](https://github.com/tlambert03/mkdocs-api-autonav/actions/workflows/ci.yml/badge.svg)](https://github.com/tlambert03/mkdocs-api-autonav/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tlambert03/mkdocs-api-autonav/branch/main/graph/badge.svg)](https://codecov.io/gh/tlambert03/mkdocs-api-autonav)

Autogenerate API reference including navigation for all submodules, with
[mkdocstrings](https://github.com/mkdocstrings/mkdocstrings).

*(removes the need for using a [custom script](#why-this-plugin) alongside `mkdocs-gen-files` and `literate-nav`)*

## Quick Start

```shell
pip install mkdocs-api-autonav
```

```yaml
# mkdocs.yml
site_name: "My Library"

plugins:
- search
- mkdocstrings:
- api-autonav:
    modules: ['src/my_library']
```

> [!IMPORTANT]
> This plugin depends on `mkdocs>=1.6` (*Released: Apr 20, 2024*)

### Configuration

Here are all the configurables, along with their default values.

```yaml
plugins:
- api-autonav:
    modules: []
    module_options: {}
    nav_section_title: "API Reference"
    api_root_uri: "reference"
    nav_item_prefix: "<code class='doc-symbol doc-symbol-nav doc-symbol-module'></code>"
    exclude_private: true
    on_implicit_namespace_package: "warn"
```

- **`modules`** (`list[str]`)- List of paths to Python modules to include in the
  navigation, relative to the project root.  This is the only required
  configuration. (e.g., `["src/package"]`)
- **`module_options`** (`dict[str, dict]`) - Dictionary of local options to pass to
  `mkdocstrings` for specific modules. The keys are python identifiers (e.g.,
  `package.module`) and the values are dictionaries of [local options to pass to
  `mkdocstrings`](https://mkdocstrings.github.io/python/usage/#globallocal-options)
  for that specific module.

  ```yaml
  - api-autonav:
      modules: ['src/package']
      module_options:
        package.submodule:
          docstring_style: google
          show_signature: false
  ```

- **`exclude`** (`list[str]`) - List of module paths or patterns to exclude.
  Can be specified as exact module paths (e.g., `["package.module"]`),
  which will also exclude any submodules, or as regex patterns prefixed with `'re:'`
  (e.g., `["re:package\\.utils\\..*"]`). Regex patterns are matched against the full
  module path.
- **`nav_section_title`** (`str`) - Title for the API reference section as it appears in
  the navigation. Default is "API Reference"
- **`api_root_uri`** (`str`) - Root folder for api docs in the generated site. This
  determines the url path for the API documentation. Default is "reference"
- **`nav_item_prefix`** (`str`) - A prefix to add to each module name in the
  navigation.  By default, renders a `[mod]` badge before each module.
  Set to the empty string to disable this.
- **`exclude_private`** (`bool`) - Exclude modules that start with an underscore
- **`on_implicit_namespace_package`** (`str`) - What to do when an [implicit
  namespace package](https://peps.python.org/pep-0420/) is found. An "implicit
  namespace package" is a directory that contains python files, but no
  `__init__.py` file; these will likely cause downstream errors for mkdocstrings.
  Options include:
    - `"raise"` - immediately stop and raise an error
    - `"warn"` - log a warning, and continue (omitting the namespace package)
    - `"skip"` - silently omit the namespace package and its children

### Integration with nav

No `nav` configuration is required in `mkdocs.yml`, but in most cases you will want to
have one anyway.  Here are the rules for how this plugin integrates with your
existing `nav` configuration.

1. **If `<nav_section_title>` exists and is explicitly referenced as a string**

    If your nav contains a string entry matching the `api-autonav.nav_section_title`
    (e.g., - `"API Reference"`), the plugin replaces it with a structured
    navigation dictionary containing the generated API documentation.  This
    can be used to reposition the API section in the navigation.

1. **If `<nav_section_title>` exists as a dictionary with a single string value**

    If the API section is defined as `{ api-autonav.nav_section_title: "some/path" }`
    (e.g., - `"API Reference": "reference/"`), the plugin verifies that
    `"some/path"` matches the expected `api-autonav.api_root_uri` directory where
    API documentation is generated. If it matches, the string is replaced with
    the structured API navigation. Otherwise, an error is logged, and no changes
    are made.  This can be used to reposition the API section in the navigation,
    and also to add additional items to the API section, for example, using
    `literate-nav` to autodetect other markdown files in your
    `docs/<api-autonav.api_root_uri>` directory.

1. **If `<nav_section_title>` is a dictionary containing a list of items**  

    If the API section is defined as `{ api-autonav.nav_section_title: [...] }`, the plugin
    appends its generated navigation structure to the existing list.  This
    can be used to add additional items to the API section.

1. **If `<nav_section_title>` is not found in nav**  

    If no API section is found in the existing nav, the plugin appends a new
    section at the end of the nav list with the generated API navigation.

### Integration with mkdocs-awesome-nav

[`mkdocs-awesome-nav`](https://lukasgeiter.github.io/mkdocs-awesome-nav/)
["completely discards the navigation that MkDocs and other plugins
generate"](https://lukasgeiter.github.io/mkdocs-awesome-nav/philosophy/), and as
such requires special consideration.  Currently, the only way we integrate with
`mkdocs-awesome-nav` is to add the generated API navigation to the end of the
`nav` list, with the name `nav_section_title` from your config.

## Configuring Docstrings

Since mkdocstrings is used to generate the API documentation, you can configure
the docstrings as usual, following the [mkdocstrings
documentation](https://mkdocstrings.github.io/python/usage/).

I find the following settings to be particularly worth considering:

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          import:
            - https://docs.python.org/3/objects.inv
          options:
            docstring_section_style: list # or "table"
            docstring_style: "numpy"
            filters: ["!^_"]
            heading_level: 1
            merge_init_into_class: true
            parameter_headings: true
            separate_signature: true
            show_root_heading: true
            show_signature_annotations: true
            show_symbol_type_heading: true
            show_symbol_type_toc: true
            summary: true
```

## Why this plugin?

I very frequently find myself using three plugins in conjunction to generate API
documentation for my projects.

- [mkdocstrings](https://github.com/mkdocstrings/mkdocstrings) with
  [mkdocstrings-python](https://github.com/mkdocstrings/python) - to generate
  the API documentation using mkdocstrings `::: <identifier>` directives.
- [mkdocs-gen-files]() - Along with a script to look through my `src` folder to
  generate virtual files (including just the mkdocstrings directives) for each
  (sub-)module in the project.
- [literate-nav]() - To consume a virtual `SUMMARY.md` file generated using
  `mkdocs-gen-files` in the previous step, and generate a navigation structure that
  mirrors the module structure.

> [!NOTE]
> This pattern was mostly borrowed/inspired by the documentation for
> [mkdocstrings](https://github.com/mkdocstrings/mkdocstrings/blob/main/scripts/gen_ref_nav.py)
> itself, created by [@pawamoy](https://github.com/pawamoy)

This requires copying the same script and configuring three different plugins.
All I *really* want to do is point to the top level module(s) in my project
and have the API documentation generated for all submodules, with navigation
matching the module structure.

This plugin does that, using lower-level plugin APIs
([`File.generated`](https://www.mkdocs.org/dev-guide/api/#mkdocs.structure.files.File.generated))
to avoid the need for `mkdocs-gen-files` and `literate-nav`.  (Those plugins are
fantastic, but are more than what was necessary for this specific task).

It doesn't currently leave a ton of room for configuration, so it's mostly
designed for those who want to document their *entire* public API.  (I find
it can actually be a useful way to remind myself of what I've actually
exposed and omitted from the public API).
