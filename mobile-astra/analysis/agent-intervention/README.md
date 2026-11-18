# Agent takeover after VLA

This export classifies the existing evaluated episodes; it does not rerun any
model or simulator. Coverage: E01–E08, E10 and E11, each 160 episodes (80 Seen,
80 Unseen). E09 remains withheld. E12 has no Planner and is **not applicable**.

## Definition

An episode counts as `takeover_success` when a VLA call is followed by a non-VLA
physical action, and the final native score is successful. Where a per-step
native success timeline exists, attribution stops at the **first native success**.
Thus the intervention must occur after VLA and before or at the first success.

- VLA: `rldx_skill`, `rldx_arm`.
- Physical intervention: `move_to`, `move_delta`, `move_base`, `navigate_to`,
  `rotate_pitch`, `set_gripper`, `release`, `scripted_grasp`, `execute_action`.
- Excluded: read-only queries, files/memory, `finish`, VLA continuation alone,
  and preparation occurring only before the first VLA call.

Successful episodes partition into VLA-only, preparation before VLA, and
takeover after VLA. Takeovers further split by the action that first reaches
native success: VLA after correction, or a manual/analytic action.
“VLA-only” still permits Planner scheduling of repeated VLA calls.

**E06 exception:** native per-step success was not saved. Its counts are marked
`final_score_proxy` and displayed with †. Only VLA → intervention → final native
success is established. Earlier transient success cannot be ruled out. The
`completion_actor` is its last physical action before final scoring, not a proven
first-success action. `confirmed_pre_success_takeover` is null, not false.

This is an observed action-path statistic, not a causal estimate of Agent benefit
or proof that continuing VLA would have failed. Initial states and VLA action
sampling were not fully controlled between batches.

## Files

- `summary.csv`: one row per experiment and split, including E12 null counts.
- `episodes.csv`: 1600 per-episode classifications, steps and evidence hashes.
- `data.json`: the same statistics plus saved physical-action sequences.
- `extract.py`: stdlib-only extractor and invariant checks.
- `render.py`: idempotent rendering into the overview, catalog, experiment pages,
  metadata and comparison page. Existing success scores are preserved.
- `app.js`: client-side episode filters and paginated action evidence.

`takeover_attempts` includes unsuccessful episodes with a qualifying intervention.
It is not the number of successful takeovers. Action counts and attributed steps
stop at first success when available; the full saved action sequence is retained
separately. Empty first-intervention/first-success steps mean none was observed;
E06 first-success steps are unknown.

## Verification and reproduction

E01 uses the reviewed published `analysis/cases/astra--TASK--SEED.json` traces.
Its new classifications match the existing `repair` categories and action counts.
Other experiments use canonical or archived `states.json` and `result.json`.
The extractor validates task/seed coverage, split, validity, final scores,
published result/state hashes, action ordering, allowed actions, and successful
path partitions. All ten settings use the same 160 task/seed keys.

The public E04 and E10 archives reserialize states JSON. When raw bytes differ,
the extractor reconstructs the original serialization and requires its exact
published SHA-256. The actual consumed and published hashes are both retained.
E06 state hashes are newly recorded, since its earlier export had result hashes only.

Create a local source configuration (do not publish machine paths):

```json
{
  "E02": {"root": "/path/to/da3_run"},
  "E03": {"root": "/path/to/notask_run"},
  "E04": {"archive": "/path/to/nocontact-audit.zip", "prefix": "results"},
  "E05": {"root": "/path/to/nogeom_run"},
  "E06": {"root": "/path/to/agent_success_run"},
  "E07": {"root": "/path/to/nomemory_run"},
  "E08": {"root": "/path/to/combined_run"},
  "E10": {"archive": "/path/to/vlm-progress-audit.zip", "prefix": "results"},
  "E11": {"root": "/path/to/vlm_contact_run"}
}
```

Each root/prefix contains `composite_seen/TASK_sSEED` and
`composite_unseen/TASK_sSEED` directories.

```bash
python mobile-astra/analysis/agent-intervention/extract.py \
  --site mobile-astra --sources /path/to/local-sources.json \
  --output mobile-astra/analysis/agent-intervention
python mobile-astra/analysis/agent-intervention/render.py
```

The public export contains selected action names, counts, step indices and hashes.
It does not copy raw model messages, task text, images, memory, tool arguments or
local machine paths.
