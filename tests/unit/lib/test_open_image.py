import importlib
import builtins
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PIL import Image

from phatch.lib import openImage


@pytest.fixture(scope='module', autouse=True)
def available_external_tools():
    with patch.object(
            openImage.system, 'find_exe',
            side_effect=lambda executable, **kwargs: executable):
        importlib.reload(openImage)
    yield
    importlib.reload(openImage)


def test_check_libtiff_accepts_raw_and_rejects_missing_tool(monkeypatch):
    monkeypatch.setattr(openImage, 'open_libtiff', None)

    openImage.check_libtiff('raw')
    with pytest.raises(Exception, match='Libtiff'):
        openImage.check_libtiff('g4')


def test_open_prefers_non_pillow_local_converter(monkeypatch):
    image = SimpleNamespace(info={}, format=None, close=lambda: None)
    monkeypatch.setattr(openImage.system, 'is_www_file', lambda uri: False)
    monkeypatch.setattr(openImage.imtools, 'get_format_filename', lambda uri: 'PNG')
    monkeypatch.setattr(openImage, 'open_image_without_pil', lambda uri, methods: image)

    result = openImage.open('input.png')

    assert result is image
    assert image.format == 'PNG'
    image.close()


def test_open_returns_supported_pillow_image(monkeypatch):
    image = SimpleNamespace(info={}, format='JPEG', close=lambda: None)
    monkeypatch.setattr(openImage.system, 'is_www_file', lambda uri: True)
    monkeypatch.setattr(openImage.imtools, 'get_format_filename', lambda uri: 'JPEG')
    monkeypatch.setattr(openImage, 'open_image_with_pil', lambda uri: image)

    assert openImage.open('https://example.test/image.jpg') is image
    image.close()


def test_open_falls_back_after_pillow_failure(monkeypatch):
    fallback = Image.new('RGB', (2, 2))
    monkeypatch.setattr(openImage.system, 'is_www_file', lambda uri: False)
    monkeypatch.setattr(openImage.imtools, 'get_format_filename', lambda uri: 'TIFF')
    calls = iter([None, fallback])
    monkeypatch.setattr(
        openImage,
        'open_image_without_pil',
        lambda uri, methods: next(calls),
    )
    monkeypatch.setattr(
        openImage,
        'open_image_with_pil',
        lambda uri: (_ for _ in ()).throw(OSError()),
    )

    assert openImage.open('input.tiff') is fallback
    fallback.close()


def test_open_reports_unreadable_remote_image(monkeypatch):
    monkeypatch.setattr(openImage.system, 'is_www_file', lambda uri: True)
    monkeypatch.setattr(openImage.imtools, 'get_format_filename', lambda uri: 'JPEG')
    monkeypatch.setattr(
        openImage,
        'open_image_with_pil',
        lambda uri: (_ for _ in ()).throw(OSError()),
    )

    with pytest.raises(OSError, match='Could not open image'):
        openImage.open('https://example.test/broken.jpg')


def test_open_uses_imtools_when_local_fallback_is_unavailable(monkeypatch):
    class FalseImage:
        def __bool__(self):
            return False

    expected = Image.new('RGB', (2, 2))
    partial = SimpleNamespace(format='PNG', info={'interlace': True})
    fallback = FalseImage()
    monkeypatch.setattr(openImage.system, 'is_www_file', lambda uri: False)
    monkeypatch.setattr(openImage.imtools, 'get_format_filename', lambda uri: 'PNG')
    calls = iter([None, fallback])
    monkeypatch.setattr(
        openImage,
        'open_image_without_pil',
        lambda uri, methods: next(calls),
    )
    monkeypatch.setattr(openImage, 'open_image_with_pil', lambda uri: partial)
    monkeypatch.setattr(openImage.imtools, 'open_image', lambda uri: expected)
    monkeypatch.setattr(openImage.Image, 'VERSION', '1.1.6', raising=False)

    assert openImage.open('input.png') is expected
    expected.close()


