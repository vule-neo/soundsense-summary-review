"""Vercel entrypoint: exposes the FastAPI app as a Python serverless function."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import app  # noqa: E402

__all__ = ["app"]
