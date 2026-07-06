"""TokenBench manual-IDE web UI.

A thin FastAPI control surface over ``tokenbench.manual``. It holds zero
benchmark logic: every route loads suites/manifests through the existing loaders
and creates/submits/scores runs through the manual service. Optional dependency
group ``ui`` (fastapi, uvicorn, jinja2, python-multipart).
"""