def test_exif_open_transposes_image(monkeypatch):
    image = Image.new('RGB', (2, 2))
    monkeypatch.setattr(openImage, 'open', lambda uri: image)
    monkeypatch.setattr(openImage.imtools, 'transpose_exif', lambda value: value)

    assert openImage.open_image_exif('input.jpg') is image
    image.close()


def test_exif_thumbnail_prefers_embedded_data(monkeypatch):
    expected = Image.new('RGB', (1, 1))
    metadata = SimpleNamespace(
        readMetadata=lambda: None,
        getThumbnailData=lambda: b'image-data',
    )
    monkeypatch.setattr(
        openImage,
        'pyexiv2',
        SimpleNamespace(Image=lambda uri: metadata),
    )
    monkeypatch.setattr(openImage.imtools, 'open_image_data', lambda data: expected)

    assert openImage.open_image_exif_thumb('input.jpg') is expected
    expected.close()


@pytest.mark.parametrize('thumbnail_data', [None, RuntimeError('broken')])
def test_exif_thumbnail_falls_back(monkeypatch, thumbnail_data):
    expected = Image.new('RGB', (1, 1))

    def get_thumbnail():
        if isinstance(thumbnail_data, RuntimeError):
            raise thumbnail_data
        return thumbnail_data

    metadata = SimpleNamespace(
        readMetadata=lambda: None,
        getThumbnailData=get_thumbnail,
    )
    monkeypatch.setattr(
        openImage,
        'pyexiv2',
        SimpleNamespace(Image=lambda uri: metadata),
    )
    monkeypatch.setattr(openImage, 'open_image_exif', lambda uri: expected)

    assert openImage.open_image_exif_thumb('input.jpg') is expected
    expected.close()


def test_open_thumb_uses_default_and_explicit_sizes(monkeypatch):
    from phatch.lib import thumbnail

    calls = []
    monkeypatch.setattr(
        thumbnail,
        'open',
        lambda **kwargs: calls.append(kwargs) or 'thumbnail',
    )

    assert openImage.open_thumb('input.jpg') == 'thumbnail'
    assert openImage.open_thumb('input.jpg', size=(32, 32)) == 'thumbnail'
    assert calls[0]['size'] == thumbnail.SIZE
    assert calls[1]['size'] == (32, 32)


def test_open_image_with_pil_uses_libtiff_for_group_compression(monkeypatch):
    source = SimpleNamespace(info={'compression': 'group4'})
    converted = Image.new('1', (2, 2))
    monkeypatch.setattr(openImage.imtools, 'open_image', lambda uri: source)
    monkeypatch.setattr(openImage, 'check_libtiff', lambda compression: None)
    monkeypatch.setattr(openImage, 'open_libtiff', lambda uri: converted)

    assert openImage.open_image_with_pil('input.tiff') is converted
    converted.close()


def test_open_image_with_pil_returns_regular_image(monkeypatch):
    image = Image.new('RGB', (2, 2))
    image.info['compression'] = 'none'
    monkeypatch.setattr(openImage.imtools, 'open_image', lambda uri: image)

    assert openImage.open_image_with_pil('input.png') is image
    image.close()


def test_open_image_without_pil_dispatches_registered_method(monkeypatch):
    registry = SimpleNamespace(
        extensions=['svg'],
        get_methods=lambda extension: [lambda filename: None, lambda filename: 'image'],
    )
    monkeypatch.setattr(openImage.system, 'file_extension', lambda filename: 'svg')

    assert openImage.open_image_without_pil('input.svg', registry) == 'image'
    registry.extensions = []
    assert openImage.open_image_without_pil('input.svg', registry) is None


def test_open_image_with_command_handles_named_output(monkeypatch, tmp_path):
    output = tmp_path / 'input.ppm'
    output.write_bytes(b'pixels')
    image = Image.new('RGB', (1, 1))
    monkeypatch.setattr(openImage.system, 'shell', lambda command: ('', ''))
    monkeypatch.setattr(openImage.Image, 'open', lambda filename: image)

    result = openImage.open_image_with_command(
        str(tmp_path / 'input.raw'), ['tool'], 'tool', temp_ext='ppm')

    assert result is image
    assert not output.exists()
    image.close()


