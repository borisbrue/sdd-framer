"""HTTP-Schnittstelle von {{project_name}}."""
from fastapi import FastAPI


def create_app(version: str) -> FastAPI:
    app = FastAPI(title="{{project_name}}", version=version)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": version}

    return app
