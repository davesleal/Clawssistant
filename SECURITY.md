# Security Policy

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in Clawssistant, please report it responsibly:

1. **Email:** Send details to security@clawssistant.dev (or the maintainer's email listed in the repo)
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if you have one)
3. **Response time:** We aim to acknowledge reports within 48 hours and provide a fix timeline within 7 days.
4. **Disclosure:** We follow coordinated disclosure — please allow 90 days for a fix before public disclosure.

## Security Model

### Threat Model

Clawssistant operates in a home network environment with the following trust boundaries:

```
Untrusted          | Trust Boundary          | Trusted
                   |                         |
Internet --------> | Firewall / Router       | Local Network
Audio environment > | Wake Word + Voice Auth  | Verified Commands
Community skills -> | Skill Sandbox           | Core Runtime
MCP servers ------> | Capability Scoping      | Device Actions
API clients ------> | Auth + TLS              | Internal Bus
```

### Core Security Principles

1. **Defense in depth** — no single layer failure compromises the system
2. **Least privilege** — skills and MCP servers only get capabilities they need
3. **Secure by default** — security features are ON by default, not opt-in
4. **Local-first** — minimize data that leaves the local network
5. **Auditable** — all security-sensitive actions are logged

### Authentication & Authorization

- **API server:** Token-based authentication required by default for all endpoints
- **Home Assistant:** Long-lived tokens stored via environment variables, never in config files
- **User profiles:** Per-user voice identification with optional PIN for sensitive actions
- **Sensitive commands:** Destructive actions (unlock doors, disarm security, shell execution) require explicit second-factor confirmation

### Sensitive Action Classification

Actions are classified by risk level:

| Level | Examples | Confirmation Required |
|-------|----------|----------------------|
| **Low** | Turn on lights, check weather, set timer | None (voice command sufficient) |
| **Medium** | Adjust thermostat, lock doors, play media | Voice confirmation ("Are you sure?") |
| **High** | Unlock doors, disarm security, make purchases | PIN code or companion app confirmation |
| **Critical** | Shell execution, system config changes, firmware updates | Companion app approval only |

### Voice Pipeline Security

- **Wake word** — configurable sensitivity to balance responsiveness vs false triggers
- **Audio liveness** — optional liveness detection to prevent replay attacks (speaker verification via pyannote/speechbrain)
- **Command confirmation** — sensitive actions require explicit confirmation
- **No always-listening storage** — audio buffers are processed in memory and never persisted unless explicitly configured for debugging

### Skill & Plugin Security

- **Skill sandboxing** — community skills run in isolated subprocesses with restricted filesystem access
- **Capability declaration** — skills must declare required permissions in their manifest (`skill.yaml`)
- **File integrity** — skill checksums verified on load; unsigned skills require explicit user approval
- **No network access by default** — skills must explicitly request network capability
- **Hot-reload restrictions** — skill directory must be owned by the service user with restricted write permissions

### MCP Server Security

- **Capability scoping** — each MCP server is granted explicit tool permissions (e.g., a weather server cannot control locks)
- **Tool call audit logging** — all MCP tool invocations are logged with timestamps, parameters, and results
- **Rate limiting** — MCP tool calls are rate-limited to prevent abuse
- **Sandboxed execution** — MCP servers run as separate processes with limited system access

### Network Security

- **Bind localhost by default** — API server binds `127.0.0.1` unless explicitly configured otherwise
- **TLS support** — HTTPS with auto-generated self-signed certificates or user-provided certs
- **No UPnP** — never automatically opens ports on the router
- **mDNS only** — device discovery limited to local network via mDNS/DNS-SD

### Data Security

- **No telemetry** — zero data collection, no phone-home, no analytics
- **Local storage encryption** — optional encryption-at-rest for the memory database
- **Conversation privacy** — conversation history stored locally, never transmitted except to Anthropic API for processing
- **API key isolation** — secrets loaded from environment variables, never logged or exposed via API

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x (pre-release) | Best-effort security fixes |
| 1.0+ (future) | Full security support for latest minor release |

## Security Checklist for Contributors

When submitting code, ensure:

- [ ] No secrets or credentials in code or config files
- [ ] Input validation on all external data (API requests, voice input, MCP tool results)
- [ ] No `eval()`, `exec()`, or `subprocess.shell=True` without explicit security review
- [ ] SQL queries use parameterized statements (no string interpolation)
- [ ] File operations validate paths to prevent directory traversal
- [ ] New skills declare minimal required capabilities
- [ ] Security-sensitive changes are flagged in the PR description
