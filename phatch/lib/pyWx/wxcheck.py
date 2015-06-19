# Copyright (C) 2007-2008 www.stani.be
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
# Follow PEP8

import os
import sys
from subprocess import call
from lib.unicoding import ENCODING


def _t(x):
    return _(x).encode(ENCODING, 'replace')


def ensure(recommended, minimal):
    """Ensures the minimal version of wxPython is installed.
    - minimal: as string (eg. '2.6')"""

    #wxversion
    try:
        import wxversion
        if wxversion.checkInstalled(recommended):
            wxversion.select(recommended)
        else:
            wxversion.ensureMinimal(minimal)
        import wx
        return wx
    except ImportError:
        sys.stdout.write(_t('Warning: python-wxversion is not installed.\n'))

    #wxversion failed, import wx anyway
    params = {'recommended': recommended, 'minimal': minimal}
    try:
        import wx
    except ImportError:
        message = _t('Error: wxPython %(recommended)s' \
                                ' (or at least %(minimal)s) can not' \
                                ' be found, but is required.'
                            ) % params +\
            '\n\n' + _t('Please (re)install it.')
        sys.stderr.write(message)
        if sys.platform.startswith('linux') and \
                os.path.exists('/usr/bin/zenity'):
            call('''zenity --error --text="%s"\n\n''' % message + \
                _t("This application needs 'python-wxversion' " \
                    "and 'python-wxgtk%(recommended)s' " \
                    "(or at least 'python-wxgtk%(minimal)s')."
                    ) % params, shell=True)
        sys.exit()

    #wxversion failed but wx is available, check version again
    params['version'] = wx.VERSION_STRING
    if wx.VERSION_STRING < minimal:

        class MyApp(wx.App):
            def OnInit(self):
                result = wx.MessageBox(
                    _t("This application is known to be compatible" \
                        " with\nwxPython version(s) %(recommended)s" \
                        " (or at least %(minimal)s),\nbut you have " \
                        "%(version)s installed."
                        ) % params + "\n\n" +\
                    _t("Please upgrade your wxPython."),
                    _t("wxPython Version Error"),
                    style=wx.ICON_ERROR)
                return False
        app = MyApp()
        app.MainLoop()
        sys.exit()
    #wxversion failed, but wx is the right version anyway
    return wx
