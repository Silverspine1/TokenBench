"""FastAPI app factory for the manual-IDE UI.

Holds no benchmark logic: HTML pages render registry data, and every mutating
action is delegated to ``tokenbench.manual``. ``create_app`` wires the routers,
templates, and static files and stashes the base/runs_root on ``app.state``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .registry import list_suites, runs_root
from .routes import bundles, charts, costs, db, results, runs, suites

_UI_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(_UI_DIR / "templates"))


def _static_version() -> str:
    """A token that changes whenever a static asset changes, for cache-busting."""
    static = _UI_DIR / "static"
    mtimes = [p.stat().st_mtime for p in static.glob("*") if p.is_file()]
    return str(int(max(mtimes))) if mtimes else "0"


# Exposed to every template so <script>/<link> can append ?v=... and the browser
# refetches assets after an edit instead of serving a stale cached copy.
TEMPLATES.env.globals["static_version"] = _static_version()


def create_app(base: Optional[Path] = None, db_path: Optional[Path] = None) -> FastAPI:
    base = Path(base) if base else Path.cwd()
    app = FastAPI(title="TokenBench manual IDE UI", docs_url="/api/docs")
    app.state.base = base
    app.state.runs_root = runs_root(base)
    app.state.db_path = Path(db_path) if db_path else (base / "tokenbench.db")

    app.mount("/static", StaticFiles(directory=str(_UI_DIR / "static")), name="static")

    app.include_router(suites.router)
    app.include_router(runs.router)
    app.include_router(bundles.router)
    app.include_router(costs.router)
    app.include_router(results.router)
    app.include_router(db.router)
    app.include_router(charts.router)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request, "index.html", {"suites": list_suites(base)}
        )

    @app.get("/queue/{suite_id}", response_class=HTMLResponse)
    def queue(request: Request, suite_id: str) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request, "task_queue.html", {"suite_id": suite_id}
        )

    @app.get("/console/{run_id}", response_class=HTMLResponse)
    def console(request: Request, run_id: str) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request, "run_console.html", {"run_id": run_id}
        )

    @app.get("/result/{run_id}", response_class=HTMLResponse)
    def result(request: Request, run_id: str) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request, "result.html", {"run_id": run_id}
        )

    @app.get("/database", response_class=HTMLResponse)
    def database(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "database.html", {})

    @app.get("/charts", response_class=HTMLResponse)
    def charts_page(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "charts.html", {})

    return app
