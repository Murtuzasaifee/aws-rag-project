import uvicorn

from ragapp.main import app
from ragapp.core.config import get_settings

settings = get_settings()

if __name__ == "__main__":

    uvicorn.run(
        "app:app",  # Format: "module_name:variable_name"
        host="0.0.0.0",
        port=settings.port,
        reload=True,  # When True, requires module:instance format
        # reload_dirs=["src"]  # Watch the src directory for changes
    )
