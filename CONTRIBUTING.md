# Contributing to the Fabric Ontology Importer

First off, thanks for taking the time to contribute! This project aims to make it easy to import RDF/TTL and DTDL ontologies into Microsoft Fabric, so every improvement helps the community.

## 📋 Ground Rules

- Be respectful and follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- Discuss big changes in an issue before submitting a PR.
- Keep pull requests focused and easy to review.
- Add or update tests when fixing bugs or implementing features.
- Document user-facing changes in the README and/or CHANGELOG.

## 🧱 Project Structure

```
src/
  cli/            # Command-line interface orchestration
  converters/     # Shared conversion utilities and helpers
  dtdl/           # DTDL parser and converter
  models/         # Shared Fabric ontology data classes
  ...             # Additional modules (fabric client, validation, etc.)
review/           # Architecture and standards review documents
samples/          # Example RDF, DTDL, and CSV datasets
```

## 🛠️ Development Workflow

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-enhancement
   ```
2. **Install dependencies** (Python 3.9+ recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. **Run tests** before committing:
   ```bash
   pytest
   ```
4. **Format & lint** (optional but appreciated):
   ```bash
   ruff check src tests
   ruff format src tests
   ```
5. **Commit** using conventional messages when possible:
   ```bash
   feat: add custom DTDL validator
   fix: handle xsd:duration mapping
   docs: update configuration guide
   ```
6. **Push** to your fork and open a pull request against `main`.

## ✅ Pull Request Checklist

- [ ] Tests pass locally (`pytest`).
- [ ] New/updated code is covered by tests.
- [ ] Documentation reflects the change.
- [ ] CHANGELOG has an entry under "Unreleased".
- [ ] Linked related issues in the PR description.

## 🧪 Testing Matrix

- **Unit tests** (`tests/test_*.py`).
- **Integration tests** (uploading sample ontologies to Fabric via mocked client).
- **Manual tests** (`samples/` contains real ontologies you can run through the CLI).

## 💬 Getting Help

- File an issue with as much detail as possible.
- Join the discussion in GitHub Discussions (coming soon).
- For security issues, follow the instructions in [SECURITY.md](SECURITY.md).

Happy contributing! 💙
