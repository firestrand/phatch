import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from phatch.core.action_registry import RegisteredAction, RegistryField
from phatch.services.action_schema import (
    ActionDocument,
    ActionField,
    ActionSchemaCatalog,
    ActionSpec,
    RegistrySchemaCatalog,
    SchemaValidationError,
    construct_document_actions,
    migrate_action_list,
    normalize_identifier,
    parse_action_list,
    serialize_action_list,
    validate_document_fields,
)


class FixtureCatalog(ActionSchemaCatalog):
    def __init__(self) -> None:
        self.accesses = 0

    def action_id(self, label: str) -> str | None:
        self.accesses += 1
        return {"Scale": "scale"}.get(label)

    def action_label(self, action_id: str) -> str | None:
        return {"scale": "Scale"}.get(action_id)

    def field_id(self, action_id: str, label: str) -> str | None:
        labels = {
            "Canvas Height": "canvas_height",
            "Canvas Width": "canvas_width",
            "Constrain Proportions": "constrain_proportions",
            "Resample Image": "resample_image",
            "Resolution": "resolution",
            "Scale Down Only": "scale_down_only",
            "__enabled__": "enabled",
        }
        return labels.get(label) if action_id == "scale" else None

    def field_label(self, action_id: str, field_id: str) -> str | None:
        fields = {
            "canvas_height": "Canvas Height",
            "canvas_width": "Canvas Width",
            "constrain_proportions": "Constrain Proportions",
            "resample_image": "Resample Image",
            "resolution": "Resolution",
            "scale_down_only": "Scale Down Only",
            "enabled": "__enabled__",
        }
        return fields.get(field_id) if action_id == "scale" else None


@pytest.mark.parametrize("fixture", ["schema_1.phatch", "schema_2.phatch"])
def test_legacy_golden_migrates_idempotently(fixture: str) -> None:
    # Given
    source = Path("tests/fixtures/actionlists", fixture).read_text(encoding="utf-8")
    catalog = FixtureCatalog()

    # When
    migrated = migrate_action_list(parse_action_list(source), catalog)
    round_tripped = migrate_action_list(
        parse_action_list(serialize_action_list(migrated)), catalog
    )

    # Then
    assert migrated == round_tripped
    assert migrated.schema_version == 3
    assert migrated.actions[0].action_id == "scale"
    assert migrated.actions[0].fields[0].field_id == "canvas_height"


def test_schema_rejects_unknown_keys_before_catalog_access() -> None:
    # Given
    catalog = FixtureCatalog()
    source = json.dumps(
        {
            "schema_version": 3,
            "description": "bad",
            "actions": [],
            "execute": "__import__('os').system('bad')",
        }
    )

    # When / Then
    with pytest.raises(SchemaValidationError, match="unknown document key"):
        migrate_action_list(parse_action_list(source), catalog)
    assert catalog.accesses == 0


def test_schema_rejects_executable_legacy_expression() -> None:
    # Given
    source = "__import__('os').system('bad')"

    # When / Then
    with pytest.raises(SchemaValidationError, match="valid JSON or legacy literal"):
        parse_action_list(source)


def test_current_schema_rejects_unknown_action_and_field_ids() -> None:
    # Given
    catalog = FixtureCatalog()
    unknown_action = ActionDocument.from_values("bad", (("missing", ()),))
    unknown_field = ActionDocument.from_values(
        "bad", (("scale", (("missing", "value"),)),)
    )

    # When / Then
    with pytest.raises(SchemaValidationError, match="unknown action ID"):
        migrate_action_list(unknown_action, catalog)
    with pytest.raises(SchemaValidationError, match="unknown field ID"):
        migrate_action_list(unknown_field, catalog)


