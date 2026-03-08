from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from hardcover_rest.api.clients.hardcover import graphql_request
from hardcover_rest.api.dependencies import get_api_key

router = APIRouter(prefix="/me/books", tags=["me-books"])

HARDCOVER_BOOK_STATUS_NAMES = {
    1: "want_to_read",
    2: "currently_reading",
    3: "read",
    4: "paused",
    5: "did_not_finish",
    6: "ignored",
}


_ME_QUERY = """
query CurrentUser {
  me {
    id
  }
}
"""


def _get_me_id(api_key: str) -> int:
    data = graphql_request(_ME_QUERY, {}, api_key)
    me = data.get("me")
    if isinstance(me, list):
        me = me[0] if me else None

    if not isinstance(me, dict) or me.get("id") is None:
        raise HTTPException(status_code=502, detail="Unable to resolve current user from Hardcover API")

    return int(me["id"])


def _resolve_status_id(api_key: str, slug: str, name: str) -> int:
    fallback_ids = {v: k for k, v in HARDCOVER_BOOK_STATUS_NAMES.items()}
    candidate_queries = [
        (
            """
            query ResolveBookStatusBySlugOrName($slug: String!, $name: String!) {
              book_statuses(
                where: {_or: [{slug: {_eq: $slug}}, {status: {_eq: $name}}]}
                limit: 1
              ) {
                id
              }
            }
            """,
            "book_statuses",
        ),
        (
            """
            query ResolveUserBookStatusBySlugOrName($slug: String!, $name: String!) {
              user_book_statuses(
                where: {_or: [{slug: {_eq: $slug}}, {status: {_eq: $name}}]}
                limit: 1
              ) {
                id
              }
            }
            """,
            "user_book_statuses",
        ),
    ]

    for query, result_key in candidate_queries:
        try:
            data = graphql_request(query, {"slug": slug, "name": name}, api_key)
        except HTTPException:
            continue

        rows = data.get(result_key, [])
        if rows and isinstance(rows[0], dict) and rows[0].get("id") is not None:
            return int(rows[0]["id"])

    fallback = fallback_ids.get(slug)
    if fallback is not None:
        return fallback

    raise HTTPException(status_code=502, detail=f"Unable to resolve status '{slug}' from Hardcover GraphQL API")


@router.get("")
def get_me_books(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_id: int | None = Query(None, ge=1),
    api_key: str = Depends(get_api_key),
):
    user_id = _get_me_id(api_key)

    if status_id is None:
        where_clause = "where: {user_id: {_eq: $user_id}}"
    else:
        where_clause = "where: {user_id: {_eq: $user_id}, status_id: {_eq: $status_id}}"

    gql_query = """
    query MeBooks($user_id: Int!, $limit: Int!, $offset: Int!, $status_id: Int) {
      user_books(
        __WHERE_CLAUSE__
        order_by: {date_added: desc}
        limit: $limit
        offset: $offset
      ) {
        id
        book_id
        edition_id
        status_id
        rating
        review_raw
        review_has_spoilers
        reviewed_at
        date_added
        book {
          id
          title
          slug
        }
      }
    }
    """
    gql_query = gql_query.replace("__WHERE_CLAUSE__", where_clause)

    data = graphql_request(
        gql_query,
        {"user_id": user_id, "limit": limit, "offset": offset, "status_id": status_id},
        api_key,
    )
    return data.get("user_books", [])


@router.get("/statuses")
def get_me_book_statuses(api_key: str = Depends(get_api_key)):
    user_id = _get_me_id(api_key)

    gql_query = """
    query MeBookStatuses($user_id: Int!) {
      user_books(
        where: {user_id: {_eq: $user_id}}
        order_by: {date_added: desc}
        limit: 500
      ) {
        id
        status_id
      }
    }
    """

    data = graphql_request(gql_query, {"user_id": user_id}, api_key)
    books = data.get("user_books", [])
    status_counts = Counter(
        int(book["status_id"]) for book in books if isinstance(book, dict) and book.get("status_id") is not None
    )

    return {
        "total_books": len(books),
        "statuses": [
            {
                "status_id": status,
                "status_name": HARDCOVER_BOOK_STATUS_NAMES.get(status, "unknown"),
                "count": count,
            }
            for status, count in sorted(status_counts.items(), key=lambda item: item[0])
        ],
    }


