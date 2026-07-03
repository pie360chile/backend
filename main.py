try:
    from app.backend.core.config import load_backend_env

    load_backend_env()
except ImportError:
    pass

import uvicorn

from app.backend.core.app_factory import create_app

app = create_app()
application = app

if __name__ == "__main__":
    uvicorn.run("main:app", port=8005, reload=True)
