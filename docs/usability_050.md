# Phatch 0.5 Usability Candidate

This guide describes the implemented 0.5 usability candidate. It is not a
release announcement: there is no published 0.5 tag, PyPI package, Linux binary,
or 0.5 macOS download. Use only an authorized local candidate checkout or wheel.
The published release remains 0.4.0.

## What changed

- `Tools > Preview...` opens one reusable, modeless before-and-after dialog.
  Choose one sample image and select `Refresh`; preview does not update
  implicitly and never writes output.
- Action-list Undo and Redo retain at most 100 committed document edits. A
  cancelled, invalid, or no-op edit adds no history entry. Save keeps history
  and moves the clean checkpoint; cancelled or failed New, Open, Save, and Save
  As operations leave document history unchanged.
- The Add Actions dialog separately reports runtime availability and preview
  support. Missing optional software and preview-policy blocking are not the
  same condition.
- Batch completion uses one terminal result per discovered source:
  `processed`, `skipped`, `failed`, or `cancelled`.
- Automation emits privacy-safe report v2 only. Action-list schema remains 3.
- Five packaged action lists support the six starter workflows below.

## Preview

Open `Tools > Preview...`, choose a PNG, JPEG, GIF, BMP, or TIFF sample, then
select `Refresh`. The dialog shows `Original` and `Result`, both dimensions, and
the requested Save format. The format is a label for the requested output; the
preview is not an encoded-output fidelity check. An enabled terminal Save is
named and omitted because preview writes no file. Editing, New, or Open clears
the images and marks the view stale until the next explicit Refresh.

`Cancel` is enabled while work is active. Cancellation, replacement requests,
closing the dialog, and closing the application stop and join the owned preview
worker; stale results are discarded.

Preview runs audited built-in image actions on the original image geometry and
downsamples only for display. Admission limits are:

- input and every post-action image: at most 8,000,000 pixels;
- estimated rolling image buffers: at most 67,108,864 bytes per action;
- wall deadline: 15 seconds, followed by bounded worker termination.

The buffer limit is an admission estimate, not a process-RSS or operating-system
memory cap. Preview blocks the whole request before running any prefix when an
enabled action is unknown, has undeclared reads, or is unsupported. Blocked
built-ins are Blender, Copy, Delete Tags, Geek, Geotag, ImageMagick, Lossless
JPEG, Rename, Rename Tag, Save Tags, Tamogen, Time Shift, and Write Tag. A single
Save is accepted only as the final enabled action and is then omitted. Background
in Image mode, Highlight, Mask, Text, and Watermark require a resolvable declared
image resource.

## Action-list history

Undo and Redo restore the complete action document and selected action. New and
successfully opened documents start fresh history. Saving does not erase history;
it updates the clean checkpoint, so Undo can move back through the saved state
and Redo can move forward again. A new edit after Undo discards the redo branch.
This document history is separate from `File > Open Recent`.

When focus is in a text control with native local history, Undo or Redo acts on
that text first. Otherwise the active valid action editor is committed before
document history is traversed; invalid or cancelled editor content is discarded.

## Keyboard shortcuts

| Command | macOS | Ubuntu/Linux |
| --- | --- | --- |
| Undo action-list edit | Command-Z | Ctrl-Z |
| Redo action-list edit | Command-Shift-Z | Ctrl-Shift-Z or Ctrl-Y |

Preview has no keyboard shortcut. Use `Tools > Preview...` and its explicit
`Refresh` button.

## Starter workflows

