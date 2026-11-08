"""Review probes in a disposable PostgreSQL database, using existing test fixtures.

Set FLEXBRIDGE_TEST_ADMIN_URL to an isolated server before running this script.
No live gateway/storage or existing application database is used.
"""
import importlib.util
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
spec = importlib.util.spec_from_file_location('review_fixtures', ROOT / 'backend/tests/conftest.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def canonical_inventory():
    from app.main import app
    model = json.loads((ROOT / 'specs/v1_4/FlexBridge_model_1_4.json').read_text(encoding='utf-8'))
    normalize = lambda value: re.sub(r'\{[^}]+\}', '{}', value)
    routes = {(method.upper(), normalize(path)): operation
              for path, operations in app.openapi()['paths'].items()
              for method, operation in operations.items() if method.upper() in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')}
    contracts = model['apis'] + model.get('helper_apis', [])
    placeholder_ids, missing = [], []
    for contract in contracts:
        operation = routes.get((contract['method'].upper(), normalize(contract['path'])))
        if operation is None:
            missing.append(contract['id'])
        elif operation.get('operationId', '').startswith('canonical_api_'):
            placeholder_ids.append(contract['id'])
    return {'total': len(contracts), 'placeholders_501': len(placeholder_ids),
            'explicit_handlers': len(contracts) - len(placeholder_ids) - len(missing),
            'missing': missing, 'placeholder_ids': placeholder_ids}


def main():
    database = fixtures.database.__wrapped__()
    next(database)
    try:
        from sqlalchemy import event, select
        from app.db.storage import get_engine, table, transaction
        from app.services.availability import availability_service
        from app.services.opportunities import opportunity_service
        from app.main import app

        identities = fixtures.identities.__wrapped__()
        candidate = identities()
        organization = fixtures.organization.__wrapped__()
        owner = identities('OWNER', organization)
        revision = opportunity_service.create_opportunity_revision(
            organization_id=organization, title='Stipend review fixture',
            opportunity_kind='GENERAL_INTERNSHIP', contract_type='INTERNSHIP_AGREEMENT',
            compensation_type='STIPEND', stipend_amount=500000, actor_user_id=owner['user_id'])
        today = date.today()
        rule = availability_service.add_availability_rule(
            candidate_id=candidate['candidate_id'], weekday=today.isoweekday(),
            start_minute=540, end_minute=720)
        opportunity_service.add_opportunity_shift(
            revision_id=revision['id'], group_code='A', weekday=today.isoweekday(),
            start_minute=540, end_minute=600, actor_user_id=owner['user_id'])
        with transaction() as conn:
            # Publish directly as a test fixture, avoiding unrelated payment/moderation setup.
            conn.execute(table('opportunities').update().where(
                table('opportunities').c.id == revision['opportunity_id']).values(status='PUBLISHED'))

        queries = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)
        event.listen(get_engine(), 'before_cursor_execute', capture)
        try:
            feed = opportunity_service.match_candidate_feed_api_003(
                candidate_id=candidate['candidate_id'], check_date=today.isoformat())
        finally:
            event.remove(get_engine(), 'before_cursor_execute', capture)
        assert len(feed) == 1
        results = {
            'stipend_classification': {
                'input': 'STIPEND', 'stored_salary_period': revision['salary_period'],
                'feed_value': feed[0]['compensation_type'],
                'defect_observed': feed[0]['compensation_type'] != 'STIPEND'},
            'matching_queries_one_opportunity_one_shift': {
                'count': len(queries),
                'unfiltered_select_count': sum('SELECT' in q.upper() and 'WHERE' not in q.upper() for q in queries)}
        }

        for case, start, end in [
            ('expired_rule', today - timedelta(days=14), today - timedelta(days=1)),
            ('future_rule', today + timedelta(days=1), today + timedelta(days=14))
        ]:
            with transaction() as conn:
                conn.execute(table('availability_rules').update().where(
                    table('availability_rules').c.id == rule['id']).values(valid_from=start, valid_to=end))
            matched = availability_service.is_candidate_available_for_shift(
                candidate_id=candidate['candidate_id'], weekday=today.isoweekday(),
                start_minute=540, end_minute=600, check_date=today.isoformat())
            results[case] = {'check_date': today.isoformat(), 'valid_from': start.isoformat(),
                'valid_to': end.isoformat(), 'actual_available': matched, 'expected_available': False,
                'defect_observed': matched is True}

        results['canonical_inventory'] = canonical_inventory()
        results['scope'] = 'Real disposable PostgreSQL; direct services, test fixture publication; no live external services or UI'
        output = Path(__file__).with_name('probe_results.json')
        output.write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(json.dumps(results, indent=2))
    finally:
        database.close()


if __name__ == '__main__':
    main()
