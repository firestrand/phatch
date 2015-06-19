# -*- coding: UTF-8 -*-

# Phatch - Photo Batch Processor
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
# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.

# Follows PEP8

#---first test
import os
import time

if __name__ == '__main__':
    import sys
    sys.path.extend(['lib', '../core', '../core/lib'])
    sys.path.insert(0, os.path.dirname(os.getcwd()))
    #test environment
    import gettext
    gettext.install("test")

#---begin
import wx

from core import ct
from lib.reverse_translation import _r
from core import pil

#core.lib
from lib import system
from core.message import send, ProgressReceiver

#gui-dependent
from lib.pyWx import clipboard
from lib.pyWx import graphics
from lib.pyWx import vlistTag
from lib.pyWx import paint
from lib.pyWx import imageInspector
from lib.pyWx.wildcard import wildcard_list, _wildcard_extension
from lib.pyWx.tag import Browser, ContentMixin

import images
from wxGlade import dialogs

VLIST_ICON_SIZE = (48, 48)
_MAX_HEIGHT = None  # cache


def get_max_height(height=510):
    global _MAX_HEIGHT
    if _MAX_HEIGHT is None:
        _MAX_HEIGHT = min(height, wx.Display(0).GetGeometry().GetHeight() - 50)
        return _MAX_HEIGHT
    else:
        return _MAX_HEIGHT


