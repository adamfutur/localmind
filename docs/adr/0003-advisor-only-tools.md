# ADR 0003: Advisor-only tools

- Status: Accepted
- Date: 2026-10-23

## Context

An AI agent that can edit files, run commands, or mutate Git creates immediate
security and trust risks, especially for a public product and for untrusted
retrieved content. The first release needs to prove retrieval, citations, and
review quality before it is allowed to change a user's workspace.

## Decision

The shipped v2 advisor is **read-only**:

- Allowed: search documents, read approved files, inspect dependencies, retrieve
  architecture rules, explain, review, and propose changes.
- Forbidden: writing files, creating or deleting files, running shell commands,
  executing code, committing, branching, pushing, or mutating Git.
- Tool permissions are enforced in code. Prompt instructions are not a security
  boundary.
- The model cannot grant itself a new tool or elevate a permission.
- Change proposals are structured data: rationale, affected files, risks,
  proposed diff, tests to run, and policy findings. Applying a proposal is a
  separate, explicit user action outside the advisor.
- The VS Code extension follows the same restriction. It renders proposals but
  does not apply them.
- Retrieved documents, repository files, and instructions are untrusted input.
  They cannot override tool permissions or the advisor policy.

## Consequences

- The first release is safer and easier to audit.
- Some user workflows require manual application of proposals.
- A future write-capable mode requires a superseding ADR, explicit user consent,
  sandboxing, and a new threat model. It must not be introduced as a hidden flag.
- Tests must verify that no write/shell/Git tools are registered in the shipped
  tool registry.

## Follow-up

- Build a typed allowlist registry before adding advisor tools.
- Add regression tests that fail if a forbidden tool is registered.
- Log tool calls without logging raw document content or secrets.
