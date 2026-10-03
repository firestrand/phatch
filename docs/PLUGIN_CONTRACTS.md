# Plugin execution contracts

Phatch's normal action interface remains the form-based Action class with `dump`, `load`, `init` and `apply`. Recipes store the canonical module identity separately from the display label. Custom modules used by workers must be importable and expose their class as `Action`; local classes and nonserializable fields are unsuitable for spawned workers.

## Optional execution modes

Custom plugins opt into these modes with the exact boolean `True`. Each declaration is the plugin author's compatibility contract. It does not sandbox Python code or prevent undeclared side effects.

| Declaration | Required behavior | Engine behavior without it |
| :--- | :--- | :--- |
| `resumable = True` | Deterministic replay with serialized parameters and declared external files; no untracked persistent side effects. | Journaled batches reject the plugin with a manifest diagnostic. Ordinary execution remains available. |
| `preview_safe = True` | Read-only, bounded image transformation; no normal outputs, deletion, subprocesses or persistent state. | Preview skips the plugin and identifies the skipped action. Custom previews remain uncached. |
| `parallel_safe = True` | Independent input processing, importable standard Action class and serializable fields; no shared mutable output state or source overwrite. | Worker setup rejects the plugin. Sequential execution remains available. |
| `sequence_safe = True` | Safe independent application to each decoded frame/page, preserving the Photo ownership contract. | Extract/preserve sequence policies reject the plugin. Explicit first-frame processing remains available. |

Built-in actions have separately audited allowlists and restrictions. A custom declaration does not override sequence encoder limitations, unresolved worker destinations, memory limits or reserved output paths. Keep action parameters stable while a batch is running; change them between invocations.

## External file dependencies

Use `ReadFileField` or its image/font subclasses for files the plugin reads. For a file stored in another form field, declare its label explicitly:

```python
resumable = True
resource_fields = ('Color File',)
```

`resource_fields` is a tuple or list of existing form labels. Every external file that can affect output must be covered. Code-loaded resources, configuration files and helper modules outside the fingerprinted engine/plugin implementation must be exposed by the plugin's dependency contract. Undeclared resources cannot be discovered reliably by the engine.

The shared [resource resolver](../phatch/core/resources.py) resolves simple `<variable>` substitutions using the same source file/root context as execution, including file dates, batch/repeat indexes and selected sequence frame indexes. It resolves bundled dictionary aliases and fonts without writing a font cache. Workers receive copies of the resolved parent dictionaries so alias selection agrees with the parent journal. The resolver supports both legacy and package-qualified form-field classes.

Unknown expressions and geometry that may change during transforms remain unresolved. A journaled input fails with a manifest diagnostic before its running record is written; Safe Mode may reject unknown variables earlier during setup. Use a resolved dependency path, or run without a manifest. Preview disables caching for unresolved dependencies. Resolution performs no action initialization or application and does not evaluate arbitrary expressions; custom field converters remain plugin code and must honor the read-only contract.

Resource content and modification time participate in each input's resume key. A changed input-specific watermark invalidates that input, while unrelated matching inputs can still resume. Repeated/frame-dependent paths are included for every selected repeat and frame. Repeated references to the same file are hashed once within a dependency snapshot, using bounded read chunks. Source and dependencies are checked again before recording completion; changes leave the input incomplete even when outputs already committed.

## Reference and verification

The importable [resource fixture plugin](../tests/fixtures/resource_action.py) reads a color from a declared text-file field and changes pixels without writing persistent state. Tests exercise it in normal execution, manifest resume, actual spawned workers, previews, frame extraction and sequence preservation. Its use of filesystem reads is intentional; the engine trusts the declaration rather than substituting a security boundary.

[Resume tests](../tests/unit/core/test_manifests.py) cover per-input watermark expressions, repeat/frame dependencies, alias/font changes, missing resources, invalid declarations and changes during serial/worker processing. [Preview tests](../tests/unit/core/test_workflow_preview.py) cover the same shared resolver's read-only behavior and cache invalidation. See [batch processing](BATCH_PROCESSING.md), [workers](BATCH_WORKERS.md), [previews](WORKFLOW_PREVIEWS.md) and [sequence policies](IMAGE_SEQUENCES.md) for mode-specific limits.
