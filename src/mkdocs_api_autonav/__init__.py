"""Autogenerate API docs with mkdocstrings, including nav"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mkdocs-api-autonav")
except PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"
