from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from hardcover_rest.api.clients.hardcover import graphql_request
from hardcover_rest.api.dependencies import get_api_key

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/search")
def search_books(
    query: str = Query(..., min_length=1),
    query_type: str = Query("Book"),
    per_page: int = Query(25, ge=1, le=100),
    page: int = Query(1, ge=1),
    api_key: str = Depends(get_api_key),
):
    gql_query = """
    query SearchBooks($query: String!, $query_type: String!, $per_page: Int!, $page: Int!) {
      search(query: $query, query_type: $query_type, per_page: $per_page, page: $page) {
        ids
        results
        query
        query_type
        page
        per_page
      }
    }
    """

    data = graphql_request(
        gql_query,
        {
            "query": query,
            "query_type": query_type,
            "per_page": per_page,
            "page": page,
        },
        api_key,
    )

    return data.get("search")


@router.get("/{book_id}")
def get_book(book_id: int, api_key: str = Depends(get_api_key)):
    gql_query = """
    query GetBookById($book_id: Int!) {
      books(where: {id: {_eq: $book_id}}, limit: 1) {
        id
        title
        subtitle
        slug
        description
        rating
        ratings_count
        reviews_count
        release_date
        pages
        contributions {
          author {
            id
            name
          }
        }
      }
    }
    """

    data = graphql_request(gql_query, {"book_id": book_id}, api_key)
    books = data.get("books", [])
    if not books:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    return books[0]
