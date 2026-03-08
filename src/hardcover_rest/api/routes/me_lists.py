from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from hardcover_rest.api.clients.hardcover import graphql_request
from hardcover_rest.api.dependencies import get_api_key

me_lists_router = APIRouter(prefix="/me/lists", tags=["me-lists"])
lists_router = APIRouter(prefix="/lists", tags=["lists"])


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


@me_lists_router.get("")
def get_me_lists(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key),
):
    user_id = _get_me_id(api_key)

    gql_query = """
    query MeLists($user_id: Int!, $limit: Int!, $offset: Int!) {
      lists(
        where: {user_id: {_eq: $user_id}}
        order_by: {created_at: desc}
        limit: $limit
        offset: $offset
      ) {
        id
        name
        description
        slug
        privacy_setting_id
        created_at
        updated_at
      }
    }
    """

    data = graphql_request(
        gql_query,
        {"user_id": user_id, "limit": limit, "offset": offset},
        api_key,
    )
    return data.get("lists", [])


@me_lists_router.post("")
def create_me_list(
    payload: dict[str, Any] = Body(...),
    api_key: str = Depends(get_api_key),
):
    if not payload.get("name"):
        raise HTTPException(status_code=422, detail="name is required")

    gql_query = """
    mutation CreateList($name: String!, $description: String, $privacy_setting_id: Int) {
      insert_list(
        object: {
          name: $name
          description: $description
          privacy_setting_id: $privacy_setting_id
        }
      ) {
        id
        list {
          id
          name
          description
          slug
          privacy_setting_id
          created_at
        }
      }
    }
    """

    variables = {
        "name": payload["name"],
        "description": payload.get("description"),
        "privacy_setting_id": payload.get("privacy_setting_id", 1),
    }

    data = graphql_request(gql_query, variables, api_key)
    return data.get("insert_list")


@lists_router.post("/{list_id}/books")
def add_book_to_list(
    list_id: int,
    payload: dict[str, Any] = Body(...),
    api_key: str = Depends(get_api_key),
):
    if payload.get("book_id") is None:
        raise HTTPException(status_code=422, detail="book_id is required")

    gql_query = """
    mutation AddBookToList($list_id: Int!, $book_id: Int!, $edition_id: Int, $position: Int) {
      insert_list_book(
        object: {
          list_id: $list_id
          book_id: $book_id
          edition_id: $edition_id
          position: $position
        }
      ) {
        id
        list_book {
          id
          list_id
          book_id
          edition_id
          position
          created_at
          updated_at
        }
      }
    }
    """

    variables = {
        "list_id": list_id,
        "book_id": payload["book_id"],
        "edition_id": payload.get("edition_id"),
        "position": payload.get("position"),
    }

    data = graphql_request(gql_query, variables, api_key)
    return data.get("insert_list_book")
