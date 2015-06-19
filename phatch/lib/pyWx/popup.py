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

# Follows PEP8

"""All translations should be done here. Only controls eg. choice controls
can give 100%safe english strings.
SetValue(english)
Display(dutch) #or any other language
GetValue(english)

The bridge between fields and ctrls is done as follows:
formField.Field <-> treeEdit.create_popup <-> popup.Ctrl"""

if __name__ == '__main__':
    import sys
    sys.path.insert(0, '..')
    sys.path.insert(0, '../..')

import os
import sys

import wx
import wx.lib.colourselect

from lib.colors import RGBToHTMLColor, HTMLColorToRGB
from lib.fonts import font_dictionary
from lib.reverse_translation import _t

from autoCompleteCtrls import AutoCompleteTextCtrl, AutoCompleteIconCtrl
from wildcard import wildcard_list

####Plain Controls (no i18N)
try:
    _
    if not callable(_):
        raise NameError
except NameError:
    _ = unicode


ICON_SIZE = (64, 64)
LOADING = _('loading') + ' ...'
FONT_PATHS = ['/usr/share/fonts/truetype']
if sys.platform.startswith('linux'):
    TEXTCTRL_BORDER = 2
else:
    TEXTCTRL_BORDER = 4


#---sizer

def SetMinVerSize(item, size, border=0):
    item_size = item.GetSize()
    min_size = (size[0], min(item.GetSize()[1], size[1] - 2 * border))
    item.SetMinSize(min_size)
    item.SetSize(min_size)


class ForcedBoxSizer(wx.BoxSizer):

    def __init__(self, orient, height, border=0):
        super(ForcedBoxSizer, self).__init__(orient)
        self._size = (height, height)
        self._border = border

    def AddForced(self, item, proportion,
            flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=None, size=None):
        if not border:
            border = self._border
        if not size:
            size = self._size
        SetMinVerSize(item, size, border)
        super(ForcedBoxSizer, self).Add(item, proportion, flag, border)


#---exceptions

class NotImplementedError(Exception):

    def __init__(self, instance, method):
        """Not implemented error."""
        self.instance = instance
        self.method = method

    def __str__(self):
        return 'Class "%s" did not implement method "%s".' \
            % (self.instance.__class__.__name__, self.method)


#---base controls

def untranslated(self, x):
    return x


class _Ctrl(object):
    _to_local = untranslated
    _to_english = untranslated
    _busy_cursor = False

    def Set(self, value):
        self.SetValue(self._to_local(value))

    def Get(self):
        return self._to_english(self.GetValue())

    def SplitValue(self, value):
        return (value, )


class _CtrlChoices(_Ctrl):

    def RegisterChoices(self, choices):
        self._choices = choices
        return [self._to_local(choice) for choice in choices]


class _CtrlWithItems(_CtrlChoices):

    def Get(self):
        index = super(ChoiceCtrl, self).GetSelection()
        if index == wx.NOT_FOUND:
            index = 0
        return self._choices[index]


class _CtrlRelevantMixin:

    def SetRelevant(self, event_id, on_change):
        if on_change:
            self.on_change = on_change
            self.Bind(event_id, self.OnChange)

    def OnChange(self, event=None):
        """Wait until change is done."""
        if event:
            event.Skip()
        if hasattr(self, 'on_change'):
            self.on_change(unicode(self.Get()))
        #other option in case troubles pop up (see also Close method)
        #wx.CallAfter(self.OnAfterChange)

    def OnAfterChange(self):
        self.on_change(unicode(self.Get()))


class TextCtrl(_CtrlRelevantMixin, _CtrlChoices, wx.ComboBox):

    def __init__(self, parent, value, id=-1, choices=None, on_change=None,
            **keyw):
        if choices is None:
            choices = []
        local_choices = self.RegisterChoices(choices)
        if hasattr(parent, "SplitValue"):
            v = parent.SplitValue(value)[0]
        else:
            v = value
        v = v.strip()
        if v and v not in local_choices:
            local_choices.insert(0, v)
        super(TextCtrl, self).__init__(parent, id, value,
            choices=local_choices, **keyw)
        self.Set(value)
        self.SetRelevant(wx.EVT_TEXT, on_change)
        self.OnChange()


