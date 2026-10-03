# Batch execution and output planning

## Python API

Initialize configuration and the plugin registry before constructing an action list. `run_batch` returns a structured result and does not require GUI receivers.

```python
from phatch import init_config_paths
from phatch.core import api
from phatch.core.batch import plan_batch, run_batch

init_config_paths()
api.import_actions()
save = api.ACTIONS['Save']()
save.set_field_as_string('In', '/tmp/photos')
save.set_field_as_string('As', 'png')
actions = [api.ACTIONS['Invert'](), save]

plan = plan_batch(actions, ['photos/'], {'recursive': True})
if plan.valid:
    result = run_batch(actions, ['photos/'], {'recursive': True})
    result.write_report('/tmp/batch-report.json')
```

Planning reads input headers and inspects serialized action fields. It never initializes or executes actions and never creates image outputs. It reports duplicate destinations, existing outputs under a fail policy, source/output overlaps, unavailable encoders, and collisions with reserved report or recipe paths. Repeat indices and recursive subfolders participate in destination planning.

Only simple, known variable substitutions can be resolved without execution. Names requiring custom expressions, unavailable metadata, or geometry after arbitrary transforms appear in each input's `unresolved` list. A valid plan can contain unresolved destinations; final atomic writes still enforce the chosen collision policy. A plan does not establish that external tools or custom plugins can initialize or execute successfully.

`run_batch` keeps caches and image state separate for each input and releases images on success, failure or cancellation. Its result has per-input statuses, committed output paths, action failures, warnings, elapsed time, and aggregate counts. Calling `to_dict()` hides absolute paths and detailed plugin messages by default. Detailed messages are available in memory and can be included explicitly with `include_details=True`; include paths only when the report's destination and audience are appropriate.

`api.apply_actions_to_photos` adapts the engine to existing progress, image-check, notification and error dialogs. `ActionListService.execute` forwards its result. Existing callers can continue ignoring the return value.

## Console usage

```bash
phatch --console --dry-run workflow.phatch photos/
phatch --console --dry-run --report plan.json workflow.phatch photos/
phatch --console --report result.json --collision-policy rename workflow.phatch photos/
phatch --console --recursive --report result.json workflow.phatch photos/
```

Dry-run output goes to stdout unless `--report` selects a file. Report files use atomic replacement and may not overlap a recipe, an input, a resolved workflow resource, or a known image output. Image, association-artifact and journal destinations also cannot overwrite resolved read resources. Preflight uses the shared resource resolver without hashing contents, checks dependencies across all inputs/repeats/frames, and reports unresolved resource paths as warnings. Manifest execution retains stricter freshness validation. `--report-paths` explicitly includes full paths. `--no-save` allows workflows without a final Save action; it does not prevent side effects and is not a dry run.

## Outcomes and collision policies

| Outcome | Exit code | Meaning |
| :--- | :--- | :--- |
| Success | 0 | Completed inputs succeeded or existing outputs were skipped. |
| Processing failure | 1 | One or more actions failed; a report identifies completed and unstarted inputs. |
| Invalid setup | 2 | The recipe, inputs, output plan, or plugin initialization could not be accepted. |
| Cancelled | 130 | Cancellation was requested; already committed outputs remain recorded. |

Each Save action offers `inherit`, `skip`, `fail`, `replace` and `rename`. Inherit uses `--collision-policy` when supplied, otherwise the existing overwrite setting. Explicit per-action choices take precedence over the console option. Rename uses deterministic numeric suffixes and a race-safe no-overwrite commit. Source/output overlap is visible as a planning warning; replacement preserves the original until encoding and metadata processing succeed.

Progress callbacks receive `ProgressEvent` values. Supply `cancel` as a callable returning a boolean to cancel between actions and inputs. A callback can request cancellation before the next action runs. In-flight encoding is not forcibly interrupted, and any output committed before cancellation is retained in the result.

An optional `on_error(failure, source)` callback can choose `skip`, `ignore`, `stop` or `abort`. Skip proceeds to the next input; ignore continues the current action sequence and retains the failure in the report; stop follows the normal error-stop policy; abort records cancellation. Without a callback, `stop_for_errors` controls whether later inputs are attempted.
## Export and resume policies

Save exposes `Metadata Policy`: `inherit` respects the old Metadata boolean;
`preserve` retains supported native metadata; `strip` removes descriptive
metadata; `selected` keeps the comma-separated EXIF names or numeric IDs in
Metadata Tags; `sharing` removes GPS, device identifiers and author fields,
and omits XMP and PNG text. Mandatory TIFF structure remains. Preserved EXIF
describes normalized pixels and the final dimensions. Unsupported preservation
appears in file warnings.

Color Policy is independent: `preserve` keeps a matching ICC profile;
`srgb` performs an ICC transform and embeds an sRGB profile. Transparency is
retained. An untagged input is assumed sRGB with a warning. Invalid profiles
and preserved profiles that no longer match the pixels fail before commit.

WebP offers quality 0–100, lossless mode and effort 0–6. Lossless mode preserves
invisible RGB too. AVIF offers quality 0–100 and speed 0–10; engine setting
`encoder_threads` defaults to one and accepts 1–64. `Format Fallback` defaults
to `error`; selecting `png` explicitly changes the planned and committed
extension when an encoder is unavailable. `phatch --capabilities` emits JSON
describing the current Pillow encoders, native features and optional external
tools without launching those tools or loading the GUI. Options follow the
tested [Pillow format contracts](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html).

Use `--manifest job.json` to record an atomic journal, then
`--manifest job.json --resume` to reuse verified work. Python callers pass
`manifest_path` and `resume` through engine settings. Each entry fingerprints
the source, recipe, settings, plugin/engine code, dependency versions, resolved per-input resource files and committed outputs.
Source or resource changes during processing leave the input incomplete. Resume hashes and verifies outputs before skipping them;
missing or changed work is processed again under the chosen collision policy.
A fail collision policy therefore still fails when changed work would replace
an existing output. Filename-based skip remains a separate, weaker choice. A job that skips any planned image or artifact stays incomplete in the journal, including mixed jobs that commit other destinations. Resume retries such jobs under the chosen collision policy; it does not treat the skipped files as verified recipe outputs.

Journals contain source/output paths and fingerprints, but no image metadata
payloads. They are owned by one running batch. Saving, renaming or modifying
source files and external-command actions do not have a resumable contract;
such recipes are rejected before execution. Custom actions must explicitly
declare `resumable = True` and provide an inspectable implementation. Journals
cannot overlap sources, outputs, recipes or reports. A corrupt journal is an
invalid setup; start a new journal explicitly rather than overwriting it while
requesting resume. Running, cancelled and failed entries are never considered
complete. Results expose verified skips through `FileResult.resumed`.

[Plugin contracts](PLUGIN_CONTRACTS.md) explains read-file fields, explicit
`resource_fields`, dictionary/font aliases and repeat/frame-dependent paths.
Unknown dependency expressions fail the journaled input with a diagnostic
instead of permitting an unverifiable skip. Resource changes invalidate only
inputs whose resolved dependency set changed; workers share the parent
alias dictionaries and journal ownership. Earlier journals safely reprocess
once after the engine fingerprint changes.
