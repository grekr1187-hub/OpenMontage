# Zernio integration for OpenMontage

OpenMontage discovers concrete `BaseTool` subclasses under `tools/` automatically.
`tools/publishers/zernio_api.py` adds the `zernio_publisher` tool.

## Configuration

Set `ZERNIO_API_KEY` in the runtime environment or in the local project `.env` file:

```dotenv
ZERNIO_API_KEY=replace-with-a-new-zernio-key
```

Never commit `.env` or paste the key into source code, issues, pull requests, or chat.
If a key was exposed, revoke it in Zernio and create a replacement.

The tool uses the existing `requests` dependency; no additional package is required.

## Supported actions

- `list_accounts`: reads `GET https://zernio.com/api/v1/accounts` and returns only account ID, platform, username, and active status.
- `create_draft`: sends `POST /v1/posts` with content and one explicit platform/account pair. It omits `publishNow` and `scheduledFor`, so Zernio saves a draft rather than publishing or scheduling it.

The tool intentionally does not provide publish-now or schedule actions. Verify drafts in the Zernio dashboard before any later publishing workflow.

## Example tool inputs

List connected accounts:

```json
{"action": "list_accounts"}
```

Create a draft (use an actual account ID returned by `list_accounts`):

```json
{
  "action": "create_draft",
  "content": "Draft text for review",
  "platform": "instagram",
  "account_id": "YOUR_CONNECTED_ACCOUNT_ID"
}
```

## Verification

After deployment, ensure `ZERNIO_API_KEY` is configured in the remote runtime, discover tools from the `tools` package, call `zernio_publisher` with `list_accounts`, and confirm the expected connected accounts are returned. This repository change does not verify or store the API key.
