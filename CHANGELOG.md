# Changelog

All notable changes to ProofSmith are documented here.

## [Unreleased]

### Added

- Safe `git diff --numstat` adapter and `proofsmith scan` command.
- Parser tests for binary files, malformed input, traversal attempts, and CLI integration.
- Repeatable impact-planning benchmark with a documented local baseline.

## [0.1.0-alpha] - 2026-08-16

### Added

- Deterministic impact planning for Python, frontend, workflow, documentation, and security changes.
- Explicit policy decisions with pass, review, blocked, and skipped statuses.
- Redacted, schema-versioned evidence bundles with canonical SHA-256 hashes.
- Hash-chain verification and a local CLI for plan, bundle, and verify commands.
- React report interface demonstrating the evidence-first product model.
- Unit tests, CI workflow, architecture documentation, and open-source policies.
