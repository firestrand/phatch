from phatch.services.action_schema import ActionDocument
from phatch.services.parallel_save import parallel_constraint


def test_dynamic_index_naming_explicitly_stays_serial() -> None:
    document = ActionDocument.from_values(
        "",
        (("save", (("file_name", "<filename>-<index>"),)),),
    )

    constraint = parallel_constraint(document)

    assert constraint == "parallel Save does not support dynamic variables: index"


def test_non_save_action_set_explicitly_stays_serial() -> None:
    document = ActionDocument.from_values("", (("scale", ()),))

    assert parallel_constraint(document) == (
        "parallel execution requires exactly one enabled Save action"
    )
