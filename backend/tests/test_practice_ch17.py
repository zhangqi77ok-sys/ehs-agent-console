"""Ch17 practice questions asset exists and is well-formed."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_practice_questions_json():
    path = ROOT / "docs" / "practice-questions.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) >= 10
    for q in data:
        assert q["id"]
        assert q["question"]
        assert q["rubric_points"]
        assert len(q["rubric_points"]) >= 1


def test_practice_rubric_doc():
    assert (ROOT / "docs" / "practice-rubric.md").exists()


def test_frontend_public_questions_synced():
    a = json.loads((ROOT / "docs" / "practice-questions.json").read_text(encoding="utf-8"))
    b = json.loads(
        (ROOT / "frontend" / "public" / "practice-questions.json").read_text(encoding="utf-8")
    )
    assert a == b