| Workflow ID | Packaged recipe | Result and safety contract |
| --- | --- | --- |
| resize-export | resize.phatch | Scale/export copies under `Desktop/phatch`; originals stay unchanged. |
| crop-scale | crop_scale.phatch | Crop 10 px per edge, fit within 60 x 60, export PNG copies under `_phatch-crop-scale`. |
| watermark | watermark.phatch | Apply packaged `watermark.png`, export PNG copies under `_phatch-watermark`. |
| metadata-preserving-export | metadata_preserving_export.phatch | Export tag copies under `_phatch-metadata`; requires optional `legacy-metadata`/pyexiv2 capability. |
| web-size-export | web_size_export.phatch | Scale down within 96 x 96, optimize PNG copies under `_phatch-web`. |
| droplet-resize | resize.phatch | Reuse resize through `phatch-gui --droplet`; originals stay unchanged. |

The recipes are package resources in `phatch_assets/data/actionlists`. The
watermark alias resolves the packaged fixture rather than a path relative to the
current directory. Check capability status before the metadata workflow:

```bash
phatch --capabilities --report-format json
phatch --dry-run --report-format json \
  metadata_preserving_export.phatch input.jpg
phatch-gui --droplet resize.phatch input.jpg
```

The metadata recipe reports unavailable capability with exit code 3 when
pyexiv2 is absent; it does not claim metadata preservation without that provider.
Existing outputs are not overwritten when `--keep` is used and are reported as
`skipped`.

## Report v2 migration

Use report v2 for all automation. Version 2 is the default, but pinning it makes
the consumer contract explicit:

```bash
phatch --report-version 2 --report-format json actions.phatch input.jpg
```

The top-level execution keys are `report_version`, `outcome`,
`elapsed_seconds`, `counts`, `files`, and `issues`. Counts contain `processed`,
`skipped`, `failed`, `cancelled`, and `total`. Every file has `source`, its
terminal outcome, `cancellation`, `rollback`, and `outputs`; every output has
`path` and `survived`. Only `survived: true` records represent outputs retained
on disk.

Do not offer or depend on a v1 compatibility mode:

```bash
# Rejected with validation exit code 2; JSON output is still a v2 error document.
phatch --report-version 1 --report-format json actions.phatch input.jpg
```

Known roots are replaced with `<action-list>`, `<input>`, `<output>`, `<home>`,
or `<temp>`; credentials and selected metadata values become `<redacted>`.
These stable placeholders make reports safe audit views, but also mean report
paths are deliberately not reusable filesystem manifests. Keep the original CLI
paths for subsequent file operations. Exit codes remain 0 success, 1 partial
success, 2 validation failure, 3 unavailable capability, 4 processing failure,
and 130 user cancellation.

## Ubuntu 24.04 user-local installation

The GUI extra may build wxPython from source on Ubuntu. Install the stable native
build prerequisites first. This is a user-local Phatch install; only `apt`
requires administrator access:

```bash
sudo apt update
sudo apt install -y build-essential desktop-file-utils freeglut3-dev \
  libcurl4-openssl-dev libgl1-mesa-dev libglu1-mesa-dev libgtk-3-dev \
  libjpeg-dev libnotify-dev libpng-dev libsecret-1-dev libsdl2-dev \
  libtiff-dev libwebkit2gtk-4.1-dev python3-dev
```

Install from an authorized local candidate checkout. Keep the quotes: this
example intentionally uses a prefix containing a space. Do not replace the local
path with a nonexistent 0.5 tag or remote URL.

```bash
SOURCE_CHECKOUT="/absolute/path/to/local/phatch-checkout"
INSTALL_ROOT="$HOME/.local/Phatch 0.5"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

uv venv --python 3.12 "$INSTALL_ROOT"
uv pip install --python "$INSTALL_ROOT/bin/python" "$SOURCE_CHECKOUT[gui]"
"$INSTALL_ROOT/bin/phatch" --help
"$INSTALL_ROOT/bin/phatch-gui" --help
```

If a separately authorized candidate wheel is supplied, install that local file
plus the GUI dependency instead; no candidate wheel is published remotely:

```bash
CANDIDATE_WHEEL="/absolute/path/to/local/Phatch-candidate.whl"
uv pip install --python "$INSTALL_ROOT/bin/python" \
  "$CANDIDATE_WHEEL" "wxPython>=4.2.3"
```