def test_legacy_schema_rejects_unknown_action_and_field_labels() -> None:
    catalog = FixtureCatalog()
    unknown_action = parse_action_list(
        '{"format_version":"2.0","actions":[{"label":"Missing","fields":{}}]}'
    )
    unknown_field = parse_action_list(
        '{"format_version":"2.0","actions":'
        '[{"label":"Scale","fields":{"Missing":"1"}}]}'
    )

    with pytest.raises(SchemaValidationError, match="unknown legacy action label"):
        migrate_action_list(unknown_action, catalog)
    with pytest.raises(SchemaValidationError, match="unknown field label"):
        migrate_action_list(unknown_field, catalog)


def test_catalog_without_descriptor_validation_reports_no_invalid_fields() -> None:
    document = ActionDocument.from_values(
        "", (("scale", (("canvas_width", "100"),)),)
    )

    assert validate_document_fields(document, FixtureCatalog()) == ()


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("[]", "must be an object"),
        ('{"schema_version": 4, "description": "", "actions": []}', "unsupported"),
        ('{"schema_version": 3, "description": 1, "actions": []}', "description"),
        ('{"schema_version": 3, "description": "", "actions": [1]}', "action"),
        (
            '{"schema_version": 3, "description": "", "actions": '
            '[{"id": "Bad", "fields": {}}]}',
            "action ID",
        ),
        (
            '{"schema_version": 3, "description": "", "actions": '
            '[{"id": "scale", "fields": []}]}',
            "fields",
        ),
        (
            '{"schema_version": 3, "description": "", "actions": '
            '[{"id": "scale", "fields": {"bad-id": "1"}}]}',
            "field IDs",
        ),
        ('{"version": "9", "actions": []}', "legacy action-list version"),
        ('{"format_version": "9", "actions": []}', "legacy action-list format"),
        ('{"format_version": "2.0", "actions": 1}', "legacy description"),
        ('{"format_version": "2.0", "actions": [1]}', "legacy action"),
        (
            '{"format_version": "2.0", "actions": [{"label": 1, "fields": {}}]}',
            "legacy action label",
        ),
        (
            '{"format_version": "2.0", "actions": '
            '[{"label": "Scale", "fields": {"Width": 1}}]}',
            "legacy field values",
        ),
    ],
)
def test_schema_parser_rejects_invalid_document_shapes(
    source: str, message: str
) -> None:
    with pytest.raises(SchemaValidationError, match=message):
        parse_action_list(source)


def test_identifier_normalization_handles_enabled_and_invalid_labels() -> None:
    assert normalize_identifier("__enabled__") == "enabled"
    assert normalize_identifier("Canvas Width") == "canvas_width"
    with pytest.raises(SchemaValidationError, match="stable identifier"):
        normalize_identifier("---")


class FakeAction:
    def __init__(self) -> None:
        self._fields: Mapping[str, RegistryField] = {"Canvas Width": FakeField()}
        self.invalid: list[str] = []
        self.loaded: Mapping[str, str] | None = None

    @property
    def label(self) -> str:
        return "Scale"

    @property
    def tags(self) -> tuple[str, ...]:
        return ()

    @property
    def metadata(self) -> tuple[str, ...]:
        return ()

    @property
    def valid_last(self) -> bool:
        return False

    def _get_fields(self):
        return self._fields

    def load(self, fields: Mapping[str, str]) -> list[str]:
        self.loaded = fields
        return self.invalid

    def init(self):
        return None

    def is_done(self):
        return False

    def is_enabled(self) -> bool:
        return True

    def is_overwrite_existing_images_forced(self) -> bool:
        return False

    def apply(self):
        return None

    def dump(self):
        return {}


class FakeField:
    def get_as_string(self):
        return ""

    def set_as_string(self, value):
        return None


class FakeRegistry:
    def __init__(self, *, fails: bool = False):
        self.value = FakeAction()
        self.fails = fails
        self.instantiations = 0

    @property
    def fields(self):
        return {"Scale": self.value._fields}

    def labels(self):
        return ("Scale",)

    def instantiate(self, label: str) -> RegisteredAction:
        self.instantiations += 1
        if self.fails:
            raise TypeError(label)
        return self.value


