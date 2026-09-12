from phatch.pyWx.frame_dependencies import FrameDependencies


def test_action_service_factory_can_be_overridden():
    dependencies = FrameDependencies(action_service_factory=lambda: "service")

    assert dependencies.action_service_factory() == "service"


def test_dialog_service_factory_can_be_overridden():
    dependencies = FrameDependencies(dialog_service_factory=lambda frame: ("dialog", frame))

    assert dependencies.dialog_service_factory("frame") == ("dialog", "frame")


def test_application_dependencies_retain_action_registry():
    registry = object()

    dependencies = FrameDependencies.for_action_registry(registry)

    assert dependencies.action_service_factory().registry is registry
