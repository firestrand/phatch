# Named image variants

The Variants action exports independent size and format branches from the incoming image. Earlier effects apply to every branch; each branch resizes the same incoming pixels rather than a previously reduced output.

## Python usage

```python
from phatch.core.batch import plan_batch, run_batch
from phatch.core.variants import Variant, variant_action

action = variant_action(
    [
        Variant('thumbnail', 320, 320, 'webp'),
        Variant('article', 1280, 1280, 'avif', quality=55),
    ],
    'exports',
)
plan = plan_batch([action], ['photo.jpg'])
if plan.valid:
    result = run_batch([action], ['photo.jpg'])
```

Width and height are maximum bounds with aspect ratio preserved. No-upscale is enabled by default; set `no_upscale=False` explicitly to enlarge smaller images. Names must contain 1–64 ASCII letters, digits, underscores or hyphens, beginning with a letter or digit. Custom definitions use a JSON list in the action's Variants field, limited to 100 branches and 64 KiB.

## Publishing preset

The web preset generates small, medium and large branches bounded by 640, 1280 and 1920 pixels, each in WebP and AVIF. WebP quality is 80; AVIF quality is 55. All branches default to sharing metadata and sRGB conversion. These are reviewable defaults, with no claim of optimal compression. The bundled recipe is [web_variants.phatch](../data/actionlists/web_variants.phatch).

Both encoders must be available unless Format Fallback is explicitly set to PNG. Fallback changes the planned and actual extension to `.png` and emits a warning. Untagged source color cannot be recovered; the shared export policy reports that limitation.

## Outputs, collisions and resume

The default names are `<filename>-<variant-name>.<format>` and `<filename>-variants.json`. Collision Policy inherits the batch setting or explicitly selects skip, fail, replace or rename. Preflight includes image and JSON destinations and detects conflicts with reports and journals. Dynamic filename expressions can remain unresolved during preflight.

The optional JSON association manifest records source name and fingerprint, each definition, dimensions, encoder, status and actual committed basename. A skipped branch records the requested dimensions and encoder; it does not certify the existing file's contents. The manifest is committed after all branches finish. It appears in `FileResult.artifacts`; image paths appear in `FileResult.outputs`.

Each file has its own atomic transaction. A later branch or manifest failure leaves earlier committed images intact and reports partial failure. Cancellation between branches retains completed outputs and omits the association manifest. The batch resume journal verifies both image and association-manifest fingerprints; a missing or changed artifact invalidates resume.

## Current boundaries

The action requires the real Photo layer/save contract. Custom callers should use the batch API. Output name fields cannot contain directory components; use In for the directory. Animation and page preservation remain separate unfinished backlog work. Installed-resource and supported GUI checks remain part of the final integration audit.