class InvalidFieldCatalog(FixtureCatalog):
    def invalid_fields(self, spec: ActionSpec) -> tuple[str, ...]:
        return ("canvas_width",)


class IncompleteAction:
    label = "Scale"
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last = False

    @property
    def _fields(self) -> Mapping[str, RegistryField]:
        return {}

    def load(self, fields: Mapping[str, str]) -> list[str]:
        return []

    def is_enabled(self) -> bool:
        return True

    def is_overwrite_existing_images_forced(self) -> bool:
        return False


class IncompleteRegistry(FakeRegistry):
    def instantiate(self, label: str) -> RegisteredAction:
        return IncompleteAction()


def test_registry_catalog_and_constructor_translate_stable_ids() -> None:
    registry = FakeRegistry()
    catalog = RegistrySchemaCatalog(registry)
    document = ActionDocument.from_values(
        "construct", (("scale", (("canvas_width", "100"),)),)
    )

    actions = construct_document_actions(document, catalog, registry)

    assert catalog.action_id("Scale") == "scale"
    assert catalog.action_id("scale") is None
    assert catalog.field_id("scale", "Canvas Width") == "canvas_width"
    assert catalog.field_id("scale", "canvas_width") is None
    assert actions == (registry.value,)
    assert registry.value.loaded == {"Canvas Width": "100"}


def test_constructor_rejects_unknown_action_and_field_ids() -> None:
    registry = FakeRegistry()
    catalog = RegistrySchemaCatalog(registry)

    with pytest.raises(SchemaValidationError, match="unknown action ID"):
        construct_document_actions(
            ActionDocument.from_values("", (("missing", ()),)), catalog, registry
        )
    with pytest.raises(SchemaValidationError, match="unknown field ID"):
        construct_document_actions(
            ActionDocument(
                3, "", (ActionSpec("scale", (ActionField("missing", "1"),)),)
            ),
            catalog,
            registry,
        )


def test_constructor_validates_entire_document_before_instantiation() -> None:
    registry = FakeRegistry()
    catalog = RegistrySchemaCatalog(registry)
    document = ActionDocument.from_values(
        "", (("scale", (("canvas_width", "100"),)), ("missing", ()))
    )

    with pytest.raises(SchemaValidationError, match="unknown action ID"):
        construct_document_actions(document, catalog, registry)

    assert registry.instantiations == 0


def test_constructor_rejects_descriptor_values_before_instantiation() -> None:
    registry = FakeRegistry()
    document = ActionDocument.from_values(
        "", (("scale", (("canvas_width", "bad"),)),)
    )

    with pytest.raises(SchemaValidationError, match=r"scale\.canvas_width"):
        construct_document_actions(document, InvalidFieldCatalog(), registry)

    assert registry.instantiations == 0


def test_constructor_rejects_invalid_loaded_fields() -> None:
    registry = FakeRegistry()
    registry.value.invalid = ["Canvas Width"]
    catalog = RegistrySchemaCatalog(registry)
    document = ActionDocument.from_values("", (("scale", (("canvas_width", "bad"),)),))

    with pytest.raises(SchemaValidationError, match="invalid fields"):
        construct_document_actions(document, catalog, registry)


def test_constructor_translates_registry_construction_errors() -> None:
    registry = FakeRegistry(fails=True)
    catalog = RegistrySchemaCatalog(registry)
    document = ActionDocument.from_values("", (("scale", ()),))

    with pytest.raises(SchemaValidationError, match="could not construct"):
        construct_document_actions(document, catalog, registry)


def test_constructor_rejects_incomplete_execution_contract() -> None:
    registry = IncompleteRegistry()
    catalog = RegistrySchemaCatalog(registry)
    document = ActionDocument.from_values("", (("scale", ()),))

    with pytest.raises(SchemaValidationError, match="execution contract"):
        construct_document_actions(document, catalog, registry)
