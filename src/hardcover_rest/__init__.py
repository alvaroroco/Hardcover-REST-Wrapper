from hardcover_rest.api import app

__all__ = ["app"]


def main() -> None:
    import uvicorn

    uvicorn.run("hardcover_rest.api:app", host="0.0.0.0", port=8000, reload=False)
