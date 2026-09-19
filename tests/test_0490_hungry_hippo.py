from pathlib import Path
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb']=types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb




def test_metadata_constraints_are_central_and_hard():
    for region in ['front_matter','back_matter','bibliography','index','paratext']:
        record={'region_type':region,'primary_text':True,'metadata_field_status':{}}
        changed=cb.apply_metadata_constraints(record)
        assert record['primary_text'] is False
        assert changed and changed[0]['field']=='primary_text'
        assert record['metadata_field_status']['primary_text']['method']=='region_type_consistency'
    record={'region_type':'main_text','primary_text':False,'metadata_field_status':{}}
    cb.apply_metadata_constraints(record)
    assert record['primary_text'] is True



