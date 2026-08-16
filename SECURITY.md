# Security Policy

## Scope

ProofSmith is local-first and currently records structured check results rather than executing arbitrary commands. The main security boundaries are input parsing, evidence redaction, filesystem persistence, and future runner integrations.

## Reporting

Please do not disclose a suspected vulnerability in a public issue. Open a private GitHub security advisory for `Alqudimi/proofsmith` when available, or contact the maintainer through the GitHub profile. Include a minimal reproduction, impact, affected version, and a safe mitigation if known.

Do not include live credentials or private source code in reports. We aim to acknowledge reports within seven days and will coordinate a fix and disclosure timeline based on impact.

## Secure development expectations

Changes that execute processes, parse untrusted formats, access the network, or change redaction behavior require tests for hostile input and an explicit threat-model note.
