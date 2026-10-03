# Metadata and color export policies

Save and Variants apply metadata and color policies independently. Native
export uses Pillow and does not require pyexiv2.

| Metadata policy | Behavior |
| --- | --- |
| preserve | Retain supported EXIF, XMP and PNG text. Report unsupported payloads. |
| strip | Remove descriptive metadata, including EXIF, XMP and PNG text. |
| selected | Retain named or numeric EXIF tags from Metadata Tags. |
| sharing | Remove location, device identifiers, author/descriptive identifiers, XMP and PNG text. |

The sharing policy is an explicit tag policy, not a guarantee that arbitrary
custom metadata or visible image content contains no identifying information.
The exact removed EXIF tags are defined in
[the export policy module](../phatch/core/export_policy.py).

Preserve color keeps a source ICC profile when the encoder supports it. Strip
and sharing do not discard that profile. Convert-to-sRGB transforms tagged pixels
through ImageCms and embeds sRGB, retaining alpha. An untagged source uses an
explicit sRGB assumption reported as a warning. An invalid profile or a profile
incompatible with the output pixel mode fails before the output is committed.

Pixels are normalized for EXIF orientation before processing. Retained EXIF
orientation is rewritten to 1 and dimension tags describe the exported image.
Pillow applies TIFF orientation during decoding; Phatch avoids applying it again.

## Native format support

| Payload | Supported outputs |
| --- | --- |
| EXIF and ICC profile | JPEG, PNG, TIFF, WebP, AVIF |
| XMP | JPEG, PNG, TIFF, WebP, AVIF |
| PNG text | PNG |
| IPTC / Photoshop payloads | Native preservation is unsupported and reported. |

TIFF embedded XMP, IPTC/Photoshop and ICC fields are handled by these dedicated
controls rather than copied around privacy or color policies through EXIF.
Encoder availability is reported by `phatch --console --capabilities`. A build
without a requested encoder needs an explicitly supported format or fallback.

Options and capabilities follow the
[Pillow file-format reference](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
and [ImageCms reference](https://pillow.readthedocs.io/en/stable/reference/ImageCms.html).

## Sequences

TIFF page preservation applies supported EXIF/XMP and ICC options independently
per page. A later page without an ICC profile retains that absence. LZW, ZIP and
PackBits preservation uses native compression; each page's tags and pixels are
verified by round-trip tests.

The native TIFF writer cannot preserve nested EXIF/GPS directories with
compression, or relocate them correctly on appended pages. Requests retaining
those directories fail with a remedy before replacing the target. Use
uncompressed output for nested tags on the first page, choose page extraction
to retain each page's nested tags separately, or choose a metadata policy that
removes the unsupported directories. These restrictions are explicit; Phatch
does not silently write incorrect metadata offsets.

Animation metadata is container-scoped. Phatch uses the first frame's supported
metadata and reports differing metadata on later frames. Different ICC profiles
cannot be preserved in one animation: choose convert-to-sRGB so each frame is
converted into the container's color space. See
[sequence policies](IMAGE_SEQUENCES.md) for playback and resource limits.

## Optional metadata editing adapter

The existing editing adapter expects the legacy `pyexiv2.Image.readMetadata`
API. The [modern pyexiv2 tutorial](https://github.com/LeoHsiao1/pyexiv2/blob/master/docs/Tutorial.md)
documents a different `read_exif` / `modify_exif` API. Installing that package
does not provide Phatch's legacy editing interface. Namespace-only and modern
incompatible imports are rejected as adapters while native exports remain
available; a subprocess regression exercises both cases.

The legacy adapter's native binary integration has not been verified on the
supported Python matrix. It is not a dependency of native export policies.
