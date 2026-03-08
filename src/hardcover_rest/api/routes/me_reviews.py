from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from hardcover_rest.api.clients.hardcover import graphql_request
from hardcover_rest.api.dependencies import get_api_key

router = APIRouter(prefix="/me/reviews", tags=["me-reviews"])


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


@router.get("")
def get_me_reviews(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    user_id = _get_me_id(api_key)

    gql_query = """
    query MeReviews($user_id: Int!, $limit: Int!, $offset: Int!) {
      user_books(
        where: {user_id: {_eq: $user_id}, has_review: {_eq: true}}
        order_by: {reviewed_at: desc}
        limit: $limit
        offset: $offset
      ) {
        id
        rating
        review_raw
        review_has_spoilers
        reviewed_at
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
        {"user_id": user_id, "limit": limit, "offset": offset},
        api_key,
    )
    return data.get("user_books", [])


@router.post("")
def create_me_review(
    payload: dict[str, Any] = Body(...),
    api_key: str = Depends(get_api_key),
):
    user_id = _get_me_id(api_key)

    if payload.get("book_id") is None:
        raise HTTPException(status_code=422, detail="book_id is required")

    gql_query = """
    mutation CreateMeReview(
      $user_id: Int!
      $book_id: Int!
      $status_id: Int!
      $rating: numeric
      $review_raw: String!
      $review_has_spoilers: Boolean
    ) {
      insert_user_book(
        object: {
          user_id: $user_id
          book_id: $book_id
          status_id: $status_id
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
        }
      }
    }
    """

    variables = {
        "user_id": user_id,
        "book_id": payload["book_id"],
        "status_id": payload.get("status_id", 3),
        "rating": payload.get("rating"),
        "review_raw": payload.get("review_raw", ""),
        "review_has_spoilers": payload.get("review_has_spoilers", False),
    }

    data = graphql_request(gql_query, variables, api_key)
    return data.get("insert_user_book")
