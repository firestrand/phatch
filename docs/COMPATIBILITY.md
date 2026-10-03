# Installation and compatibility verification

Verified on Linux aarch64 on 2026-10-03. These results describe the tested
environments; they do not establish Windows, macOS or Linux x86_64 coverage.

## Dependency matrix

| Python | Pillow | Rich | Verification |
| --- | --- | --- | --- |
| 3.12.14 | 11.3.0 | 13.0.0 | Full suite: 2,524 passed, 12 skipped |
| 3.13.15 | 12.3.0 | 15.0.0 | Full suite: 2,524 passed, 12 skipped |
| 3.14.8 | 12.3.0 | 15.0.0 | Full suite: 2,524 passed, 12 skipped |

The first row exercises the declared minimum Pillow and Rich versions. All
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

## Installed GUI

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

## Current artifact checkpoint

After mixed-skip resume, resource protection, bounded rename and final preview corrections, the full source suite
passes on all three headless matrix rows above. The wheel rebuilt from its
source distribution is reinstalled and passes the outside-checkout scripts in
all three headless and both GUI environments. Archive inspection compares the
current batch, resource, journal, worker, variant, atomic and preview modules byte for byte and
confirms packaged recipes, fonts, desktop entries, the man page and the source changelog. Planning reports are absent from the source archive. Current locked verification uses uv 0.12.22.

Artifact SHA-256 values at this checkpoint:

- `phatch-0.3.0-py3-none-any.whl`: `9278ac85489417a8d983f773fc22251d30248d62b67062b3e3772e2675f9ff18`
- `phatch-0.3.0.tar.gz`: `99ad98d0afdb3b6f861b809d71b5abcb61dbed59e504bc26e69ab496f07b4288`

Further source changes require rebuilding and repeating installed checks.
