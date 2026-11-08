from alembic import context
from app.db.storage import get_database_url, get_engine, metadata

def run_migrations_offline():
    raise RuntimeError('This baseline requires an online PostgreSQL connection; offline generation is unsupported')

def run_migrations_online():
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, include_schemas=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
