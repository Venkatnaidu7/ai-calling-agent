# Security

- Passwords use Argon2.
- JWTs expire after eight hours.
- Twilio signatures are validated when the auth token is configured.
- Voice stream URLs use an HMAC token bound to the call.
- Tool execution is tenant and agent-version scoped.
- API keys are stored as SHA-256 hashes and returned only at creation.
- Outbound calling is disabled by default and must pass consent/compliance checks.
- Provider secrets must be supplied through environment variables or a production secret manager.

Before production: enable least-privilege database access/RLS, WAF/rate limiting, centralized secrets, retention controls, security testing and live provider verification.
