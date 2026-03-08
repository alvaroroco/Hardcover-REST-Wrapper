from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from hardcover_rest.api.clients.hardcover import graphql_request
from hardcover_rest.api.dependencies import get_api_key

router = APIRouter(prefix="/me/books", tags=["me-books"])

_ME_QUERY = """
query CurrentUser {
  me {
    id
  }
}
"""

STATUS_TO_ID = {
    "to_read": 1,
    "reading": 2,
    "read": 3,
}


class MeBookCreatePayload(BaseModel):
    book_id: int
    status: str


class MeBookStatusPayload(BaseModel):
    status: str


class MeBookPatchPayload(BaseModel):
    status_id: int | None = None
    progress_percent: float | None = None
    progress_pages: int | None = None


def _get_me_id(api_key: str) -> int:
    data = graphql_request(_ME_QUERY, {}, api_key)
    me = data.get("me")
    if isinstance(me, list):
        me = me[0] if me else None

    if not isinstance(me, dict) or me.get("id") is None:
        raise HTTPException(
            status_code=502, detail="Unable to resolve current user from Hardcover API"
        )

    return int(me["id"])


def resolve_status_id(status: str) -> int:
    normalized = status.strip().lower()
    status_id = STATUS_TO_ID.get(normalized)
    if status_id is None:
        raise HTTPException(
            status_code=422,
            detail="Invalid status. Use one of: to_read, reading, read",
        )
    return status_id


def _status_label(status_id: int) -> str:
    reverse = {v: k for k, v in STATUS_TO_ID.items()}
    return reverse.get(status_id, "unknown")


def _get_me_books_by_status(
    api_key: str,
    status: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    user_id = _get_me_id(api_key)
    status_id = resolve_status_id(status)

    gql_query = """
    query MeBooksByStatus($user_id: Int!, $status_id: Int!, $limit: Int!, $offset: Int!) {
      user_books(
        where: {user_id: {_eq: $user_id}, status_id: {_eq: $status_id}}
        order_by: {date_added: desc}
        limit: $limit
        offset: $offset
      ) {
        id
        book_id
        status_id
        date_added
        book {
          id
          title
          slug
        }
      }
    }
    """

    data = graphql_request(
        gql_query,
        {
            "user_id": user_id,
            "status_id": status_id,
            "limit": limit,
            "offset": offset,
        },
        api_key,
    )

    books = data.get("user_books", [])
    for book in books:
        if isinstance(book, dict) and book.get("status_id") is not None:
            book["status"] = _status_label(int(book["status_id"]))
    return books


def get_user_book_id(book_id: int, api_key: str) -> int:
    user_id = _get_me_id(api_key)

    gql_query = """
    query GetUserBookId($user_id: Int!, $book_id: Int!) {
      user_books(
        where: {user_id: {_eq: $user_id}, book_id: {_eq: $book_id}}
        limit: 1
      ) {
        id
      }
    }
    """

    data = graphql_request(gql_query, {"user_id": user_id, "book_id": book_id}, api_key)
    rows = data.get("user_books", [])
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Book {book_id} is not in your library",
        )

    row = rows[0]
    if not isinstance(row, dict) or row.get("id") is None:
        raise HTTPException(status_code=502, detail="Unable to resolve user_book_id")

    return int(row["id"])


@router.get("/reading")
def get_reading_books(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    return _get_me_books_by_status(api_key=api_key, status="reading", limit=limit, offset=offset)


@router.get("/to-read")
def get_to_read_books(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    return _get_me_books_by_status(api_key=api_key, status="to_read", limit=limit, offset=offset)


@router.get("/read")
def get_read_books(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    return _get_me_books_by_status(api_key=api_key, status="read", limit=limit, offset=offset)


@router.post("")
def create_me_book(
    payload: MeBookCreatePayload = Body(...),
    api_key: str = Depends(get_api_key),
):
    user_id = _get_me_id(api_key)
    status_id = resolve_status_id(payload.status)

    gql_query = """
    mutation CreateMeBook($user_id: Int!, $book_id: Int!, $status_id: Int!) {
      insert_user_book(
        object: {
          user_id: $user_id
          book_id: $book_id
          status_id: $status_id
        }
      ) {
        id
        user_book {
          id
          user_id
          book_id
          status_id
          date_added
        }
      }
    }
    """

    variables = {
        "user_id": user_id,
        "book_id": payload.book_id,
        "status_id": status_id,
    }

    data = graphql_request(gql_query, variables, api_key)
    result = data.get("insert_user_book", {})
    user_book = result.get("user_book") if isinstance(result, dict) else None
    if isinstance(user_book, dict):
        user_book["status"] = _status_label(int(user_book.get("status_id", 0)))

    return result


@router.patch("/{book_id}/status")
def patch_me_book_status(
    book_id: int,
    payload: MeBookStatusPayload = Body(...),
    api_key: str = Depends(get_api_key),
):
    user_book_id = get_user_book_id(book_id=book_id, api_key=api_key)
    status_id = resolve_status_id(payload.status)

    gql_query = """
    mutation UpdateMeBookStatus($id: Int!, $status_id: Int!) {
      update_user_book(
        id: $id
        object: {
          status_id: $status_id
        }
      ) {
        id
        user_book {
          id
          user_id
          book_id
          status_id
          date_added
        }
      }
    }
    """

    data = graphql_request(
        gql_query,
        {"id": user_book_id, "status_id": status_id},
        api_key,
    )
    result = data.get("update_user_book", {})
    user_book = result.get("user_book") if isinstance(result, dict) else None
    if isinstance(user_book, dict):
        user_book["status"] = _status_label(int(user_book.get("status_id", 0)))

    return result


@router.patch("/{user_book_id}")
def patch_me_book(
    user_book_id: int,
    payload: MeBookPatchPayload = Body(...),
    api_key: str = Depends(get_api_key),
):
    if payload.progress_pages is not None:
        raise HTTPException(
            status_code=422,
            detail="progress_pages is not supported by the current Hardcover GraphQL schema",
        )

    gql_query = """
    mutation UpdateMeBook(
      $id: Int!
      $status_id: Int
      $progress_percent: numeric
    ) {
      update_user_book(
        id: $id
        object: {
          status_id: $status_id
          progress_percent: $progress_percent
        }
      ) {
        id
        user_book {
          id
          user_id
          book_id
          status_id
          progress_percent
          reviewed_at
          date_added
        }
      }
    }
    """

    variables = {"id": user_book_id}
    payload_data = payload.model_dump(exclude_none=True)

    for field in ["status_id", "progress_percent"]:
        if field in payload_data and payload_data[field] is not None:
            variables[field] = payload_data[field]

    if len(variables) == 1:
        raise HTTPException(
            status_code=422,
            detail="At least one of status_id or progress_percent is required",
        )

    data = graphql_request(gql_query, variables, api_key)
    result = data.get("update_user_book", {})
    user_book = result.get("user_book") if isinstance(result, dict) else None
    if isinstance(user_book, dict) and user_book.get("status_id") is not None:
        user_book["status"] = _status_label(int(user_book["status_id"]))

    return result
