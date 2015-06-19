#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2010  www.stani.be
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
#
# Follows PEP8

"""This is a plugin/hook for bazaar.

Linux/Mac: Symlink (ln -s) this file to ~/.bazaar/plugins/
Windows: Copy this file to C:\Program Files\Bazaar\plugins
"""

import sys
from bzrlib import branch
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), """
import urllib
from bzrlib import builtins, errors, option
""")

LINUX = sys.platform.startswith('linux')
WINDOWS = sys.platform.startswith('win')


def master_to_path(master):
    path = urllib.unquote(master.base.replace('file://', ''))
    if WINDOWS:
        path = path.lstrip('/').replace('/', '\\')
    return path


def pre_commit_hook(local, master, old_revno, old_revid, future_revno,
        future_revid, tree_delta, future_tree):
    """This hook will execute precommit script from root path of the bazaar
    branch. Commit will be canceled if precommit fails."""

    # bzr requires that modules are imported inside the hook
    import os
    import subprocess
    import time
    import urllib

    # initialize time
    time_start = time.time()

    # initializes paths
    current_dir = os.getcwd()
    master_dir = master_to_path(master)
    test_dir = os.path.join(master_dir, 'tests')
    phatch_dir = os.path.join(master_dir, 'phatch')

    if not os.path.exists(phatch_dir):
        # Ignore other projects other than Phatch
        return

    # Ensure to undo the directory change
    def exit(error=None):
        os.chdir(current_dir)
        print('\nRan precommit tests in %.3fs\n' % (time.time() - time_start))
        if error:
            raise errors.BzrError(
                'Unable to commit, because %s test failed.' % error)

    os.chdir(test_dir)

    # Use subprocesses so exceptions can't mess with the state
    print(' ' * 80)

    if LINUX and subprocess.call(['python', 'license_test.py']):
        exit('license')

    if not WINDOWS and subprocess.call(['python', 'doc_test.py']):
        exit('doctest')

    print('-' * 70)

    if subprocess.call(['python', 'pep8_test.py']):
        exit('PEP8')

    exit()

branch.Branch.hooks.install_named_hook('pre_commit', pre_commit_hook,
    'Check pre_commit hook')
