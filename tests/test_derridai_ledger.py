import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.derridai_ledger import (
    compact_public_record,
    rehydrate_evidence_pointers,
    sparse_json,
    validate_compact_record,
)


def identity(record):
    return dict(record)


def test_sparse_preserves_required_confidence_null():
    assertion = {
        'assertion_id':'a1','record_id':'r1','field_id':'f1','field_name':'speaker',
        'derivation_method':'model','evaluation_status':'value_supported',
        'authority_status':'unreviewed','value_status':'present','value':'Derrida',
        'confidence':None,'actor':None,'evidence':[],'legacy_metadata':{},
    }
    out=sparse_json(assertion)
    assert out['confidence'] is None
    assert 'actor' not in out and 'evidence' not in out and 'legacy_metadata' not in out


def test_not_evaluated_omits_confidence():
    assertion = {
        'assertion_id':'a1','record_id':'r1','field_id':'f1',
        'derivation_method':'imported','evaluation_status':'not_evaluated',
        'authority_status':'unreviewed','value_status':'unresolved','confidence':None,
    }
    out=sparse_json(assertion)
    assert 'confidence' not in out


def test_compact_deduplicates_evidence_and_drops_flat_projection():
    evidence=[{'block_id':'b1','quote':'abc'}]
    record={
        'record_id':'r1','source_document_id':'doc1','text':'abc',
        'source_spans':[{'source_document_id':'doc1','source_unit_id':'b1'}],
        'speaker':'Derrida','concepts':[],
        'field_assertions':{
            'derridai.speaker':[
                {
                    'assertion_id':'a1','record_id':'r1','field_id':'derridai.speaker','field_name':'speaker',
                    'value':'Derrida','derivation_method':'model','evaluation_status':'value_supported',
                    'authority_status':'unreviewed','value_status':'present','confidence':0.82,
                    'evidence':evidence,
                },
                {
                    'assertion_id':'a2','record_id':'r1','field_id':'derridai.speaker','field_name':'speaker',
                    'value':'Derrida','derivation_method':'model','evaluation_status':'value_supported',
                    'authority_status':'human_confirmed','value_status':'present','confidence':0.82,
                    'evidence':evidence,'supersedes_assertion_id':'a1','actor':None,
                },
            ]
        },
        'current_field_assertions':{'derridai.speaker':'a2'},
        'legacy_metadata':{},
    }
    out=compact_public_record(record,serialize_record=identity)
    assert 'speaker' not in out
    a1,a2=out['field_assertions']['derridai.speaker']
    assert a1['evidence']==evidence
    assert 'evidence' not in a2
    assert a2['evidence_source_assertion_id']=='a1'
    hydrated=rehydrate_evidence_pointers(out)
    assert hydrated['field_assertions']['derridai.speaker'][1]['evidence']==evidence
    assert 'evidence_source_assertion_id' not in hydrated['field_assertions']['derridai.speaker'][1]
    assert validate_compact_record(out)==[]


def test_unresolved_assertion_is_not_removed():
    record={
        'record_id':'r1','source_document_id':'doc1','text':'abc',
        'source_spans':[{'source_document_id':'doc1','source_unit_id':'b1'}],
        'field_assertions':{
            'derridai.position_holder':[
                {
                    'assertion_id':'a3','record_id':'r1','field_id':'derridai.position_holder','field_name':'position_holder',
                    'value':None,'derivation_method':'model','evaluation_status':'no_supported_value',
                    'authority_status':'unreviewed','value_status':'unresolved','confidence':None,
                    'evidence':[],'legacy_metadata':{},
                }
            ]
        },
        'current_field_assertions':{'derridai.position_holder':'a3'},
    }
    out=compact_public_record(record,serialize_record=identity)
    a3=out['field_assertions']['derridai.position_holder'][0]
    assert a3['value_status']=='unresolved'
    assert 'value' not in a3
    assert 'confidence' in a3 and a3['confidence'] is None
