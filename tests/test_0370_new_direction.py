from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))








def test_collection_name_contract_is_validated_in_api_schema():
    from app.models import StoreCreate

    with pytest.raises(ValidationError):
        StoreCreate(name="x")
    with pytest.raises(ValidationError):
        StoreCreate(name="192.168.1.1")
    with pytest.raises(ValidationError):
        StoreCreate(name="bad name")
    model = StoreCreate(name="derrida-primary")
    assert model.retrieval_mode == "hybrid"
    assert model.distance_metric == "cosine"







