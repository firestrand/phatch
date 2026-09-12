# Modernization and Windows Readiness Implementation Plan

## Purpose

Modernize Phatch without replacing its wxPython interface or action-plugin
model. The work makes the application reproducibly buildable, installable, and
testable on Windows, Linux, and macOS; reduces global state and platform
coupling; and adds reliability features on top of tested architectural seams.

This is an implementation plan, not an instruction to change all legacy code
at once. Each phase must preserve externally visible behavior unless its
acceptance criteria explicitly define a change.

## Current Baseline

- `python -m ruff check .` passes with the current, intentionally permissive
  Ruff configuration.
- `python -m pytest --collect-only -q` discovers 2,153 tests but currently
  fails while importing `phatch.actions.geek` and `phatch.console.console`.
  Both failures result from import-time initialization looking for
  `geek.txt` in user or interpreter-prefix locations.
- `setup.py` exits immediately on Windows and uses `distutils`.
- Installed Windows initialization also exits in `phatch/core/config.py`.
- `pyproject.toml` configures Ruff but has no PEP 517 build metadata,
  dependency groups, coverage policy, or type-checker configuration.
- Pillow 11.3 and wxPython 4.2.3 require Python 3.9 or newer, contradicting the
  repository's Python 3.8 claim.
- Platform paths, package resources, executable discovery, subprocess
  invocation, metadata, and temporary output handling are spread across
  modules and rely on global or import-time state.

Before Phase 1 begins, capture these commands and their outputs under
`.omo/evidence/baseline/` so future failures can be classified as existing or
introduced:

```bash
python --version
python -m pytest --collect-only -q
python -m ruff check .
python bin/phatch --help
```

## Non-Negotiable Engineering Rules

### TDD and coverage

Every behavioral change follows red-green-refactor:

1. Add the smallest test that expresses the desired behavior or reproduces the
   defect.
2. Run the focused test and retain evidence that it fails for the expected
   reason.
3. Add the minimum production code required to pass.
4. Run the focused test and adjacent suite.
5. Refactor only after green, then run the repository verification command.

Tests must cover a happy path and at least one relevant failure path. New and
materially changed modules must maintain at least 90% line and branch coverage.
Project-wide coverage must never decrease and must be ratcheted to at least 90%
before this roadmap is complete. Exclusions require a source comment explaining
why the branch is unreachable plus explicit approval; generated wxGlade code is
the only planned broad exclusion.

Tests must not pass solely because an optional tool was skipped. Required CI
jobs install their tools explicitly. Optional-capability tests assert both the
available and unavailable states.

### SOLID, DRY, and KISS

- **Single responsibility:** separate path discovery, resource loading,
  process execution, image transformation, output commit, metadata handling,
  progress reporting, and UI decisions.
- **Open/closed:** add platforms and optional tools through implementations of
  small interfaces rather than new condition chains in core orchestration.
- **Liskov substitution:** fakes used by tests obey the same result and error
  contracts as real filesystem, process, metadata, and capability providers.
- **Interface segregation:** prefer narrow `Protocol` interfaces such as
  `ResourceProvider`, `ProcessRunner`, and `MetadataProvider`; do not create a
  general service locator.
- **Dependency inversion:** construct platform and integration dependencies at
  entry points and inject them into services. Domain code must not import wx,
  `winreg`, or `win32com`.
- **DRY:** centralize OS paths, resource lookup, executable resolution, command
  construction, capability detection, and output-conflict policy.
- **KISS:** retain the current plugin and GUI models. Introduce an abstraction
  only for a real external boundary or when at least two implementations need
  the same contract.

### Modern Python baseline

- Support CPython 3.11, 3.12, and 3.13 on x64 Windows, Linux, and macOS.
- Use `pyproject.toml` with PEP 517 and PEP 621 metadata and setuptools as the
  initial backend. Changing backend is out of scope unless setuptools cannot
  package a required resource.
- Use `uv` for development and CI locking, syncing, and command execution;
  wheels remain standards-compliant and do not require users to install `uv`.
- Use Ruff for formatting and linting and `ty` for type checking. Tighten rules
  incrementally for touched modules rather than reformatting the entire tree.
