# python-template

A minimalist, modern Python project template preconfigured with:
- **Python 3.12+** and packaging via PEP 621 (`pyproject.toml` + `hatchling`)
- **[uv](https://github.com/astral-sh/uv)** for fast package and virtual environment management
- **[Ruff](https://github.com/astral-sh/ruff)** for linting and formatting (PEP 8 compliant, 88 columns)
- **[Pyright](https://github.com/microsoft/pyright)** for static type checking
- **[Pre-commit](https://pre-commit.com/)** git hooks for code hygiene and security
- **[Pytest](https://pytest.org/)** test runner with smoke test
- **[pip-audit](https://github.com/pypa/pip-audit)** for dependency vulnerability scanning
- **Idiomatic Makefile** for development workflow automation
- **GitHub Actions CI** matching local checks
- **[Nix flake](flake.nix)** with a pinned dev shell (`python312`, `uv`, `make`, `node`, `git`)

---

## Quickstart

### 1. Using this template

Click **"Use this template"** on GitHub or clone the repository:

```bash
git clone https://github.com/<username>/<repo-name>.git
cd <repo-name>
```

### 2. Rename the project

Run the renaming helper to configure your package name and update `pyproject.toml` and tests:

```bash
make rename NAME=my-new-project
```

### 3. Install dependencies and git hooks

```bash
make sync
make hooks
```

### 4. (Optional) Enter the Nix dev shell

If you have [Nix](https://nixos.org/download/) with flakes enabled, the toolchain
comes from the pinned `flake.lock` instead of your system:

```bash
nix develop          # python 3.12 + uv + make + node + git
make ci              # same pipeline, now fully reproducible
nix develop -c make ci   # one-shot equivalent, no shell entry needed
nix fmt              # format the .nix files (alejandra)
```

`nix flake check` validates the flake outputs. `uv` is told
`UV_PYTHON_PREFERENCE=only-system` inside the shell, so it reuses the Nix-provided
interpreter instead of downloading a managed CPython.

---

## Available Commands

| Command | Description |
|---|---|
| `make help` | Show all available commands |
| `make sync` | Install runtime and dev dependencies using `uv` |
| `make hooks` | Install pre-commit hooks into `.git/hooks` |
| `make hooks-run` | Run pre-commit checks on all files |
| `make test` | Run tests with `pytest` |
| `make lint` | Check code with `ruff` |
| `make lint-fix` | Automatically fix linting issues |
| `make format` | Format code with `ruff` |
| `make format-check` | Check code formatting without modifying |
| `make typecheck` | Run static type checking with `pyright` |
| `make audit` | Audit dependencies for vulnerabilities with `pip-audit` |
| `make ci` | Run full verification pipeline locally (`lint`, `format-check`, `typecheck`, `audit`, `test`) |
| `make clean` | Remove caches and build artifacts |
| `make rename NAME=...` | Rename package and update configuration |

---

## Project Structure

```text
.
├── .github/workflows/ci.yml   # GitHub Actions CI workflow
├── src/
│   └── app_name/              # Source code directory (renamed via make rename)
│       ├── __init__.py
│       └── py.typed
├── tests/
│   ├── __init__.py
│   └── test_smoke.py          # Initial smoke test
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── Makefile
├── pyproject.toml
├── README.md
├── flake.nix                 # Nix flake: pinned dev shell (nix develop)
└── flake.lock                # Pinned nixpkgs revision for the flake
```
