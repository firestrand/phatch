from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from phatch.lib.image_process import ImageProcessPaths

Value = str | int | float | bool
Values = Mapping[str, Value]
EffectBuilder = Callable[[ImageProcessPaths, Values], tuple[str, ...]]


def _value(values: Values, name: str) -> str:
    return str(values[name])


def _edge(paths: ImageProcessPaths, _values: Values) -> tuple[str, ...]:
    source = str(paths.input)
    return (
        "-fx",
        "A",
        "+matte",
        "-blur",
        "0x6",
        "-shade",
        "110x30",
        "-normalize",
        source,
        "-compose",
        "Overlay",
        "-composite",
        source,
        "-matte",
        "-compose",
        "Dst_In",
        "-composite",
    )


def _blur(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return ("-blur", f"{_value(values, 'blur_radius')}x{_value(values, 'blur_sigma')}")


def _bullet(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return (
        "-matte",
        "(",
        "+clone",
        "-channel",
        "A",
        "-separate",
        "+channel",
        "-negate",
        "-bordercolor",
        "black",
        "-border",
        _value(values, "border"),
        "-blur",
        f"0x{_value(values, 'blur1')}",
        "-shade",
        _value(values, "shade"),
        "-normalize",
        "-blur",
        f"0x{_value(values, 'blur2')}",
        "-fill",
        _value(values, "color"),
        "-tint",
        "100",
        ")",
        "-gravity",
        "center",
        "-compose",
        "Atop",
        "-composite",
    )


def _charcoal(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return ("-charcoal", _value(values, "charcoal_radius"))


def _motion_blur(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    geometry = (
        f"{_value(values, 'blur_radius')}x{_value(values, 'blur_sigma')}"
        f"+{_value(values, 'blur_angle')}"
    )
    return (
        "-motion-blur",
        geometry,
    )


def _pencil(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    geometry = (
        f"{_value(values, 'sketch_radius')}x{_value(values, 'sketch_sigma')}"
        f"+{_value(values, 'sketch_angle')}"
    )
    return (
        "-colorspace",
        "gray",
        "-sketch",
        geometry,
    )


def _paint(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return ("-paint", _value(values, "paint_radius"))


def _polaroid(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    caption = _value(values, "caption")
    caption_options = (
        ("-caption", caption, "-gravity", "center") if caption.strip() else ()
    )
    return (
        *caption_options,
        "-bordercolor",
        _value(values, "border_color"),
        "-background",
        _value(values, "shadow_color"),
        "+polaroid",
    )


def _shadow(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    geometry = (
        f"{_value(values, 'blur_radius')}x{_value(values, 'blur_sigma')}"
        f"+{_value(values, 'horizontal_offset')}"
        f"+{_value(values, 'vertical_offset')}"
    )
    return (
        "(",
        "+clone",
        "-background",
        _value(values, "shadow_color"),
        "-shadow",
        geometry,
        ")",
        "+swap",
        "-background",
        "none",
        "-layers",
        "merge",
        "+repage",
    )


def _sharpen(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return (
        "-sharpen",
        f"{_value(values, 'sharpen_radius')}x{_value(values, 'sharpen_sigma')}",
    )


def _contrast(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return (
        "-sigmoidal-contrast",
        f"{_value(values, 'contrast_factor')},{_value(values, 'contrast_treshold')}%",
    )


def _unsharp(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return (
        "-unsharp",
        f"{_value(values, 'unsharp_radius')}x{_value(values, 'unsharp_sigma')}",
    )


def _wave(_paths: ImageProcessPaths, values: Values) -> tuple[str, ...]:
    return ("-wave", f"{_value(values, 'wave_height')}x{_value(values, 'wave_length')}")


BUILDERS: dict[str, EffectBuilder] = {
    "3D Edge": _edge,
    "Blur": _blur,
    "Bullet": _bullet,
    "Charcoal": _charcoal,
    "Motion Blur": _motion_blur,
    "Pencil Sketch": _pencil,
    "Paint": _paint,
    "Polaroid": _polaroid,
    "Shadow": _shadow,
    "Sharpen": _sharpen,
    "Sigmoidal Contrast": _contrast,
    "Unsharp": _unsharp,
    "Wave": _wave,
}


def build_argv(
    effect: str,
    executable: Path,
    paths: ImageProcessPaths,
    values: Values,
) -> tuple[str, ...]:
    middle = BUILDERS[effect](paths, values)
    if effect == "Polaroid":
        caption_count = 4 if _value(values, "caption").strip() else 0
        return (
            str(executable),
            *middle[:caption_count],
            str(paths.input),
            *middle[caption_count:],
            str(paths.output),
        )
    return (str(executable), str(paths.input), *middle, str(paths.output))