class _ComposedCtrl(_Ctrl, wx.Panel):
    """Composed controls are a wx.Panel with controls (extra button,...)."""

    def __init__(self, parent, value, size, **extra):
        super(_ComposedCtrl, self).__init__(parent, id=-1, size=size)
        self._CreateCtrls(value, **extra)
        self._Layout(height=size[1])
        self._CreateEvents()
        self.SetBackgroundColour(parent.GetBackgroundColour())

    def _Layout(self, height):
        sizer = ForcedBoxSizer(wx.HORIZONTAL, height, 0)
        self._AddCtrls(sizer, height)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    #---hooks to be overwritten
    def _CreateCtrls(self):
        """Needs to be overwritten."""
        raise NotImplementedError(self, "_CreateCtrls")

    def _AddCtrls(self, sizer, height):
        """Needs to be overwritten."""
        raise NotImplementedError(self, "_AddCtrls")

    def _CreateEvents(self):
        """Needs to be overwritten."""
        raise NotImplementedError(self, "_CreateEvents")

    def GetValue(self):
        raise NotImplementedError(self, "GetValue")

    def SetValue(self):
        raise NotImplementedError(self, "SetValue")


class _PathCtrl(_ComposedCtrl):
    InputCtrl = TextCtrl

    def _CreateCtrls(self, value, extensions=[], **extra):
        #folder
        self.path = self.InputCtrl(self, id=-1, value=value, **extra)
        if self.InputCtrl == wx.TextCtrl \
                and not sys.platform.startswith('win'):
            self.path.SetSelection(-1, -1)
        #browse button
        bmp = wx.ArtProvider_GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER,
                        size=(16, 16))
        self.browse = wx.BitmapButton(self, -1, bmp, style=wx.NO_BORDER)
        #extensions
        self._extensions = extensions

    def _AddCtrls(self, sizer, height):
        if wx.Platform == '__WXGTK__':
            #gtk provides a border already
            b = 0
        else:
            #windows & mac like some distance
            b = 4
        #don't force button, as crop is preferred to being crippled
        sizer.Add(self.browse, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            b)
        sizer.AddForced(self.path, 1)

    def _CreateEvents(self):
        self.Bind(wx.EVT_BUTTON, self.OnBrowse, self.browse)

    def GetDefaultPath(self, default_path=None):
        if default_path is None:
            default_path = os.path.dirname(self.path.GetValue())
        old = None
        while not os.path.exists(default_path) and (default_path != old):
            old = default_path
            default_path = os.path.dirname(default_path)
        return default_path

    def GetValue(self):
        return self.path.GetValue()

    def SetBackgroundColour(self, color):
        super(_PathCtrl, self).SetBackgroundColour(color)
        self.browse.SetBackgroundColour(color)

    def SetValue(self, x):
        self.path.SetValue(x)

    def SetFocus(self):
        self.path.SetFocus()

METRICS = ['px', '%', 'cm', 'mm', 'inch']

#---Main Controls (will be automatically registered through meta-class)


class BooleanCtrl(_CtrlRelevantMixin, _Ctrl, wx.CheckBox):

    def __init__(self, parent, value, size, on_change=None):
        super(BooleanCtrl, self).__init__(parent, -1, '', size=size)
        self.SetValue(bool(value))
        self.SetRelevant(wx.EVT_CHECKBOX, on_change)
        self.OnChange()

    def Get(self):
        return (_t('no'), _t('yes'))[self.GetValue()]


class ChoiceCtrl(_CtrlRelevantMixin, _CtrlWithItems, wx.Choice):

    def __init__(self, parent, value, size, choices, on_change=None):
        local_choices = self.RegisterChoices(choices)
        super(ChoiceCtrl, self).__init__(parent, -1, choices=local_choices,
            size=size)
        self.Set(value)
        self.SetRelevant(wx.EVT_CHOICE, on_change)

    def SetValue(self, value):
        self.SetStringSelection(value)


