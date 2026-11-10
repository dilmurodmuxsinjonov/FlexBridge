"""Previously valid canonical imports with inconsistent academic links stay historical."""
from datetime import timedelta

import pytest
from sqlalchemy import select,text

from app.db.storage import table,now
from app.db.institution_scope import TASHKENT
from app.services.placements import insert_row,get_row
from test_institution_migration import populated_database,seed_old_scope
from test_academic_migration import legacy_academic,history


@pytest.mark.parametrize('different_institution',[False,True])
def test_mismatched_imported_supervision_does_not_break_upgrade_or_grant_review(different_institution):
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:
            f=legacy_academic(conn)
            if different_institution:
                coordinator,inst,member,_,_=seed_old_scope(conn)
                institution_id=inst['id'];coordinator_id=member['id']
                teacher_member=insert_row(conn,'institution_memberships',institution_id=institution_id,user_id=f['teacher_id'],status='ACTIVE',accepted_at=now())
                appointment=insert_row(conn,'institution_appointments',institution_id=institution_id,user_id=f['teacher_id'],document_file_id=f['document_id'],
                    status='ACTIVE',valid_from=now().astimezone(TASHKENT).date()-timedelta(days=1),accepted_at=now())
                insert_row(conn,'institution_role_grants',membership_id=teacher_member['id'],role_id=f['teacher_role_id'],appointment_id=appointment['id'])
            else:
                institution_id=f['institution_id'];teacher_member={'id':f['teacher_member_id']}
                coordinator_id=get_row(conn,'student_supervisions',f['supervision_id'])['coordinator_membership_id']
            p=get_row(conn,'placements',f['placement_id'])
            other_enrollment=insert_row(conn,'enrollments',candidate_id=p['candidate_id'],institution_id=institution_id,program='Different imported enrollment',
                start_date=now().astimezone(TASHKENT).date()-timedelta(days=20),status='VERIFIED')
            agreement=insert_row(conn,'institution_agreements',institution_id=institution_id,version=1 if different_institution else 2,status='ACTIVE',
                valid_from=now().astimezone(TASHKENT).date()-timedelta(days=20),purposes=['ACADEMIC_VIEW'])
            supervision=insert_row(conn,'student_supervisions',institution_id=institution_id,enrollment_id=other_enrollment['id'],
                coordinator_membership_id=coordinator_id,agreement_id=agreement['id'],purpose='ACADEMIC_VIEW',legal_basis='Original separate scope.',status='ACTIVE',accepted_at=now())
            conn.execute(table('academic_assignments').update().where(table('academic_assignments').c.id==f['assignment_id']).values(
                institution_id=institution_id,teacher_membership_id=teacher_member['id'],supervision_id=supervision['id']))
        migrate('0014_placement_admission')
        with engine.begin() as conn:before=history(conn)
        result=migrate('head',False)
        assert result.returncode==0,'\n'.join(result.stderr.splitlines()[:12])
        with engine.begin() as conn:
            assert history(conn)==before
            b=conn.execute(select(table('placement_academic_bindings'))).mappings().one()
            assert b['supervision_id'] is None
            assert conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),{'a':f['assignment_id'],'t':f['terms_id']}).scalar_one() is False
