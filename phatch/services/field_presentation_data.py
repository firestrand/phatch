# ruff: noqa: E501

from __future__ import annotations

from types import MappingProxyType
from typing import Final

_ACTION_FIELD_DATA: Final = {
    "auto_contrast": "amount=Amount|cutoff=Cutoff",
    "background": "color=Color|fill=Fill|horizontal_justification=Horizontal Justification|horizontal_offset=Horizontal Offset|mark=Mark|method=Method|offset=Offset|opacity=Opacity|orientation=Orientation|position=Position|vertical_justification=Vertical Justification|vertical_offset=Vertical Offset",
    "blender": "auto_crop=Auto Crop|background=Background|background_color=Background Color|box_color=Box Color|box_depth=Box Depth|camera=Camera|camera_distance=Camera Distance|camera_horizontal_rotation=Camera Horizontal Rotation|camera_lens_angle=Camera Lens Angle|camera_roll=Camera Roll|camera_vertical_rotation=Camera Vertical Rotation|cover_color=Cover Color|floor_color=Floor Color|floor_opacity=Floor Opacity|floor_reflection=Floor Reflection|gradient_bottom=Gradient Bottom|gradient_top=Gradient Top|image_size=Image Size|left_page=Left Page|lid_rotation=Lid Rotation|mist=Mist|object=Object|page_mapping=Page Mapping|render_height=Render Height|render_width=Render Width|show_background_options=Show Background Options|show_floor_options=Show Floor Options|stars=Stars|stars_color=Stars Color|transparent_background=Transparent Background|use_floor=Use Floor",
    "border": "border_width=Border Width|bottom=Bottom|color=Color|left=Left|method=Method|opacity=Opacity|right=Right|top=Top",
    "brightness": "amount=Amount",
    "canvas": "align_horizontal=Align Horizontal|align_vertical=Align Vertical|background_color=Background Color|canvas_height=Canvas Height|canvas_width=Canvas Width|opacity=Opacity|resolution=Resolution",
    "color_to_alpha": "color_value=Color Value|select_color_by=Select Color By",
    "colorize": "amount=Amount|black=Black|white=White",
    "common": "amount=Amount|radius=Radius",
    "contour": "contour_color=Contour Color|fill_color=Fill Color|include_image=Include image|offset=Offset|opacity=Opacity|size=Size",
    "contrast": "amount=Amount",
    "convert_mode": "mode=Mode",
    "copy": "file_name=File Name|in=In",
    "crop": "all=All|bottom=Bottom|left=Left|mode=Mode|right=Right|top=Top",
    "delete_tags": "method=Method|tag=Tag",
    "desaturate": "amount=Amount",
    "effect": "amount=Amount|filter=Filter|repeat=Repeat",
    "equalize": "amount=Amount",
    "fit": "align_horizontal=Align Horizontal|align_vertical=Align Vertical|bleed=Bleed|canvas_height=Canvas Height|canvas_width=Canvas Width|resample_image=Resample Image|resolution=Resolution",
    "geek": "allow_as_last_action=Allow as last action|command=Command|verify_input=Verify Input|verify_output=Verify Output|verify_program=Verify Program",
    "geotag": "gps_data_gpx=GPS Data (gpx)|gps_report_csv=GPS Report (csv)|time_shift_seconds=Time Shift (seconds)",
    "grid": "column_line_width=Column Line Width|columns=Columns|line_color=Line Color|line_opacity=Line Opacity|row_line_width=Row Line Width|rows=Rows|scale_to_keep_size=Scale to Keep Size",
    "highlight": "highlight=Highlight|opacity=Opacity|resample_highlight=Resample Highlight",
    "imagemagick": "action=Action|blur_angle=Blur Angle|blur_radius=Blur Radius|blur_sigma=Blur Sigma|border_color=Border Color|caption=Caption|charcoal_radius=Charcoal Radius|color=Color|contrast_factor=Contrast Factor|contrast_treshold=Contrast Treshold|horizontal_offset=Horizontal Offset|paint_radius=Paint Radius|shadow_color=Shadow Color|sharpen_radius=Sharpen Radius|sharpen_sigma=Sharpen Sigma|sketch_angle=Sketch Angle|sketch_radius=Sketch Radius|sketch_sigma=Sketch Sigma|unsharp_radius=Unsharp Radius|unsharp_sigma=Unsharp Sigma|vertical_offset=Vertical Offset|wave_height=Wave Height|wave_length=Wave Length",
    "invert": "amount=Amount",
    "lossless_jpeg": "all=All|angle=Angle|angle_2=Angle |bottom=Bottom|copy=Copy|direction=Direction|direction_2=Direction |file_name=File Name|in=In|left=Left|mode=Mode|preserve_timestamp=Preserve Timestamp|right=Right|show_advanced_options=Show Advanced Options|top=Top|transformation=Transformation|transformation_2=Transformation |update_exif_thumbnail=Update Exif Thumbnail|update_jpeg=Update JPEG|update_orientation_tag=Update Orientation Tag|utility=Utility",
    "mask": "mask=Mask|resample_mask=Resample Mask",
    "maximum": "amount=Amount|radius=Radius",
    "median": "amount=Amount|radius=Radius",
    "minimum": "amount=Amount|radius=Radius",
    "mirror": "direction=Direction",
    "offset": "horizontal_offset=Horizontal Offset|vertical_offset=Vertical Offset",
    "perspective": "auto_crop=Auto Crop|background_color=Background Color|background_opacity=Background Opacity|bottom_shear_factor=Bottom Shear Factor|horizontal_offset=Horizontal Offset|left_shear_angle=Left Shear Angle|projection=Projection|resample_image=Resample Image|right_shear_factor=Right Shear Factor|scale=Scale|top_shear_angle=Top Shear Angle|transpose=Transpose|vertical_offset=Vertical Offset",
    "posterize": "amount=Amount|bits=Bits",
    "rank": "amount=Amount|radius=Radius|rank=Rank",
    "reflection": "background_color=Background Color|background_opacity=Background Opacity|blur_reflection=Blur Reflection|depth=Depth|gap=Gap|opacity=Opacity|scale_method=Scale Method|scale_reflection=Scale Reflection",
    "rename": "file_name=File Name|in=In",
    "rename_tag": "from_exif_iptc=From (Exif, Iptc)|to_exif_iptc=To (Exif, Iptc)",
    "rotate": "amount=Amount|angle=Angle|background_color=Background Color|background_opacity=Background Opacity|expand=Expand|resample_image=Resample Image",
    "round": "background_color=Background Color|bottom_left_corner=Bottom Left Corner|bottom_right_corner=Bottom Right Corner|method=Method|opacity=Opacity|radius=Radius|same_method_for_all_corners=Same Method for All Corners|top_left_corner=Top Left Corner|top_right_corner=Top Right Corner",
    "saturation": "amount=Amount",
    "save": "as=As|file_name=File Name|in=In|jpeg_quality=JPEG Quality|jpeg_size_maximum=JPEG Size Maximum|jpeg_size_tolerance=JPEG Size Tolerance|metadata=Metadata|png_optimize=PNG Optimize|resolution=Resolution|show_type_options=Show Type Options|tiff_compression=TIFF Compression",
    "save_tags": "file_name=File Name|in=In",
    "scale": "canvas_height=Canvas Height|canvas_width=Canvas Width|constrain_proportions=Constrain Proportions|resample_image=Resample Image|resolution=Resolution|scale_down_only=Scale Down Only",
    "shadow": "background_color=Background Color|border=Border|force_background_color=Force Background Color|horizontal_offset=Horizontal Offset|shadow_blur=Shadow Blur|shadow_color=Shadow Color|vertical_offset=Vertical Offset",
    "sketch": "details_degree=Details Degree",
    "solarize": "amount=Amount|treshold=Treshold",
    "tamogen": "canvas_height=Canvas Height|canvas_width=Canvas Width|columns=Columns|fill_folder=Fill Folder|fill_image=Fill Image|fill_type=Fill Type|rows=Rows",
    "text": "color=Color|font=Font|horizontal_justification=Horizontal Justification|horizontal_offset=Horizontal Offset|offset=Offset|orientation=Orientation|position=Position|size=Size|text=Text|vertical_justification=Vertical Justification|vertical_offset=Vertical Offset",
    "time_shift": "change=Change|days=Days|hours=Hours|minutes=Minutes|months=Months|seconds=Seconds|use_exif_datetime=Use exif datetime|years=Years",
    "transpose": "amount=Amount|method=Method",
    "warm_up": "amount=Amount|brighten=Brighten|midtone=Midtone",
    "watermark": "horizontal_justification=Horizontal Justification|horizontal_offset=Horizontal Offset|mark=Mark|method=Method|offset=Offset|opacity=Opacity|orientation=Orientation|position=Position|vertical_justification=Vertical Justification|vertical_offset=Vertical Offset",
    "write_tag": "tag_exif_iptc=Tag (Exif, Iptc)|value=Value",
}


