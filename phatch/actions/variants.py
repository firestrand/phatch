# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate independent named output branches and their association manifest."""

from collections.abc import Callable, Mapping
from typing import Any

from phatch.core.models import Action as BaseAction
from phatch.core.variants import definitions, export_variants


class Action(BaseAction):
    label = 'Variants'
    author = 'Phatch contributors'
    email = ''
    version = '1.0'
    tags = ['file', 'default']
    valid_last = True
    __doc__ = 'Generate named sizes and formats independently from one image'

    def interface(self, fields: dict[str, Any]) -> None:
        fields['Preset'] = self.ChoiceField('web', choices=['web', 'custom'])
        fields['Variants'] = self.CharField('[]')
        fields['File Name'] = self.FileNameField(self.FILENAME)
        fields['In'] = self.FolderField(
            self.DEFAULT_FOLDER, choices=self.FOLDERS
        )
        fields['Write Manifest'] = self.BooleanField(True)
        fields['Manifest Name'] = self.FileNameField('<filename>-variants')
        fields['Collision Policy'] = self.ChoiceField(
            'inherit', choices=['inherit', 'skip', 'fail', 'replace', 'rename']
        )
        fields['Format Fallback'] = self.ChoiceField(
            'error', choices=['error', 'png']
        )
        fields['Animation Policy'] = self.ChoiceField(
            'inherit', choices=['inherit', 'reject', 'first', 'extract']
        )
        fields['Page Policy'] = self.ChoiceField(
            'inherit', choices=['inherit', 'reject', 'first', 'extract']
        )

    def is_overwrite_existing_images_forced(self) -> bool:
        return False

    def get_relevant_field_labels(self) -> list[str]:
        labels = ['Preset']
        if self.get_field_string('Preset') == 'custom':
            labels.append('Variants')
        labels.extend(['File Name', 'In', 'Write Manifest'])
        if self.get_field_string('Write Manifest') in {'yes', 'true'}:
            labels.append('Manifest Name')
        labels.extend(
            [
                'Collision Policy',
                'Format Fallback',
                'Animation Policy',
                'Page Policy',
            ]
        )
        return labels

    def apply(
        self,
        photo: Any,
        setting: Callable[[str], Any],
        cache: Mapping[str, Any],
    ) -> Any:
        collision = self.get_field_string('Collision Policy')
        if collision == 'inherit':
            collision = setting('collision_policy') or (
                'replace' if setting('overwrite_existing_images') else 'skip'
            )
        return export_variants(
            photo,
            definitions(self.dump()['fields']),
            self.get_field('In', photo.info),
            self.get_field('File Name', photo.info),
            manifest_name=self.get_field('Manifest Name', photo.info)
            if self.get_field('Write Manifest', photo.info)
            else None,
            collision_policy=collision,
            fallback=self.get_field_string('Format Fallback'),
            encoder_threads=setting('encoder_threads') or 1,
            cancel=setting('_cancel_callback'),
        )
