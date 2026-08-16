# Contributing to ProofSmith

Thank you for improving the evidence layer for safer software changes. Start with an issue for larger behavior changes, keep pull requests focused, and explain the user-facing or review-facing contract in the description.

## Local workflow

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[test]'
PYTHONPATH=src pytest
pnpm install && pnpm check && pnpm build
```

Use conventional commits when practical, include tests for behavior changes, and avoid adding a dependency without documenting its security and maintenance value. Never include credentials, customer data, or generated evidence containing secrets in a pull request.

## Pull requests

A good pull request states the problem, the invariant being changed, the evidence that validates it, and any compatibility or migration impact. Maintainers may ask for a threat-model note when code touches execution, parsing, persistence, or integrations.
