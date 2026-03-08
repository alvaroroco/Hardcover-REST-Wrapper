from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException


def get_api_key(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Provide your Hardcover API key.",
        )

    return authorization
