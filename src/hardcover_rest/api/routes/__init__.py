from hardcover_rest.api.routes.books import router as books_router
from hardcover_rest.api.routes.me_books import router as me_books_router

__all__ = [
    "books_router",
    "me_books_router",
]
