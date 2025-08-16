# Contributing

PRs and contributions are welcome!

## Development Setup

To get started with development, clone the repository and install the required dependencies:

```sh
git clone https://github.com/tlambert03/mkdocs-api-autonav.git
cd mkdocs-api-autonav
uv sync
```

### Testing

```sh
uv run pytest
```

### Run local docs fitures

```sh
uv run --group docs mkdocs serve -f tests/fixtures/repo1/mkdocs.yml
```