- Prefer `pathlib.Path`, `importlib.resources`, `platformdirs`, context
  managers, `dataclasses`, `enum.Enum`, `typing.Protocol`, explicit encodings,
  exception chaining, and structured `logging`.
- Use subprocess argument sequences with `shell=False`. Shell syntax and manual
  quote assembly are forbidden for new or migrated commands.
- Do not add mutable default arguments, mutable class-level defaults, wildcard
  imports, path mutation, import-time I/O, bare `except`, silent exception
  handling, `as any`-style type suppression, or compatibility shims without a
  persisted-data or external-consumer requirement.
- Normalize newly persisted timestamps to UTC and convert to local time only at
  filesystem or display boundaries.

## Supported Product and Distribution Contract

The planned Windows deliverables are:

1. A standards-compliant wheel installable into CPython 3.11-3.13 x64.
2. An unsigned portable PyInstaller application produced on Windows x64 using
   Python 3.12.
3. Console and GUI entry points from both the wheel and portable application.

Windows ARM64 compatibility jobs may be added for Python 3.11-3.13 after the
x64 gate is green. A signed installer, MSIX, Microsoft Store publication,
certificate management, automatic updater, and 32-bit Windows support are not
part of this plan.

Action-list formats 1.0 and 2.0 remain readable. Native integrations including
pywin32, pyexiv2, ImageMagick, JPEG utilities, Blender, and HEIF support remain
optional capabilities; their absence must not prevent startup or core image
processing.

## Target Architecture

Dependency direction must converge toward:

```text
bin/entry points and wx/console adapters
                |
                v
application services and typed execution results
                |
                v
action/plugin domain and image transformation logic
                |
                v
narrow ports: resources, paths, process, metadata, output store, clock
                |
                v
stdlib/Pillow/platformdirs/winreg/win32com/external-tool adapters
```

No lower layer may import a higher layer. wx objects remain in GUI adapters.
Windows registry and COM imports remain in Windows adapters. Existing public
functions may remain as compatibility wrappers while callers migrate.

## Phase 1: Hermetic Test Foundation

### Objective

Make test collection and core imports deterministic on a clean machine before
adding CI or refactoring runtime behavior.

### Test-first work

1. Add subprocess-based import tests that set temporary home, data, config, and
   cache directories and import `phatch`, `phatch.console.console`, and every
   action from a working directory outside the repository.
2. Confirm the tests reproduce the current missing-`geek.txt` failures.
3. Add fixtures that create a complete isolated runtime-path object without
   mutating real user directories.
4. Move console initialization, font registration, action loading, and resource
   copying out of module imports and into explicit entry-point startup.
5. Replace test-time `sys.path` insertion with installation of the project in
   editable mode once Phase 2 packaging is available. Until then, isolate the
   temporary compatibility fixture in one location.
6. Replace module-scoped temporary directories with `tmp_path` and close every
   Pillow image through context managers or fixture finalizers.

### Exit criteria

```bash
python -m pytest --collect-only -q
python -m pytest tests/unit/core tests/unit/console tests/unit/actions/test_geek.py
```

Both commands exit zero in an environment with temporary user directories and
without writing under the real home directory. Importing core modules performs
no filesystem writes, process launches, font scans, or GUI construction.

## Phase 2: Project Metadata and Reproducible Tooling

### Objective

Create one authoritative project definition and one local/CI verification
entry point.

### Test-first work

1. Add metadata tests asserting the supported Python range, package name,
   version, console/GUI entry points, core dependencies, and optional extras.
2. Move package metadata and dependencies into `pyproject.toml` using PEP 621.
   Keep `setup.py` only as a temporary thin compatibility launcher, then remove
   it after clean sdist and wheel installation tests pass.
3. Define extras for `gui`, `windows`, `metadata`, `heif`, and `dev`; keep
   Pillow as the only unconditional image runtime dependency unless a current
   import proves another package is core.
4. Generate and commit `uv.lock`. Configure dependency update automation to
   submit reviewed changes rather than silently floating lower bounds in CI.
