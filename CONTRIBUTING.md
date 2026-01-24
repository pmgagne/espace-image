# Contributing

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Workflow

1.  **Fork** the repo on GitHub.
2.  **Clone** the project to your own machine.
3.  **Install dependencies** using `uv sync --dev`.
4.  **Create a branch** for your specific change.
5.  **Lint/format** with `uv run ruff check .` and `uv run ruff format . --check`.
6.  **Test** your changes using `uv run pytest tests/ -v --cov=app`.
7.  **Commit** changes to your own branch.
8.  **Push** your work back up to your fork.
9.  Submit a **Pull Request** so that we can review your changes.

## Reporting Bugs

**If you find a security vulnerability, please do NOT open an issue. Email the maintainers instead.**

Report bugs using GitHub's [issue tracker](https://github.com/pmgagne/espace-image/issues).

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
