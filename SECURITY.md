# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please open an issue on GitHub.

## Sensitive Information

**Never commit** the following to this repository:

- DEEPSEEK_API_KEY
- OPENAI_API_KEY
- .env files
- codex/config.toml (use codex/config.toml.example as template)
- GitHub personal access tokens (gho_*, ghp_*)
- Bearer tokens
- Any API credentials or authentication tokens

These are already covered by .gitignore:

`
.env
.env.*
codex/config.toml
`

## If You Accidentally Commit a Secret

1. Immediately revoke the token/API key from the provider's dashboard
2. Rotate to a new key
3. Use git filter-branch or BFG Repo-Cleaner to remove the secret from history
4. Force push after ensuring all collaborators are aware