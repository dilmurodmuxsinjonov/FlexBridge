"""Typed metadata for the forward-only institutional review proof tables."""
from sqlalchemy import Column,Table


def register_tables(metadata,types):
    definitions={
        'institution_onboarding_requests':{
            'case_id':'uuid','created_at':'timestamptz','institution_id':'uuid','appointment_id':'uuid',
            'requester_user_id':'uuid','target_user_id':'uuid','mode':'text','role_id':'uuid',
            'idempotency_key':'text','request_fingerprint':'text'},
        'institution_onboarding_submissions':{
            'case_id':'uuid','revision':'integer','created_at':'timestamptz','submitted_by_id':'uuid','session_id':'uuid',
            'auth_version':'integer','requester_grant_id':'uuid','requester_contact_id':'uuid',
            'requester_contact_digest':'text','requester_contact_verified_at':'timestamptz','target_contact_id':'uuid',
            'target_contact_digest':'text','target_contact_verified_at':'timestamptz','target_auth_version':'integer',
            'document_file_id':'uuid','agreement_id':'uuid','legal_basis':'text','valid_from':'date','valid_to':'date','payload':'jsonb'},
        'institution_onboarding_consents':{
            'id':'uuid','case_id':'uuid','revision':'integer','event_no':'integer','created_at':'timestamptz',
            'actor_id':'uuid','session_id':'uuid','auth_version':'integer','decision':'text','contact_id':'uuid',
            'contact_digest':'text','contact_verified_at':'timestamptz','expires_at':'timestamptz'},
        'institution_onboarding_decisions':{
            'case_id':'uuid','revision':'integer','created_at':'timestamptz','actor_id':'uuid','session_id':'uuid',
            'auth_version':'integer','platform_grant_id':'uuid','decision':'text','reason':'text'}}
    optional={'requester_grant_id','valid_to','contact_id','contact_digest','contact_verified_at','expires_at'}
    for name,fields in definitions.items():
        keys={'case_id','revision'} if name.endswith(('submissions','decisions')) else ({'id'} if name.endswith('consents') else {'case_id'})
        Table(name,metadata,*[Column(column,types[kind],primary_key=column in keys,nullable=column in optional)
            for column,kind in fields.items()])
