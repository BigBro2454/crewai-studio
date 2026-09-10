"""Application entrypoint – run with: python -m main  or  uvicorn main:app."""
import uvicorn
from backend.api.app import app  # noqa: F401 – re-export for uvicorn
from backend.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
