# ADR 0002: Demo API Keys with Hashed Lookup

## Status

Accepted

## Context

Enterprise gateways require tenant isolation and role-based access. Full OIDC/SAML integration is out of scope for a portfolio demo, but the auth boundary must be real enough to enforce tool permissions and eval cases.

## Decision

Use **header-based API keys** (`X-API-Key`) mapped to `{subject, tenant_id, role}` entries. Store **SHA-256 hashes** in settings; document plaintext demo keys in README only.

## Consequences

- **Positive:** Simple local dev story; deterministic eval authentication.
- **Positive:** No secrets committed to git.
- **Negative:** Not suitable for production without rotation, KMS, and SSO federation.
- **Follow-on:** Replace with OAuth2 client credentials or JWT validation behind API gateway.
