import fs from 'node:fs';
import { randomUUID } from 'node:crypto';
import { PGlite } from 'file:///D:/Codex/2026-10-26/sh/work/review_2026_11_05/runtime/node_modules/@electric-sql/pglite/dist/index.js';
import { btree_gist } from 'file:///D:/Codex/2026-10-26/sh/work/review_2026_11_05/runtime/node_modules/@electric-sql/pglite/dist/contrib/btree_gist.js';

const schemaPath = 'D:/FlexBridge/specs/v1_4/FlexBridge_1_4_schema.sql';
const modelPath = 'D:/FlexBridge/specs/v1_4/FlexBridge_model_1_4.json';
const reportPath = 'D:/FlexBridge/specs/v1_4/v1_4_schema_verification.json';

const db = new PGlite({ extensions: { btree_gist } });
const schemaSql = fs.readFileSync(schemaPath, 'utf8');
const model = JSON.parse(fs.readFileSync(modelPath, 'utf8'));

await db.exec(schemaSql);
await db.exec('SET search_path TO flexbridge, public;');

const pgVersion = (await db.query('SELECT version() AS v')).rows[0].v;
const tableCount = +(await db.query("SELECT count(*) AS n FROM information_schema.tables WHERE table_schema='flexbridge' AND table_type='BASE TABLE'")).rows[0].n;
const columnCount = +(await db.query("SELECT count(*) AS n FROM information_schema.columns WHERE table_schema='flexbridge'")).rows[0].n;
const generatedColumnCount = +(await db.query("SELECT count(*) AS n FROM information_schema.columns WHERE table_schema='flexbridge' AND is_generated='ALWAYS'")).rows[0].n;
const fkConstraintCount = +(await db.query("SELECT count(*) AS n FROM information_schema.table_constraints WHERE table_schema='flexbridge' AND constraint_type='FOREIGN KEY'")).rows[0].n;
const retentionCount = +(await db.query('SELECT count(*) AS n FROM retention_policies')).rows[0].n;

const checks = [];
async function runCheck(name, fn, shouldPass, expectedCode = null) {
  let accepted = false;
  let errorCode = null;
  let errorMessage = null;
  await db.exec('SAVEPOINT sp_check;');
  try {
    await fn();
    accepted = true;
    await db.exec('RELEASE SAVEPOINT sp_check;');
  } catch (err) {
    errorCode = err.code || null;
    errorMessage = err.message || String(err);
    await db.exec('ROLLBACK TO SAVEPOINT sp_check;');
    await db.exec('RELEASE SAVEPOINT sp_check;');
  }
  const passed = (accepted === shouldPass) && (expectedCode === null || errorCode === expectedCode);
  checks.push({ name, shouldPass, accepted, errorCode, expectedCode, passed, errorMessage: accepted ? null : errorMessage });
}

await db.exec('BEGIN;');

const ids = Object.fromEntries(
  ['u1', 'u2', 'u3', 'c1', 'c2', 'org1', 'org2', 'opp1', 'opp2', 'rev1', 'rev2', 'app1', 'app2', 'att1', 'att2', 'pl1', 'terms1', 'log1', 'lrev1', 'ord1', 'pay1'].map(
    (k) => [k, randomUUID()]
  )
);

// Base seed entities
for (const [u, n] of [[ids.u1, 'User 1'], [ids.u2, 'User 2'], [ids.u3, 'User 3']]) {
  await db.query("INSERT INTO users(id,display_name,status,locale,timezone) VALUES ($1,$2,'ACTIVE','uz','Asia/Tashkent')", [u, n]);
}
for (const [c, u] of [[ids.c1, ids.u1], [ids.c2, ids.u2]]) {
  await db.query("INSERT INTO candidate_profiles(id,user_id,headline,region,experience_months,visibility) VALUES ($1,$2,'Candidate','Tashkent',0,'PRIVATE')", [c, u]);
}
for (const [o, tax] of [[ids.org1, '300000001'], [ids.org2, '300000002']]) {
  await db.query("INSERT INTO organizations(id,tax_id,legal_name,public_name,region,status) VALUES ($1,$2,'Org','Org','Tashkent','VERIFIED')", [o, tax]);
}

