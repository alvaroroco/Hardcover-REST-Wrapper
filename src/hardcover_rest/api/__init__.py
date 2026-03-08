from fastapi import FastAPI

from hardcover_rest.api.routes.books import router as books_router
from hardcover_rest.api.routes.me_books import router as me_books_router
from hardcover_rest.api.routes.me_lists import lists_router, me_lists_router
from hardcover_rest.api.routes.me_reviews import router as me_reviews_router

app = FastAPI(title="Hardcover REST Wrapper", version="0.1.0")

app.include_router(books_router)
app.include_router(me_books_router)
app.include_router(me_reviews_router)
app.include_router(me_lists_router)
app.include_router(lists_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