class ComboCtrl(_CtrlWithItems, wx.ComboBox):

    def __init__(self, parent, value, size, choices,
            style=['DROPDOWN', 'SORT']):
        local_choices = self.RegisterChoices(choices)
        style = self.RegisterStyle(style)
        super(ComboCtrl, self).__init__(parent, -1, choices=local_choices,
            size=size, style=style)
        self.Set(value)

    def Get(self):
        if 'READONLY' in self.style:
            return _CtrlWithItems.Get(self)
        else:
            return _Ctrl.Get(self)

    def RegisterStyle(self, style):
        "from a list of strings ['DROPDOWN','SORT'] to wx"
        self.style = style
        result = 0
        for s in style:
            result |= getattr(wx, 'CB_' + s)
        return result


class ImageDictionaryFileCtrl(_CtrlRelevantMixin, _Ctrl, wx.Button):
    _label = _t('Images')
    dialogs = {}

    def __init__(self, parent, value, size, extensions, dictionary,
            dialog, show_path=True, on_change=None, icon_size=(64, 64)):
        #avoid circular FIXME
        global imageFileBrowser
        import imageFileBrowser
        super(ImageDictionaryFileCtrl, self).__init__(parent, -1,
            LOADING, size=size)
        self.value = value
        self.extensions = extensions
        self.dictionary = dictionary
        self.title = _(dialog)
        self.show_path = show_path
        self.icon_size = icon_size
        self.Disable()
        wx.CallAfter(self.OnChange, None, value)
        self.SetRelevant(wx.EVT_BUTTON, on_change)

    def OnChange(self, event, value=None):
        if self.title in self.dialogs:
            dlg = ImageDictionaryFileCtrl.dialogs[self.title]
        else:
            dlg = None
        if not dlg:
            if self.icon_size == (128, 128):
                height = 350
            else:
                height = 400
            frame = wx.GetApp().GetTopWindow()
            dlg = self.dialogs[self.title] = \
                imageFileBrowser.Dialog(
                    parent=frame,
                    files=self.dictionary,
                    title=self.title,
                    size=(frame.GetSize()[0], height),
                    icon_size=self.icon_size,
                )
            dlg.ShowPath(self.show_path)
        if value is None:
            value = self.GetValue()
        else:
            self.SetValue(value)
            self.Enable()
        dlg.SetValue(value)
        if dlg.ShowModal() == wx.ID_OK:
            self.SetValue(dlg.image_path.GetValue())
        dlg.Hide()
        super(ImageDictionaryFileCtrl, self).OnChange(event)

    def SetValue(self, value):
        self.value = value
        self.SetLabel(_(value))

    def GetValue(self):
        return self.value


class ColorCtrl(_Ctrl, wx.lib.colourselect.ColourSelect):

    def __init__(self, parent, value, size):
        label = value
        if isinstance(value, (str, unicode)):
            value = HTMLColorToRGB(value)
        super(ColorCtrl, self).__init__(parent, -1, '', value, size=size)
        self.Bind(wx.lib.colourselect.EVT_COLOURSELECT, self.OnSelectColor)
        wx.CallAfter(self.SetLabel, label)
        wx.CallAfter(self.SetValue, value)
        wx.CallAfter(self.OnClick, None)

    def GetValue(self):
        return self.GetColorAsString()

    def GetColorAsString(self, color=None):
        if color == None:
            color = self.GetColour()
        if isinstance(color, (str, unicode)):
            return color
        return RGBToHTMLColor((color.Red(), color.Green(), color.Blue()))

    def OnSelectColor(self, event):
        color = event.GetValue()
        self.SetLabel(self.GetColorAsString(color))
        self.SetValue(wx.NamedColour(color))


class FileCtrl(_PathCtrl):
    wildcard = _t('All files') + '|*'

    def OnBrowse(self, event):
        style = wx.OPEN | wx.CHANGE_DIR
        if hasattr(wx, 'FD_PREVIEW'):
            style |= wx.FD_PREVIEW
        dlg = wx.FileDialog(self, self._to_local("Choose a file"),
            defaultFile=self.GetDefaultPath(),
            wildcard=self.GetWildcard(),
            style=style,
            )
        if dlg.ShowModal() == wx.ID_OK:
            value = dlg.GetPath()
            self.path.SetValue(value)
            #send event to signal the path has changed
            evt = wx.CommandEvent(wx.EVT_TEXT.typeId)
            evt.SetId(self.path.GetId())
            evt.SetEventObject(self.path)
            evt.SetString(value)
            self.path.GetEventHandler().ProcessEvent(evt)
        dlg.Destroy()

    def GetWildcard(self):
        return self._to_local(self.wildcard)