@router.get("/currently-reading")
def get_currently_reading_books(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    currently_reading_status_id = _resolve_status_id(api_key, "currently_reading", "Currently Reading")
    return get_me_books(limit=limit, offset=offset, status_id=currently_reading_status_id, api_key=api_key)


@router.get("/read")
def get_read_books(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    read_status_id = _resolve_status_id(api_key, "read", "Read")
    return get_me_books(limit=limit, offset=offset, status_id=read_status_id, api_key=api_key)


@router.get("/want-to-read")
def get_want_to_read_books(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    want_to_read_status_id = _resolve_status_id(api_key, "want_to_read", "Want to Read")
    return get_me_books(limit=limit, offset=offset, status_id=want_to_read_status_id, api_key=api_key)


@router.post("")
def create_me_book(
    payload: dict[str, Any] = Body(...),
    api_key: str = Depends(get_api_key),
):
    user_id = _get_me_id(api_key)

    if payload.get("book_id") is None:
        raise HTTPException(status_code=422, detail="book_id is required")
    if payload.get("status_id") is None:
        raise HTTPException(status_code=422, detail="status_id is required")

    gql_query = """
    mutation CreateMeBook(
      $user_id: Int!
      $book_id: Int!
      $status_id: Int!
      $edition_id: Int
      $rating: numeric
      $review_raw: String
      $review_has_spoilers: Boolean
    ) {
      insert_user_book(
        object: {
          user_id: $user_id
          book_id: $book_id
          status_id: $status_id
          edition_id: $edition_id
          rating: $rating
          review_raw: $review_raw
          review_has_spoilers: $review_has_spoilers
        }
      ) {
        id
        user_book {
          id
          user_id
          book_id
          status_id
          rating
          review_raw
          review_has_spoilers
          reviewed_at
          date_added
        }
      }
    }
    """

    variables = {
        "user_id": user_id,
        "book_id": payload["book_id"],
        "status_id": payload["status_id"],
        "edition_id": payload.get("edition_id"),
        "rating": payload.get("rating"),
        "review_raw": payload.get("review_raw"),
        "review_has_spoilers": payload.get("review_has_spoilers"),
    }

    data = graphql_request(gql_query, variables, api_key)
    return data.get("insert_user_book")


@router.patch("/{user_book_id}")
def patch_me_book(
    user_book_id: int,
    payload: dict[str, Any] = Body(...),
    api_key: str = Depends(get_api_key),
):
    gql_query = """
    mutation UpdateMeBook(
      $id: Int!
      $status_id: Int
      $edition_id: Int
      $rating: numeric
      $review_raw: String
      $review_has_spoilers: Boolean
      $owned: Boolean
    ) {
      update_user_book(
        id: $id
        object: {
          status_id: $status_id
          edition_id: $edition_id
          rating: $rating
          review_raw: $review_raw
          review_has_spoilers: $review_has_spoilers
          owned: $owned
        }
      ) {
        id
        user_book {
          id
          user_id
          book_id
          status_id
          rating
          review_raw
          review_has_spoilers
          reviewed_at
          date_added
        }
      }
    }
    """

    variables = {
        "id": user_book_id,
        "status_id": payload.get("status_id"),
        "edition_id": payload.get("edition_id"),
        "rating": payload.get("rating"),
        "review_raw": payload.get("review_raw"),
        "review_has_spoilers": payload.get("review_has_spoilers"),
        "owned": payload.get("owned"),
    }

    data = graphql_request(gql_query, variables, api_key)
    return data.get("update_user_book")
