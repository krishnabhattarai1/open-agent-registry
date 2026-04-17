# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| `main` (latest) | ✅ |
| older tags | ❌ — please upgrade |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues via **GitHub's private vulnerability reporting**:

1. Go to the repository on GitHub
2. Click **Security** → **Advisories** → **Report a vulnerability**
3. Fill in the details

Alternatively email the maintainer directly (see the GitHub profile).

### What to include

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- (Optional) Suggested fix

### What to expect

- **Acknowledgement within 48 hours**
- **Status update within 7 days**
- Credit in the security advisory once resolved (unless you prefer anonymity)

## Scope

In scope:
- Authentication bypass or key leakage
- SQL injection or data exposure
- Privilege escalation (accessing another publisher's agents/keys)
- Usage log tampering

Out of scope:
- Rate limiting / DoS (not implemented yet — known limitation)
- Issues requiring physical access to the server
- Issues in dependencies — report to the upstream project directly

## Security design notes

- API keys are bcrypt-hashed — raw keys are never stored
- Keys support per-key enable/disable/delete without affecting other keys
- Soft-delete preserves audit logs
- Middleware-level usage logging runs in a separate DB session so failures never affect API responses
