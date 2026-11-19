Bind private evidence retrieval to an immutable provider object reference.

Source review identified a conditional storage-integrity gap: current download
authorization compares DB hash/version snapshots, then presigns GET by storage key.
The normal scan pipeline writes content-addressed private keys, so this is not a
demonstrated public authentication or ordinary-upload overwrite exploit. Provider
overwrite/version guarantees are not validated by the mocked-storage/native PG tests.

Current storage.write_private returns VersionId or ETag in one object_version field.
Do not blindly pass an ETag as a VersionId. Define explicit version/ETag provenance,
legacy behavior and a fail-closed policy where an immutable reference cannot be
established. Preserve owner-only and named-case/assigned-reviewer scope, audit and
short URL lifetimes. Bind actual retrieval to the recorded version or enforce and
verify provider immutable-key semantics; metadata comparison alone is not that proof.

Test both versioned and legacy/ETag responses, content replacement after authorization,
replay, unchanged scan/copy behavior, provider failure and no private data leakage.
Use a disposable local S3-compatible integration with ephemeral credentials to
observe actual version-pinned reads/overwrite protection. Keep live infrastructure,
production credential rotation and real provider acceptance separate. Update
readiness/deployment documentation to require the actual guarantees selected.

This is follow-up to PR56's bounded metadata/role workflow and is required before
any broader live-provider/pilot claim. It must not be described as already fixed
or as a proven public exploit. The current guide documents this limitation.