A wxPython source build is CPU- and disk-intensive. Allow several gigabytes of
free disk and use the build tool's default parallelism; large RAM allocations are
not a Phatch runtime requirement. If the build is killed, reduce build
parallelism rather than assuming a 31 GB memory requirement.

### Install the desktop launcher and icon

Desktop Entry `Exec` is not a shell command: `$HOME` is not expanded there.
`desktop-file-install` therefore writes the already-resolved, quoted absolute
executable path. `%U` remains outside the quotes as the Desktop Entry URL/file
placeholder.

```bash
install -d "$XDG_DATA_HOME/applications" \
  "$XDG_DATA_HOME/icons/hicolor/scalable/apps"
install -m 0644 \
  "$SOURCE_CHECKOUT/phatch_assets/images/icons/scalable/phatch.svg" \
  "$XDG_DATA_HOME/icons/hicolor/scalable/apps/phatch.svg"
desktop-file-install --dir="$XDG_DATA_HOME/applications" \
  --set-key=Exec --set-value="\"$INSTALL_ROOT/bin/phatch-gui\" %U" \
  "$SOURCE_CHECKOUT/linux/phatch.desktop"
desktop-file-validate "$XDG_DATA_HOME/applications/phatch.desktop"
update-desktop-database "$XDG_DATA_HOME/applications"
```

The installed launcher is named `Phatch PHoto bATCH Processor`. Test resource
lookup independently of the checkout working directory:

```bash
(cd /tmp && gtk-launch phatch)
```

This opens a native GUI in the active graphical session. For an automated probe,
record the PID started by that command and stop only that owned Phatch instance;
never kill an unrelated user window.

### Uninstall the user-local candidate

Close the candidate instance, then remove exactly the prefix, launcher, and icon
created above:

```bash
rm -rf "$INSTALL_ROOT"
rm -f "$XDG_DATA_HOME/applications/phatch.desktop"
rm -f "$XDG_DATA_HOME/icons/hicolor/scalable/apps/phatch.svg"
update-desktop-database "$XDG_DATA_HOME/applications"
```

This does not remove source checkouts, images, action lists, or another Phatch
installation. User settings and caches are also retained; remove them only after
backing up anything needed.

### Ubuntu troubleshooting

- `gtk-launch: no such application`: run `desktop-file-validate`, confirm
  `$XDG_DATA_HOME/applications/phatch.desktop` exists, and rerun
  `update-desktop-database` with the same `XDG_DATA_HOME`.
- `phatch-gui` cannot import `wx`: install the apt prerequisites above and rerun
  the quoted `uv pip install` command. A headless console install does not prove
  GUI readiness.
- Blank or unavailable GUI over SSH: `gtk-launch` needs the active desktop's
  display and D-Bus session. A tty-only SSH session is not native GUI evidence.
- Wayland may block synthetic physical-key injection. This limits automation
  evidence; it does not change the native wx accelerator mapping. Native wx
  event tests remain required.
- Optional actions show `[Unavailable]` with their missing capability, while a
  separate preview badge explains whether preview is supported or blocked.

## Platform status

| Platform | Available artifact/input | Verification truth |
| --- | --- | --- |
| Ubuntu 24.04 | Source or local candidate wheel | Task 20 verified |
| macOS 14+ Apple silicon | Published 0.4.0 ZIP | Ad-hoc signed |
| Windows | Source only | Native 0.5 verification deferred |

The published macOS 0.4.0 application is ad-hoc signed, not Developer ID signed
or notarized. No Intel Mac, Windows binary, Linux binary, Mint, or other Linux
distribution is claimed by the 0.5 candidate verification. See
[`release_gate.md`](release_gate.md) for the release gate and historical scope,
and [`action_list_schema.md`](action_list_schema.md) for the complete automation
schema.
