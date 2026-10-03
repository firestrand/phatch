# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Importable plugin declaring a text-file dependency outside ReadFileField."""

from pathlib import Path

from phatch.core.models import Action as BaseAction


class Action(BaseAction):
    label = 'Resource fixture'
    version = '1.0'
    resumable = True
    parallel_safe = True
    preview_safe = True
    sequence_safe = True
    resource_fields = ('Color File',)
    tags = ['transform']

    def interface(self, fields):
        fields['Color File'] = self.CharField('')

    def apply(self, photo, setting, cache):
        path = self.get_field('Color File', photo.info)
        with Path(path).open() as stream:
            color = stream.read(65)
        if len(color) > 64:
            raise ValueError('Color definition exceeds 64 characters')
        color = color.strip()
        image = photo.get_layer().image
        painted = image.convert('RGB')
        painted.paste(color, (0, 0, painted.width, painted.height))
        photo.get_layer().image = painted
        image.close()
        return photo