// 1. INV-14: Deferred circular FK allows inserting parent + child in one transaction
await runCheck('INV-14_deferred_circular_insert_opportunity_and_revision', async () => {
  await db.query(
    "INSERT INTO opportunities(id,organization_id,kind,status,current_revision_id,capacity,occupied_count) VALUES ($1,$2,'PART_TIME','PUBLISHED',$3,2,0)",
    [ids.opp1, ids.org1, ids.rev1]
  );
  await db.query(
    "INSERT INTO opportunity_revisions(id,opportunity_id,revision,author_id,title,description,region,work_mode,eligibility,currency,is_paid,salary_min,salary_max,salary_period,salary_basis,start_date,schedule_policy,shift_match_mode,snapshot_schema,contract_type) VALUES ($1,$2,1,$3,'Barista','Shift work','Tashkent','ONSITE','ALL_CANDIDATES','UZS',true,2000000,3000000,'MONTH','GROSS',CURRENT_DATE,'STRICT','ANY',1,'LABOR_PART_TIME')",
    [ids.rev1, ids.opp1, ids.u1]
  );
}, true);

// 2. AC-039 / INV-07: Reject invalid contract_type and invalid salary combinations
await runCheck('AC-039_reject_invalid_contract_type', async () => {
  await db.query(
    "INSERT INTO opportunity_revisions(id,opportunity_id,revision,author_id,title,description,region,work_mode,eligibility,currency,is_paid,start_date,schedule_policy,shift_match_mode,snapshot_schema,contract_type) VALUES ($1,$2,2,$3,'Invalid','Desc','Tashkent','ONSITE','ALL_CANDIDATES','UZS',false,CURRENT_DATE,'STRICT','ALL',1,'INVALID_TYPE')",
    [randomUUID(), ids.opp1, ids.u1]
  );
}, false, '23514');

await runCheck('INV-07_reject_unpaid_with_salary', async () => {
  await db.query(
    "INSERT INTO opportunity_revisions(id,opportunity_id,revision,author_id,title,description,region,work_mode,eligibility,currency,is_paid,salary_min,start_date,schedule_policy,shift_match_mode,snapshot_schema,contract_type) VALUES ($1,$2,2,$3,'Invalid','Desc','Tashkent','ONSITE','ALL_CANDIDATES','UZS',false,100000,CURRENT_DATE,'STRICT','ALL',1,'INTERNSHIP_AGREEMENT')",
    [randomUUID(), ids.opp1, ids.u1]
  );
}, false, '23514');

await runCheck('INV-07_reject_paid_without_salary_period', async () => {
  await db.query(
    "INSERT INTO opportunity_revisions(id,opportunity_id,revision,author_id,title,description,region,work_mode,eligibility,currency,is_paid,salary_min,start_date,schedule_policy,shift_match_mode,snapshot_schema,contract_type) VALUES ($1,$2,2,$3,'Invalid','Desc','Tashkent','ONSITE','ALL_CANDIDATES','UZS',true,1000000,CURRENT_DATE,'STRICT','ALL',1,'LABOR_PART_TIME')",
    [randomUUID(), ids.opp1, ids.u1]
  );
}, false, '23514');

