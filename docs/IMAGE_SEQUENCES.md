# Animation and multipage policies

Batch processing rejects multiframe input by default. Choose an explicit animation or page policy to avoid accidentally discarding content. Existing single-frame workflows continue normally.

## Select a policy

The Save action exposes Animation Policy and Page Policy controls. Variants exposes the compatible reject, first and extract choices. Their default, inherit, uses batch settings; an unspecified batch setting resolves to reject. Explicit batch settings override recipe controls. Conflicting explicit recipe controls fail preflight.

```python
from phatch.core.batch import run_batch

result = run_batch(
    actions,
    ['animation.gif', 'document.tiff'],
    {'animation_policy': 'preserve', 'page_policy': 'extract'},
)
```

```bash
phatch --console --animation-policy preserve recipe.phatch animation.gif
phatch --console --page-policy extract recipe.phatch document.tiff
```

| Policy | Behavior |
| :--- | :--- |
| reject | Reject multiframe input before action initialization or output creation. |
| first | Process the first frame/page and report discarded content as a warning. |
| extract | Process every frame/page independently and append `-frame-0000`, `-frame-0001`, etc. to output names. |
| preserve | Apply compatible transforms to every frame/page, then commit a supported sequence as one atomic output. |

The `<frameindex>` and `<framecount>` variables are available to action expressions. Extraction suffixes apply even when a filename expression already includes an index. Preflight lists all extraction destinations, including per-frame variant association manifests.

## Preservation contracts

Supported animation outputs are GIF, APNG, WebP and AVIF. Multipage preservation uses TIFF and permits different page dimensions. Animation frames must have consistent dimensions after transforms.

Pillow decodes composited frames, including transparency and disposal effects. Transforms process those rendered frames. GIF disposal codes and APNG blend/disposal settings are normalized to replace full frames, preserving rendered playback rather than reproducing original delta-frame encoding. WebP lossless is useful when exact pixels matter; lossy encoders retain their normal fidelity limits.

Frame/page count, dimensions, animation duration and loop count are checked by reopening the temporary output before commit. An encoder that merges frames or changes timing causes a visible failure and preserves the previous target. GIF requires durations divisible by 10 milliseconds. AVIF encoding does not expose loop-count preservation, so inputs carrying a loop count cannot be preserved as AVIF. A separate APNG poster image requires APNG output. These incompatible requests fail rather than silently discard sequence semantics.

Preserve and extract accept the audited image-transform actions and Save. Variants supports extraction; sequence-preserving variants remain unsupported. External commands and source-modifying actions are rejected for these policies. A custom action can explicitly declare `sequence_safe = True`, accepting responsibility for retaining the incoming Photo object and processing independently per frame; this is a compatibility contract, not a security sandbox.

The [shared export metadata and color policies](EXPORT_POLICIES.md) apply during encoding. TIFF EXIF/XMP and profiles are independent per page, including pages without profiles. Native compressed TIFF cannot retain nested EXIF/GPS directories; appended pages cannot retain them even uncompressed because the encoder does not relocate their offsets. Those requests fail with a remedy before replacing the target. Page extraction retains supported nested tags in separate files.

Animation metadata is container-scoped: the first frame supplies it, and differing later-frame metadata is reported. Different preserved ICC profiles fail with a convert-to-sRGB remedy. Each frame can be converted to sRGB before encoding into the shared color space.

## Resource ownership, failure and resume

Default limits are 1,000 frames/pages and 256 MiB of decoded RGBA-equivalent source pixels, configurable through `max_sequence_frames` and `sequence_memory_bytes`. The pixel budget is checked before loading each frame. It is not a hard limit on total process memory; transforms, codec buffers and export copies consume additional memory.

Cancellation is checked during decoding, between frame transforms and before frame preparation. A running native encoder completes before control returns. Preserved outputs commit as one transaction. Extracted outputs commit individually; earlier committed files remain reported if a later frame fails or is cancelled.

Resume journals fingerprint all committed extracted files or the preserved sequence. Missing or changed outputs invalidate resume. Sequence policies and resource settings participate in job identity. Direct Photo construction rejects multiframe input unless an explicit frame index is supplied; the batch API provides the complete policy contract.

Format behavior follows the [Pillow file-format documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html). Runtime codec availability still depends on the installed Pillow build.
