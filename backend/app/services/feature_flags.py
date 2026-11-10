"""Durable global flag access; human changes require actual current ADMIN authority."""
from app.services.feature_flag_admin import flag_admin_service
from app.services.governance import GovernanceError


class FeatureFlagService:
    def verify_storage(self):
        return flag_admin_service.verify_storage()

    def is_enabled(self,key,*,organization_id=None):
        if organization_id is not None:
            raise GovernanceError('GLOBAL_FEATURE_FLAGS_ONLY',status_code=422)
        return flag_admin_service.effective_enabled(key)

    def set_global_flag(self,*,key,enabled,actor,reason,idempotency_key,expected_version):
        return flag_admin_service.administer(actor=actor,code=key,enabled=enabled,reason=reason,
            idempotency_key=idempotency_key,expected_version=expected_version)

    def set_organization_override(self,**values):
        raise GovernanceError('GLOBAL_FEATURE_FLAGS_ONLY',status_code=422)