def test_open_image_with_command_reports_missing_output(monkeypatch):
    temp = SimpleNamespace(path='/missing/output.png', close=lambda **kwargs: None)
    monkeypatch.setattr(openImage.system, 'TempFile', lambda extension: temp)
    monkeypatch.setattr(openImage.system, 'shell', lambda command: ('out', 'err'))
    monkeypatch.setattr(builtins, '_', str, raising=False)

    with pytest.raises(OSError, match='Could not open image'):
        openImage.open_image_with_command('input.svg', ['tool'], 'tool')


def test_libtiff_info_parses_fields(monkeypatch):
    output = ' Compression Scheme: LZW\n Image Width: 10 Image Length: 20\n'
    monkeypatch.setattr(openImage.system, 'shell', lambda command: (output, ''))

    result = openImage.get_info_libtiff('input.tiff')

    assert result['compression'] == 'lzw'


def test_libtiff_info_rejects_empty_output(monkeypatch):
    monkeypatch.setattr(openImage.system, 'shell', lambda command: ('', ''))

    with pytest.raises(OSError, match='bad magic'):
        openImage.get_info_libtiff('input.tiff')


def test_open_libtiff_loads_converted_image(monkeypatch):
    image = Image.new('RGB', (2, 2))
    temp = SimpleNamespace(path='/tmp/converted.tiff', close=lambda **kwargs: None)
    monkeypatch.setattr(openImage, 'get_info_libtiff', lambda filename: {'tag': 'value'})
    monkeypatch.setattr(openImage.system, 'TempFile', lambda: temp)
    monkeypatch.setattr(openImage.system, 'shell_returncode', lambda command: 0)
    monkeypatch.setattr(openImage.Image, 'open', lambda filename: image)

    result = openImage.open_libtiff('input.tiff')

    assert result is image
    assert result.info['Convertor'] == 'libtiff'
    image.close()


def test_open_libtiff_reports_conversion_failure(monkeypatch):
    temp = SimpleNamespace(path='/tmp/converted.tiff', close=lambda **kwargs: None)
    monkeypatch.setattr(openImage, 'get_info_libtiff', lambda filename: {})
    monkeypatch.setattr(openImage.system, 'TempFile', lambda: temp)
    monkeypatch.setattr(openImage.system, 'shell_returncode', lambda command: 1)

    with pytest.raises(OSError, match='Could not extract'):
        openImage.open_libtiff('input.tiff')


def test_save_libtiff_uses_pillow_for_raw_compression():
    calls = []
    image = SimpleNamespace(save=lambda *args, **kwargs: calls.append((args, kwargs)))

    assert openImage.save_libtiff(
        image, 'output.tiff', compression='raw', quality=90) == ''
    assert calls == [(('output.tiff', 'tiff'), {'quality': 90})]


@pytest.mark.parametrize(
    ('compression', 'mode'),
    [('g4', 'RGB'), ('jpeg', 'RGBA'), ('tiff_lzw', 'RGB')],
)
def test_save_libtiff_builds_converter_command(
        monkeypatch, compression, mode):
    commands = []
    temp = SimpleNamespace(path='/tmp/input.tiff', close=lambda **kwargs: None)
    converted = SimpleNamespace(
        mode='1',
        info={},
        save=lambda *args, **kwargs: None,
        convert=lambda target: None,
    )
    image = SimpleNamespace(
        mode=mode,
        info={'compression': compression},
        save=lambda *args, **kwargs: None,
        convert=lambda target: converted,
    )
    monkeypatch.setattr(openImage.system, 'TempFile', lambda: temp)
    monkeypatch.setattr(
        openImage.system,
        'shell',
        lambda command: commands.append(command) or ('', ''),
    )

    assert openImage.save_libtiff(
        image, 'output.tiff', compression=compression) == ''
    assert commands


