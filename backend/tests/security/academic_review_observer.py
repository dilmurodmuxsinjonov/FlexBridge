"""Diagnostic labels only: observe each actual HTTP request's PostgreSQL wait."""
from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic,sleep

from sqlalchemy import event,text

_LABEL=ContextVar('academic_review_observation',default=None)


@contextmanager
def labeled_requests(engine):
    def label_cursor(conn,cursor,statement,parameters,context,executemany):
        value=_LABEL.get()
        if value:
            # Diagnostic metadata only; execute the original statement unchanged.
            cursor.execute("SELECT set_config('application_name',%s,true)",(value,))
    def call(label,operation,*args):
        token=_LABEL.set(label)
        try:return operation(*args)
        finally:_LABEL.reset(token)
    event.listen(engine,'before_cursor_execute',label_cursor)
    try:yield call
    finally:event.remove(engine,'before_cursor_execute',label_cursor)


def wait_for_requests(engine,labels,*,intent_only=False):
    deadline=monotonic()+10;rows=[]
    while monotonic()<deadline:
        with engine.connect() as observer:
            rows=[dict(row) for row in observer.execute(text("""SELECT pid,application_name,wait_event,
                pg_blocking_pids(pid) AS blockers,query LIKE '%pg_advisory_xact_lock%' AS at_intent_lock
                FROM pg_stat_activity WHERE application_name=ANY(:labels) AND wait_event_type='Lock'"""),
                {'labels':list(labels)}).mappings()]
        if {row['application_name'] for row in rows}==set(labels) and all(row['blockers'] for row in rows):
            if not intent_only or all(row['at_intent_lock'] for row in rows):return rows
        sleep(.01)
    raise AssertionError('Actual labeled HTTP database lock waits not observed: '+repr(rows))
