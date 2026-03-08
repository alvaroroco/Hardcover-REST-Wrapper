from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hardcover_rest.api.clients.hardcover import graphql_request
from hardcover_rest.api.dependencies import get_api_key

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/search")
def search_books(
    query: str = Query(..., min_length=1),
    api_key: str = Depends(get_api_key),
):
    gql_query = """
    query SearchBooks($query: String!) {
      search(query: $query, query_type: "Book", per_page: 10, page: 1) {
        ids
        results
        query
        query_type
        page
        per_page
      }
    }
    """

    data = graphql_request(gql_query, {"query": query}, api_key)
    return data.get("search")
