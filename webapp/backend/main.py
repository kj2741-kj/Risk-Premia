"""
FastAPI entry point. Run from this directory with:
    uvicorn main:app --reload --port 8000

Centralizes the sys.path bootstrap that each Streamlit dashboard's app.py
otherwise repeats independently -- this backend is one process importing all
four asset classes' modules, so scattering sys.path.insert() across every
router/service file would just be noise. The boot-time import assertion
below makes a broken checkout (e.g. a deploy that only ships webapp/ and not
the rest of the repo) fail loudly at startup, not on a user's first request.
"""

import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_BACKEND_DIR))

for _p in (
    _BACKEND_DIR,
    _REPO_ROOT,
    os.path.join(_REPO_ROOT, "scripts"),
    os.path.join(_REPO_ROOT, "research"),
    os.path.join(_REPO_ROOT, "research", "configs"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import common_curve_loader  # noqa: F401
    import common_engine  # noqa: F401
    import rolling_continuous  # noqa: F401
except ImportError as exc:
    raise RuntimeError(
        f"Backend could not import repo-root research modules from {_REPO_ROOT!r}. "
        "Run this backend from within the full Risk Premia repo checkout (the webapp/ "
        "folder alone is not enough -- it depends on common_engine.py, scripts/, and "
        "research/ living alongside it)."
    ) from exc

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api import router as api_router  # noqa: E402

app = FastAPI(title="Risk Premia API")

# FRONTEND_ORIGINS: comma-separated extra origins (set on Render once the
# Vercel URL is known, e.g. "https://risk-premia.vercel.app"). The regex
# additionally allows any Vercel preview-deployment subdomain automatically,
# since those change per branch/PR and can't be pinned to one static value.
_extra_origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *_extra_origins],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
