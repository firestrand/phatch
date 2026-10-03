#!/usr/bin/env python

# Phatch - Photo Batch Processor
# Copyright (C) 2007-2009  www.stani.be
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/

# Follows PEP8

"""Resource installation adapter; project metadata lives in pyproject.toml."""

from pathlib import Path
from setuptools import setup


def resource_files() -> list[tuple[str, list[str]]]:
    """Preserve the established share layout on every supported platform."""
    result = []
    for source, destination in (
        ('data', 'share/phatch/data'),
        ('images', 'share/phatch/images'),
        ('locale', 'share/locale'),
    ):
        root = Path(source)
        for directory in sorted(
            {p.parent for p in root.rglob('*') if p.is_file()}
        ):
            files = sorted(
                str(p)
                for p in directory.iterdir()
                if p.is_file() and p.suffix != '.pyc'
            )
            result.append(
                (str(Path(destination) / directory.relative_to(root)), files)
            )
    result.extend(
        [
            (
                'share/applications',
                ['linux/phatch.desktop', 'linux/phatch-inspector.desktop'],
            ),
            ('share/man/man1', ['linux/phatch.1']),
            ('share/mime/packages', ['linux/phatch.xml']),
        ]
    )
    return result


if __name__ == '__main__':
    setup(data_files=resource_files())
