"""Contact Scraper API - Main application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API for scraping contact information from websites",
    version="1.0.0",
    debug=settings.debug,
)


# Middleware to ensure proper response completion (fixes n8n hanging issue)
class ResponseCleanupMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Ensure Connection: close header for proper response completion
        response.headers["Connection"] = "close"
        return response


# Add response cleanup middleware first
app.add_middleware(ResponseCleanupMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
