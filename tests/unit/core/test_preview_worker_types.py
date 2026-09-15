from __future__ import annotations

import pytest
from PIL import Image

from phatch.services.preview_types import PreviewAdmissionError, PreviewErrorCode
from phatch.services.preview_worker import _layer_image


class _Layer:
    image: Image.Image | None = None


def test_missing_layer_image_raises_typed_worker_failure() -> None:
    with pytest.raises(PreviewAdmissionError) as captured:
        _layer_image(_Layer())

    assert captured.value.code is PreviewErrorCode.WORKER_FAILED
