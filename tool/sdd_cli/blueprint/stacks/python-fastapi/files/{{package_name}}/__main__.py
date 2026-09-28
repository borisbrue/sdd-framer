"""Einstieg: `python -m {{package_name}}` startet den Dienst (uvicorn)."""
from . import __version__
from .api import create_app

app = create_app(__version__)


def main() -> int:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
