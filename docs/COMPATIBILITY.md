# Installation and compatibility verification

The integration targets Ubuntu 24.04 aarch64 and Python 3.12–3.14. Native macOS verification remains required by [the release gate](release_gate.md) before publishing the 0.5 candidate. These results do not establish Windows, macOS or Linux x86_64 coverage.

## Historical feature-branch dependency matrix

| Python | Pillow | Rich | Verification |
| --- | --- | --- | --- |
| 3.12.14 | 11.3.0 | 13.0.0 | Full suite: 2,524 passed, 12 skipped |
| 3.13.15 | 12.3.0 | 15.0.0 | Full suite: 2,524 passed, 12 skipped |
| 3.14.8 | 12.3.0 | 15.0.0 | Full suite: 2,524 passed, 12 skipped |

These runs preceded the modernization integration and do not validate the combined candidate. The first row exercises the feature branch’s then-declared minimum Pillow and Rich versions. All
three installed-wheel checks run outside the repository in fresh XDG profiles,
without wxPython. They load packaged recipes and fonts, export twelve variants,
render a text preview, execute the installed CLI's capabilities and dry-run
commands, process two inputs with spawned workers, and verify two resume skips.
These checks are separate from the full suites, which exercise repository source.

The full suites retain existing warnings and skips. An earlier crash-test stall
was reproduced on Python 3.13 and 3.14. Captured stacks identified blocked shared
queue and cancellation Event locks. Per-job event pipes and a parent-written
cancellation notification replace those locks; 960 crash checks pass across
Python 3.12–3.14. See [worker guarantees and evidence](BATCH_WORKERS.md).
A separate assertion was corrected to isolate the
registered transaction under test: pool termination can leave another worker's
empty temporary if it dies before its registration handshake, as documented in
[the worker guarantees](BATCH_WORKERS.md).

## Historical feature-branch installed GUI

| Python | wxPython | Pillow | Verification |
| --- | --- | --- | --- |
| 3.12.14 | 4.2.3, GTK3, wxWidgets 3.2.8 | 11.3.0 | Main frame, packaged preset, preview |
| 3.14.7 | 4.3.1, GTK3, wxWidgets 3.3.3 | 12.3.0 | Main frame, packaged preset, preview |

Both installed GUI checks also exercise editor-loaded Save collision policies through the service adapter, with non-modal notifications. Scoped GUI typing and separate actual GUI integration tests pass in both environments.

Both GUI environments use conda-forge binaries, an installation route described
by the [wxPython download guide](https://wxpython.org/pages/downloads/index.html).
They use the built wheel and an existing display. The smoke check constructs the
actual editor, inserts the bundled web variants preset, checks the preview menu,
and waits for an asynchronous preview through the wx event loop. No export is
written during preview. Separate GUI integration tests also pass in each
environment. This is startup and feature smoke coverage, not an exhaustive
interactive usability or platform test.

## Build and reproduction

`uv build --no-sources` successfully builds the source distribution and then the
wheel from that distribution. Archive inspection confirms the new modules,
bundled web variants recipe, FreeSans font, desktop entries, man page and MIME
registration are included.

After installing the wheel in an isolated environment, run from a directory
outside this repository:

```sh
/path/to/headless-env/bin/python /path/to/phatch/tests/installed_distribution_smoke.py /tmp/phatch-headless-smoke
/path/to/gui-env/bin/python /path/to/phatch/tests/installed_gui_smoke.py /tmp/phatch-gui-smoke
```

Use a fresh scratch directory for each invocation. The GUI check requires a
working display and wxPython. These scripts isolate configuration and outputs
under the supplied directory and assert that the imported package is installed.

Fresh-profile testing found and fixed three startup defects: Geek command
defaults assumed a user file already existed, legacy configuration and font
modules did not share installed resource paths, and spawned console workers
could resolve the legacy launcher ahead of the package. A subprocess regression
checks fresh-profile registry loading, shared configuration, font roots and
spawned package imports without creating a Geek configuration file.

WebP and AVIF encoders are available in the tested headless wheels. Availability
on other builds remains discoverable through `phatch --console --capabilities`;
an unavailable codec requires an explicit supported fallback.

## Combined candidate verification

The combined candidate keeps the dynamic package version `0.5.0rc1` and the
`phatch_assets` resource layout. Its wheel and source distribution build
successfully, pass Twine metadata
validation and pass the repository artifact scanner. Archive inspection finds
all 26 bundled recipe/preview resource entries and no task research, planning
or temporary files. Historical 0.3.0 artifact hashes are not candidate evidence.

The native Ubuntu gate uses Python 3.12.14, Pillow 11.3.0 and wxPython 4.3.1
(GTK3, wxWidgets 3.3.3). wxPython is installed from conda-forge, with the locked
development dependencies installed into that environment. Invoke the same
verification script with that environment's Python and `CI` unset. The full
gate against `origin/master` passes: **5,614 tests passed, 12 skipped**, with
**95.68% line coverage and 92.75% branch coverage**. Every changed module meets
the 90% line/branch requirement. Lock, formatting, lint, typing, wheel/sdist
builds and metadata validation also pass. Existing warnings and skips remain;
optional external tools and native Windows checks are not established by this
Ubuntu result.

The wxPython 4.2.3 environment failed in native progress-dialog teardown; its
startup smoke results above do not establish full-suite compatibility. The
Python 3.14 native environment also needs a complete candidate gate before it
can be claimed as fully verified. Headless checks, installed-wheel smoke tests
and native gates are separate evidence.

The rebuilt installed wheel passes headless smoke checks outside the checkout:

| Python | Pillow | Rich | Verification |
| --- | --- | --- | --- |
| 3.12.14 | 11.3.0 | 15.0.0 | Resources, 12 variants, preview, CLI, workers, two verified resume skips |
| 3.13.15 | 12.3.0 | 15.0.0 | Same installed checks |
| 3.14.8 | 12.3.0 | 15.0.0 | Same installed checks |

Native installed GUI smoke checks also pass on Python 3.12.14 and 3.14.7 with
Pillow 11.3.0 and wxPython 4.3.1. Each constructs the editor, loads the packaged
variant recipe, renders an asynchronous preview and exercises all four Save
collision policies through the explicit batch adapter. These are installed
smoke checks, separate from the full verification gate.

The Ubuntu XDG launcher passes desktop-file validation and opens an installed
native window from outside the checkout using a prefix containing a space.
The probe identifies its window by the owned process ID, then stops only its
processes and removes only its temporary launcher, icon and XDG profile.

No native macOS candidate gate or packaged application check has been run in
this environment. The candidate remains unpublished until those required
checks pass.
