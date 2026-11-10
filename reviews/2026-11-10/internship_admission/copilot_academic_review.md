No unconditional P1/P2 defects found in the reviewed paths.

Uncertainty, not counted as a finding: The migration imports existing academic placements as
LEGACY_IMPORT (0015, lines 61–70), but academic_placement_ready requires b.origin='PUBLIC' and
checks coordinator authority using b.actor_id (lines 275–286); imported bindings have no actor.
Thus, an imported placement that still needs activation cannot pass the start-readiness check. If
preserving activation for pending legacy placements is required, add a narrowly validated
legacy-readiness path or a reviewed re-admission process. Whether this is intentional fail-closed
behavior is unclear.

