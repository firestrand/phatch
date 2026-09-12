from io import BytesIO

import pytest
from PIL import Image

from phatch.lib import imtools, thumbnail
from phatch.services.image_output import render_image


@pytest.mark.parametrize("format_name", ["PNG", "JPEG", "TIFF", "GIF"])
def test_format_data_is_decodable_image_bytes(format_name: str) -> None:
    with Image.new("RGB", (32, 16), (12, 34, 56)) as source:
        data = imtools.get_format_data(source, format_name)

        assert isinstance(data, bytes)
        with Image.open(BytesIO(data)) as decoded:
            decoded.load()
            assert decoded.format == format_name
            assert decoded.size == (32, 16)
            assert decoded.convert("RGB").getpixel((0, 0)) == pytest.approx(
                (12, 34, 56), abs=2
            )
        assert source.size == (32, 16)


def test_thumbnail_format_data_encodes_the_resized_image() -> None:
    with Image.new("RGB", (32, 16), "navy") as source:
        data = thumbnail.get_format_data(source, "PNG", (8, 8))

        assert isinstance(data, bytes)
        with Image.open(BytesIO(data)) as decoded:
            decoded.load()
            assert decoded.size == (8, 4)
            assert decoded.getpixel((0, 0)) == (0, 0, 128)
        assert source.size == (32, 16)


def test_metadata_rendering_produces_a_real_encoded_thumbnail() -> None:
    with Image.new("RGB", (320, 160), "navy") as source:
        rendered = render_image(source, "JPEG", None, preserve_metadata=True)

        assert isinstance(rendered.thumbnail_data, bytes)
        with Image.open(BytesIO(rendered.thumbnail_data)) as decoded:
            decoded.load()
            assert decoded.format == "JPEG"
            assert decoded.size == (160, 80)
        assert rendered.image.size == (320, 160)