class BrowseMixin:

    def show_dir_dialog(self, defaultPath, message=_('Choose a folder'),
            style=wx.DEFAULT_DIALOG_STYLE):
        dlg = wx.DirDialog(self, message,
            defaultPath=defaultPath,
            style=wx.DEFAULT_DIALOG_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
        else:
            path = None
        dlg.Destroy()
        return path


class IconMixin:

    if wx.Platform == '__WXGTK__':
        _icon_size = (32, 32)  # (48, 48)
    else:
        _icon_size = (32, 32)

    def _icon(self, name='information'):
        name = 'ART_%s' % name.upper()
        #title icon
        bitmap = graphics.bitmap(name, (16, 16))
        _ic = wx.EmptyIcon()
        _ic.CopyFromBitmap(bitmap)
        self.SetIcon(_ic)
        #dialog icon
        bitmap = graphics.bitmap(name, self._icon_size)
        self.icon.SetBitmap(bitmap)
        self.icon.Show(True)


class ErrorDialog(dialogs.ErrorDialog, IconMixin):

    def __init__(self, parent, message, ignore=True, **keyw):
        super(ErrorDialog, self).__init__(parent, -1, **keyw)
        self._icon('error')
        self.message.SetLabel(system.wrap(message, 70))
        if not ignore:
            self.ignore.Hide()
            self.skip.SetDefault()
        self.GetSizer().Fit(self)
        self.Layout()

    #---events
    def on_skip(self, event):
        self.EndModal(wx.ID_FORWARD)

    def on_abort(self, event):
        self.EndModal(wx.ID_ABORT)

    def on_ignore(self, event):
        self.EndModal(wx.ID_IGNORE)


class ExecuteDialog(BrowseMixin, dialogs.ExecuteDialog):

    def __init__(self, parent, drop=False, **options):
        super(ExecuteDialog, self).__init__(parent, -1, **options)
        self.set_drop(drop)

    def browse_files(self):
        style = wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR
        if hasattr(wx, 'FD_PREVIEW'):
            style |= wx.FD_PREVIEW
        dlg = wx.FileDialog(
            self, message=_("Choose File(s)"),
            defaultDir=self.get_default_path(),
            defaultFile="",
            wildcard=self.wildcard(),
            style=style,
            )
        if dlg.ShowModal() == wx.ID_OK:
            self.path.SetValue(ct.PATH_DELIMITER.join(dlg.GetPaths()))
        dlg.Destroy()

    def browse_folder(self):
        path = self.show_dir_dialog(
            defaultPath=self.get_default_path(),
            message=_("Choose an image folder"))
        if path != None:
            self.path.SetValue(path)

    def get_default_path(self):
        path = self.path.GetValue().split(ct.PATH_DELIMITER)[0]
        return os.path.dirname(path)

    def export_settings(self, settings):
        settings['paths'] = self.path.GetValue().split(ct.PATH_DELIMITER)
        settings['extensions'] = [self.extensions.GetString(i) \
            for i in range(self.extensions.GetCount()) \
            if self.extensions.IsChecked(i)]
        settings['recursive'] = self.recursive.GetValue()
        settings['stop_for_errors'] = self.stop_for_errors.GetValue()
        settings['overwrite_existing_images'] = \
            self.overwrite_existing_images.GetValue()
        settings['always_show_status_dialog'] = \
            self.always_show_status_dialog.GetValue()
        settings['check_images_first'] = self.check_images_first.GetValue()
        settings['browse_source'] = self.source.GetSelection()
        settings['desktop'] = self.desktop.GetValue()
        settings['repeat'] = self.repeat.GetValue()
        wx.GetApp()._saveSettings()

    def get_selected_extensions(self):
        result = []
        exts = pil.IMAGE_READ_EXTENSIONS
        for index, extension in enumerate(exts):
            if self.extensions.IsChecked(index):
                result.append(extension)
        return result

    def set_drop(self, drop):
        if drop:
            #change title
            self.SetTitle(_('Drag & Drop'))
            #radio box
            self.source.Hide()
            #hide browse & path
            self.browse.Hide()
            self.path.Hide()
            #layout (only allow vertical fit)
            grid_sizer = self.GetSizer()
            size = (self.GetSize()[0], grid_sizer.GetMinSize()[1])
            self.SetMinSize(size)
            self.Fit()

    def import_settings(self, settings):
        #path
        self.path.SetValue(ct.PATH_DELIMITER.join(settings['paths']))
        #browse source
        self.source.SetSelection(settings['browse_source'])
        self.on_source(None)
        #extensions
        exts = pil.IMAGE_READ_EXTENSIONS
        self.extensions.Set(exts)
        for index, extension in enumerate(exts):
            if extension in settings['extensions']:
                self.extensions.Check(index)
        #overwrite existing images
        self.overwrite_existing_images.SetValue(
            settings['overwrite_existing_images'] or\
            settings['overwrite_existing_images_forced'])
        #overwrite existing files
        self.check_images_first.SetValue(
            settings['check_images_first'])
        #recursive
        self.recursive.SetValue(settings['recursive'])
        #errors
        self.stop_for_errors.SetValue(settings['stop_for_errors'])
        #always_show_status_dialog
        self.always_show_status_dialog.SetValue(
            settings['always_show_status_dialog'])
        #always save on desktop
        self.desktop.SetValue(settings['desktop'])
        #repeat images
        self.repeat.SetValue(settings['repeat'])

    #---wildcard
    def wildcard(self):
        extensions = self.get_selected_extensions()
        selected = wildcard_list(_('All selected types'),
                        extensions)
        default = wildcard_list(_('All readable and writable types'),
                        pil.IMAGE_EXTENSIONS)
        read = wildcard_list(_('All readable types'),
                        pil.IMAGE_READ_EXTENSIONS)
        result = [selected, default, read]
        result.extend([('%s ' + _('images') + '|%s')\
                    % (ext, _wildcard_extension(ext))
                    for ext in extensions])
        return '|'.join(result)

    #---events
    def on_browse(self, event):
        if self.source.GetSelection() == 0:
            self.browse_folder()
        else:
            self.browse_files()

    def on_default(self, event):
        state = self.select.GetLabel() == _("&All Types")
        exts = pil.IMAGE_READ_EXTENSIONS
        for index, extension in enumerate(exts):
            self.extensions.Check(index, state)
        if state:
            self.select.SetLabel(_("&No Types"))
        else:
            self.select.SetLabel(_("&All Types"))

    def on_source(self, event):
        source = self.source.GetStringSelection()
        if source == _('Clipboard'):
            self.browse.Disable()
            self.browse.SetLabel(_('Browse'))
            self.path.SetValue(clipboard.get_text()\
                .replace('\n', ct.PATH_DELIMITER))
        else:
            self.browse.Enable()
            self.browse.SetLabel(_('Browse %s') % source)


class FilesDialog(dialogs.FilesDialog, IconMixin):

    def __init__(self, parent, message, title, files, icon='warning', **keyw):
        super(FilesDialog, self).__init__(parent, -1, **keyw)
        self.SetTitle(title)
        self.message.SetLabel(message)
        self.list.InsertColumn(0, _("File"))
        self.list.InsertColumn(1, _("Folder"))
        for index, f in enumerate(files):
            index = self.list.InsertStringItem(index, os.path.basename(f))
            self.list.SetStringItem(index, 1, os.path.dirname(f))
        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.list.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        min = 100
        if self.list.GetColumnWidth(0) < min:
            self.list.SetColumnWidth(0, min)
        self._icon(icon)


class ProgressDialog(wx.ProgressDialog, ProgressReceiver):
    """+1 is added because eg opening a file is also an action"""

    def __init__(self, parent, title, parent_max=1, child_max=1, message=''):
        if message == '':
            message = '.' * 80
        ProgressReceiver.__init__(self, parent_max, child_max)
        wx.ProgressDialog.__init__(self,
                title=title,
                message=message,
                maximum=self.max,
                parent=parent,
                style=wx.PD_CAN_ABORT
                            | wx.PD_APP_MODAL
                            | wx.PD_REMAINING_TIME
                            | wx.PD_SMOOTH)
        self.Bind(wx.EVT_CLOSE, self.close, self)

    #---pubsub event methods
    def close(self, event=None):
        self.unsubscribe_all()
        self.Destroy()

    def update(self, result, value, **message):
        """Fix for wxPython2.6"""
        status = self.Update(value, **message)
        if type(status) == bool:
            result['keepgoing'] = result['skip'] = status
        else:
            result['keepgoing'], result['skip'] = status
        if result['keepgoing']:
            self.Refresh()
        else:
            self.close()

    def sleep(self):
        time.sleep(0.001)


class ActionListBox(ContentMixin, vlistTag.Box):

    #---vlist.Box obligatory overwritten
    def SetTag(self, tag=imageInspector.ALL):
        super(ActionListBox, self).SetTag(tag)
        #process tag
        self.tag = tag
        if tag == imageInspector.SELECT:
            tag = _('default')
        #choose tag actions
        if tag == imageInspector.ALL:
            self.tag_actions = self.all_actions
        else:
            tag_i18n = tag.lower()
            self.tag_actions = [a for a in self.all_actions
                if tag_i18n in a.tags_i18n]
        #sort
        self.tag_actions.sort(cmp=lambda \
            x, y: cmp(_(x.label_i18n), _(y.label_i18n)))
        #take filter in account
        self.SetFilter(self.GetFilter().GetValue())

    def SetFilter(self, filter):
        filter = filter.strip().lower()
        actions = self.tag_actions[:]
        if filter:
            actions = self._filter_actions(filter, actions)
            if not actions:
                #nothing found for the tag, look everywhere
                actions = self._filter_actions(filter, self.all_actions[:])
        self.actions = actions
        self.SetItemCount(len(self.actions))
        self.GetParent().CheckEmpty()
        self.RefreshAll()
        wx.GetTopLevelParent(self).ok.Enable(not self.IsEmpty())

    def _filter_actions(self, filter, actions):
        selected = self._filter_attr(filter, 'label_i18n', actions)
        selected += self._filter_attr(filter, 'doc__i18n', actions)
        selected += self._filter_attr(filter, 'tags_i18n', actions)
        selected += self._filter_attr(filter, 'tags_hidden_i18n', actions)
        return selected

    def _filter_attr(self, filter, attr, actions):
        selected1 = [action for action in actions
            if unicode(getattr(action, attr)).startswith(filter)]
        for action in selected1:
            actions.remove(action)
        selected2 = [action for action in actions
            if filter in unicode(getattr(action, attr))]
        for action in selected2:
            actions.remove(action)
        return selected1 + selected2

    def _events(self):
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

    #---actions
    def SetActions(self, actions):
        self.all_actions = actions.values()
        for action in self.all_actions:
            self.TranslateAction(action)
        self.all_actions.sort(cmp=lambda x, y: \
            cmp(_(x.label_i18n), _(y.label_i18n)))

    def TranslateAction(self, action):
        action.label_i18n = _(action.label).lower()
        action.doc__i18n = _(action.__doc__).lower()
        action.tags_i18n = [_(tag).lower() for tag in action.tags]
        action.tags_hidden_i18n = [_(tag).lower()
            for tag in action.tags_hidden]

    def OnContextMenu(self, event):
        # todo: does contextmenu always have to be recreated?
        #create id
        self.id_view_source = wx.NewId()
        #create menu
        menu = wx.Menu()
        item = wx.MenuItem(menu, self.id_view_source, _("View Source"))
        item.SetBitmap(graphics.bitmap('ART_FIND', (16, 16)))
        self.Bind(wx.EVT_MENU, self.OnViewSource, id=self.id_view_source)
        menu.AppendItem(item)
        #show menu
        self.PopupMenu(menu)
        #destroy menu
        menu.Destroy()

    def OnViewSource(self, event):
        action = self.actions[self.GetSelection()]
        module = action.__module__.split('.')[-1]
        filename = os.path.join(ct.PHATCH_ACTIONS_PATH, '%s.py' % module)
        message = open(filename).read()
        dir, base = os.path.split(filename)
        send.frame_show_scrolled_message(message, '%s - %s' % (base, dir),
            size=(600, 300))

    def RefreshList(self):
        self.actions.sort(cmp=lambda x, y: cmp(_(x.label), _(y.label)))
        self.Clear()
        self.SetItemCount(len(self.actions))
        self.RefreshAll()

    def GetItem(self, n):
        action = self.actions[n]
        return (_(action.label), _(action.__doc__),
            graphics.bitmap(action.icon, self.GetIconSize()))

    def GetStringSelection(self):
        return self.actions[self.GetSelection()].label

    def IsEmpty(self):
        return not (hasattr(self, 'actions') and self.actions)


class ActionBrowser(Browser):
    ContentCtrl = ActionListBox
    paint_message = _("broaden your search")
    paint_color = images.LOGO_COLOUR
    #paint_logo = images.LOGO


class ActionDialog(paint.Mixin, vlistTag.Dialog):
    ContentBrowser = ActionBrowser

    def __init__(self, parent, actions, tag='default', **keyw):
        #extract tags
        tags = self.ExtractTags(actions.values())
        #init dialog
        super(ActionDialog, self).__init__(parent, tags, -1, **keyw)
        #configure listbox
        list_box = self.GetListBox()
        list_box.SetActions(actions)
        list_box.SetIconSize(VLIST_ICON_SIZE)
        list_box.SetTag(_(tag))
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

    def ExtractTags(self, actions):
        """Called by SetActions."""
        tags = vlistTag.extract_tags(actions)
        tags.remove(_('default'))
        tags.sort()
        tags = [imageInspector.SELECT, imageInspector.ALL] + tags
        return tags

    def GetListBox(self):
        return self.browser.content

    def GetStringSelection(self):
        return self.GetListBox().GetStringSelection()

    def GetTagSelection(self):
        return _r(self.GetListBox().GetTag().GetStringSelection())

    def OnActivate(self, event):
        if event.GetActive():
            wx.CallAfter(self.GetListBox().GetFilter().SetFocus)


class WritePluginDialog(dialogs.WritePluginDialog, IconMixin):

    def __init__(self, parent, message, **keyw):
        super(WritePluginDialog, self).__init__(parent, -1, **keyw)
        path = os.path.join(ct.PATH, 'templates', 'action.py')
        self._icon('information')
        self.message.SetLabel(message)
        self.path.SetLabel('%s: %s' % (_('Path'), path))
        self._code(path)
        self.template_show(False)

    def _code(self, path):
        self.code.SetValue(open(path).read())
        self.code.SetMinSize((660, 300))
        self.code.SetFont(wx.Font(10, wx.TELETYPE, wx.NORMAL, wx.NORMAL,
            0, ""))

    #---events
    def on_help(self, event):
        import webbrowser
        url = "https://lists.launchpad.net/phatch-dev/"
        webbrowser.open(url)

    def on_template(self, event):
        self.template_show(event.IsChecked())

    def template_show(self, show):
        sizer = self.GetSizer()
        self.path.Show(show)
        self.code.Show(show)
        self.SetMinSize(sizer.GetMinSize())
        self.Fit()
        self.code.ShowPosition(0)


def example():

    class App(wx.App):

        def OnInit(self):
            wx.InitAllImageHandlers()
            frame = wx.Frame(None, -1, "")
            self.SetTopWindow(frame)
            frame.Show(False)
            wx.CallAfter(self.show_dialogs)
            return 1

        def show_dialogs(self):
##            self.show_error_dialog()
##            self.show_execute_dialog()
##            self.show_files_dialog()
##            self.show_progress_dialog()
            self.show_action_dialog()
            self.GetTopWindow().Destroy()

        def show_error_dialog(self):
            dlg = ErrorDialog(self.GetTopWindow(), 'message')
            dlg.ShowModal()
            dlg.Destroy()

        def show_execute_dialog(self, drop=False):
            dlg = ExecuteDialog(self.GetTopWindow(), drop)
            dlg.ShowModal()
            dlg.Destroy()

        def show_files_dialog(self):
            dlg = FilesDialog(self.GetTopWindow(), 'message', 'title',
                ['path/file'], 'warning')
            dlg.ShowModal()
            dlg.Destroy()

        def show_progress_dialog(self):
            from lib.events import send
            import time
            n = 5
            dlg = ProgressDialog(self.GetTopWindow(), 'title', 'messages', n)
            result = {}
            for value in range(n):
                send.progress_update(result, value)
                if not result['keepgoing']:
                    break
                time.sleep(1)
            dlg.Destroy()

        def show_action_dialog(self):
            from core import api
            api.init()
            dlg = ActionDialog(self.GetTopWindow(), api.ACTIONS,
                size=(400, 500))
            dlg.ShowModal()
            dlg.Destroy()

    app = App(0)
    app.MainLoop()


class ImageTreeDialog(dialogs.ImageTreeDialog):

    def __init__(self, *args, **keyw):
        super(ImageTreeDialog, self).__init__(*args, **keyw)
        self.SetSize(keyw['size'])
        self.browser.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK,
            self.on_tree_item_right_click)
        self.browser.list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK,
            self.on_list_item_right_click)

    def SetColumnWidths(self, *widths):
        self.browser.SetColumnWidths(*widths)

    def UpdateHeaders(self, headers=None):
        self.browser.UpdateHeaders(headers)

    def SetData(self, data):
        self.browser.SetData(data)

    def SetOkLabel(self, label):
        self.ok.SetLabel(label)

    def ShowButtons(self, visible):
        self.hint.Show(visible)
        self.ok.Show(visible)
        self.cancel.Show(visible)

    def _AppendMenuItem(self, menu, label, method, shortcut='', id=None):
        if id is None:
            id = wx.NewId()
        menu.Append(id, '%s\t%s' % (label, shortcut))
        self.Bind(wx.EVT_MENU, method, id=id)

    def inspect_list_item(self, index):
        self.inspect(self.browser.get_list_file(index))

    def inspect_tree_item(self, item):
        self.inspect(self.browser.get_tree_folder(item))

    def inspect(self, path):
        frame = ImageInspectorFrame(None,
            filename=path,
            size=(470, get_max_height(510)),
            icon=images.get_icon('inspector'))
        frame.Show()

    def on_tree_item_right_click(self, event):
        item = event.GetItem()
        #menu events handlers

        def on_open(event):
            self.browser.start_tree_item(item)

        def on_inspect(event):
            self.inspect_tree_item(item)

        #build menu control
        menu = wx.Menu()
        self._AppendMenuItem(menu, _('&Open...'), on_open,
            id=wx.ID_OPEN)
        self._AppendMenuItem(menu, _('&Inspect...'), on_inspect,
            id=wx.ID_FIND)

        #show menu
        self.PopupMenu(menu)
        menu.Destroy()

    def on_list_item_right_click(self, event):
        index = event.GetIndex()
        #menu events handlers

        def on_open(event):
            self.browser.start_list_item(index)

        def on_inspect(event):
            self.inspect_list_item(index)

        #build menu control
        menu = wx.Menu()
        self._AppendMenuItem(menu, _('&Open...'), on_open,
            id=wx.ID_OPEN)
        self._AppendMenuItem(menu, _('&Inspect...'), on_inspect,
            id=wx.ID_FIND)

        #show menu
        self.PopupMenu(menu)
        menu.Destroy()


