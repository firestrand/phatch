# Action Lists and Automation

Phatch writes action lists with schema version 3 and continues to read legacy
formats 1.0 and 2.0. Legacy files are parsed as JSON or safe Python literal data,
validated structurally, and migrated in memory before any action plugin is
constructed.

## Schema Version 3

The document keys are `schema_version`, `description`, and `actions`. Each action
has an unlocalized `id` and a `fields` object whose keys are unlocalized field
IDs. IDs use lowercase ASCII letters, digits, and underscores. Unknown keys,
action IDs, field IDs, non-string field values, future schema versions, and
executable expressions are rejected.

```json
{
  "schema_version": 3,
  "description": "Create smaller copies",
  "actions": [
    {
      "id": "scale",
      "fields": {
        "canvas_width": "800px",
        "canvas_height": "800px",
        "enabled": "yes"
      }
    }
  ]
}
```

Migration is pure and idempotent: migrating an already migrated version 3
document produces the same document. Loading maps validated IDs to the active
registry only after structural validation succeeds.

## Structured CLI

The installed `phatch` command uses its existing argparse interface:

```bash
phatch --dry-run --report-format json actions.phatch input.jpg
phatch --capabilities --report-format json
phatch --resume /absolute/path/batch.jsonl --report-format json \
  actions.phatch input-folder
phatch --max-workers 2 --verbose --report-format json \
  save-only.phatch input-folder
phatch --report-version 2 --report-format json \
  actions.phatch input.jpg
```

`--dry-run` discovers inputs and reports planned outputs, existing conflicts,
unavailable capabilities, unsafe operations, invalid fields, and estimated work.
It does not initialize user directories, font caches, logs, journals, action
execution, or output files. `--resume` uses the transactional recovery journal
and skips only verified completed outputs whose input and execution fingerprint
still match.

`--max-workers` is validated from 1 through the host logical CPU count and
defaults to the legacy serial path at 1. More than one worker is used only for
the documented, typed subset of independent Save jobs. Unsupported Save options,
`--keep`, and `--resume` report an explicit serial fallback rather than being
silently ignored. See [Codec and Parallel Processing](parallel_processing.md)
for the exact eligibility contract, worker limits, traces, and measured tuning
guidance.

JSON reports use `report_version: 2`; requesting any other report version is a
validation error. JSON keys and enum values are stable and unlocalized;
diagnostics are written to stderr so stdout remains one parseable JSON document.
Human-readable text is localized at the display boundary.

### Migrating report consumers from v1 to v2

Action-list schema version and execution-report version are independent. Phatch
still writes action-list schema version 3 and reads legacy action-list formats
1.0 and 2.0. Report v2 is the only emitted automation format; there is no legacy
report switch. `--report-version 1` is rejected with validation exit code 2. If
JSON was requested, that rejection is itself a report-v2 error document.

Consumers migrating from report v1 must read each explicit file `outcome`, use
the four reconciled count fields, and accept an output only when its `survived`
field is true. Do not reconstruct status from issue counts and do not use
redacted report paths to access the filesystem. A version-pinned invocation is:

```bash
phatch --report-version 2 --report-format json actions.phatch input.jpg
```

Execution reports contain `outcome`, `elapsed_seconds`, `counts`, ordered
`files`, and `issues`. Each file contains `source`, its explicit terminal
`outcome` (`processed`, `skipped`, `failed`, or `cancelled`), `cancellation`,
`rollback`, and output records. Each output record contains a `path` and a
`survived` flag. Consumers must treat only records with `survived: true` as
files produced by the run. The counts object contains each terminal outcome and
`total`, which equals the number of ordered file records.

Report paths are privacy-safe audit identifiers rather than reusable filesystem
paths. Known action-list, input, output, home, and temporary roots are replaced
by stable placeholders such as `<action-list>`, `<input>`, `<output>`, `<home>`,
and `<temp>`; multiple roots use deterministic numbered forms such as
`<input:1>`. The longest path root wins and replacement requires a path
boundary. Credentials and common image-metadata values are redacted from
diagnostic fields. Capability, preflight, execution, and error JSON documents
all use this policy. Use the original action-list and CLI paths when filesystem
access is required.

## Exit Codes

| Code | Outcome |
| ---: | --- |
| 0 | success |
| 1 | partial success |
| 2 | validation failure |
| 3 | unavailable capability |
| 4 | processing failure |
| 130 | user cancellation |
