from fastapi import APIRouter, HTTPException, Header
from hardcover_rest.api.clients.hardcover import graphql_request

router = APIRouter(prefix="/series")

@router.get("/{series_id}/books")
def get_series_books(series_id: int, authorization: str | None = Header(None)):

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    query = """
    query GetSeriesBooks($series_id: Int!) {
      book_series(where: {series_id: {_eq: $series_id}}) {
        position
        book {
          id
          title
          rating
          pages
        }
      }
    }
    """

    data = graphql_request(query, {"series_id": series_id}, authorization)

    return data["data"]
