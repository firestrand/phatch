# Configured workflow previews

The editor's **Tools → Workflow preview** command opens a modeless before/after
view for a selected image. The view renders the current action parameters,
offers intermediate steps, refreshes after edits, and provides Cancel and
full-resolution crop controls. It runs image processing on an owned worker and
delivers widget updates through [wx.CallAfter](https://docs.wxpython.org/wx.functions.html#wx.CallAfter).
Superseded requests cannot replace newer results, even if an old result is
already queued on the UI event loop.

## Python usage

```python
from phatch import init_config_paths
from phatch.core import api
from phatch.core.workflow_preview import PreviewOptions, PreviewRenderer

init_config_paths()
api.import_actions()
actions = [api.ACTIONS['Invert'](), api.ACTIONS['Save']()]
renderer = PreviewRenderer(cache_bytes=64 * 1024 * 1024)
result = renderer.render('photo.png', actions, PreviewOptions(size=(512, 512)))
if result.status == 'success':
    with result.after.open() as image:
        print(image.size)
```

Results contain PNG pixel payloads for `before`, `after`, and optional `steps`,
plus skipped-action labels, warnings, errors, approximation status, cache
identity and timing. Opening a payload returns a caller-owned image. Mutating
that image cannot change cached results. Preview payloads carry no source
metadata, and rendering creates no normal output files or persistent preview
cache. Font discovery uses a read-only cache option. File dependency resolution is
shared with resume; see [plugin contracts](PLUGIN_CONTRACTS.md).

The renderer takes snapshots of action form parameters. Built-in image
operations are explicitly allowed; Save, source-file operations, metadata
editing, external commands and unsupported custom actions are skipped without
initialization or execution. Their labels remain visible. Save quality, color
and metadata policies therefore require an actual export check. Custom actions
must explicitly declare `preview_safe = True`, implement standard serializable
action forms, and obey the pure, thread-safe preview contract. This declaration
is a plugin contract, not a sandbox for arbitrary plugin code.

## Fidelity, caching and cancellation

The default processes a thumbnail and labels the approximation. Pixel-sized
effects and metadata expressions may differ from a full batch. Use
`PreviewOptions(full_resolution=True)` to process the full source, or supply
`crop=(left, top, right, bottom)` to inspect a full-resolution region. Crop
mode applies the workflow to the complete image before selecting the region;
it does not process an isolated crop as though it were the source. Crop
coordinates apply to each intermediate image, clip at its right/bottom edge,
and fail visibly if their origin is outside a stage. Output display still fits
the requested preview size.

The cache includes source content/timestamp, enabled action parameters,
implementation/dependency identity, preview options, and resolved file/font
resources. Unresolved resource expressions and custom actions disable caching.
Parameter, source and resource changes invalidate applicable entries. The cache
uses a byte bound and evicts old results. Defaults bound source and stage sizes
to 50 million pixels, result payloads to 64 MiB, and workflows to 100 image
steps. These checks do not impose an operating-system memory limit on a plugin
while it is executing.

Supply `cancel` and `progress` callables to `PreviewRenderer.render` for
cooperative cancellation between steps. Cancelled or failed renders are never
cached. An in-flight native operation is not forcibly interrupted. Multiframe
inputs currently show their first frame/page with an explicit warning; the
batch sequence policy is separate from this preview contract. The first
frame/page uses `frameindex=0`, the source frame count, and zero batch/repeat
indexes for parameter and dependency resolution.

`WorkflowPreviewService` in `phatch.services.workflow_preview` provides an
asynchronous adapter with one running job and at most one queued latest job.
Its dispatcher accepts a no-argument callable; `wx.CallAfter` is suitable.
`invalidate()` cancels pending delivery after edits, and `close()` owns worker
shutdown. Use its context manager for synchronous lifecycle ownership, or
`close(wait=False)` during UI teardown to request cooperative cancellation
without blocking the event loop.

## Verification

Tests compare a configured sequence and full-resolution crop with independent
Pillow reference pixels; exercise source/action/resource cache changes,
immutable payloads, byte/pixel bounds, safe expressions and read-only fonts;
and check cancellation, supersession, queued UI races and worker failures.
An actual wx smoke test opens the preview controls, receives a background
result, changes the workflow, refreshes and closes the window.