// 3. AC-039: Availability rules & opportunity shifts int4range + group_code matching
await runCheck('AC-039_shift_groups_and_int4range_matching', async () => {
  await db.query(
    "INSERT INTO availability_rules(id,candidate_id,weekday,start_minute,end_minute,valid_from,timezone) VALUES ($1,$2,1,840,1260,CURRENT_DATE,'Asia/Tashkent')",
    [randomUUID(), ids.c1]
  );
  await db.query(
    "INSERT INTO opportunity_shifts(id,revision_id,weekday,start_minute,end_minute,timezone,group_code) VALUES ($1,$2,1,540,780,'Asia/Tashkent','GROUP_A'), ($3,$2,1,900,1200,'Asia/Tashkent','GROUP_B')",
    [randomUUID(), ids.rev1, randomUUID()]
  );
  const res = await db.query(
    `SELECT s.group_code
       FROM opportunity_shifts s
       JOIN availability_rules a
         ON a.weekday = s.weekday
        AND a.candidate_id = $1
        AND a.minute_range @> int4range(lower(s.minute_range) - 30, upper(s.minute_range) + 30, '[)')
      WHERE s.revision_id = $2`,
    [ids.c1, ids.rev1]
  );
  if (res.rows.length !== 1 || res.rows[0].group_code !== 'GROUP_B') {
    throw new Error('Expected exact GROUP_B match with 30m buffer');
  }
}, true);

// 4. INV-01 & INV-14: Cross-opportunity attempt and foreign current_attempt rejection
await db.query(
  "INSERT INTO opportunities(id,organization_id,kind,status,capacity,occupied_count) VALUES ($1,$2,'PART_TIME','DRAFT',1,0)",
  [ids.opp2, ids.org1]
);
await db.query(
  "INSERT INTO opportunity_revisions(id,opportunity_id,revision,author_id,title,description,region,work_mode,eligibility,currency,is_paid,start_date,schedule_policy,shift_match_mode,snapshot_schema,contract_type) VALUES ($1,$2,1,$3,'Intern','Desc','Tashkent','REMOTE','ALL_CANDIDATES','UZS',false,CURRENT_DATE,'STRICT','ALL',1,'INTERNSHIP_AGREEMENT')",
  [ids.rev2, ids.opp2, ids.u1]
);
await db.query("INSERT INTO applications(id,candidate_id,opportunity_id,status,version) VALUES ($1,$2,$3,'SUBMITTED',1)", [ids.app1, ids.c1, ids.opp1]);
await db.query("INSERT INTO applications(id,candidate_id,opportunity_id,status,version) VALUES ($1,$2,$3,'SUBMITTED',1)", [ids.app2, ids.c2, ids.opp1]);
await db.query(
  "INSERT INTO application_attempts(id,application_id,opportunity_id,attempt_no,revision_id,profile_snapshot,schedule_result,matching_version,submitted_at,idempotency_key) VALUES ($1,$2,$3,1,$4,'{}','MATCH','1.4',now(),'idem-att-1')",
  [ids.att1, ids.app1, ids.opp1, ids.rev1]
);

await runCheck('INV-01_reject_attempt_with_mismatched_opportunity_revision', async () => {
  await db.query(
    "INSERT INTO application_attempts(id,application_id,opportunity_id,attempt_no,revision_id,profile_snapshot,schedule_result,matching_version,submitted_at,idempotency_key) VALUES ($1,$2,$3,1,$4,'{}','MATCH','1.4',now(),'idem-att-bad')",
    [randomUUID(), ids.app2, ids.opp1, ids.rev2]
  );
}, false, '23503');

await runCheck('INV-14_reject_foreign_current_attempt_on_application', async () => {
  await db.query('SAVEPOINT sp_defer;');
  await db.query('UPDATE applications SET current_attempt_id = $1 WHERE id = $2', [ids.att1, ids.app2]);
  await db.query('SET CONSTRAINTS fk_applications_current_attempt IMMEDIATE;');
}, false, '23503');

