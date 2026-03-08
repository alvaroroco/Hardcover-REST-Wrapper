# Hardcover REST Wrapper

`hardcover-rest` is a FastAPI service that wraps the Hardcover GraphQL API and exposes it through REST endpoints.

It is designed for clients that work better with REST than GraphQL, especially AI agents and tool-calling workflows that prefer:

- predictable HTTP paths
- query parameters and JSON bodies
- OpenAPI schemas for automatic tool generation

## Why this project

Hardcover provides a GraphQL API. This wrapper translates common reading workflows into REST endpoints so you can integrate faster in systems where GraphQL is not ideal.

Examples:

- searching books
- reading/updating your shelves (`/me/books`)
- creating reviews (`/me/reviews`)
- managing lists (`/me/lists`)

## Tech Stack

- Python 3.12+
- FastAPI
- Requests
- Uvicorn

## Quick Start

1. Install dependencies:

```bash
uv sync
```

2. Run the API locally:

```bash
uv run uvicorn hardcover_rest.api:app --host 0.0.0.0 --port 8000 --reload
```

3. Open docs:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Authentication

All protected endpoints expect your Hardcover API key in the `Authorization` header:

```http
Authorization: <HARDCOVER_API_KEY>
```

If the header is missing, the API returns `401`.

## Implemented Endpoints

### Health

- `GET /health`

### Books

- `GET /books/search`
- `GET /books/{book_id}`

### My Books

- `GET /me/books`
- `GET /me/books/statuses`
- `GET /me/books/currently-reading`
- `GET /me/books/read`
- `GET /me/books/want-to-read`
- `POST /me/books`
- `PATCH /me/books/{user_book_id}`

### My Reviews

- `GET /me/reviews`
- `POST /me/reviews`

### My Lists

- `GET /me/lists`
- `POST /me/lists`
- `POST /lists/{list_id}/books`

## Example Requests

### Search books

```bash
curl -X GET "http://localhost:8000/books/search?query=dune&query_type=Book&per_page=10&page=1" \
  -H "Authorization: $HARDCOVER_API_KEY"
```

### Add a book to your library

```bash
curl -X POST "http://localhost:8000/me/books" \
  -H "Authorization: $HARDCOVER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 123,
    "status_id": 2,
    "rating": 4.5
  }'
```

### Discover available status IDs

```bash
curl -X GET "http://localhost:8000/me/books/statuses" \
  -H "Authorization: $HARDCOVER_API_KEY"
```

### Get only books with one status

```bash
curl -X GET "http://localhost:8000/me/books?status_id=2&limit=100&offset=0" \
  -H "Authorization: $HARDCOVER_API_KEY"
```

### Get currently reading books directly

```bash
curl -X GET "http://localhost:8000/me/books/currently-reading?limit=50&offset=0" \
  -H "Authorization: $HARDCOVER_API_KEY"
```

### Get read books directly

```bash
curl -X GET "http://localhost:8000/me/books/read?limit=50&offset=0" \
  -H "Authorization: $HARDCOVER_API_KEY"
```

### Get want-to-read books directly

```bash
curl -X GET "http://localhost:8000/me/books/want-to-read?limit=50&offset=0" \
  -H "Authorization: $HARDCOVER_API_KEY"
```

### Create a review

```bash
curl -X POST "http://localhost:8000/me/reviews" \
  -H "Authorization: $HARDCOVER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 123,
    "review_raw": "Great pacing and world-building.",
    "rating": 4.0,
    "review_has_spoilers": false
  }'
```

## AI-Friendly Usage Notes

- Use `/openapi.json` to auto-generate tools/functions in your AI platform.
- Keep one tool per endpoint for simpler agent behavior.
- Forward the user’s Hardcover API key as `Authorization`.

## Project Structure

```text
src/hardcover_rest/api/
  __init__.py            # FastAPI app
  dependencies.py        # auth dependency
  clients/hardcover.py   # GraphQL request client
  routes/                # REST endpoints
```