5. Configure Ruff format/check, `ty`, pytest, and coverage in `pyproject.toml`.
6. Add a cross-platform `scripts/verify.py` entry point that runs format check,
   lint, type check, unit/integration tests, coverage, package build, and wheel
   metadata validation without shell-specific syntax.
7. Update README and test documentation to use `uv sync --all-extras --dev` and
   `uv run python scripts/verify.py` while retaining standard `pip install`
   instructions for users.

### Exit criteria

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run python -m build
uv run python -m twine check dist/*
```

The metadata declares Python 3.11-3.13 consistently. Building from both the
working tree and generated sdist produces a wheel without importing the GUI or
writing to user directories.

## Phase 3: Package Resources and Entry Points

### Objective

Make source, editable, wheel, and portable execution resolve identical assets
without relying on the current working directory or `sys.prefix/share`.

### Test-first work

1. Add parameterized resource tests for action lists, icons, fonts, masks,
   highlights, perspective assets, locales, documentation, and Blender files
   from source and an installed wheel.
2. Introduce a narrow `ResourceProvider` backed by `importlib.resources`.
3. Move or map distributable data into package data and remove `data_files`
   destination assumptions.
4. Replace `sys.path` mutation and unqualified internal imports with package
   imports in touched modules. Add tests that launch from a path containing
   spaces and from a different current directory.
5. Define `phatch` console and `phatch-gui` GUI entry points. Preserve
   `bin/phatch` only as a compatibility wrapper that calls the packaged entry
   point.
6. Change font and default-data initialization to copy from resource streams
   only when required and only into injected user-data paths.

### Exit criteria

A clean virtual environment can install the wheel, run `phatch --help`, import
every action, locate every required packaged resource, and start the GUI adapter
without referencing the repository checkout.

## Phase 4: Cross-Platform Paths and Windows Filesystem Behavior

### Objective

Centralize path policy and prove correct behavior for Windows-native locations
and path forms.

### Test-first work

1. Add a `UserPaths` immutable dataclass and tests for Windows, macOS, Linux,
   overridden environment variables, missing variables, and portable mode.
2. Implement user data/config/cache locations with `platformdirs`. On Windows,
   roaming settings belong under `%APPDATA%`; caches, logs, previews, and
   generated font indexes belong under `%LOCALAPPDATA%`.
3. Add a URI-to-path function using `urllib.parse` plus
   `urllib.request.url2pathname`; test drive-letter URLs, UNC URLs,
   percent-encoding, Unicode, malformed URLs, and ordinary paths.
4. Convert touched filesystem boundaries to `Path` while accepting `os.PathLike`
   at public APIs. Avoid converting back to strings until an external library
   requires it.
5. Add Windows-specific tests for spaces, non-ASCII profile names, long paths,
   case-insensitive output collisions, reserved names, read-only directories,
   and open-file deletion behavior.
6. Replace recursive directory creation and manual rename behavior with
   `Path.mkdir(parents=True, exist_ok=True)` and `os.replace` where contracts
   require atomic replacement.

### Exit criteria

Path tests pass on all three operating systems. Windows tests run as a standard
user and make no machine-wide changes. Application state is written only to the
configured platform directories or an explicit portable-data directory.

## Phase 5: Process Execution and Optional Capabilities

### Objective

Replace command strings and implicit optional dependencies with explicit,
typed, testable contracts.

### Test-first work

1. Define immutable `Command`, `ProcessResult`, and typed process exceptions.
   Test success, non-zero exit, missing executable, timeout, Unicode output,
   cancellation, and paths containing shell metacharacters.
2. Implement `ProcessRunner` with `subprocess.run`/`Popen`, argument vectors,
   `shell=False`, explicit text encoding/error policy, timeout, checked return
   codes, and consumer-routed logging.
3. Replace executable lookup with `shutil.which` plus injected search paths.
   Remove quoted executable values and global executable caches from domain
   code.
4. Migrate ImageMagick, jpegtran/exiftran, and Blender adapters one at a time.
   Lock each migration with command-construction and failure tests before
   removing its legacy path.
5. Introduce `CapabilityRegistry` with statuses `AVAILABLE`, `UNAVAILABLE`, and
   `MISCONFIGURED`, including an actionable reason. Detect pywin32, metadata,
   HEIF, external executables, and supported versions without importing them in
   core startup.
6. Rewrite Windows executable lookup to parse registry command lines safely,
   close keys with context managers, distinguish registry views, and report
   specific failures.
7. Make Explorer verbs per-user under `HKCU\Software\Classes`. Add isolated
   fake-registry tests for registration, coexistence, rollback, and removal.
   Never write the real registry from automated tests.
8. Keep shortcut creation in a pywin32 adapter and test generated target,
   arguments, working directory, icon, and missing-pywin32 behavior.

### Exit criteria

No migrated external action constructs a shell command string. A failed or
missing tool produces a typed error and capability status, leaves no partial
output, and cannot be mistaken for successful processing.

## Phase 6: Typed Execution and Plugin Boundaries

### Objective

Reduce the blast radius of `core/api.py`, global registries, and mutable result
dictionaries while preserving the action contract.

### Test-first work

1. Characterize current batch behavior for discovery order, disabled actions,
   safe mode, overwrite policy, skip/abort/continue, cancellation, progress,
   reporting, and error logging.
2. Introduce dataclasses/enums for `ExecutionRequest`, `ExecutionContext`,
   `ExecutionResult`, `FileResult`, `ExecutionDecision`, and `ExecutionIssue`.
3. Extract focused services for file discovery, action validation, action
   execution, progress publication, and report creation. Keep a thin legacy
   wrapper around `apply_actions_to_photos` until callers migrate.
4. Replace module-global action registries with an injected `ActionRegistry`.
   Use `importlib` and explicit plugin validation; return structured import and
   initialization failures.
5. Replace mutable class-level plugin defaults with immutable tuples or
   per-instance state. Add multi-instance and repeated-initialization tests.
6. Standardize action dependencies through a narrow immutable dependency
   object. Migrate representative pure-Pillow, file-output, metadata, and
   external-tool actions before applying the pattern to every action.
7. Remove import-time initialization and module-global lazy imports as each
   action migrates. A parameterized contract test must import and initialize
   every action independently in randomized order.
8. Type-check all new boundaries strictly and use exhaustive `match` statements
   for result/decision enums where appropriate.

### Exit criteria

Core execution tests can run without wx, real user directories, real external
tools, or process-global registry mutation. Existing GUI and console adapters
produce equivalent user-visible results through compatibility tests.

Completion requires evidence that all built-in plugins own mutable instance state
and initialize independently without module-global lazy dependency rebinding. The
registry must return fresh factory instances without generic deep copying,
randomized catalog contracts must cover every action, and the canonical
verification gate must pass the 90% line and branch requirement for every changed
module. Detailed commands and results belong in
`.omo/evidence/task-6-typed-execution.md`.

## Phase 7: Transactional Output, Metadata, and Resume

### Objective

Prevent corrupt or partial output and make interrupted batches safely
resumable.

### Test-first work

1. Characterize save behavior for JPEG, PNG, GIF, TIFF, transparency, EXIF
   orientation, metadata preservation, overwrite, timestamps, and failures.
2. Extract image rendering, encoded-file writing, metadata writing, output
   validation, atomic commit, and report update into separate operations.
3. Write output into the destination filesystem, flush and validate it, then
   commit with `os.replace`. On failure, preserve the previous destination and
   remove temporary files.
4. Define a `MetadataProvider` protocol and explicit no-metadata provider.
   Test unavailable native support, malformed tags, unsupported formats,
   thumbnail failures, orientation, and timestamp conversion boundaries.
5. Add an append-only UTC batch journal containing stable input identity,
   action-list digest, output path, state, and issue summary. Writes must be
   atomic and recover from a truncated final record.
6. Resume only entries whose input identity and action-list digest still match.
   Changed inputs, changed action lists, missing outputs, and previously failed
   items must be reported and re-evaluated rather than silently skipped.
7. Add crash/failure injection tests around encode, metadata, flush, replace,
   journal write, cancellation, and Windows file-lock errors.

### Exit criteria

For every injected failure, the previous destination is intact, temporary
resources are cleaned when safe, and the journal gives an unambiguous recovery
decision. A killed batch can resume without duplicating verified completed
work.

## Phase 8: Action-List Schema, Preflight, and Structured CLI

### Objective

Expose reliable automation features on top of the typed execution services.

### Test-first work

1. Define a versioned action-list schema with explicit required fields, action
   IDs, field values, and migration boundaries. Validate before constructing
   action objects.
2. Preserve readers for formats 1.0 and 2.0 with golden fixtures. Add a pure,
   idempotent migration to the new schema and golden round-trip tests.
3. Implement preflight/dry-run as a read-only execution-plan builder. It reports
   discovered inputs, planned outputs, conflicts, unavailable capabilities,
   unsafe operations, invalid fields, and estimated work without opening output
   files or changing state.
4. Add `--dry-run`, `--report-format text|json`, `--resume`, and
   `--capabilities` through the existing argparse boundary. Do not introduce a
   second CLI framework.
5. Define stable exit codes for success, partial success, validation failure,
   unavailable capability, processing failure, and user cancellation.
6. Define a versioned JSON report schema and snapshot tests. Human text remains
   localized; JSON keys and enum values remain stable and unlocalized.
7. Update the GUI to consume the same preflight and capability results through
   existing service/controller injection, keeping wx event handlers thin.

### Exit criteria

CLI end-to-end tests invoke installed entry points and verify stdout, stderr,
exit code, JSON schema, no-write dry runs, partial failures, cancellation, and
resume. GUI service tests verify the same domain results without constructing
wx controls; a separate wx smoke test covers wiring.

## Phase 9: Modern Formats and Bounded Parallel Processing

### Objective

Expand format support and throughput only after execution is deterministic and
transactional.

### Test-first work

1. Build a format-capability table from Pillow's registered codecs at runtime.
   Add real-file tests for JPEG, PNG, TIFF, GIF, and WebP.
2. Add AVIF when the supported Pillow build provides it. Add HEIF only through
   an optional provider/extras group. Unavailable codecs must be visible in
   preflight rather than causing late failures.
3. Test color mode, transparency, animation policy, ICC profile, EXIF, and
   quality-option behavior per format. Golden checks compare dimensions,
   modes, selected metadata, and bounded pixel metrics rather than unstable
   byte-for-byte encodings.
4. Add a `max_workers` execution option with a conservative default. Use a
   process pool only for independent CPU-bound image jobs; keep registry,
   journaling, progress aggregation, and output commits in the coordinator.
5. Prove deterministic output naming, ordering, cancellation, error isolation,
   cache behavior, and journal consistency at worker counts 1, 2, and CPU-based
   maximum.
6. Benchmark representative small, medium, and large images. Enable parallel
   execution by default only if it improves elapsed time without material
   memory regression; otherwise retain one worker and document opt-in tuning.

### Exit criteria

The same fixtures produce equivalent logical results with one and multiple
workers. Peak memory and throughput measurements are recorded, worker crashes
do not corrupt unrelated outputs, and unsupported formats fail during
preflight.

## Phase 10: CI, Portable Windows Application, and Release Gate

### Objective

Continuously prove supported source, wheel, GUI, and portable behavior.

### CI jobs

1. Fast quality job on Python 3.12: lock check, Ruff format/check, `ty`, and unit
   tests.
2. OS/Python matrix on Windows, Linux, and macOS for Python 3.11-3.13: install
   from lock, run non-GUI tests, and enforce coverage.
3. Wheel job on every OS: build from sdist, install into a clean environment,
   run entry-point/resource/import smoke tests from another directory, and
   archive metadata.
4. Windows GUI smoke job on x64 with wxPython binary wheels: create `wx.App`,
   open the main frame, load an action list, run preflight, process one image,
   close cleanly, and assert no error dialog/log entry.
5. Windows path job using spaces and Unicode in checkout, user profile fixture,
   input, and output paths. Include mocked long-path and locked-file failures.
6. Optional-capability contract job with all optional dependencies absent, plus
   targeted jobs for available metadata, pywin32, and external-tool adapters.
7. PyInstaller job on Windows Python 3.12 x64. Build from a reviewed spec/hook,
   inspect bundled resources and licenses, then run console and GUI smoke tests
   against the unpacked portable artifact.

### Release requirements

- Pin CI actions by immutable commit SHA and keep permissions minimal.
- Produce a software bill of materials, dependency/license report, wheel,
  sdist, portable archive, SHA-256 checksums, coverage XML, and test results.
- Scan built artifacts for unexpected files, local paths, credentials, and
  development-only dependencies.
- Re-run smoke tests on downloaded artifacts, not only build-directory copies.
- Document optional features and unsupported targets accurately.
- Do not sign or publish artifacts without separate explicit authorization.

### Exit criteria

All required jobs pass on a clean commit. A Windows user can extract the
portable archive into a path containing spaces, run both interfaces, process a
sample image, save and reload an action list, and leave application data only in
the selected platform or portable-data location.

## Verification and Quality Gate

The final repository verification entry point must execute, in order:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest --cov=phatch --cov-branch --cov-report=term-missing \
  --cov-report=xml --cov-fail-under=90
uv run python -m build
uv run python -m twine check dist/*
```

During the coverage ratchet, `--cov-fail-under` may start at the measured
baseline only if every changed module separately meets 90% line and branch
coverage. Each merge raises or preserves the project threshold. The final phase
cannot close until the repository-wide threshold is 90%.

Each implementation task must retain evidence for:

- the focused failing test before production changes;
- the focused passing test afterward;
- adjacent and full verification output;
- relevant wheel, portable application, CLI, or GUI manual smoke invocation;
- coverage for each changed module;
- cleanup and rollback assertions for its failure scenario.

## Phase Dependency Order

```text
Hermetic tests
  -> project metadata/tooling
  -> resources/entry points
  -> platform paths
  -> process/capabilities
  -> typed execution/plugins
  -> transactional output/metadata/resume
  -> schema/preflight/structured CLI
  -> formats/parallelism
  -> complete CI/portable release gate
```

Work may run in parallel only when targets do not overlap:

- resource packaging and verify-script design may proceed together after test
  isolation;
- path, URI, and fake-registry tests may proceed together after `UserPaths` is
  defined;
- metadata and process adapters may proceed together after their protocols are
  approved;
- CLI and GUI adapters may proceed together after typed execution/preflight
  contracts are stable;
- format providers and process-pool experiments may proceed together after
  transactional output and resume are green.

## Rollback and Compatibility Strategy

- Keep thin compatibility wrappers until all in-repository callers use the new
  service; remove wrappers only with reference search and full tests.
- Preserve golden fixtures for existing action lists and representative output
  semantics throughout the roadmap.
- Land one external-action migration at a time. A failing adapter can be
  reverted without reverting the process abstraction.
- Keep parallel processing disabled until deterministic equivalence and memory
  criteria pass.
- Keep new optional formats capability-gated; their providers can be disabled
  without changing core formats.
- Portable artifact failures must not block wheel/source use until the portable
  artifact is declared a required release deliverable at Phase 10 completion.
- Database services, network services, cloud processing, telemetry, auto-update,
  and a GUI framework rewrite are forbidden scope expansion.

## Completion Definition

This plan is complete only when:

- test collection and the full verification entry point pass from a clean
  environment;
- project-wide line and branch coverage are at least 90%;
- no required test or quality tool can silently skip because it is absent;
- wheel installs and entry points pass on Python 3.11-3.13 across Windows,
  Linux, and macOS;
- the unsigned Windows portable artifact passes console, GUI, resource,
  Unicode-path, dry-run, processing, and resume smoke tests;
- core runtime imports perform no I/O or process initialization;
- migrated commands use argument vectors and checked results;
- standard-user Windows execution avoids machine-wide registry writes;
- action-list 1.0/2.0 compatibility and new-schema migration are proven by
  golden tests;
- failed writes and interrupted batches preserve prior files and resume safely;
- preflight, capability reporting, structured CLI output, modern formats, and
  bounded parallelism satisfy their failure as well as happy-path tests;
- user, contributor, architecture, optional-dependency, Windows, portable, and
  release documentation match actual verified behavior.
