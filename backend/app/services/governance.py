"""Governance, Dual-Control (`INV-11`), and Scope Authorization (`INV-12`, `API-060`, `API-061`, `AC-041`) service (S2.2.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.audit import AppendOnlyAuditStore


class GovernanceError(Exception):
    """Raised on Dual-Control (`INV-11`), Role (`API-060/061`), or Scope (`INV-12`, `AC-041`) violations."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass
class GovernanceScopeService:
    """Enforces Dual-Control (`INV-11`), Cross-Table Scope (`INV-12`), and API-060/061 role rules (`AC-041`)."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    org_members: dict[str, dict[str, Any]] = field(default_factory=dict)
    inst_members: dict[str, dict[str, Any]] = field(default_factory=dict)
    student_supervisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    academic_assignments: dict[str, dict[str, Any]] = field(default_factory=dict)
    moderation_actions: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create_org_member_request(
        self,
        *,
        organization_id: str,
        user_id: str,
        role_code: str,
        created_by: str,
    ) -> dict[str, Any]:
        member_id = str(uuid4())
        record = {
            "id": member_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "role_code": role_code,
            "status": "PENDING_APPROVAL",
            "created_by": created_by,
            "approved_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.org_members[member_id] = record
        return dict(record)

    def approve_org_member(
        self,
        *,
        organization_id: str,
        member_id: str,
        approved_by: str,
        approver_org_id: str,
    ) -> dict[str, Any]:
        """Approve an organization membership enforcing `INV-11` (`created_by != approved_by`) and `INV-12` scope."""
        record = self.org_members.get(member_id)
        if not record:
            raise GovernanceError("MEMBER_NOT_FOUND", "A'zolik so'rovi topilmadi", status_code=404)

        if record["organization_id"] != organization_id or approver_org_id != organization_id:
            raise GovernanceError(
                "SCOPE_VIOLATION",
                "Begona tashkilot a'zosini tasdiqlash taqiqlangan (INV-12, AC-041)",
                status_code=403,
            )

        if record["created_by"] == approved_by:
            raise GovernanceError(
                "SELF_APPROVAL_FORBIDDEN",
                "Ikki shaxs qoidasi (INV-11): yaratuvchi o'z so'rovini o'zi tasdiqlay olmaydi (AC-041)",
                status_code=409,
            )

        record["status"] = "ACTIVE"
        record["approved_by"] = approved_by
        record["approved_at"] = datetime.now(timezone.utc).isoformat()
        self.audit_store.append_audit_event(
            actor_id=approved_by,
            action="ORG_MEMBER_APPROVED_DUAL_CONTROL",
            entity_type="organization_member",
            entity_id=member_id,
            metadata={"organization_id": organization_id, "created_by": record["created_by"]},
        )
        return dict(record)

    def register_student_supervision(
        self,
        *,
        institution_id: str,
        student_id: str,
        supervisor_id: str,
    ) -> dict[str, Any]:
        sup_id = str(uuid4())
        record = {
            "id": sup_id,
            "institution_id": institution_id,
            "student_id": student_id,
            "supervisor_id": supervisor_id,
            "status": "ACTIVE",
        }
        self.student_supervisions[sup_id] = record
        return dict(record)

    def create_academic_assignment_api_060(
        self,
        *,
        actor_id: str,
        actor_role: str,
        actor_institution_id: str | None,
        institution_id: str,
        placement_id: str,
        supervision_id: str,
        supervisor_id: str,
    ) -> dict[str, Any]:
        """API-060 (`POST /api/v1/internships/academic-assignments`):

        1.4 PDF section 4 & `AC-041`:
        - Allowed ONLY for `INST_INTERNSHIP_COORDINATOR` or `SUPER_ADMIN` (`ACADEMIC_SUPERVISOR` is forbidden).
        - `supervision_id` and `supervisor_id` must belong to the same `institution_id` (`INV-09`).
        """
        if actor_role not in ("INST_INTERNSHIP_COORDINATOR", "SUPER_ADMIN"):
            raise GovernanceError(
                "FORBIDDEN_ROLE_FOR_API_060",
                "API-060 faqat INST_INTERNSHIP_COORDINATOR yoki SUPER_ADMIN uchun ruxsat etilgan (AC-041)",
                status_code=403,
            )

        if actor_role == "INST_INTERNSHIP_COORDINATOR" and actor_institution_id != institution_id:
            raise GovernanceError(
                "SCOPE_VIOLATION",
                "Koordinator faqat o'z muassasasi (institution_id) doirasida tayinlov yarata oladi (AC-041)",
                status_code=403,
            )

        sup = self.student_supervisions.get(supervision_id)
        if not sup or sup["institution_id"] != institution_id or sup["supervisor_id"] != supervisor_id:
            raise GovernanceError(
                "CROSS_INSTITUTION_SUPERVISION_MISMATCH",
                "Talaba va akademik rahbar aynan shu oliygoh/muassasaga tegishli bo'lishi shart (INV-09)",
                status_code=409,
            )

        assignment_id = str(uuid4())
        record = {
            "id": assignment_id,
            "institution_id": institution_id,
            "placement_id": placement_id,
            "supervision_id": supervision_id,
            "supervisor_id": supervisor_id,
            "assigned_by": actor_id,
            "status": "ACTIVE",
            "evaluation_note": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.academic_assignments[assignment_id] = record
        return dict(record)

    def update_academic_assignment_api_061(
        self,
        *,
        assignment_id: str,
        actor_id: str,
        actor_role: str,
        actor_institution_id: str | None,
        status: str | None = None,
        evaluation_note: str | None = None,
    ) -> dict[str, Any]:
        """API-061 (`PATCH /api/v1/internships/academic-assignments/{id}`):

        1.4 PDF section 4 & `AC-041`:
        - Allowed ONLY for `INST_INTERNSHIP_COORDINATOR`, `ACADEMIC_SUPERVISOR`, or `SUPER_ADMIN`.
        - Non-SUPER_ADMIN actors must match `assignment.institution_id`, and `ACADEMIC_SUPERVISOR`
          must also be the assigned `supervisor_id`.
        """
        if actor_role not in ("INST_INTERNSHIP_COORDINATOR", "ACADEMIC_SUPERVISOR", "SUPER_ADMIN"):
            raise GovernanceError(
                "FORBIDDEN_ROLE_FOR_API_061",
                "API-061 uchun ruxsat etilmagan rol",
                status_code=403,
            )

        record = self.academic_assignments.get(assignment_id)
        if not record:
            raise GovernanceError("ASSIGNMENT_NOT_FOUND", "Akademik tayinlov topilmadi", status_code=404)

        if actor_role != "SUPER_ADMIN":
            if actor_institution_id != record["institution_id"]:
                raise GovernanceError(
                    "SCOPE_VIOLATION",
                    "Begona muassasa akademik tayinlovini o'zgartirish taqiqlangan (AC-041)",
                    status_code=403,
                )
            if actor_role == "ACADEMIC_SUPERVISOR" and record["supervisor_id"] != actor_id:
                raise GovernanceError(
                    "SCOPE_VIOLATION",
                    "Akademik rahbar faqat o'ziga biriktirilgan tayinlovni yangilay oladi (AC-041)",
                    status_code=403,
                )

        if status is not None:
            record["status"] = status
        if evaluation_note is not None:
            record["evaluation_note"] = evaluation_note
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(record)

    def record_moderation_action(
        self,
        *,
        actor_id: str,
        target_entity_type: str,
        target_entity_id: str,
        action_type: str,
        policy_code: str,
        reason_code: str,
        justification: str,
    ) -> dict[str, Any]:
        """Enforce `AC-041` / `chk_moderation_justification`: policy_code, reason_code, and justification >= 15 chars."""
        if not policy_code.strip() or not reason_code.strip() or len(justification.strip()) < 15:
            raise GovernanceError(
                "MODERATION_JUSTIFICATION_REQUIRED",
                "Moderatsiya amali uchun policy_code, reason_code va kamida 15 belgili justification majburiy (AC-041)",
                status_code=422,
            )
        action_id = str(uuid4())
        record = {
            "id": action_id,
            "actor_id": actor_id,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "action_type": action_type,
            "policy_code": policy_code.strip(),
            "reason_code": reason_code.strip(),
            "justification": justification.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.moderation_actions[action_id] = record
        self.audit_store.append_audit_event(
            actor_id=actor_id,
            action=f"MODERATION_{action_type}",
            entity_type=target_entity_type,
            entity_id=target_entity_id,
            metadata={"policy_code": record["policy_code"], "reason_code": record["reason_code"]},
        )
        return dict(record)


governance_service = GovernanceScopeService()
