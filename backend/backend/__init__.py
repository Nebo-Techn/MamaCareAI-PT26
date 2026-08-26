"""
MamaCare AI backend.

Present so the backend is importable as a package from the repository root,
which is what makes these work:

    python -m backend.modules.pipeline.worker --stage extract
    python -m backend.modules.pipeline.cli submit --url ...

The FastAPI quick start in the root README still runs from inside `backend/`
(`uvicorn main:app --reload`); both entry styles work.
"""