class LabelFileCtrl(FileCtrl):
    _label = _t('Selection')
    _all_files = _t('All files')

    def GetWildcard(self):
        if self._extensions:
            if len(self._extensions) < 5:
                label = '%s (%s)' % (self._label,
                    ','.join(self._extensions))
            else:
                label = self._label
            menu = [wildcard_list(self._to_local(label), self._extensions)]
        else:
            menu = []
        menu.append(self._all_files + '|*')
        return '|'.join(menu)


class FolderCtrl(_PathCtrl):

    def OnBrowse(self, event):
        dlg = wx.DirDialog(self, self._to_local("Choose a folder"),
            defaultPath=self.GetDefaultPath(),
            style=wx.DEFAULT_DIALOG_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.path.SetValue(dlg.GetPath())
        dlg.Destroy()


class DictionaryFileCtrl(LabelFileCtrl):
    dictionary = {}

    def __init__(self, parent, value, size, dictionary, **extra):
        self.dictionary = dictionary
        choices = dictionary.keys()
        choices.sort()
        super(DictionaryFileCtrl, self).__init__(parent, value, size,
            choices=choices, **extra)

    def GetDefaultPath(self, default_path=None):
        if default_path is None:
            value = self.path.GetValue()
            default_path = self.dictionary.get(value, value)
        return super(DictionaryFileCtrl, self).GetDefaultPath(default_path)


class AutoCompleteDictionaryFileCtrl(DictionaryFileCtrl):
    InputCtrl = AutoCompleteTextCtrl

    def _CreateCtrls(self, value, extensions=[], **extra):
        super(AutoCompleteDictionaryFileCtrl, self)._CreateCtrls(value,
            extensions,
            style=wx.CB_DROPDOWN,  # for compatibility with dropdown
            ** extra)
        if hasattr(self.path, "StartEvents"):
            self.path.StartEvents()


class FontFileCtrl(AutoCompleteDictionaryFileCtrl):
    _label = _t('Fonts')
    _busy_cursor = True

    def GetDefaultPath(self, default_path=None):
        if default_path is None:
            value = self.path.GetValue()
            default_path = font_dictionary().get(value, value)
        if not os.path.isdir(default_path.strip()):
            for path in FONT_PATHS:
                if os.path.isdir(path):
                    return path
        return super(FontFileCtrl, self).GetDefaultPath(default_path)

    def Close(self):
        if hasattr(self.path, "StopEvents"):
            self.path.StopEvents()


class ImageReadFileCtrl(LabelFileCtrl):
    _label = _t('Images')


class PixelCtrl(_ComposedCtrl):
    SizeCtrl = TextCtrl
    units = METRICS

    def _CreateCtrls(self, value, **extra):
        self.size = self.SizeCtrl(self, id=-1, value=value, **extra)
##        if  not sys.platform.startswith('win'):
##            self.size.SetSelection(-1, -1)
        self.unit = wx.Choice(self, id=-1, choices=self.units)
        self.SetValue(value)

    def _AddCtrls(self, sizer, height):
        sizer.AddForced(self.size, 1)
        width = self.unit.GetSize()[0]
        if wx.Platform == '__WXGTK__':
            width = int(width * 0.8)
        sizer.AddForced(self.unit, 0, size=(width, height))

    def _CreateEvents(self):
        """Nothing to do"""

    def SplitValue(self, value):
        "Split value and unit"
        value = value.strip()
        unit = self.units[0]
        for u in self.units:
            if value.endswith(u):
                unit = u
                value = value[:-len(u)]
                break
        return value, unit

    def SetValue(self, value):
        value, unit = self.SplitValue(value)
        self.size.SetValue(value)
        self.unit.SetStringSelection(unit)

    def GetValue(self):
        value = self.size.GetValue()
        if value:
            return '%s %s' % (value, self.unit.GetStringSelection())
        else:
            return ''

    def SetFocus(self):
        self.size.SetFocus()

FILE_SIZE_UNITS = ['kb', 'bt', 'mb', 'gb']


class FileSizeCtrl(PixelCtrl):
    units = FILE_SIZE_UNITS


class SliderCtrl(_ComposedCtrl):
    """Needs to mimic a wx.SliderCtrl"""

    def _CreateCtrls(self, value, minValue, maxValue):
        value = int(value)
        #spin ctrl
        self.spin = wx.SpinCtrl(self, id=-1)
        self.spin.SetRange(minValue, maxValue)
        self.spin.SetValue(value)
        #slider
        self.slider = wx.Slider(self, -1, value, minValue, maxValue,
                        style=wx.SL_HORIZONTAL)

    def _AddCtrls(self, sizer, height):
        sizer.AddForced(self.spin, 0, size=(int(height * 1.85), height))
        sizer.AddForced(self.slider, 1)

    def _CreateEvents(self):
        self.Bind(wx.EVT_SPINCTRL, self.OnSpin, self.spin)
        self.Bind(wx.EVT_SCROLL, self.OnScroll, self.slider)

    #---control methods (obligatory)
    def GetValue(self):
        return unicode(self.slider.GetValue())

    def SetBackgroundColour(self, color):
        super(SliderCtrl, self).SetBackgroundColour(color)
        if wx.Platform == '__WXMSW__':
            self.spin.SetBackgroundColour(color)
        self.slider.SetBackgroundColour(color)

    def SetFocus(self):
        self.spin.SetFocus()

    #---events
    def OnSpin(self, event):
        self.slider.SetValue(self.spin.GetValue())

    def OnScroll(self, event):
        self.spin.SetValue(self.slider.GetValue())


class FloatSliderCtrl(SliderCtrl):
    """Needs to mimic a wx.SliderCtrl"""
    unit = 100.0

    def _CreateCtrls(self, value, minValue, maxValue):
        value = int(value)
        #spin ctrl
        self.spin = wx.TextCtrl(self, -1, str(value))
        #slider
        self.slider = wx.Slider(self, -1, int(value * self.unit),
            int(minValue * self.unit), int(maxValue * self.unit),
            style=wx.SL_HORIZONTAL)

    def _CreateEvents(self):
        self.Bind(wx.EVT_TEXT, self.OnSpin, self.spin)
        self.Bind(wx.EVT_SCROLL, self.OnScroll, self.slider)

    #---control methods (obligatory)
    def GetValue(self):
        return self.spin.GetValue()

    #---events
    def OnSpin(self, event):
        s = event.GetString()
        try:
            value = int(float(s) * self.unit)
        except ValueError:
            return
        self.slider.SetValue(value)

    def OnScroll(self, event):
        self.spin.SetValue(str(self.slider.GetValue() / self.unit))

#todo implement all controls as panel with custom BoxSizer
#or maybe PopupControl should take care of this

CTRL_CACHE = {}


def ctrl_factory(name, CtrlMixin):
    ctrl_key = (name, CtrlMixin)
    try:
        Ctrl = CTRL_CACHE[ctrl_key]
    except KeyError:
        #example: name = FontFile (derived from class name)
        _globals = globals()
        ctrl_name = name + 'Ctrl'
        if ctrl_name in _globals:
            #this control is defined in this module
            Ctrl = _globals[ctrl_name]
        else:
            #unknown -> default to textctrl
            Ctrl = globals().get(ctrl_name, TextCtrl)
        if not (CtrlMixin is None):
            if isinstance(CtrlMixin, list):
                bases = tuple(CtrlMixin + [Ctrl])
            else:
                bases = (CtrlMixin, Ctrl)
            Ctrl = type(name, bases, {})
        CTRL_CACHE[ctrl_key] = Ctrl
    return Ctrl


class EditPanel(wx.Panel):
    "See for example create_popup in treeEdit"

    def __init__(self, parent, typ, value, extra={}, size=(28, 28), pos=(0, 0),
            offset=0, label='', border=0, CtrlMixin=None):
        super(EditPanel, self).__init__(parent, id=-1, pos=pos, size=size)
        self.Freeze()
        self._SetColours()
        if label:
            self._CreateLabel(label)
        height = size[1]
        border = self._CreateEdit(value, extra, typ, height, border, CtrlMixin)
        self._Layout(offset, height, border, label)
        self.Thaw()

    def _CreateLabel(self, label):
        self.label = label
        self.labelCtrl = wx.StaticText(self, -1, label)
        self.labelCtrl.SetForegroundColour(self.fgcolor)

    def _CreateEdit(self, value_as_string, extra, typ, height, border,
            CtrlMixin):
        #create ctrl class
        Ctrl = ctrl_factory(typ, CtrlMixin)
        #adjust border
        if issubclass(Ctrl, TextCtrl):
            border = max(border, TEXTCTRL_BORDER)
        #create ctrl instance
        if Ctrl._busy_cursor:
            wx.BeginBusyCursor()
        self.edit = Ctrl(self, value=Ctrl._to_english(value_as_string),
                            size=(height, height - 2 * border), **extra)
        #check min size
        if self.edit.GetSize()[1] > height:
            self.edit.SetMinSize((self.edit.GetMinSize()[0], height))
        self.edit.SetFocus()
        if Ctrl._busy_cursor:
            wx.EndBusyCursor()
        return border

    def _Layout(self, offset, height, border, label):
        """Offset is an integer."""
        sizer = ForcedBoxSizer(wx.HORIZONTAL, height, border)
        sizer.Add((offset, offset), 0)
        if label:
            sizer.Add(self.labelCtrl, proportion=0,
                flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sizer.AddForced(self.edit, proportion=1, border=border)
        if border < TEXTCTRL_BORDER and wx.Platform != '__WXGTK__':
            border = min(TEXTCTRL_BORDER, border)
            sizer.Add((border, border), 0)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def Close(self):
        """Loses focus"""
        if self:
            if hasattr(self.edit, "Close"):
                getattr(self.edit, "Close")()
            result = unicode(self.edit.Get())
            self.Destroy()
            return result

    #---support methods
    def _SetColours(self):
        self.bgcolor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        self.fgcolor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        self.SetBackgroundColour(self.bgcolor)


def example():
    width, height = 300, 28
    obj = globals()
    ctrls = [(name[:-4], obj[name]) for name in globals().keys()
        if name.endswith('Ctrl') and \
            not name.startswith('_') and \
            not name in ('AutoCompleteTextCtrl', 'AutoCompleteIconCtrl',
            'ImageDictionaryFileCtrl', 'ColorCtrl')]
    ctrls.sort()

    class App(wx.App):

        def OnInit(self, *args, **keyw):
            """Keep this in sync with treeEdit.create_popup"""
            frame = wx.Frame(None, -1, 'popup test')
            sizer = wx.BoxSizer(wx.VERTICAL)

            def on_change(*args):
                print('on_change %s' % str(args))

            for typ, ctrl in ctrls:
                if issubclass(ctrl, SliderCtrl):
                    extra = {'minValue': 0, 'maxValue': 100}
                elif issubclass(ctrl, BooleanCtrl):
                    extra = {'on_change': on_change}
                elif issubclass(ctrl, ChoiceCtrl):
                    extra = {'choices': ('1', '2'), 'on_change': on_change}
                elif issubclass(ctrl, ComboCtrl):
                    extra = {'choices': ('1', '2')}
                elif issubclass(ctrl, DictionaryFileCtrl):
                    extra = {'dictionary': {'hello': 'world'}}
                elif issubclass(ctrl, FileCtrl):
                    extra = {'extensions': ('*.py', '*.png')}
                else:
                    extra = {}
                if issubclass(ctrl, ColorCtrl):
                    value = '#FFFFFF'
                else:
                    value = '1'
                popup = EditPanel(frame, typ, value=value, extra=extra,
                                size=(width, height), pos=(0, 0), offset=10,
                                label=typ, border=1, CtrlMixin=None)
                sizer.Add(popup, flag=wx.EXPAND)

            frame.SetSizer(sizer)
            sizer.Fit(frame)

            frame.SetSize((width, frame.GetSize()[1]))
            frame.Layout()
            frame.Show()
            self.SetTopWindow(frame)
            return True

    app = App(0)
    app.MainLoop()


if __name__ == '__main__':
    example()