def test_save_libtiff_reports_converter_output(monkeypatch):
    temp = SimpleNamespace(path='/tmp/input.tiff', close=lambda **kwargs: None)
    image = SimpleNamespace(
        mode='RGB',
        info={'compression': 'lzw'},
        save=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(openImage.system, 'TempFile', lambda: temp)
    monkeypatch.setattr(openImage.system, 'shell', lambda command: ('out', 'err'))

    assert 'Subprocess' in openImage.save_libtiff(
        image, 'output.tiff', compression=None)


def test_verify_image_with_pil_records_valid_and_invalid(monkeypatch):
    valid = []
    invalid = []
    image = SimpleNamespace(info={}, verify=lambda: None)
    monkeypatch.setattr(openImage, 'open', lambda path: image)

    assert openImage.verify_image_with_pil({'path': 'good.jpg'}, valid, invalid)
    monkeypatch.setattr(
        openImage,
        'open',
        lambda path: (_ for _ in ()).throw(OSError()),
    )
    assert not openImage.verify_image_with_pil(
        {'path': 'bad.jpg'}, valid, invalid)
    assert valid == [{'path': 'good.jpg'}]
    assert invalid == ['bad.jpg']


def test_verify_image_dispatches_registered_verifier(monkeypatch):
    valid = []
    invalid = []
    registry = SimpleNamespace(
        extensions=['raw'],
        get_methods=lambda extension: [lambda path: False, lambda path: True],
    )
    monkeypatch.setattr(openImage.system, 'file_extension', lambda path: 'raw')

    assert openImage.verify_image_without_pil(
        {'path': 'input.raw'}, registry, valid, invalid)
    registry.get_methods = lambda extension: [lambda path: False]
    assert not openImage.verify_image_without_pil(
        {'path': 'bad.raw'}, registry, valid, invalid)
    assert invalid == ['bad.raw']


def test_verify_image_selects_pillow_and_registered_paths(monkeypatch):
    events = []
    registry = openImage.system.MethodRegister()
    registry.register(['raw'], lambda path: True)
    monkeypatch.setattr(
        openImage.system,
        'file_extension',
        lambda path: 'raw' if path.endswith('.raw') else 'jpg',
    )
    monkeypatch.setattr(
        openImage,
        'verify_image_without_pil',
        lambda *args: events.append('external'),
    )
    monkeypatch.setattr(
        openImage,
        'verify_image_with_pil',
        lambda *args: events.append('pillow'),
    )

    openImage.verify_image({'path': 'input.raw'}, [], [], registry)
    openImage.verify_image({'path': 'input.jpg'}, [], [], registry)

    assert events == ['external', 'pillow']


def test_verify_image_with_pil_skips_converter_output_verification(monkeypatch):
    image = SimpleNamespace(info={'Convertor': 'tool'})
    monkeypatch.setattr(openImage, 'open', lambda path: image)
    valid = []

    assert openImage.verify_image_with_pil({'path': 'input.pdf'}, valid, [])
    assert valid == [{'path': 'input.pdf'}]


def test_external_tool_adapters_build_expected_commands(monkeypatch):
    commands = []
    monkeypatch.setattr(
        openImage,
        'open_image_with_command',
        lambda filename, command, app, **kwargs: commands.append(
            (filename, command, app, kwargs)) or 'image',
    )
    monkeypatch.setattr(openImage.system, 'shell_returncode', lambda command: 0)

    assert openImage.open_inkscape('input.svg') == 'image'
    assert openImage.open_imagemagick('input.pdf') == 'image'
    assert openImage.open_xcf('input.xcf') == 'image'
    assert openImage.open_dcraw('input.raw') == 'image'
    assert openImage.verify_imagemagick('input.pdf')
    assert openImage.verify_xcf('input.xcf')
    assert openImage.verify_dcraw('input.raw')
    assert len(commands) == 4


def test_external_verifiers_report_nonzero(monkeypatch):
    monkeypatch.setattr(openImage.system, 'shell_returncode', lambda command: 1)

    assert not openImage.verify_imagemagick('input.pdf')
    assert not openImage.verify_xcf('input.xcf')
    assert not openImage.verify_dcraw('input.raw')
