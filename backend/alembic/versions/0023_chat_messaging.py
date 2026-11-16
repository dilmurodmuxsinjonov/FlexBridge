"""User-to-user chat: direct conversations, groups with invite links, contact codes and blocks (Issue #253)."""
from alembic import op

revision = '0023_chat_messaging'
down_revision = '0022_enrollment_inst_review'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.chat_conversations (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      kind text NOT NULL CHECK (kind IN ('DIRECT', 'GROUP')),
      title text CHECK (title IS NULL OR char_length(title) BETWEEN 1 AND 80),
      direct_key text UNIQUE,
      created_by uuid NOT NULL REFERENCES flexbridge.users(id),
      invite_token_hash text UNIQUE,
      last_message_at timestamptz,
      CHECK ((kind = 'DIRECT' AND direct_key IS NOT NULL AND title IS NULL AND invite_token_hash IS NULL)
          OR (kind = 'GROUP' AND direct_key IS NULL AND title IS NOT NULL))
    );

    CREATE TABLE flexbridge.chat_members (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      conversation_id uuid NOT NULL REFERENCES flexbridge.chat_conversations(id) ON DELETE CASCADE,
      user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      role text NOT NULL CHECK (role IN ('OWNER', 'MEMBER')),
      joined_at timestamptz NOT NULL,
      left_at timestamptz,
      last_read_at timestamptz,
      UNIQUE (conversation_id, user_id)
    );
    CREATE INDEX idx_chat_members_user ON flexbridge.chat_members(user_id) WHERE left_at IS NULL;

    CREATE TABLE flexbridge.chat_messages (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      conversation_id uuid NOT NULL REFERENCES flexbridge.chat_conversations(id) ON DELETE CASCADE,
      sender_id uuid NOT NULL REFERENCES flexbridge.users(id),
      body text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 4000),
      deleted_at timestamptz
    );
    CREATE INDEX idx_chat_messages_conversation ON flexbridge.chat_messages(conversation_id, created_at DESC, id DESC);

    CREATE TABLE flexbridge.chat_contact_codes (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      user_id uuid NOT NULL UNIQUE REFERENCES flexbridge.users(id),
      code text NOT NULL UNIQUE CHECK (code ~ '^[A-Z0-9]{8}$')
    );

    CREATE TABLE flexbridge.chat_blocks (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      blocker_id uuid NOT NULL REFERENCES flexbridge.users(id),
      blocked_id uuid NOT NULL REFERENCES flexbridge.users(id),
      UNIQUE (blocker_id, blocked_id),
      CHECK (blocker_id <> blocked_id)
    );
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS flexbridge.chat_blocks CASCADE;
    DROP TABLE IF EXISTS flexbridge.chat_contact_codes CASCADE;
    DROP TABLE IF EXISTS flexbridge.chat_messages CASCADE;
    DROP TABLE IF EXISTS flexbridge.chat_members CASCADE;
    DROP TABLE IF EXISTS flexbridge.chat_conversations CASCADE;
    """)