// 5. AC-040 & AC-017 & INV-09: Diary 0-minute draft, GiST EXCLUDE overlap, and SUBMIT trigger
const mem1 = randomUUID();
const offer1 = randomUUID();
await db.query(
  "INSERT INTO org_memberships(id,organization_id,user_id,status,accepted_at) VALUES ($1,$2,$3,'ACTIVE',now())",
  [mem1, ids.org1, ids.u1]
);
await db.query(
  "INSERT INTO offers(id,application_id,attempt_id,revision_id,issuer_membership_id,status,terms_snapshot,expires_at,accepted_at,idempotency_key) VALUES ($1,$2,$3,$4,$5,'ACCEPTED','{}',now() + interval '7 days',now(),'idem-offer-1')",
  [offer1, ids.app1, ids.att1, ids.rev1, mem1]
);
await db.query(
  "INSERT INTO placements(id,application_id,offer_id,candidate_id,organization_id,academic_track,status,start_date,end_date,version) VALUES ($1,$2,$3,$4,$5,false,'ACTIVE',CURRENT_DATE - 5,CURRENT_DATE + 25,1)",
  [ids.pl1, ids.app1, offer1, ids.c1, ids.org1]
);
await db.query(
  "INSERT INTO placement_terms(id,placement_id,version,schema_version,terms_snapshot,daily_limit_minutes,weekly_limit_minutes,required_minutes) VALUES ($1,$2,1,1,'{}',480,2400,7200)",
  [ids.terms1, ids.pl1]
);
await db.query("INSERT INTO daily_logs(id,placement_id,local_date,version) VALUES ($1,$2,CURRENT_DATE,1)", [ids.log1, ids.pl1]);
await db.query(
  "INSERT INTO log_revisions(id,daily_log_id,revision,terms_id,author_id,day_type,summary,total_minutes,status,idempotency_key) VALUES ($1,$2,1,$3,$4,'WORKED','Draft log',0,'DRAFT','idem-log-1')",
  [ids.lrev1, ids.log1, ids.terms1, ids.u1]
);

const zeroTaskId = randomUUID();
await runCheck('AC-040_allow_zero_minute_draft_task_entry', async () => {
  await db.query(
    "INSERT INTO log_task_entries(id,revision_id,result_text,minutes,start_minute,end_minute) VALUES ($1,$2,'Planned task',0,NULL,NULL)",
    [zeroTaskId, ids.lrev1]
  );
}, true);

await runCheck('AC-040_reject_submit_worked_day_with_zero_total_minutes', async () => {
  await db.query("UPDATE log_revisions SET status = 'SUBMITTED', submitted_at = now() WHERE id = $1", [ids.lrev1]);
}, false, '23514');

await runCheck('AC-017_AC-040_reject_overlapping_task_time_ranges_via_gist_exclude', async () => {
  await db.query(
    "INSERT INTO log_task_entries(id,revision_id,result_text,minutes,start_minute,end_minute) VALUES ($1,$2,'Morning task',120,540,660)",
    [randomUUID(), ids.lrev1]
  );
  await db.query(
    "INSERT INTO log_task_entries(id,revision_id,result_text,minutes,start_minute,end_minute) VALUES ($1,$2,'Overlapping task',90,630,720)",
    [randomUUID(), ids.lrev1]
  );
}, false, '23P01');

await runCheck('INV-09_accept_valid_submitted_worked_day_and_auto_sum_minutes', async () => {
  await db.query('DELETE FROM log_task_entries WHERE id = $1', [zeroTaskId]);
  await db.query(
    "INSERT INTO log_task_entries(id,revision_id,result_text,minutes,start_minute,end_minute) VALUES ($1,$2,'Task 1',120,540,660), ($3,$2,'Task 2',60,720,780)",
    [randomUUID(), ids.lrev1, randomUUID()]
  );
  await db.query("UPDATE log_revisions SET status = 'SUBMITTED', submitted_at = now() WHERE id = $1", [ids.lrev1]);
  const r = await db.query('SELECT total_minutes FROM log_revisions WHERE id = $1', [ids.lrev1]);
  if (+r.rows[0].total_minutes !== 180) {
    throw new Error(`Expected auto-summed total_minutes = 180, got ${r.rows[0].total_minutes}`);
  }
}, true);

// 6. AC-041 & INV-12: Dual-Control self-approval checks & refund limit trigger
await runCheck('AC-041_reject_self_review_on_verification_cases', async () => {
  await db.query(
    "INSERT INTO verification_cases(id,requester_id,organization_id,kind,status,current_revision,assigned_reviewer_id,due_at) VALUES ($1,$2,$3,'ORG_VERIFY','IN_REVIEW',1,$2,now() + interval '2 days')",
    [randomUUID(), ids.u1, ids.org1]
  );
}, false, '23514');

