"""Einstieg: `python -m {{package_name}}`."""
from . import __version__


def main() -> int:
    print(f"{{project_name}} {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