class StatusDialog(dialogs.StatusDialog):

    def SetMessage(self, text, report=None):
        if report:
            wx.GetApp().report = report
        self.report.Show(bool(wx.GetApp().report))
        self.message.SetLabel(text)
        self.GetSizer().Fit(self)
        self.Layout()

    def on_button_report(self, event):
        self.GetParent().show_report()
        self.EndModal(wx.ID_OK)

    def on_button_log(self, event):
        self.GetParent().show_log()
        self.EndModal(wx.ID_OK)


class ImageInspectorGrid(imageInspector.GridTag):
    corner_logo = images.ICON_INSPECTOR_96HIGH

    def CreateRowLabelMenu(self, menu, row):
        super(ImageInspectorGrid, self).CreateRowLabelMenu(menu, row)
        if self.HasActionList():
            id_insert = wx.NewId()
            menu.Append(id_insert,
                _('&Insert Tag in Action List...') + '\tCtrl+Shift+I')

            def on_insert(event):
                self.InsertTagInActionList(row)

            self.Bind(wx.EVT_MENU, on_insert, id=id_insert)

    def ProcessKey(self, key_code, row, col, shift, ctrl, alt):
        if ctrl and shift and key_code == 73:
            self.InsertTagInActionList(row)
        return super(ImageInspectorGrid, self).ProcessKey(key_code, row, col,
            shift, ctrl, alt)

    def InsertTagInActionList(self, row):
        key = '<%s>' % self.GetRowLabelValue(row)
        frame = wx.GetApp().GetTopWindow()
        frame.tree.set_form_field_value_selected(key)

    def HasActionList(self):
        frame = wx.GetApp().GetTopWindow()
        return hasattr(frame, 'tree')


class ImageInspectorBrowser(imageInspector.Browser):
    ContentCtrl = ImageInspectorGrid
    paint_logo = images.LOGO_INSPECTOR


class ImageInspectorFrame(imageInspector.Frame):
    Browser = ImageInspectorBrowser


if __name__ == '__main__':
    example()