def _parse_fields(value: str) -> tuple[tuple[str, str], ...]:
    parsed: list[tuple[str, str]] = []
    for item in value.split("|"):
        field_id, label = item.split("=", 1)
        parsed.append((field_id, label))
    return tuple(parsed)


ACTION_FIELD_LABELS: Final = MappingProxyType(
    {action_id: _parse_fields(value) for action_id, value in _ACTION_FIELD_DATA.items()}
)


_PERCENTAGE_DATA: Final = {
    "background": "offset:axis|horizontal_offset:width|vertical_offset:height",
    "blender": "render_width:width|render_height:height|box_depth:height",
    "border": "border_width:average|left:width|right:width|top:height|bottom:height",
    "canvas": "canvas_width:width|canvas_height:height",
    "contour": "size:average|offset:average",
    "crop": "all:average|left:width|right:width|top:height|bottom:height",
    "fit": "canvas_width:width|canvas_height:height",
    "grid": "column_line_width:height|row_line_width:width",
    "imagemagick": "horizontal_offset:width|vertical_offset:height|blur_radius:average|blur_sigma:average|charcoal_radius:average|paint_radius:average|sharpen_radius:average|sharpen_sigma:average|sketch_radius:average|sketch_sigma:average|unsharp_radius:average|unsharp_sigma:average|wave_height:average|wave_length:average",
    "lossless_jpeg": "all:average|left:width|right:width|top:height|bottom:height",
    "offset": "horizontal_offset:width|vertical_offset:height",
    "perspective": "horizontal_offset:width|vertical_offset:height",
    "reflection": "depth:height|gap:height",
    "round": "radius:width_plus_half_height",
    "scale": "canvas_width:width|canvas_height:height",
    "shadow": "horizontal_offset:width|vertical_offset:height|border:average",
    "tamogen": "canvas_width:width|canvas_height:height",
    "text": "size:average|offset:axis|horizontal_offset:width|vertical_offset:height",
    "watermark": "offset:axis|horizontal_offset:width|vertical_offset:height",
}


PERCENTAGE_BASES: Final = MappingProxyType(
    {
        (action_id, field_id): basis
        for action_id, value in _PERCENTAGE_DATA.items()
        for field_id, basis in (item.split(":", 1) for item in value.split("|"))
    }
)
