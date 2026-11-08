"""Durable, non-destructive operational evaluations. No in-memory execution claims."""
from dataclasses import dataclass, field
import hashlib
import json
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.api.dependencies import require_platform
from app.core.audit import AppendOnlyAuditStore
from app.core.circuit_breaker import shared_circuit_breaker
from app.core.iam_security import rate_limit
from app.db.storage import transaction,now,retention_evaluations
from app.services.organizations import require_mfa
from app.services.feature_flags import FeatureFlagService
from app.services.retention import RetentionPolicyService


class OperationsInvariantError(ValueError):
    def __init__(self,code,status_code=409):
        super().__init__(code);self.code,self.status_code=code,status_code


@dataclass
class PilotOperationsService:
    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    circuit_breaker: object = field(default_factory=lambda:shared_circuit_breaker)
    retention_service: RetentionPolicyService = field(default_factory=RetentionPolicyService)
    feature_flag_service: FeatureFlagService = field(default_factory=FeatureFlagService)

    def submit_and_resolve_moderation_appeal(self,**kwargs):
        raise OperationsInvariantError('COMBINED_APPEAL_REMOVED_SEPARATE_DURABLE_REVIEW_REQUIRED',410)

    def execute_retention_job(self,**kwargs):
        raise OperationsInvariantError('PURGE_NOT_EXECUTED_USE_DURABLE_EVALUATION',410)

    def record_retention_evaluation(self,actor,*,data_category,age_days,records_scanned,idempotency_key):
        require_platform(actor,'COMPLIANCE');require_mfa(actor)
        if (type(age_days) is not int or type(records_scanned) is not int or
            not isinstance(idempotency_key,str) or not 8<=len(idempotency_key)<=128 or
            not 0<=age_days<=365000 or not 0<=records_scanned<=1000000000):
            raise OperationsInvariantError('INVALID_EVALUATION_INPUT',422)
        try:
            evaluation=self.retention_service.evaluate_age_days(data_category,age_days)
            policy=self.retention_service.get_policy(data_category)
        except (ValueError,KeyError) as exc:
            raise OperationsInvariantError('INVALID_RETENTION_POLICY_OR_AGE',422) from exc
        rate_limit('retention-evaluation',actor.user_id,30,600)
        fingerprint=hashlib.sha256(json.dumps([data_category,age_days,records_scanned],separators=(',',':')).encode()).hexdigest()
        with transaction() as conn:
            created=conn.execute(insert(retention_evaluations).values(id=str(uuid4()),created_at=now(),actor_id=actor.user_id,
                idempotency_key=idempotency_key,request_fingerprint=fingerprint,data_category=data_category,
                requested_age_days=age_days,requested_records_scanned=records_scanned,
                policy_snapshot={**policy,'source':'REFERENCE_V1_EVALUATION_ONLY','legal_approval_status':'NOT_CERTIFIED'},
                evaluation=evaluation,mode='DRY_RUN',status='EVALUATED_ONLY',records_scanned=0,records_actioned=0,finished_at=now())
                .on_conflict_do_nothing(index_elements=['actor_id','idempotency_key']).returning(retention_evaluations.c.id)).scalar_one_or_none()
            row=conn.execute(select(retention_evaluations).where(retention_evaluations.c.actor_id==actor.user_id,
                retention_evaluations.c.idempotency_key==idempotency_key).with_for_update()).mappings().one()
            if row['request_fingerprint']!=fingerprint:
                raise OperationsInvariantError('IDEMPOTENCY_PAYLOAD_CONFLICT')
            if created:
                self.audit_store.append_audit_event(actor_id=actor.user_id,action='RETENTION_DRY_RUN_RECORDED',
                    entity_type='retention_evaluation',entity_id=row['id'],metadata={'data_category':data_category,'records_actioned':0})
            return self._report(row,idempotent_replay=not bool(created))

    def get_retention_evaluation(self,actor,evaluation_id):
        require_platform(actor,'COMPLIANCE','ADMIN');require_mfa(actor)
        with transaction() as conn:
            row=conn.execute(select(retention_evaluations).where(retention_evaluations.c.id==evaluation_id)).mappings().first()
            if not row:raise OperationsInvariantError('RETENTION_EVALUATION_NOT_FOUND',404)
            return self._report(row)

    def _report(self,row,**extra):
        return {'id':row['id'],'created_at':row['created_at'],'actor_id':row['actor_id'],
            'dry_run':True,'execution_status':'NOT_EXECUTED','mode':row['mode'],'status':row['status'],
            'records_scanned':0,'records_actioned':0,'requested_records_scanned':row['requested_records_scanned'],
            'evaluation':row['evaluation'],'policy_snapshot':row['policy_snapshot'],**extra}

    def get_pilot_readiness_report(self) -> dict:
        """Generates the S2.10.1 R1 Pilot Readiness Report across schema, DR targets, AC-001..042, and Q-011."""
        from app.core.readiness import dependency_readiness
        report=dependency_readiness()
        return {
            'pilot_ready':False,
            'acceptance_status':'REQUIRES_E2E_AND_DR_EVIDENCE',
            'infrastructure':report,
            'schema_migrated':report['checks']['database'],
            'finance_circuit_state':self.circuit_breaker.state,
            'release_stage':'R1_IMPLEMENTATION',
            'disaster_recovery_targets':{'rpo_hours':24,'rto_hours':4,'restore_drill_verified':False},
            'r2_freelance_enabled':self.feature_flag_service.is_enabled('R2_FREELANCE_MARKETPLACE'),
        }
