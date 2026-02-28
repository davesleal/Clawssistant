# Contributing to Clawssistant

Thank you for your interest in contributing to Clawssistant! This document provides
guidelines and instructions for contributing.

## Code of Conduct

Be respectful, constructive, and inclusive. We're building something for everyone's home —
treat contributors the way you'd treat a guest in yours.

## How to Contribute

### Reporting Bugs

1. Search [existing issues](https://github.com/davesleal/Clawssistant/issues) first
2. If not found, open a new issue using the **Bug Report** template
3. Include: steps to reproduce, expected behavior, actual behavior, hardware/OS info, logs

### Suggesting Features

1. Open a [Discussion](https://github.com/davesleal/Clawssistant/discussions) in the Ideas category
2. Describe the use case, not just the solution
3. Major features should be discussed before implementation

### Submitting Code

1. **Fork** the repository
2. **Create a branch** from `main`: `git checkout -b feature/my-feature`
3. **Write your code** following the style guide below
4. **Write tests** — all new features require tests
5. **Run the checks:**
   ```bash
   ruff check .
   ruff format .
   pytest tests/
   mypy clawssistant/
   ```
6. **Commit** with a clear message (see commit conventions below)
7. **Push** and open a **Pull Request** using the PR template

### Writing Skills (Plugins)

Community skills are one of the best ways to contribute. See the [Skill Development Guide](docs/skills.md) (coming soon) for details.

Quick version:
1. Create a Python file in `skills/`
2. Implement the `ClawssistantSkill` interface
3. Add a `skill.yaml` manifest declaring capabilities and metadata
4. Write tests in `tests/skills/`
5. Submit a PR

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/Clawssistant.git
cd Clawssistant
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Full suite
pytest tests/

# With coverage
pytest tests/ --cov=clawssistant --cov-report=term-missing

# Specific module
pytest tests/test_brain.py -v
```

### Linting & Formatting

```bash
ruff check .         # Lint
ruff format .        # Format
mypy clawssistant/   # Type check
```

## Style Guide

### Python

- **Version:** Python 3.12+
- **Formatter:** ruff (configured in `pyproject.toml`)
- **Type hints:** required on all public APIs
- **Docstrings:** Google style, required on public APIs
- **Async:** use `async/await` for all I/O operations
- **Line length:** 100 characters

### Commit Messages

Use conventional commits:

```
type(scope): short description

Longer description if needed.
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `security`

Examples:
```
feat(skills): add energy monitoring skill
fix(voice): handle microphone disconnect during STT
docs(readme): add satellite hardware wiring diagram
security(api): add rate limiting to REST endpoints
```

### Pull Requests

- Keep PRs focused — one feature or fix per PR
- Update documentation if behavior changes
- Add tests that cover the new/changed code
- Reference related issues in the PR description
- PRs require at least one maintainer review

## Architecture Decisions

For significant changes (new dependencies, API changes, security model changes), open an
Architecture Decision Record (ADR) as a Discussion first. Include:

- **Context:** what problem are you solving?
- **Decision:** what approach do you propose?
- **Consequences:** what are the tradeoffs?

## Developer Certificate of Origin (DCO)

By contributing, you certify that your contribution is your own work (or you have the right
to submit it) under the MIT license. Sign off your commits:

```bash
git commit -s -m "feat(skills): add weather alerts"
```

This adds a `Signed-off-by` line to your commit message.

## Getting Help

- **Questions:** Open a Discussion in the Q&A category
- **Chat:** Join our Discord server (link in README when available)
- **Security issues:** See [SECURITY.md](SECURITY.md) — do NOT open public issues for vulnerabilities
