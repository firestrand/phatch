from phatch.pyWx.frame_dependencies import FrameDependencies


def test_action_service_factory_can_be_overridden():
    dependencies = FrameDependencies(action_service_factory=lambda: "service")

    assert dependencies.action_service_factory() == "service"


def test_dialog_service_factory_can_be_overridden():
    dependencies = FrameDependencies(dialog_service_factory=lambda frame: ("dialog", frame))

    assert dependencies.dialog_service_factory("frame") == ("dialog", "frame")
