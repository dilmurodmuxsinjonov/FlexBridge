"""SQLAlchemy table shapes for the chat tables created by migration 0023_chat_messaging."""
from sqlalchemy import Column, Table

FIELDS = {
    'chat_conversations': {
        'id': 'uuid', 'created_at': 'timestamptz', 'updated_at': 'timestamptz', 'kind': 'text', 'title': 'text',
        'direct_key': 'text', 'created_by': 'uuid', 'invite_token_hash': 'text', 'last_message_at': 'timestamptz',
    },
    'chat_members': {
        'id': 'uuid', 'created_at': 'timestamptz', 'updated_at': 'timestamptz', 'conversation_id': 'uuid',
        'user_id': 'uuid', 'role': 'text', 'joined_at': 'timestamptz', 'left_at': 'timestamptz',
        'last_read_at': 'timestamptz',
    },
    'chat_messages': {
        'id': 'uuid', 'created_at': 'timestamptz', 'updated_at': 'timestamptz', 'conversation_id': 'uuid',
        'sender_id': 'uuid', 'body': 'text', 'deleted_at': 'timestamptz',
    },
    'chat_contact_codes': {
        'id': 'uuid', 'created_at': 'timestamptz', 'updated_at': 'timestamptz', 'user_id': 'uuid', 'code': 'text',
    },
    'chat_blocks': {
        'id': 'uuid', 'created_at': 'timestamptz', 'updated_at': 'timestamptz', 'blocker_id': 'uuid',
        'blocked_id': 'uuid',
    },
}
NULLABLE = {'title', 'direct_key', 'invite_token_hash', 'last_message_at', 'left_at', 'last_read_at', 'deleted_at'}


def register_tables(metadata, types):
    for name, fields in FIELDS.items():
        if 'flexbridge.' + name not in metadata.tables:
            Table(name, metadata, *[Column(f, types[k], primary_key=f == 'id', nullable=f in NULLABLE)
                                    for f, k in fields.items()], schema='flexbridge')
