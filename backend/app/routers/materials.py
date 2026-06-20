"""Router for the material library.

- GET  /materials          read current library (sample fallback if none saved)
- POST /materials/ingest   resume file/text -> decomposed library (preview, not saved)
- PUT  /materials          save a library to backend/data/materials.json
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from ..config import get_settings
from ..deps import make_client
from ..llm import LLMClient, LLMError
from ..materials_merge import merge_libraries
from ..materials_store import load_materials, save_materials
from ..pipeline.ingest import decompose_resume
from ..schemas import MaterialsLibrary
from ..text_extract import extract_text

router = APIRouter(tags=["materials"])


@router.get("/materials", response_model=MaterialsLibrary)
def get_materials() -> MaterialsLibrary:
    try:
        return load_materials()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load materials: {e}")


@router.post("/materials/ingest", response_model=MaterialsLibrary)
async def ingest_resume(
    file: Optional[UploadFile] = File(default=None),
    resume_text: str = Form(default=""),
    mode: str = Form(default="replace"),  # "replace" | "append"
    base_library: str = Form(default=""),  # JSON of the library to append into
    client: LLMClient = Depends(make_client),
) -> MaterialsLibrary:
    """Decompose an uploaded resume (file and/or pasted text) into a library.

    mode="append" merges the parse into a base library, adding only new
    experiences/bullets/skills. The base is `base_library` (the client's current
    in-memory library) when provided — this lets consecutive appends accumulate
    without saving in between — otherwise the saved user library on disk.
    Returns the (possibly merged) library for PREVIEW; nothing is saved until PUT.
    """
    text = resume_text or ""
    if file is not None:
        data = await file.read()
        try:
            text = extract_text(file.filename or "upload", data)
        except Exception as e:  # noqa: BLE001 - surface extraction problems clearly
            raise HTTPException(status_code=422, detail=f"Could not read file: {e}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No resume text provided.")

    try:
        parsed = decompose_resume(text, client=client)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if mode != "append":
        return parsed

    base: Optional[MaterialsLibrary] = None
    if base_library.strip():
        try:
            base = MaterialsLibrary.model_validate_json(base_library)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Invalid base_library: {e}")
    elif get_settings().materials_path.exists():
        base = load_materials()

    return merge_libraries(base, parsed) if base is not None else parsed


@router.put("/materials")
def put_materials(library: MaterialsLibrary) -> dict:
    """Persist a (reviewed) library to backend/data/materials.json (gitignored)."""
    path = save_materials(library)
    settings = get_settings()
    return {"saved": True, "path": str(path), "is_user_library": path == settings.materials_path}
