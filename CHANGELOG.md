# Changelog

## Unreleased

### Added

- Atomic image and recipe writes with skip, fail, replace and deterministic rename collision policies.
- Validated JSON and legacy literal recipes, stable plugin identities, bounded parsing and actionable diagnostics.
- Structured batch results, output preflight, dry-run planning, JSON reports and documented console exit codes.
- Native metadata preservation, stripping, selected tags and sharing policies, with independent ICC preservation or sRGB conversion.
- WebP quality/lossless/effort and AVIF quality/speed controls, runtime codec diagnostics and explicit PNG fallback.
- Verified batch resume journals that track source, recipe, settings, plugin, resource and output fingerprints.
- Configured workflow previews with intermediate steps, full-resolution crop checks, cancellation and asynchronous desktop rendering.
- Named size/format variants, no-upscale controls, source association manifests and an opt-in web publishing recipe.
- Explicit animation and multipage reject, first, extract and supported preservation policies.
- Opt-in bounded process workers with parent-owned progress, cancellation and journals, memory admission limits and registered-output crash recovery. Local benchmark results document throughput and memory tradeoffs.

### Changed

- Require Python 3.12 or later, Pillow 11.3 or later and Rich 13 or later. Desktop support is optional through the `gui` extra and requires wxPython 4.2.3 or later.
- Move package metadata to `pyproject.toml`, include services and installed resources, provide the `phatch` console entry point and lock development tools with uv.
- Keep filename-based collision skips separate from verified resume: jobs with skipped planned destinations remain incomplete in the journal.
- Reject destinations overlapping resolved workflow resources before writing images, manifests or reports.

### Fixed

- Preserve existing targets when encoding, metadata finalization or validation fails; clean up only owned temporary files.
- Preserve normalized orientation, final dimensions and supported per-page TIFF metadata/profile policies. Unsupported compressed or appended TIFF subdirectories fail explicitly before commit.
- Avoid shared multiprocessing queue and cancellation-lock stalls after worker crashes.
- Resolve installed fonts, presets, legacy configuration imports and spawned console imports in fresh profiles.
- Replace removed Pillow resampling and image-math APIs used by existing actions.
- Record actual frame-suffixed paths for skipped extracted variants and bound rename preflight to the atomic commit limit.

Compatibility results and platform/backend limits are documented in [Installation and compatibility verification](docs/COMPATIBILITY.md), [Export policies](docs/EXPORT_POLICIES.md) and [Worker guarantees](docs/BATCH_WORKERS.md). This entry does not announce a release or change the package version.
