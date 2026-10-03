# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Repeatable image workload measurements, including optional subprocess RSS."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _rss_tree(pid: int) -> int:
    """Linux aggregate resident bytes at this instant, including descendants."""
    try:
        values = Path(f'/proc/{pid}/statm').read_text().split()
        rss = int(values[1]) * os.sysconf('SC_PAGE_SIZE')
        children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
    except (OSError, IndexError, ValueError):
        return 0
    return rss + sum(_rss_tree(int(child)) for child in children)


def measure(workload: str, workers: int, count: int) -> dict[str, object]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        '--execute',
        '--workload',
        workload,
        '--workers',
        str(workers),
        '--count',
        str(count),
    ]
    with tempfile.TemporaryFile(mode='w+') as output:
        process = subprocess.Popen(command, stdout=output, text=True)
        peak = 0
        while process.poll() is None:
            peak = max(peak, _rss_tree(process.pid))
            time.sleep(0.01)
        if process.returncode:
            raise RuntimeError(
                f'Workload process exited with {process.returncode}'
            )
        output.seek(0)
        result = json.load(output)
    result['peak_aggregate_rss_bytes'] = (
        peak if sys.platform.startswith('linux') else None
    )
    result['rss_sample_interval_seconds'] = 0.01
    return result


def execute(workload: str, workers: int, count: int) -> dict[str, object]:
    from PIL import (
        Image,
        ImageCms,
        ImageOps,
        TiffImagePlugin,
        __version__ as pillow_version,
    )
    from phatch.core import api
    from phatch.core.batch import run_batch

    api.import_actions()
    registry = api.ACTIONS
    assert registry is not None
    with tempfile.TemporaryDirectory(prefix='phatch-benchmark-') as root:
        folder = Path(root)
        dimensions = (
            (6000, 4000)
            if workload == 'large'
            else (1200, 800)
            if workload == 'pages'
            else (2400, 1600)
        )
        gradient = Image.linear_gradient('L').resize(dimensions)
        inverse = ImageOps.invert(gradient)
        source = Image.merge('RGB', (gradient, inverse, gradient))
        gradient.close()
        inverse.close()
        exif = Image.Exif()
        exif[315] = 'Benchmark artist'
        exif[271] = 'Benchmark camera'
        xmp = None
        comment = (
            b'ASCII\x00\x00\x00' + b'Synthetic benchmark comment. ' * 1024
        )
        if workload == 'metadata_payload':
            exif[34853] = {1: 'N', 2: (1.0, 2.0, 3.0)}
            exif[34665] = {
                36867: '2020:01:02 03:04:05',
                37510: comment,
            }
            xmp = (
                b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
                b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
                b'<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">'
                b'<dc:description>'
                + b'Synthetic benchmark keywords. ' * 1024
                + b'</dc:description></rdf:Description></rdf:RDF></x:xmpmeta>'
            )
        profile = ImageCms.ImageCmsProfile(
            ImageCms.createProfile('sRGB')
        ).tobytes()
        inputs = []
        page_count = 8 if workload == 'pages' else 1
        for index in range(count):
            path = (
                folder
                / f'input-{index:03d}.{"tiff" if workload == "pages" else "jpg"}'
            )
            if workload == 'pages':
                pages = []
                try:
                    for page_index in range(page_count):
                        page = (
                            source.copy()
                            if page_index % 2 == 0
                            else ImageOps.invert(source)
                        )
                        tags = Image.Exif()
                        tags[270] = f'Benchmark page {page_index}'
                        page.encoderinfo = {
                            'exif': tags.tobytes(),
                            'icc_profile': profile,
                        }
                        pages.append(page)
                    pages[0].save(path, save_all=True, append_images=pages[1:])
                finally:
                    for page in pages:
                        page.close()
            else:
                source.save(
                    path,
                    quality=95,
                    exif=exif,
                    icc_profile=profile,
                    **({'xmp': xmp} if xmp else {}),
                )
            inputs.append(path)
        source.close()
        actions = []
        if workload in {'resize', 'large'}:
            scale = registry['Scale']()
            limit = '2000px' if workload == 'large' else '1024px'
            scale.set_field_as_string('Canvas Width', limit)
            scale.set_field_as_string('Canvas Height', limit)
            scale.set_field_as_string('Scale Down Only', 'yes')
            actions.append(scale)
        if workload in {'watermark', 'journal_watermark'}:
            mark = folder / 'mark.png'
            with Image.new('RGBA', (256, 128), (255, 255, 255, 100)) as stamp:
                stamp.save(mark)
            watermark = registry['Watermark']()
            watermark.set_field_as_string('Mark', str(mark))
            actions.append(watermark)
        save = registry['Save']()
        save.set_field_as_string('In', str(folder / 'outputs'))
        save.set_field_as_string(
            'As',
            'jpeg'
            if workload in {'metadata', 'metadata_payload'}
            else 'tiff'
            if workload == 'pages'
            else 'png',
        )
        if workload == 'metadata':
            save.set_field_as_string('Metadata Policy', 'sharing')
            save.set_field_as_string('Color Policy', 'srgb')
        if workload == 'pages':
            save.set_field_as_string('TIFF Compression', 'lzw')
        actions.append(save)
        settings: dict[str, object] = {'workers': workers}
        if workload == 'pages':
            settings['page_policy'] = 'preserve'
        if workload == 'journal_watermark':
            settings['manifest_path'] = str(folder / 'journal.json')
        started = time.perf_counter()
        result = run_batch(actions, inputs, settings)
        elapsed = time.perf_counter() - started
        if result.status != 'success' or len(result.files) != count:
            raise RuntimeError(str(result.to_dict(include_details=True)))
        digest = hashlib.sha256()
        for item in result.files:
            assert len(item.outputs) == 1
            for path in item.outputs:
                assert path.stem == item.source.stem
                digest.update(path.name.encode())
                with Image.open(path) as image:
                    assert getattr(image, 'n_frames', 1) == page_count
                    for frame_index in range(page_count):
                        image.seek(frame_index)
                        image.load()
                        digest.update(str(image.size).encode())
                        digest.update(image.tobytes())
                        if workload == 'pages':
                            assert isinstance(
                                image, TiffImagePlugin.TiffImageFile
                            )
                            assert (
                                image.getexif()[270]
                                == f'Benchmark page {frame_index}'
                            )
                            assert image.tag_v2[259] == 5
                            assert image.tag_v2[34675] == profile
                            with Image.open(item.source) as original:
                                original.seek(frame_index)
                                original.load()
                                assert image.size == original.size
                                assert image.tobytes() == original.tobytes()
                        if workload == 'metadata_payload':
                            tags = image.getexif()
                            assert tags.get_ifd(34665)[37510] == comment
                            assert (
                                tags.get_ifd(34665)[36867]
                                == '2020:01:02 03:04:05'
                            )
                            assert tuple(tags.get_ifd(34853)[2]) == (
                                1.0,
                                2.0,
                                3.0,
                            )
                            assert image.info['xmp'] == xmp
                            assert image.info['icc_profile'] == profile
        resume_elapsed = None
        if workload == 'journal_watermark':
            started = time.perf_counter()
            resumed = run_batch(actions, inputs, {**settings, 'resume': True})
            resume_elapsed = time.perf_counter() - started
            assert resumed.status == 'success' and all(
                item.resumed for item in resumed.files
            )
            assert [item.outputs for item in resumed.files] == [
                item.outputs for item in result.files
            ]
        return {
            'workload': workload,
            'workers': workers,
            'count': count,
            'input_dimensions': dimensions,
            'frames_per_input': page_count,
            'input_bytes': sum(path.stat().st_size for path in inputs),
            'exif_payload_bytes': len(exif.tobytes())
            if workload == 'metadata_payload'
            else None,
            'xmp_payload_bytes': len(xmp) if xmp else None,
            'resume_verification_seconds': resume_elapsed,
            'elapsed_seconds': elapsed,
            'images_per_second': count / elapsed,
            'output_pixel_sha256': digest.hexdigest(),
            'python': platform.python_version(),
            'pillow': pillow_version,
            'platform': platform.platform(),
            'cpu_count': os.cpu_count(),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument(
        '--workload',
        choices=[
            'resize',
            'watermark',
            'metadata',
            'large',
            'metadata_payload',
            'pages',
            'journal_watermark',
        ],
        required=True,
    )
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--count', type=int, default=8)
    arguments = parser.parse_args()
    result = (
        execute(arguments.workload, arguments.workers, arguments.count)
        if arguments.execute
        else measure(arguments.workload, arguments.workers, arguments.count)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
