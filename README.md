# Cornea-EDOF-IOL-coupling

Zemax OpticStudio / ZOS-API research software for studying coupling between post-refractive corneal optical archetypes and non-diffractive EDOF IOL surrogate mechanisms.

## Repository layout

```text
docs/                         authoritative URD/ADD/MDD/TDD/RMD/TRACE documents
src/whole_eye_mvp/            Python application package
tests/unit/                   pure Python unit tests
tests/fixtures/               frozen test fixtures
.vibe/                        vibe-coding trace/coupling state
pyproject.toml                uv/Python project configuration
```

Generated Zemax models, locks, manifests, results, images, and logs are runtime project outputs and are not committed by default.

## Development

Python dependencies and environments are managed with **uv**. Automated tests use **pytest**.

```bash
uv sync
uv run pytest
uv run ruff check .
```

Zemax integration tests require Windows, Ansys Zemax OpticStudio 2026 R1, and a valid ZOS-API license:

```bash
uv run pytest -m zemax
```

The scientific and software requirements are defined in `docs/`; implementation must not silently change frozen scientific locks or the 18-carrier / 72-configuration MVP design.