const prodId = randomUUID();
const priceId = randomUUID();
await db.query("INSERT INTO products(id,code,name,service_kind,active) VALUES ($1,'ORG_PLAN_30D','Korxona tarifi','ORG_PLAN',true)", [prodId]);
await db.query("INSERT INTO price_versions(id,product_id,version,amount,currency,duration_days,tax_included,valid_from) VALUES ($1,$2,1,599000,'UZS',30,true,now())", [priceId, prodId]);
await db.query("INSERT INTO orders(id,organization_id,purchaser_id,price_id,status,amount,currency,price_snapshot,idempotency_key) VALUES ($1,$2,$3,$4,'PAID',599000,'UZS','{}','idem-ord-1')", [ids.ord1, ids.org1, ids.u1, priceId]);
await db.query("INSERT INTO payment_attempts(id,order_id,provider,provider_transaction_id,status,amount,currency,requested_at,confirmed_at) VALUES ($1,$2,'CLICK','prov-1','CAPTURED',599000,'UZS',now(),now())", [ids.pay1, ids.ord1]);

await runCheck('AC-041_reject_refund_with_duplicate_approvers', async () => {
  await db.query(
    "INSERT INTO refunds(id,payment_attempt_id,requester_id,approver_id,second_approver_id,amount,currency,reason,status) VALUES ($1,$2,$3,$4,$4,100000,'UZS','Duplicate approver','APPROVED')",
    [randomUUID(), ids.pay1, ids.u1, ids.u2]
  );
}, false, '23514');

await runCheck('INV-12_reject_refund_exceeding_captured_amount', async () => {
  await db.query(
    "INSERT INTO refunds(id,payment_attempt_id,requester_id,approver_id,second_approver_id,amount,currency,reason,status) VALUES ($1,$2,$3,$4,$5,600000,'UZS','Too much','APPROVED')",
    [randomUUID(), ids.pay1, ids.u1, ids.u2, ids.u3]
  );
}, false, '23514');

await runCheck('INV-12_accept_valid_dual_control_refund', async () => {
  await db.query(
    "INSERT INTO refunds(id,payment_attempt_id,requester_id,approver_id,second_approver_id,amount,currency,reason,status) VALUES ($1,$2,$3,$4,$5,200000,'UZS','Partial refund','APPROVED')",
    [randomUUID(), ids.pay1, ids.u1, ids.u2, ids.u3]
  );
}, true);

// 7. INV-16: Immutability triggers on audit_events and published opportunity_revisions
const auditId = randomUUID();
await db.query(
  "INSERT INTO audit_events(id,actor_id,action,object_type,object_key,scope_snapshot,request_id,occurred_at) VALUES ($1,$2,'TEST_ACTION','opportunity',$3,'{}','req-1',now())",
  [auditId, ids.u1, ids.opp1]
);

await runCheck('INV-16_reject_update_on_audit_events', async () => {
  await db.query("UPDATE audit_events SET action = 'TAMPERED' WHERE id = $1", [auditId]);
}, false, '23514');

await runCheck('INV-16_reject_delete_on_audit_events', async () => {
  await db.query('DELETE FROM audit_events WHERE id = $1', [auditId]);
}, false, '23514');

await db.exec('COMMIT;');

const report = {
  verified_at: new Date().toISOString(),
  engine: pgVersion,
  model_stats: model.stats,
  database_introspection: {
    base_tables: tableCount,
    total_columns_including_generated: columnCount,
    generated_stored_columns: generatedColumnCount,
    non_generated_columns: columnCount - generatedColumnCount,
    foreign_key_constraints: fkConstraintCount,
    retention_policy_v1_rows: retentionCount,
  },
  all_checks_passed: checks.every((c) => c.passed),
  total_checks: checks.length,
  passed_checks: checks.filter((c) => c.passed).length,
  checks,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
console.log(JSON.stringify(report, null, 2));
await db.close();
if (!report.all_checks_passed) {
  process.exit(1);
}
