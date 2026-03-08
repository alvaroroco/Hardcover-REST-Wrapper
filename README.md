# Hardcover REST Wrapper

`hardcover-rest` is a FastAPI wrapper around Hardcover GraphQL focused on a minimal, AI-friendly API.

The API intentionally hides internal Hardcover details like `status_id` and `user_book_id`.

## Supported Workflows

1. Search books
2. View your books by status
3. Add a book to your library
4. Change a book status

Supported statuses:

- `to_read`
- `reading`
- `read`

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

2. Run locally:

```bash
uv run uvicorn hardcover_rest.api:app --host 0.0.0.0 --port 8000 --reload
```

3. Open docs:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Authentication

Protected endpoints require your Hardcover API key in the `Authorization` header:

```http
Authorization: <HARDCOVER_API_KEY>
```

## Endpoints

### Health

- `GET /health`

### Books

- `GET /books/search?query=<text>`

### My Books

- `GET /me/books/reading`
- `GET /me/books/to-read`
- `GET /me/books/read`
- `POST /me/books`
- `PATCH /me/books/{book_id}/status`

## Example Requests

### Search books

```bash
curl -X GET "http://localhost:8000/books/search?query=mistborn" \
  -H "Authorization: $HARDCOVER_API_KEY"
```

### Add book to library

```bash
curl -X POST "http://localhost:8000/me/books" \
  -H "Authorization: $HARDCOVER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 123,
    "status": "to_read"
  }'
```

### Start reading a book

```bash
curl -X PATCH "http://localhost:8000/me/books/123/status" \
  -H "Authorization: $HARDCOVER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "reading"
  }'
```

### Mark book as read

```bash
curl -X PATCH "http://localhost:8000/me/books/123/status" \
  -H "Authorization: $HARDCOVER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "read"
  }'
```

## Notes for AI Agents

- Use only status strings: `to_read`, `reading`, `read`.
- Do not send `status_id` or `user_book_id`.
- Use `/openapi.json` to generate tools.

## Project Structure

```text
src/hardcover_rest/api/
  __init__.py            # FastAPI app
  dependencies.py        # auth dependency
  clients/hardcover.py   # GraphQL request client
  routes/                # REST endpoints
```
