"""Zernio publishing integration.

Supports read-only account discovery and draft creation. This tool deliberately
does not publish or schedule content; those actions require a separate,
explicitly reviewed workflow.
"""
from __future__ import annotations

import os
from typing import Any

import requests

from tools.base_tool import (
    BaseTool,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)


class ZernioPublisher(BaseTool):
    """List connected Zernio accounts and save a post as a draft."""

    name = "zernio_publisher"
    version = "0.1.0"
    tier = ToolTier.PUBLISH
    stability = ToolStability.BETA
    runtime = ToolRuntime.API
    capability = "social_publishing"
    provider = "zernio"
    dependencies = ["env:ZERNIO_API_KEY", "python:requests"]
    install_instructions = (
        "Set ZERNIO_API_KEY in the environment or the project .env file. "
        "Never commit the key to source control."
    )
    capabilities = ["list_social_accounts", "create_social_draft"]
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_accounts", "create_draft"],
            },
            "content": {"type": "string"},
            "platform": {
                "type": "string",
                "enum": [
                    "twitter", "instagram", "facebook", "linkedin", "tiktok",
                    "youtube", "pinterest", "reddit", "bluesky", "threads",
                    "googlebusiness", "telegram", "snapchat", "whatsapp",
                    "discord", "slack",
                ],
            },
            "account_id": {"type": "string"},
            "title": {"type": "string"},
        },
        "required": ["action"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "accounts": {"type": "array"},
            "post": {"type": "object"},
        },
    }
    side_effects = [
        "Reads connected social-account metadata from Zernio",
        "Can create a draft post in Zernio; never publishes or schedules",
    ]
    user_visible_verification = [
        "For list_accounts, verify returned platform, username, and account ID",
        "For create_draft, verify the returned post status is draft",
    ]

    base_url = "https://zernio.com/api/v1"
    timeout_seconds = 20

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        api_key = os.environ.get("ZERNIO_API_KEY")
        if not api_key:
            raise ValueError(
                "ZERNIO_API_KEY is missing. Set it in the runtime environment; "
                "do not put secrets in source code."
            )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            timeout=self.timeout_seconds,
            **kwargs,
        )
        if not response.ok:
            # Avoid including request headers or secret values in error output.
            detail = ""
            try:
                payload = response.json()
                detail = str(payload.get("error") or payload.get("message") or "")
            except ValueError:
                detail = response.text[:300]
            raise RuntimeError(
                f"Zernio API returned HTTP {response.status_code}"
                + (f": {detail}" if detail else "")
            )
        if not response.content:
            return {}
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Zernio API returned an unexpected response format.")
        return payload

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        """Execute a safe account-list or draft-creation action."""
        action = inputs.get("action")
        try:
            if action == "list_accounts":
                payload = self._request("GET", "/accounts")
                raw_accounts = payload.get("accounts", [])
                accounts = []
                for account in raw_accounts if isinstance(raw_accounts, list) else []:
                    if not isinstance(account, dict):
                        continue
                    account_id = account.get("_id") or account.get("id")
                    accounts.append({
                        "id": account_id,
                        "platform": account.get("platform"),
                        "username": account.get("username"),
                        "is_active": account.get("isActive"),
                    })
                return ToolResult(
                    success=True,
                    data={"action": action, "accounts": accounts},
                )

            if action == "create_draft":
                content = inputs.get("content")
                platform = inputs.get("platform")
                account_id = inputs.get("account_id")
                if not isinstance(content, str) or not content.strip():
                    return ToolResult(
                        success=False,
                        error="'content' is required for create_draft.",
                    )
                if not isinstance(platform, str) or not platform.strip():
                    return ToolResult(
                        success=False,
                        error="'platform' is required for create_draft.",
                    )
                if not isinstance(account_id, str) or not account_id.strip():
                    return ToolResult(
                        success=False,
                        error="'account_id' is required for create_draft.",
                    )

                body: dict[str, Any] = {
                    "content": content.strip(),
                    "platforms": [
                        {"platform": platform.strip().lower(), "accountId": account_id.strip()}
                    ],
                }
                title = inputs.get("title")
                if isinstance(title, str) and title.strip():
                    body["title"] = title.strip()

                # Per Zernio API behavior, omitting publishNow and scheduledFor
                # saves the post as a draft. Do not add either field here.
                payload = self._request("POST", "/posts", json=body)
                post = payload.get("post", {})
                status = post.get("status") if isinstance(post, dict) else None
                if status and str(status).lower() not in {"draft", "pending"}:
                    return ToolResult(
                        success=False,
                        data={"action": action, "post": post},
                        error=(
                            "Zernio returned an unexpected post status; "
                            "verify it in the Zernio dashboard before proceeding."
                        ),
                    )
                return ToolResult(
                    success=True,
                    data={"action": action, "post": post, "message": payload.get("message")},
                )

            return ToolResult(
                success=False,
                error="Unsupported action. Use 'list_accounts' or 'create_draft'.",
            )
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            return ToolResult(success=False, error=str(exc))
