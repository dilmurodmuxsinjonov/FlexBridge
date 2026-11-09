"""Ungranted claimants must not enumerate registered contacts via staff intake."""
from uuid import uuid4
from test_institution_onboarding import first_claim,submit
from test_invitations import contact
from test_regressions import count


def test_pending_first_claimant_cannot_distinguish_registered_staff_contacts(client,identities):
    f=first_claim(identities);created=submit(client,f);assert created.status_code==202,created.text
    target=identities();registered=contact(target,value=str(uuid4())+'@example.test',channel='EMAIL')
    template={key:f['body'][key] for key in ('registry_code','document_file_id','contact_id','valid_from','valid_to','legal_basis','file_ids','evidence_note')}
    template.update(agreement_id=created.json()['proposal']['agreement']['id'],target_channel='EMAIL')
    replies=[]
    for index,value in enumerate((registered['normalized_value'],str(uuid4())+'@example.test')):
        response=client.post('/api/v1/institution-appointments',headers={**f['user']['headers'],'Idempotency-Key':'unauthorized-staff-'+str(index)},json={**template,'target_destination':value})
        assert response.status_code==403,response.text
        replies.append(response.json()['detail']['code'])
    assert replies==['INSTITUTION_SCOPE_FORBIDDEN','INSTITUTION_SCOPE_FORBIDDEN'],replies
    assert count('institution_onboarding_requests')==count('institutions')==1 and count('institution_role_grants')==0
