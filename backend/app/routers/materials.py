"""Router for the material library. `GET /materials` (read).

Pulled forward from M8 because the web UI needs it to map experience/project
ids to human-readable titles when displaying selection results.
`PUT /materials` (write) will be added in M8.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..materials_store import load_materials
from ..schemas import MaterialsLibrary

router = APIRouter(tags=["materials"])


@router.get("/materials", response_model=MaterialsLibrary)
def get_materials() -> MaterialsLibrary:
    try:
        return load_materials()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load materials: {e}")
