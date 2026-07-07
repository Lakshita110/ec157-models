"""Notion property-mapping tests against a recorded fixture — no live API."""

import json
from datetime import date
from pathlib import Path

from vesper.tools.notion import parse_knee_log_page, parse_task_page

DAY = date(2026, 7, 6)
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "knee_log_page.json").read_text())


def test_parse_knee_log_page():
    parsed = parse_knee_log_page(FIXTURE, DAY)
    assert parsed.pain_level == 4
    assert parsed.pain_location == "Left knee (medial)"
    assert parsed.pt_done is True
    assert parsed.day_score == 7
    assert parsed.habits == {"Stretching": True, "Reading": False}  # PT excluded


def test_parse_knee_log_page_tolerates_missing_properties():
    parsed = parse_knee_log_page({"properties": {}}, DAY)
    assert parsed.pain_level is None
    assert parsed.pt_done is False
    assert parsed.habits == {}


def test_parse_task_page():
    page = {
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "PT appointment"}]}
        }
    }
    assert parse_task_page(page) == "PT appointment"
    assert parse_task_page({"properties": {}}) == ""
