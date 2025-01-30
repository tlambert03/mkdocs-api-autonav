# mkdocs-api-autonav

[![License](https://img.shields.io/pypi/l/mkdocs-api-autonav.svg?color=green)](https://github.com/tlambert03/mkdocs-api-autonav/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/mkdocs-api-autonav.svg?color=green)](https://pypi.org/project/mkdocs-api-autonav)
[![Python Version](https://img.shields.io/pypi/pyversions/mkdocs-api-autonav.svg?color=green)](https://python.org)
[![CI](https://github.com/tlambert03/mkdocs-api-autonav/actions/workflows/ci.yml/badge.svg)](https://github.com/tlambert03/mkdocs-api-autonav/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tlambert03/mkdocs-api-autonav/branch/main/graph/badge.svg)](https://codecov.io/gh/tlambert03/mkdocs-api-autonav)

Autogenerate API reference including navigation for all submodules, with
[mkdocstrings](https://github.com/mkdocstrings/mkdocstrings).

## Quick Start

_Until this is published on PyPI, please install directly from GitHub._

```shell
pip install git+https://github.com/tlambert03/mkdocs-api-autonav
```

```yaml
site_name: "My Library"

plugins:
- search
- mkdocstrings:
- api-autonav:
    modules: ['src/my_library']
```

### Configuration

Here are all the configurables, along with their default values.

```yaml
plugins:
- api-autonav:
    modules: []  
    api_title: "API Reference"
    api_root: "reference" 
    nav_item_prefix: "<code class='doc-symbol doc-symbol-nav doc-symbol-module'></code>"
    exclude_private: true  
```

- **`modules`** (`list[str]`)- List of paths to Python modules to include in the
  navigation, relative to the project root.  This is the only required
  configuration.
- **`api_title`** (`str`) - Title for the API reference section as it appears in
  the navigation. Default is "API Reference"
- **`api_root`** (`str`) - Root folder for api docs in the generated site. This
  determines the url path for the API documentation. Default is "reference"
- **`nav_item_prefix`** (`str`) - A prefix to add to each module name in the
  navigation.  By default, renders a `[mod]` badge before each module.
  Set to the empty string to disable this.
- **`exclude_private`** (`bool`) - Exclude modules that start with an underscore

### Integration with nav

No `nav` configuration is required in `mkdocs.yml`, but in most cases you will want to
have one anyway.  Here are the rules for how this plugin integrates with your
existing `nav` configuration.

1. **If `<api_title>` exists and is explicitly referenced as a string**

    If your nav contains a string entry matching the `api-autonav.api_title`
    (e.g., - `"API Reference"`), the plugin replaces it with a structured
    navigation dictionary containing the generated API documentation.  This
    can be used to reposition the API section in the navigation.

1. **If `<api_title>` exists as a dictionary with a single string value**

    If the API section is defined as `{ api-autonav.api_title: "some/path" }`
    (e.g., - `"API Reference": "reference/"`), the plugin verifies that
    `"some/path"` matches the expected `api-autonav.api_root` directory where
    API documentation is generated. If it matches, the string is replaced with
    the structured API navigation. Otherwise, an error is logged, and no changes
    are made.  This can be used to reposition the API section in the navigation,
    and also to add additional items to the API section, for example, using
    `literate-nav` to autodetect other markdown files in your
    `docs/<api-autonav.api_root>` directory.

1. **If `<api_title>` is a dictionary containing a list of items**  

    If the API section is defined as `{ api-autonav.api_title: [...] }`, the plugin
    appends its generated navigation structure to the existing list.  This
    can be used to add additional items to the API section.

1. **If `<api_title>` is not found in nav**  

    If no API section is found in the existing nav, the plugin appends a new
    section at the end of the nav list with the generated API navigation.

## Why this plugin?

I very frequently find myself using three plugins in conjunction to generate API
documentation for my projects.

- [mkdocstrings](https://github.com/mkdocstrings/mkdocstrings) with
  [mkdocstrings-python](https://github.com/mkdocstrings/python) - to generate
  the API documentation using mkdocstrings `::: <identifier>` directives.
- [mkdocs-gen-files]() - To generate virtual files (including just the
  mkdocstrings directives) for each (sub-)module in the project.
- [literate-nav]() - To consume the a virtual `SUMMARY.md` file generated by
  `mkdocs-gen-files` and generate a navigation structure that mirrors the module
  structure.

> [!NOTE] This pattern was mostly borrowed/inspired by the documentation for
> [mkdocstrings](https://github.com/mkdocstrings/mkdocstrings/blob/main/scripts/gen_ref_nav.py)
> itself, created by [@pawamoy](https://github.com/pawamoy)

All I really want to do, is point to the top level module(s) in my project, and
have the API documentation generated for all submodules, with navigation
matching the module structure.

This plugin does that, using lower-level plugin APIs
([`File.generated`](https://www.mkdocs.org/dev-guide/api/#mkdocs.structure.files.File.generated))
to avoid the need for `mkdocs-gen-files` and `literate-nav`.  (Those plugins are
fantastic, but are more than what was necessary for this specific task).
