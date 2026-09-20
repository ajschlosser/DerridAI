"""Central, hard metadata constraints.

Why: some field combinations are impossible (front matter cannot be primary text).
The rule lives in one function, apply_metadata_constraints, so single-record edits,
bulk edits, and automatic enrichment all enforce it identically.
How: passes minimal record dicts to the function and inspects the result.
"""

import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb']=types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb


def test_metadata_constraints_are_central_and_hard():
    """Non-primary regions force primary_text=False; main_text defaults it to True.

    What: for front_matter, back_matter, bibliography, index and paratext, a record
    marked primary_text=True is corrected to False, the change is reported, and its
    status records method "region_type_consistency". A main_text record with
    primary_text=False is set to True.
    Why: this keeps apparatus (bibliography, index, paratext) out of the primary corpus.
    """
    for region in ['front_matter','back_matter','bibliography','index','paratext']:
        record={'region_type':region,'primary_text':True,'metadata_field_status':{}}
        changed=cb.apply_metadata_constraints(record)
        assert record['primary_text'] is False
        assert changed and changed[0]['field']=='primary_text'
        assert record['metadata_field_status']['primary_text']['method']=='region_type_consistency'
    record={'region_type':'main_text','primary_text':False,'metadata_field_status':{}}
    cb.apply_metadata_constraints(record)
    assert record['primary_text'] is True



