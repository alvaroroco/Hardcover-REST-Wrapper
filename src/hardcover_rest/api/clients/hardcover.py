from __future__ import annotations

from typing import Any

import requests
from fastapi import HTTPException

from hardcover_rest.config import HARDCOVER_API


def graphql_request(query: str, variables: dict[str, Any], api_key: str) -> dict[str, Any]:
    try:
        response = requests.post(
            HARDCOVER_API,
            json={"query": query, "variables": variables},
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Failed to connect to Hardcover API") from exc

    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text}

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=payload)

    if isinstance(payload, dict) and payload.get("errors"):
        raise HTTPException(
            status_code=502,
            detail={"message": "Hardcover GraphQL error", "errors": payload["errors"]},
        )

    if not isinstance(payload, dict) or "data" not in payload:
        raise HTTPException(status_code=502, detail="Invalid response from Hardcover API")

    return payload["data"]
