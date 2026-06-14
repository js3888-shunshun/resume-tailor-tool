"""Endpoint test: append uses the client's base_library so consecutive appends
accumulate (regression test for 'previous appended experience disappears')."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.routers import materials as mat
from app.schemas import (
    Bullet,
    Category,
    Experience,
    MaterialsLibrary,
    PersonalInfo,
)


def _lib_with(title: str, org: str, bullet: str) -> MaterialsLibrary:
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="e", phone="p"),
        experiences=[
            Experience(id="x", title=title, organization=org, categories=[Category.SDE],
                       bullets=[Bullet(id="b", text=bullet)])
        ],
    )


def test_append_accumulates_via_base_library(monkeypatch):
    client = TestClient(app)

    # First append: base = library with experience A, new parse = experience B.
    monkeypatch.setattr(mat, "decompose_resume", lambda text, c=None: _lib_with("B", "Beta", "b-bullet"))
    base_a = _lib_with("A", "Alpha", "a-bullet").model_dump(mode="json")
    r1 = client.post("/materials/ingest", data={
        "resume_text": "exp B text", "mode": "append", "base_library": json.dumps(base_a),
    })
    assert r1.status_code == 200
    merged1 = r1.json()
    assert {e["title"] for e in merged1["experiences"]} == {"A", "B"}

    # Second append: feed merged1 back as base, new parse = experience C.
    monkeypatch.setattr(mat, "decompose_resume", lambda text, c=None: _lib_with("C", "Gamma", "c-bullet"))
    r2 = client.post("/materials/ingest", data={
        "resume_text": "exp C text", "mode": "append", "base_library": json.dumps(merged1),
    })
    assert r2.status_code == 200
    # All three accumulate — A is NOT lost.
    assert {e["title"] for e in r2.json()["experiences"]} == {"A", "B", "C"}
