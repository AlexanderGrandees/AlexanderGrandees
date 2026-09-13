# Vexi Security / Auth UI

Vexi v0.1.3 introduces a local Settings UI with **Assistant**, **Plugins**, and **Security** tabs.

## Security tab

Manual API/token values are accepted only through masked UI fields and written to Windows Credential Manager. Vexi never asks the user to dictate or paste secrets into normal voice/chat interaction.

The runtime may expose only credential metadata/state:

`NOT_CONFIGURED | AUTH_REQUIRED | CONNECTED | EXPIRED | PERMISSION_DENIED`

Raw credentials are excluded from logs, prompts, local personal memory, Browser Pack snapshots, public GitHub and Notion documentation.

## Registered auth types

`NONE_LOCAL`, `EXTENSION_PERMISSION`, `API_KEY`, `OAUTH_USER`, `BOT_TOKEN`, `APP_TOKEN`, `PARTNER_KEY`.

OAuth routes are registered as capability/auth contracts but v0.1.3 does not treat manual pasted OAuth tokens as the canonical flow.

## High-risk policy

This release deliberately uses a stricter policy than a convenience assistant:

- resolved read/reversible UI actions can execute automatically;
- reversible account mutation requires a dedicated approval contract;
- material external communication is denied;
- financial, legal-external, medical, identity/security-sensitive and irreversible/high-risk side effects are denied.

Examples currently blocked include payments, trading orders, withdrawals, legal filings/submissions, password/2FA/security/permission changes and account deletion.

The policy inherits the project's governance principle: **capability does not imply authorization** and unknown/conflicting permission state resolves conservatively.
