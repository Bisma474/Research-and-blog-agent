"""Render-friendly entry point.

Puts `src/` on sys.path so `api` is importable, then re-exports the app.
Used as `uvicorn run:app` on Render.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from api.main import app  # noqa: E402, F401
