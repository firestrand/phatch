# Copyright (C) 2007-2008  www.stani.be
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
#
# Follows PEP8


import os
import sys
import _winreg

PYTHONW = os.path.join(sys.prefix, 'pythonw.exe')
PY = 'Python.File'
PYW = 'Python.NoConFile'


def fix_label(x):
    return x.title().replace(' ', '').encode('ascii', 'ignore')


def getFiletype(extension):
    return _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT, extension)

#---register


def register(label, action, filetype='Python.File', suffix='"%1"'):
    try:
        k = '%s\\shell\\%s' % (filetype, label)
        key = _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, k)
    except:
        pass
    try:
        command = '%s %s' % (action, suffix)
        _winreg.SetValue(key, "command", _winreg.REG_SZ, command)
        return key
    except:
        return False


def register_extension(label, action, extension, suffix='"%1"'):
    "Registering action for extension in windows explorer context menu."
    try:
        filetype = getFiletype(extension)
    except:
        return False
    return register(
        label=label,
        action='"%s" %s' % (PYTHONW, action),
        filetype=filetype,
        suffix=suffix,
    )


def register_extensions(label, action, extensions, folder=False,
        suffix='"%1"'):
    "Registering action for extensions in windows explorer context menu."
    result = []
    if folder:
        if register(label, action, 'Folder', suffix):
            result.append('folder')
    for extension in extensions:
        if register_extension(label, action, extension, suffix):
            result.append(extension)
    return result


def register_py(label, action, suffix='"%1"'):
    """ Registering action for python (*.py, *.pyw) in windows
        explorer contextmenu."""
    keyw = {
        'label': label,
        'action': '"%s" "%s"' % (PYTHONW, action),
        'suffix': suffix}
    py, pyw = keys\
            = (register(filetype=PY, **keyw), register(filetype=PYW, **keyw))
    if py and pyw:
        return keys
    else:
        return False

#---deregister


def deregister(label, filetype='Python.File'):
    try:
        key = '%s\\shell\\%s' % (filetype, label)
        _winreg.DeleteKey(_winreg.HKEY_CLASSES_ROOT, key + '\\command')
    except  Exception, message:
        pass
    try:
        _winreg.DeleteKey(_winreg.HKEY_CLASSES_ROOT, key)
        return True
    except  Exception, message:
        return False


def deregister_extension(label, extension):
    try:
        filetype = getFiletype(extension)
    except:
        return False
    return deregister(label, filetype)


def deregister_extensions(label, extensions, folder=True):
    result = []
    if folder:
        if deregister(label, 'Folder'):
            result.append('folder')
    for extension in extensions:
        if deregister_extension(label, extension):
            result.append(extension)
    return result


def deregister_py(label):
    deregister(label=label, filetype=PY)
    deregister(label=label, filetype=PYW)
