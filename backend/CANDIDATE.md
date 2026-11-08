# Candidate backend (CAN-CODEX-001)

All routes require `Authorization: Bearer <access_token>`. The actor comes from
the session; request bodies cannot select another user/candidate or assign verification.
Candidate/profile/schedule/matching/file responses use `Cache-Control: no-store`.
No frontend or institution/skill-review workflow is supplied by this package.

## Profile and skills

- `GET /api/v1/me/candidate`: own profile and skills, including computed `verified`.
- `PATCH /api/v1/me/candidate` (`API-026`): partial update of `headline` (1–200),
  `region` (1–100), `bio` (nullable, up to 5000), `experience_months` (0–1200).
  Other fields are rejected. Student status/evidence is not required to edit a profile.
  Visibility remains server-owned; there is no public profile listing in this package.
- `GET /api/v1/skills?q=Python&limit=50`: active UZ/RU catalog, at most 100 rows.
  The catalog must be provisioned separately; requests cannot create verified skills.
- `PATCH /api/v1/me/candidate/skills` (`API-032`): partial upsert/removal:

```json
{"skills":[{"skill_id":"CATALOG_UUID","level":"INTERMEDIATE"}],"remove_skill_ids":[]}
```

Up to 100 entries in each list; IDs must be unique and cannot appear in both lists.
`level` is a self-declared label (1–64 characters); canonical sources do not prescribe
an enum. Only active catalog skills may be added/updated. A new entry is unverified.
An existing linked case must be APPROVED and target this candidate for `verified=true`.
Changing the level clears its verification association; a no-op preserves it.
Clients cannot submit `verified` or `verification_case_id`. Independent verification
submission/review remains a later workflow.

## Private CV

1. Use `/files/upload-intents`, upload the PDF to the returned URL, then call
   `/files/{id}/complete-upload` (see README for storage/AV configuration).
2. Wait for the existing worker to finish scanning. Client scan assertions are rejected.
3. `POST /api/v1/me/candidate/cv` (`API-033`) with `{"file_id":"FILE_UUID"}` links
   only your own nondeleted CLEAN PDF. Pending/scanning/quarantined files return 409;
   someone else's file returns 403. The link and audit write share one transaction.
4. `{"file_id":null}` unlinks the CV; it does not delete the file.

Profile responses return the file UUID, never a storage key or signed URL. Existing
`GET /files/{id}/download` checks current ownership/cleanliness and issues a 60-second
URL. Linking a CV grants no access to another candidate, HR or an organization.
Application-scoped HR sharing is still an APP task. The current upload adapter retains
its existing `VERIFICATION_EVIDENCE` retention class; defining CV-specific retention
and protecting active references during a real purge remain OPS work. This package
does not run retention deletion or assert a legal retention period for CVs.

## Weekly schedule and date exceptions

`PUT /api/v1/me/availability` (`API-028`) atomically replaces all own weekly rules:

```json
{"rules":[{"weekday":1,"start_minute":510,"end_minute":750,
  "valid_from":"2026-11-09","valid_to":null,"timezone":"Asia/Tashkent"}]}
```

At most 100 input rules. Weekday is ISO 1=Monday … 7=Sunday. Minutes are half-open
`[start,end)`, `0 <= start < end <= 1440`. Validity dates are inclusive; `valid_from`
defaults to the current Asia/Tashkent date. The R1 implementation accepts
`Asia/Tashkent`; other zones are rejected explicitly. Split an overnight interval
into the actual neighboring weekdays/dates. Identical weekday/validity/timezone
groups merge overlapping/adjacent intervals. Conflicting date-period groups return
409 and roll back the whole replacement. An empty list clears the weekly schedule.

`PUT /api/v1/me/availability/exceptions` (`API-036`) replaces only the supplied
inclusive date range (at most 366 days), leaving dates outside it intact:

```json
{"from_date":"2026-11-09","to_date":"2026-11-09","exceptions":[
  {"local_date":"2026-11-09","kind":"UNAVAILABLE","start_minute":600,"end_minute":660}]}
```

At most 400 inputs. `AVAILABLE` adds intervals; `UNAVAILABLE` subtracts them.
Same-date/same-kind inputs merge; conflicting kinds with overlapping minutes return
409 and roll back. An empty list clears exceptions only inside that date range.

`GET /api/v1/me/availability?from_date=2026-11-09&days=28` (`API-035`) returns raw
relevant rules/exceptions plus effective daily intervals and `availability_revision`.
`days` is 1–366; the default start is the local current date.

## Matching

`POST /api/v1/matching/preview` (`API-003`):

```json
{"candidate_id":"YOUR_CANDIDATE_UUID","opportunity_id":"PUBLISHED_OPPORTUNITY_UUID",
 "schedule_match_mode":"ANY_SHIFT_IN_GROUP","commute_buffer_minutes":30}
```

Only current PUBLISHED, unexpired revisions are visible. A missing/draft/old revision
returns 404; if both opportunity/revision IDs are supplied they must refer to that
same current revision. `check_date` is optional; historical dates are clamped to today.
The checked window starts at max(today, check_date, revision start), lasts at most
28 days, and is clipped to the inclusive revision end. `checked_to` is exclusive.

Every real weekly occurrence in the window is checked against that occurrence's
actual local date, including validity dates and exceptions. ALL requires every
group; ANY requires at least one complete group. There is no MATCH from an empty
occurrence set. Missing shifts/data/occurrences or unsupported persisted zones
return UNKNOWN with reason codes; a known uncovered occurrence returns CONFLICT.

ONSITE/HYBRID default to a displayed 30-minute buffer before and after the shift;
REMOTE uses zero. The request may explicitly choose 0–180 minutes. This is a user
assumption, not measured travel time. Windows crossing midnight/Sunday are checked
against the actual previous/next date. Responses include `algorithm_version=1.4.1-can`,
`availability_revision`, checked dates/occurrence count, buffer and matched groups.

Without target IDs, preview returns a page of `items` (matches) and `evaluations`
(including conflicts/unknowns). `limit` is 1–100; `after_id` takes `next_cursor`.
The top-level result summarizes only that page; checked dates span its individual
evaluation windows. Each evaluation retains its own at-most-28-day window.
The cursor refers to the last examined opportunity, so a page with no matches can
still advance. `GET /opportunities/feed` exposes the same bounded pagination with
`candidate_id`, `limit`, `after_id`, `check_date`, mode and buffer query parameters.
Ordering is stable UUID order in this package; full JOB search/ranking remains separate.

Matching uses four scoped SELECTs per nonempty page: visible revisions, their shifts,
own active/date-relevant rules, own date-range exceptions. A REPEATABLE READ transaction
prevents combining schedule versions during concurrent edits. Writes serialize on
the candidate profile row; database exclusion constraints remain authoritative.
