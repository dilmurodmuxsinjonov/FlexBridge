"""User-to-user chat: direct conversations and groups (Issue #253).

Who can reach whom
------------------
A user may start a direct chat or add someone to a group only when a real
relationship exists (``_relations``):

* colleagues: both ACTIVE members of the same organization or institution;
* employer <-> applicant: an organization member and a candidate who applied
  to one of that organization's opportunities;
* university <-> student: an institution staff member and a candidate with a
  VERIFIED enrollment at that institution;
* an existing direct-chat partner.

Anyone else can be reached only with the other person's personal contact
code, which that person chooses to share (and can rotate). Blocks work in
both directions. Conversations are visible only to their current members;
for everyone else they do not exist (404).
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.dependencies import ActorContext
from app.db.storage import now, table, transaction
from app.services.authority import account_authority
from app.services.governance import GovernanceError
from app.services.placements import insert_row

MAX_BODY = 4000
MAX_GROUP = 200
PAGE = 50
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

RELATION_LABELS = ("COLLEAGUE", "EMPLOYER", "APPLICANT", "UNIVERSITY", "STUDENT", "CHAT")


def _err(code: str, status: int = 409) -> GovernanceError:
    return GovernanceError(code, status_code=status)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


class ChatService:
    # ------------------------------------------------------------------ relations
    def _relations(self, conn, uid: str) -> dict[str, str]:
        om, im = table("org_memberships"), table("institution_memberships")
        apps, opp, cp, enr = table("applications"), table("opportunities"), table("candidate_profiles"), table("enrollments")
        conv, mem = table("chat_conversations"), table("chat_members")

        def active(m):
            return and_(m.c.status == "ACTIVE", m.c.revoked_at.is_(None))

        found: dict[str, str] = {}

        def add(rows, label):
            for (other,) in rows:
                if other and str(other) != uid:
                    found.setdefault(str(other), label)

        for m in (om, im):
            a, b = m.alias(), m.alias()
            key = "organization_id" if m is om else "institution_id"
            add(conn.execute(select(b.c.user_id).select_from(a.join(b, a.c[key] == b.c[key]))
                             .where(a.c.user_id == uid, active(a), active(b))).all(), "COLLEAGUE")
        # employer side sees applicants; applicant side sees the employer's members
        add(conn.execute(select(cp.c.user_id).select_from(
            om.join(opp, opp.c.organization_id == om.c.organization_id)
              .join(apps, apps.c.opportunity_id == opp.c.id).join(cp, cp.c.id == apps.c.candidate_id))
            .where(om.c.user_id == uid, active(om))).all(), "APPLICANT")
        add(conn.execute(select(om.c.user_id).select_from(
            cp.join(apps, apps.c.candidate_id == cp.c.id).join(opp, opp.c.id == apps.c.opportunity_id)
              .join(om, om.c.organization_id == opp.c.organization_id))
            .where(cp.c.user_id == uid, active(om))).all(), "EMPLOYER")
        # university staff <-> verified students
        add(conn.execute(select(cp.c.user_id).select_from(
            im.join(enr, enr.c.institution_id == im.c.institution_id).join(cp, cp.c.id == enr.c.candidate_id))
            .where(im.c.user_id == uid, active(im), enr.c.status == "VERIFIED")).all(), "STUDENT")
        add(conn.execute(select(im.c.user_id).select_from(
            cp.join(enr, enr.c.candidate_id == cp.c.id).join(im, im.c.institution_id == enr.c.institution_id))
            .where(cp.c.user_id == uid, enr.c.status == "VERIFIED", active(im))).all(), "UNIVERSITY")
        # existing direct-chat partners
        mine, other = mem.alias(), mem.alias()
        add(conn.execute(select(other.c.user_id).select_from(
            mine.join(conv, conv.c.id == mine.c.conversation_id).join(other, other.c.conversation_id == conv.c.id))
            .where(mine.c.user_id == uid, conv.c.kind == "DIRECT", other.c.user_id != uid)).all(), "CHAT")
        return found

    def _blocked_ids(self, conn, uid: str) -> set[str]:
        b = table("chat_blocks")
        rows = conn.execute(select(b.c.blocker_id, b.c.blocked_id).where(or_(b.c.blocker_id == uid, b.c.blocked_id == uid))).all()
        return {str(y) if str(x) == uid else str(x) for x, y in rows}

    def _active_users(self, conn, ids) -> dict[str, str]:
        if not ids:
            return {}
        u = table("users")
        rows = conn.execute(select(u.c.id, u.c.display_name).where(u.c.id.in_(list(ids)), u.c.status == "ACTIVE")).all()
        return {str(i): n for i, n in rows}

    def _reachable(self, conn, uid: str) -> dict[str, tuple[str, str]]:
        """user_id -> (display_name, relation) for everyone the caller may chat with."""
        rel = self._relations(conn, uid)
        blocked = self._blocked_ids(conn, uid)
        names = self._active_users(conn, [i for i in rel if i not in blocked])
        return {i: (names[i], rel[i]) for i in names}

    # ------------------------------------------------------------------ membership helpers
    def _member(self, conn, conversation_id: str, uid: str, *, lock: bool = False) -> dict[str, Any]:
        mem, conv = table("chat_members"), table("chat_conversations")
        q = select(mem, conv.c.kind, conv.c.title).select_from(mem.join(conv, conv.c.id == mem.c.conversation_id)).where(
            mem.c.conversation_id == conversation_id, mem.c.user_id == uid, mem.c.left_at.is_(None))
        row = conn.execute(q.with_for_update(of=mem) if lock else q).mappings().first()
        if not row:
            raise _err("CHAT_NOT_FOUND", 404)
        return dict(row)

    def _owner(self, conn, conversation_id: str, uid: str) -> dict[str, Any]:
        m = self._member(conn, conversation_id, uid, lock=True)
        if m["kind"] != "GROUP":
            raise _err("CHAT_GROUP_REQUIRED", 422)
        if m["role"] != "OWNER":
            raise _err("CHAT_OWNER_REQUIRED", 403)
        return m

    def _active_members(self, conn, conversation_id: str) -> list[dict[str, Any]]:
        mem, u = table("chat_members"), table("users")
        return [dict(r) for r in conn.execute(
            select(mem.c.user_id, mem.c.role, mem.c.joined_at, u.c.display_name)
            .select_from(mem.join(u, u.c.id == mem.c.user_id))
            .where(mem.c.conversation_id == conversation_id, mem.c.left_at.is_(None))
            .order_by(mem.c.joined_at, mem.c.id)).mappings().all()]

    def _join(self, conn, conversation_id: str, uid: str, role: str = "MEMBER") -> None:
        mem = table("chat_members")
        existing = conn.execute(select(mem).where(mem.c.conversation_id == conversation_id, mem.c.user_id == uid)).mappings().first()
        if existing:
            if existing["left_at"] is not None:
                conn.execute(mem.update().where(mem.c.id == existing["id"]).values(left_at=None, joined_at=now(), role=role, updated_at=now()))
            return
        insert_row(conn, "chat_members", conversation_id=conversation_id, user_id=uid, role=role, joined_at=now())

    # ------------------------------------------------------------------ contact code / contacts
    def my_code(self, actor: ActorContext, *, rotate: bool = False) -> dict[str, Any]:
        codes = table("chat_contact_codes")
        with transaction() as conn:
            account_authority(conn, actor)
            row = conn.execute(select(codes).where(codes.c.user_id == actor.user_id).with_for_update()).mappings().first()
            if row and not rotate:
                return {"contact_code": row["code"]}
            for _ in range(5):
                code = _new_code()
                if conn.execute(select(codes.c.id).where(codes.c.code == code)).first():
                    continue
                if row:
                    conn.execute(codes.update().where(codes.c.id == row["id"]).values(code=code, updated_at=now()))
                else:
                    insert_row(conn, "chat_contact_codes", user_id=actor.user_id, code=code)
                return {"contact_code": code}
        raise _err("CHAT_CODE_UNAVAILABLE", 503)

    def contacts(self, actor: ActorContext, q: str | None = None) -> dict[str, Any]:
        with transaction() as conn:
            account_authority(conn, actor)
            reach = self._reachable(conn, actor.user_id)
        needle = (q or "").strip().lower()
        items = [{"user_id": i, "display_name": n, "relation": r} for i, (n, r) in reach.items() if not needle or needle in n.lower()]
        items.sort(key=lambda x: x["display_name"].lower())
        return {"items": items[:200]}

    # ------------------------------------------------------------------ conversations
    def _summaries(self, conn, uid: str, conversation_ids: list[str]) -> list[dict[str, Any]]:
        conv, mem, msg, u = table("chat_conversations"), table("chat_members"), table("chat_messages"), table("users")
        if not conversation_ids:
            return []
        out = []
        rows = conn.execute(select(conv).where(conv.c.id.in_(conversation_ids))).mappings().all()
        for c in rows:
            cid = str(c["id"])
            members = self._active_members(conn, cid)
            me = next((m for m in members if str(m["user_id"]) == uid), None)
            mine_row = conn.execute(select(mem.c.last_read_at, mem.c.role).where(mem.c.conversation_id == cid, mem.c.user_id == uid)).mappings().first()
            last = conn.execute(select(msg.c.body, msg.c.sender_id, msg.c.created_at, msg.c.deleted_at, u.c.display_name)
                                .select_from(msg.join(u, u.c.id == msg.c.sender_id)).where(msg.c.conversation_id == cid)
                                .order_by(msg.c.created_at.desc(), msg.c.id.desc()).limit(1)).mappings().first()
            unread_q = select(func.count()).select_from(msg).where(msg.c.conversation_id == cid, msg.c.sender_id != uid, msg.c.deleted_at.is_(None))
            if mine_row and mine_row["last_read_at"]:
                unread_q = unread_q.where(msg.c.created_at > mine_row["last_read_at"])
            others = [m for m in members if str(m["user_id"]) != uid]
            if c["kind"] == "DIRECT":
                partner_id = next((p for p in str(c["direct_key"]).split(":") if p != uid), None)
                partner = next((m for m in others if str(m["user_id"]) == partner_id), None)
                title = partner["display_name"] if partner else "Suhbatdosh"
            else:
                partner_id, title = None, c["title"]
            out.append({
                "id": cid,
                "kind": c["kind"],
                "title": title,
                "partner_id": partner_id,
                "member_count": len(members),
                "my_role": (me or mine_row or {}).get("role"),
                "unread_count": int(conn.execute(unread_q).scalar_one()),
                "last_message": None if not last else {
                    "body": None if last["deleted_at"] else last["body"][:160],
                    "deleted": last["deleted_at"] is not None,
                    "sender_id": str(last["sender_id"]),
                    "sender_name": last["display_name"],
                    "mine": str(last["sender_id"]) == uid,
                    "created_at": last["created_at"].isoformat(),
                },
                "updated_at": (c["last_message_at"] or c["created_at"]).isoformat(),
            })
        out.sort(key=lambda x: x["updated_at"], reverse=True)
        return out

    def list_conversations(self, actor: ActorContext) -> dict[str, Any]:
        mem = table("chat_members")
        with transaction() as conn:
            account_authority(conn, actor)
            ids = [str(r) for (r,) in conn.execute(select(mem.c.conversation_id).where(mem.c.user_id == actor.user_id, mem.c.left_at.is_(None))).all()]
            items = self._summaries(conn, actor.user_id, ids)
        return {"items": items, "unread_total": sum(i["unread_count"] for i in items)}

    def get_conversation(self, actor: ActorContext, conversation_id: str) -> dict[str, Any]:
        conv = table("chat_conversations")
        with transaction() as conn:
            account_authority(conn, actor)
            me = self._member(conn, conversation_id, actor.user_id)
            summary = self._summaries(conn, actor.user_id, [conversation_id])[0]
            members = self._active_members(conn, conversation_id)
            has_link = conn.execute(select(conv.c.invite_token_hash).where(conv.c.id == conversation_id)).scalar_one() is not None
            blocked = self._blocked_ids(conn, actor.user_id)
        return {
            **summary,
            "members": [{"user_id": str(m["user_id"]), "display_name": m["display_name"], "role": m["role"]} for m in members],
            "invite_link_active": has_link if me["role"] == "OWNER" else None,
            "blocked": bool(summary["partner_id"] and summary["partner_id"] in blocked),
        }

    def start_direct(self, actor: ActorContext, *, user_id: str | None, contact_code: str | None) -> dict[str, Any]:
        conv, codes, u = table("chat_conversations"), table("chat_contact_codes"), table("users")
        uid = actor.user_id
        with transaction() as conn:
            account_authority(conn, actor)
            if contact_code:
                target = conn.execute(select(codes.c.user_id).where(codes.c.code == contact_code.strip().upper())).scalar_one_or_none()
                if not target:
                    raise _err("CHAT_CODE_NOT_FOUND", 404)
                target = str(target)
            elif user_id:
                target = str(user_id)
                if target not in self._relations(conn, uid):
                    raise _err("CHAT_NOT_A_CONTACT", 403)
            else:
                raise _err("INVALID_INPUT", 422)
            if target == uid:
                raise _err("CHAT_SELF_NOT_ALLOWED", 422)
            if conn.execute(select(u.c.status).where(u.c.id == target)).scalar_one_or_none() != "ACTIVE":
                raise _err("CHAT_CODE_NOT_FOUND", 404)
            if target in self._blocked_ids(conn, uid):
                raise _err("CHAT_BLOCKED", 403)
            key = ":".join(sorted((uid, target)))
            conn.execute(pg_insert(conv).values(id=str(uuid4()),
                                                created_at=now(), updated_at=now(), kind="DIRECT", direct_key=key, created_by=uid)
                         .on_conflict_do_nothing(index_elements=[conv.c.direct_key]))
            cid = str(conn.execute(select(conv.c.id).where(conv.c.direct_key == key)).scalar_one())
            self._join(conn, cid, uid)
            self._join(conn, cid, target)
        return self.get_conversation(actor, cid)

    def create_group(self, actor: ActorContext, *, title: str, member_ids: list[str]) -> dict[str, Any]:
        clean = (title or "").strip()
        if not 1 <= len(clean) <= 80:
            raise _err("INVALID_CHAT_TITLE", 422)
        wanted = list(dict.fromkeys(str(m) for m in member_ids if str(m) != actor.user_id))
        if len(wanted) + 1 > MAX_GROUP:
            raise _err("CHAT_GROUP_TOO_LARGE", 422)
        with transaction() as conn:
            account_authority(conn, actor)
            reach = self._reachable(conn, actor.user_id)
            if any(m not in reach for m in wanted):
                raise _err("CHAT_NOT_A_CONTACT", 403)
            c = insert_row(conn, "chat_conversations", kind="GROUP", title=clean, created_by=actor.user_id)
            self._join(conn, c["id"], actor.user_id, "OWNER")
            for m in wanted:
                self._join(conn, c["id"], m)
        return self.get_conversation(actor, c["id"])

    def rename_group(self, actor: ActorContext, conversation_id: str, title: str) -> dict[str, Any]:
        clean = (title or "").strip()
        if not 1 <= len(clean) <= 80:
            raise _err("INVALID_CHAT_TITLE", 422)
        conv = table("chat_conversations")
        with transaction() as conn:
            account_authority(conn, actor)
            self._owner(conn, conversation_id, actor.user_id)
            conn.execute(conv.update().where(conv.c.id == conversation_id).values(title=clean, updated_at=now()))
        return self.get_conversation(actor, conversation_id)

    def add_members(self, actor: ActorContext, conversation_id: str, member_ids: list[str]) -> dict[str, Any]:
        with transaction() as conn:
            account_authority(conn, actor)
            self._owner(conn, conversation_id, actor.user_id)
            reach = self._reachable(conn, actor.user_id)
            wanted = list(dict.fromkeys(str(m) for m in member_ids if str(m) != actor.user_id))
            if any(m not in reach for m in wanted):
                raise _err("CHAT_NOT_A_CONTACT", 403)
            if len(self._active_members(conn, conversation_id)) + len(wanted) > MAX_GROUP:
                raise _err("CHAT_GROUP_TOO_LARGE", 422)
            for m in wanted:
                self._join(conn, conversation_id, m)
        return self.get_conversation(actor, conversation_id)

    def remove_member(self, actor: ActorContext, conversation_id: str, user_id: str) -> dict[str, Any]:
        mem = table("chat_members")
        with transaction() as conn:
            account_authority(conn, actor)
            me = self._member(conn, conversation_id, actor.user_id, lock=True)
            if me["kind"] != "GROUP":
                raise _err("CHAT_GROUP_REQUIRED", 422)
            target = str(user_id)
            if target != actor.user_id and me["role"] != "OWNER":
                raise _err("CHAT_OWNER_REQUIRED", 403)
            row = conn.execute(select(mem).where(mem.c.conversation_id == conversation_id, mem.c.user_id == target,
                                                 mem.c.left_at.is_(None)).with_for_update()).mappings().first()
            if not row:
                raise _err("CHAT_MEMBER_NOT_FOUND", 404)
            conn.execute(mem.update().where(mem.c.id == row["id"]).values(left_at=now(), role="MEMBER", updated_at=now()))
            if row["role"] == "OWNER":
                # The owner left: the longest-standing remaining member takes over.
                heir = conn.execute(select(mem.c.id).where(mem.c.conversation_id == conversation_id, mem.c.left_at.is_(None))
                                    .order_by(mem.c.joined_at, mem.c.id).limit(1)).scalar_one_or_none()
                if heir:
                    conn.execute(mem.update().where(mem.c.id == heir).values(role="OWNER", updated_at=now()))
                conn.execute(table("chat_conversations").update().where(table("chat_conversations").c.id == conversation_id)
                             .values(invite_token_hash=None, updated_at=now()))
        return {"ok": True, "left": target == actor.user_id}

    def invite_link(self, actor: ActorContext, conversation_id: str, *, enable: bool) -> dict[str, Any]:
        conv = table("chat_conversations")
        with transaction() as conn:
            account_authority(conn, actor)
            self._owner(conn, conversation_id, actor.user_id)
            token = secrets.token_urlsafe(24) if enable else None
            conn.execute(conv.update().where(conv.c.id == conversation_id)
                         .values(invite_token_hash=_digest(token) if token else None, updated_at=now()))
        return {"invite_token": token}

    def join_by_link(self, actor: ActorContext, token: str) -> dict[str, Any]:
        conv = table("chat_conversations")
        with transaction() as conn:
            account_authority(conn, actor)
            row = conn.execute(select(conv.c.id).where(conv.c.invite_token_hash == _digest((token or "").strip()),
                                                       conv.c.kind == "GROUP").with_for_update()).scalar_one_or_none()
            if not row:
                raise _err("CHAT_INVITE_INVALID", 404)
            cid = str(row)
            if len(self._active_members(conn, cid)) >= MAX_GROUP:
                raise _err("CHAT_GROUP_TOO_LARGE", 422)
            self._join(conn, cid, actor.user_id)
        return self.get_conversation(actor, cid)

    # ------------------------------------------------------------------ messages
    def list_messages(self, actor: ActorContext, conversation_id: str, *, before: str | None = None, limit: int = PAGE) -> dict[str, Any]:
        msg, u = table("chat_messages"), table("users")
        limit = max(1, min(int(limit or PAGE), 100))
        with transaction() as conn:
            account_authority(conn, actor)
            self._member(conn, conversation_id, actor.user_id)
            q = (select(msg.c.id, msg.c.sender_id, msg.c.body, msg.c.created_at, msg.c.deleted_at, u.c.display_name)
                 .select_from(msg.join(u, u.c.id == msg.c.sender_id)).where(msg.c.conversation_id == conversation_id))
            if before:
                pivot = conn.execute(select(msg.c.created_at, msg.c.id).where(msg.c.id == before, msg.c.conversation_id == conversation_id)).first()
                if not pivot:
                    raise _err("CHAT_MESSAGE_NOT_FOUND", 404)
                q = q.where(or_(msg.c.created_at < pivot[0], and_(msg.c.created_at == pivot[0], msg.c.id < pivot[1])))
            rows = conn.execute(q.order_by(msg.c.created_at.desc(), msg.c.id.desc()).limit(limit + 1)).mappings().all()
        has_more = len(rows) > limit
        items = [{
            "id": str(r["id"]),
            "sender_id": str(r["sender_id"]),
            "sender_name": r["display_name"],
            "body": None if r["deleted_at"] else r["body"],
            "deleted": r["deleted_at"] is not None,
            "mine": str(r["sender_id"]) == actor.user_id,
            "created_at": r["created_at"].isoformat(),
        } for r in rows[:limit]]
        items.reverse()
        return {"items": items, "has_more": has_more}

    def send(self, actor: ActorContext, conversation_id: str, body: str) -> dict[str, Any]:
        text = (body or "").strip()
        if not 1 <= len(text) <= MAX_BODY:
            raise _err("INVALID_CHAT_MESSAGE", 422)
        from app.core.iam_security import rate_limit

        rate_limit("chat-send", actor.user_id, 30, 60)
        conv, mem = table("chat_conversations"), table("chat_members")
        with transaction() as conn:
            account_authority(conn, actor)
            me = self._member(conn, conversation_id, actor.user_id)
            if me["kind"] == "DIRECT":
                others = [str(m["user_id"]) for m in self._active_members(conn, conversation_id) if str(m["user_id"]) != actor.user_id]
                if any(o in self._blocked_ids(conn, actor.user_id) for o in others):
                    raise _err("CHAT_BLOCKED", 403)
            stamp = now()
            m = insert_row(conn, "chat_messages", conversation_id=conversation_id, sender_id=actor.user_id, body=text)
            conn.execute(conv.update().where(conv.c.id == conversation_id).values(last_message_at=m["created_at"], updated_at=stamp))
            conn.execute(mem.update().where(mem.c.conversation_id == conversation_id, mem.c.user_id == actor.user_id)
                         .values(last_read_at=m["created_at"], updated_at=stamp))
        return {"id": m["id"], "body": text, "created_at": m["created_at"].isoformat(), "mine": True, "sender_id": actor.user_id, "deleted": False}

    def mark_read(self, actor: ActorContext, conversation_id: str) -> dict[str, Any]:
        mem = table("chat_members")
        with transaction() as conn:
            account_authority(conn, actor)
            self._member(conn, conversation_id, actor.user_id)
            conn.execute(mem.update().where(mem.c.conversation_id == conversation_id, mem.c.user_id == actor.user_id)
                         .values(last_read_at=now(), updated_at=now()))
        return {"ok": True}

    def delete_message(self, actor: ActorContext, message_id: str) -> dict[str, Any]:
        msg = table("chat_messages")
        with transaction() as conn:
            account_authority(conn, actor)
            row = conn.execute(select(msg).where(msg.c.id == message_id).with_for_update()).mappings().first()
            if not row:
                raise _err("CHAT_MESSAGE_NOT_FOUND", 404)
            self._member(conn, str(row["conversation_id"]), actor.user_id)
            if str(row["sender_id"]) != actor.user_id:
                raise _err("CHAT_MESSAGE_NOT_YOURS", 403)
            # The text is erased, not just hidden.
            conn.execute(msg.update().where(msg.c.id == message_id).values(body="·", deleted_at=now(), updated_at=now()))
        return {"ok": True}

    # ------------------------------------------------------------------ blocks
    def block(self, actor: ActorContext, user_id: str, *, blocked: bool) -> dict[str, Any]:
        b = table("chat_blocks")
        target = str(user_id)
        if target == actor.user_id:
            raise _err("CHAT_SELF_NOT_ALLOWED", 422)
        with transaction() as conn:
            account_authority(conn, actor)
            if blocked:
                if not conn.execute(select(b.c.id).where(b.c.blocker_id == actor.user_id, b.c.blocked_id == target)).first():
                    if not self._active_users(conn, [target]):
                        raise _err("CHAT_USER_NOT_FOUND", 404)
                    insert_row(conn, "chat_blocks", blocker_id=actor.user_id, blocked_id=target)
            else:
                conn.execute(b.delete().where(b.c.blocker_id == actor.user_id, b.c.blocked_id == target))
        return {"ok": True, "blocked": blocked}


chat_service = ChatService()
