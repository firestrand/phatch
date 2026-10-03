# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Importable plugin exercising spawned worker failure boundaries."""

from phatch.core.models import Action as BaseAction


class Action(BaseAction):
    label = 'Worker fixture'
    version = '1.0'
    parallel_safe = True
    resumable = True
    tags = ['transform']

    def interface(self, fields):
        fields['Mode'] = self.ChoiceField(
            'fail',
            choices=[
                'fail',
                'allocate',
                'crash',
                'crash_encode',
                'crash_encode_foreign',
                'crash_committed',
                'crash_artifact',
                'crash_transport',
                'crash_cancel',
            ],
        )

    def apply(self, photo, setting, cache):
        if self.get_field_string('Mode') == 'crash':
            from pathlib import Path

            source = Path(photo.info['path'])
            with (source.parent / 'worker-invocations.log').open('a') as ledger:
                ledger.write(source.name + '\n')
        if photo.info['imageindex'] == 0:
            mode = self.get_field_string('Mode')
            if mode == 'allocate':
                bytearray(1024 * 1024 * 1024)
            elif mode == 'crash':
                import os

                os._exit(9)
            elif mode == 'crash_cancel':
                import os
                from phatch.core import workers

                if hasattr(workers._CANCEL, '_cond'):
                    # Reproduce termination inside the old Event's critical
                    # section. The pipe-based view has no shared mutex.
                    workers._CANCEL._cond.acquire()
                else:
                    workers._CANCEL.is_set()
                os._exit(9)
            elif mode in {'crash_encode', 'crash_encode_foreign'}:
                from pathlib import Path
                import os
                from PIL import Image

                def crash(image, filename, **options):
                    if mode == 'crash_encode_foreign':
                        Path(filename).unlink()
                    Path(filename).write_bytes(b'partial encoding')
                    os._exit(9)

                Image.Image.save = crash
            elif mode == 'crash_committed':
                import os

                def crash(*args, **kwargs):
                    os._exit(9)

                photo.append_to_report = crash
            elif mode == 'crash_artifact':
                import os
                from phatch.lib.atomic import AtomicOutput

                original = AtomicOutput.__exit__

                def crash(transaction, *args):
                    original(transaction, *args)
                    if transaction.target.suffix == '.json':
                        os._exit(9)

                AtomicOutput.__exit__ = crash
            elif mode == 'crash_transport':
                import os
                import struct
                from phatch.core import workers

                original = workers._emit

                def crash(connection, event):
                    if event.kind == 'output_finished':
                        # Inject an interrupted Connection frame after commit.
                        connection._send(struct.pack('!i', 4096) + b'partial')
                        os._exit(9)
                    return original(connection, event)

                workers._emit = crash
            else:
                raise ValueError('injected worker failure')
        return photo
