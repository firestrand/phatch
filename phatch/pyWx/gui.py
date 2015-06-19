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
# Phatch recommends SPE (http://pythonide.stani.be) for python editing.

# Follows PEP8

#---Global import

#import
import new
import sys

#check wx
from lib.pyWx.wxcheck import ensure
try:
    wx = ensure('2.8', '2.8')
except:
    #sphinx
    import wx

#force wxpython2.6 for testing
#import wxversion
#wxversion.select('2.6')
#import wx

#check with other encoding
##wx.SetDefaultPyEncoding('ISO8859-15')

#standard library
import glob
import pprint
import webbrowser
import os


#---Local import

#gui-independent
from core import api
from core import ct
from core import config
from core import pil
from core.message import FrameReceiver
from lib import formField
from lib import notify
from lib import safe
from lib import system
from lib import listData
from lib.unicoding import exception_to_unicode
notify.init(ct.INFO['name'])

#gui-dependent
from lib.pyWx import droplet
from lib.pyWx import graphics
from lib.pyWx import imageFileBrowser
from lib.pyWx import imageInspector
from lib.pyWx import paint
from lib.pyWx.clipboard import copy_text

import images
import dialogs
import plugin
from wxGlade import frame

WX_ENCODING = wx.GetDefaultPyEncoding()
COMMAND_PASTE = \
    _('You can paste it as text into the properties of a new launcher.')
ERROR_INSTALL_ACTION = \
_('Sorry, you need to install the %s action for this action list.')
WARNING_LOST_VALUES = \
_('Sorry, the values of these options will be lost in %(name)s %(version)s:')
CLIPBOARD_ACTIONLIST = \
_('The droplet command for this action list was copied to the clipboard.')
CLIPBOARD_RECENT = \
_('The droplet command for recent action lists was copied to the clipboard.')
CLIPBOARD_IMAGE_INSPECTOR = \
_('The droplet command for the image inspector was copied to the clipboard.')
NO_PHOTOS = \
_('In Phatch you need to open or create an action list first.') + ' ' + \
_('As an example try out the polaroid action list from the library.') + \
'\n' + \
_('Afterwards you can drag&drop images on the Phatch window to batch them.') +\
'\n\n' + \
_('For more information see the tutorials (Help>Documentation)')
#---theme


def _theme():
    if wx.Platform != '__WXGTK__':
        set_theme('nuovext')


def set_theme(name='default'):
    if name == 'nuovext':
        from nuovext import Provider
        wx.ArtProvider.Push(Provider())

#---Functions


def findWindowById(id):
    return wx.GetApp().GetTopWindow().FindWindowById(id)


class DialogsMixin:
    _icon_filename = None

    #---dialogs
    def show_error(self, message):
        return self.show_message(message, style=wx.OK | wx.ICON_ERROR)

    def show_execute_dialog(self, result, settings, files=None):
        dlg = dialogs.ExecuteDialog(self, drop=files)
        if settings['overwrite_existing_images_forced']:
            dlg.overwrite_existing_images.Disable()
        if files:
            #store in settings, not result as it will be saved
            settings['paths'] = files
        dlg.import_settings(settings)
        result['cancel'] = dlg.ShowModal() == wx.ID_CANCEL
        if result['cancel']:
            dlg.Destroy()
            return
        #Retrieve settings from dialog
        dlg.export_settings(settings)
        dlg.Destroy()

    def show_files_message(self, result, message, title, files):
        dlg = dialogs.FilesDialog(self, message, title, files)
        x0, y0 = self.GetSize()
        x1, y1 = dlg.GetSize()
        x = max(x0, x1)
        y = max(y1, 200)
        dlg.SetSize((x, y))
        result['cancel'] = dlg.ShowModal() == wx.ID_CANCEL

    def show_message(self, message, title='',
            style=wx.OK | wx.ICON_EXCLAMATION):
        if self.IsShown():
            parent = self
        else:
            parent = None
        dlg = wx.MessageDialog(parent,
                message,
                '%(name)s ' % ct.INFO + title,
                style,
        )
        answer = dlg.ShowModal()
        dlg.Destroy()
        return answer

    def show_status(self, message, log=True):
        dlg = dialogs.StatusDialog(self)
        dlg.log.Show(log)
        dlg.SetMessage(message)
        dlg.ShowModal()
        dlg.Destroy()

    def show_question(self, message, style=wx.YES_NO | wx.ICON_QUESTION):
        return self.show_message(message, style=style)

    def show_image_tree(self, result, image_infos, widths, headers,
            ok_label='&OK', buttons=False, modal=False):
        data = listData.files_data_dict(image_infos)
        dlg = dialogs.ImageTreeDialog(data, listData.DataDict, headers,
            self, size=(600, dialogs.get_max_height(300)))
        dlg.SetColumnWidths(*widths)
        dlg.SetOkLabel(ok_label)
        dlg.ShowButtons(buttons)
        if modal or buttons:
            answer = dlg.ShowModal()
            result['answer'] = answer == wx.ID_OK
        else:
            dlg.Show()

    def show_report(self):
        report = wx.GetApp().report
        if report:
            self.show_image_tree({}, report,
                widths=(200, 60, 60, 60, 500),
                headers=['filename', 'width', 'height', 'mode',
                    'source'],
                buttons=False,
                modal=not isinstance(self, Frame))
        else:
            self.show_message(_('No images have been processed to report.'))

    def show_log(self):
        if os.path.exists(ct.USER_LOG_PATH):
            log_file = open(ct.USER_LOG_PATH)
            msg = log_file.read().strip()
            log_file.close()
            if not msg:
                msg = _('Hooray, no issues!')
        else:
            msg = _('Nothing has been logged yet.')
        self.show_scrolled_message(msg, '%s - %s' \
            % (_('Log'), ct.USER_LOG_PATH))

    def show_info(self, message, title=''):
        return self.show_message(message, title,
            style=wx.OK | wx.ICON_INFORMATION)

    def show_progress(self, title, parent_max, child_max=1, message=''):
        dlg = dialogs.ProgressDialog(self, title, parent_max, child_max,
            message)

    def show_progress_error(self, result, message, ignore=True):
        message += '\n\n' + api.SEE_LOG
        errorDlg = dialogs.ErrorDialog(self, message, ignore)
        answer = errorDlg.ShowModal()
        result['stop_for_errors'] = not errorDlg.future_errors.GetValue()
        errorDlg.Destroy()
        if answer == wx.ID_ABORT:
            result['answer'] = _('abort')
            self.show_log()
        elif answer == wx.ID_FORWARD:
            result['answer'] = _('skip')
        else:
            result['answer'] = _('ignore')

    def show_scrolled_message(self, message, title, **keyw):
        import wx.lib.dialogs
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, message, title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.MAXIMIZE_BOX | wx.RESIZE_BORDER,
            **keyw)
        dlg.ShowModal()

    def show_notification(self, message, force=False, report=None):
        self.set_report(report)
        active = wx.GetApp().IsActive() or self.IsActive()
        if force or not active:
            notify.send(
                title=system.filename_to_title(self.filename),
                message=message,
                icon=self.get_icon_filename(),
                wxicon=graphics.bitmap(images.ICON_PHATCH_64))
        if not active:
            self.RequestUserAttention()

    #---settings
    def get_setting(self, name):
        return wx.GetApp().settings[name]

    def set_setting(self, name, value):
        wx.GetApp().settings[name] = value

    #---data
    def load_actionlist_data(self, filename):
        if not os.path.exists(filename):
            return
        try:
            data, warnings = api.open_actionlist(filename)
        except KeyError, details:
            self.show_error(ERROR_INSTALL_ACTION\
                % exception_to_unicode(details, WX_ENCODING))
            return
        except:
            self.show_error(api.ERROR_INCOMPATIBLE_ACTIONLIST % ct.INFO)
            return
        if data['invalid labels']:
            self.show_message('\n'.join([
            _('This action list was made by a different %(name)s version.')\
                % ct.INFO + '\n\n' + \
            WARNING_LOST_VALUES % ct.INFO + '\n',
            '\n'.join(data['invalid labels'])]))
        if warnings:
            if formField.get_safe():
                self.show_error('%s\n\n%s\n%s' % (
                    api.ERROR_UNSAFE_ACTIONLIST_INTRO, warnings,
                    api.ERROR_UNSAFE_ACTIONLIST_DISABLE_SAFE))
                return
            else:
                wx.CallAfter(self.show_error, '%s\n\n%s\n%s' % (
                    api.ERROR_UNSAFE_ACTIONLIST_INTRO, warnings,
                    api.ERROR_UNSAFE_ACTIONLIST_ACCEPT))
        return data

    #---notification
    def _execute(self, actionlist, **keyw):
        app = wx.GetApp()
        self.set_report([])
        api.apply_actions_to_photos(actionlist, app.settings,
            update=self._send_update_event, **keyw)

    def _send_update_event(self):
        update_event = imageInspector.UpdateEvent()
        for frame in wx.GetTopLevelWindows():
            if frame != self:
                wx.PostEvent(frame, update_event)

    def set_report(self, report):
        wx.GetApp().report = report

    def get_icon_filename(self):
        if self._icon_filename == None:
            self._icon_filename = os.path.join(
                self.get_setting("PHATCH_IMAGE_PATH"), 'icons',
                    '48x48', 'phatch.png')
        return self._icon_filename


class Frame(DialogsMixin, dialogs.BrowseMixin, droplet.Mixin, paint.Mixin,
        frame.Frame, FrameReceiver):
    DEFAULT_PAINT_MESSAGE = _("click '+' to add actions")
    paint_message = DEFAULT_PAINT_MESSAGE
    paint_color = images.LOGO_COLOUR
    paint_logo = images.LOGO

    def __init__(self, actionlist, *args, **keyw):
        frame.Frame.__init__(self, *args, **keyw)
        _theme()
        self.dlg_library = None
        self.dirty = False
        self.EnableBackgroundPainting(self.empty)
        self._menu()
        self._toolBar()
        self._plugin()
        self.on_menu_file_new()
        images.set_icon(self, 'phatch')
        self._title()
        self._description()
        self._drop()
        self._set_size()
        self._events()
        self._pubsub()
        if actionlist.endswith(ct.EXTENSION):
            self._open(actionlist)

    def _set_size(self):
        #make it eee pc friendly
        self._width = 400
        self._max_height = dialogs.get_max_height()
        self.SetSize((self._width, min(600, self._max_height)))
        super(Frame, self).__set_properties()

    def _plugin(self):
        plugin.install_frame(self)

    def _description(self):
        self.show_description(False)

    def _drop(self):
        self.SetAsFileDropTarget(self.tree, self.on_drop)

    def _menu(self):
        #export menu
        self.menu_file_export = \
            self.menu_file_export_actionlist_to_clipboard.GetMenu()
        #file history
        self.menu_file_recent = wx.Menu()
        self.filehistory = wx.FileHistory()
        self.filehistory.UseMenu(self.menu_file_recent)
        self._set_file_history(self.get_setting('file_history'))
        self.Bind(wx.EVT_MENU_RANGE, self.on_menu_file_history,
            id=wx.ID_FILE1, id2=wx.ID_FILE9)
        self.menu_file.InsertMenu(2, wx.ID_REFRESH,
            _("Open &Recent"),
            self.menu_file_recent, "")

        #library
        #actionlists = [(system.filename_to_title(a), a)
        #    for a in wx.GetApp().get_action_list_files()]
        #actionlists.sort()
        #library = self.menu_file_library = wx.Menu()
        #prefix = len(actionlists) < 10
        #self.library_files = {}
        #for index, actionlist in enumerate(actionlists):
        #    id = wx.NewId()
        #    label = actionlist[0]
        #    if prefix:
        #        label = '&%d %s' % (index + 1, label)
        #    item = library.Append(id, label)
        #    self.library_files[id] = actionlist[1]
        #    self.Bind(wx.EVT_MENU, self.on_menu_file_library, item)
        ##wx2.6 compatible
        #wx_ID_EDIT = 5030
        #self.menu_file.InsertMenu(3, wx_ID_EDIT, _("Open &Library"),
        #   library, "")
        self.library_files_dictionary = formField.files_dictionary(
                    paths=[config.PATHS["PHATCH_ACTIONLISTS_PATH"],
                    ct.USER_ACTIONLISTS_PATH],
                    extensions=['png'])

        #shell
        self.shell = None
        #menu_item (for enabling/disabling)
        edit = [getattr(self, attr) for attr in dir(self)
            if attr[:10] == 'menu_edit_']
        edit.remove(self.menu_edit_add)
        view = [getattr(self, attr) for attr in dir(self)
            if attr[:10] == 'menu_view_']
        self.menu_item = [
            (self.menu_file, [
                self.menu_file_new.GetId(),
                self.menu_file_save.GetId(),
                self.menu_file_save_as.GetId()]),
            (self.menu_edit, [item.GetId() for item in edit]),
            (self.menu_view, [item.GetId() for item in view]),
            (self.menu_tools, [
                self.menu_tools_execute.GetId(),
                self.menu_tools_show_report.GetId(),
                self.menu_tools_show_log.GetId()]),
            (self.menu_file_export, [
                self.menu_file_export_actionlist_to_clipboard.GetId()])]
        self.on_show_droplet(False)
        # Mac  tweaks
        if wx.Platform == "__WXMAC__":
            #todo: about doesn't seem to work: why?!
            app = wx.GetApp()
            #app.SetMacHelpMenuTitleName(_('&Help'))
            app.SetMacAboutMenuItemId(wx.ID_ABOUT)
            app.SetMacExitMenuItemId(wx.ID_EXIT)
            #app.SetMacPreferencesMenuItemId(wx.ID_PREFERENCES)
        else:
            self.menu_file.InsertSeparator(8)

    def _title(self):
        path, filename = os.path.split(self.filename)
        self.SetTitle(ct.FRAME_TITLE\
            % (self.dirty, os.path.splitext(filename)[0]))
        self.frame_statusbar.SetStatusText(path)
        self.SetStatusText(ct.COPYRIGHT)

    def is_protected_actionlist(self, filename):
        return config.PATHS["PHATCH_ACTIONLISTS_PATH"] == \
            os.path.dirname(filename)

    #---toolBar
    def add_tool(self, bitmap, label, tooltip, method, item=wx.ITEM_NORMAL):
        id = wx.NewId()
        bitmap = graphics.bitmap(bitmap, self.tool_bitmap_size,
                    client=wx.ART_TOOLBAR)
        args = (id, label, bitmap, wx.NullBitmap, item,
                    tooltip, "")
        tool = self.frame_toolbar.AddLabelTool(*args)
        self.Bind(wx.EVT_TOOL, method, id=id)
        return tool

    def _toolBar(self):
        self.tool_bitmap_size = (32, 32)
        self.frame_toolbar = wx.ToolBar(self, -1, style=wx.TB_FLAT)
        self.SetToolBar(self.frame_toolbar)
        self.frame_toolbar.SetToolBitmapSize(self.tool_bitmap_size)
        tools_item_other = [
            self.add_tool('ART_FILE_OPEN', _("Open"),
                _("Open an action list"), self.on_menu_file_open)]
        tools_item = [
            self.add_tool('ART_EXECUTABLE_FILE', _("Execute"),
                _("Execute the action"), self.on_menu_tools_execute)]
        self.frame_toolbar.AddSeparator()
        tools_item_other.extend([
            self.add_tool('ART_ADD_BOOKMARK', _("Add"),
                _("Add an action"), self.on_menu_edit_add)])
        tools_item.extend([
            self.add_tool('ART_DEL_BOOKMARK', _("Remove"),
                _("Remove the selected action"), self.on_menu_edit_remove),
            self.add_tool('ART_GO_UP', _("Up"),
                _("Move the selected action up"), self.on_menu_edit_up),
            self.add_tool('ART_GO_DOWN', _("Down"),
                _("Move the selected action down"), self.on_menu_edit_down)])
        self.frame_toolbar.AddSeparator()
        tools_item_other.extend([
            self.add_tool('ART_FIND', _("Image Inspector"),
                _("Look up exif and iptc tags"),
                self.on_menu_tools_image_inspector)])
        self.frame_toolbar.AddSeparator()
        self.toolbar_description = self.add_tool('ART_TIP', _("Description"),
            _("Show description of the action list"),
            self.on_menu_view_description, item=wx.ITEM_CHECK)
        tools_item.extend([self.toolbar_description])
        self.tools_item = [tool.GetId() for tool in tools_item]
        self.tools_all = tools_item + \
            [tool.GetId() for tool in tools_item_other]
        self._menu_toolbar_state = True
        self.frame_toolbar.Realize()

    def enable_actions(self, state=True):
        if state != self._menu_toolbar_state:
            for tool in self.tools_item:
                self.frame_toolbar.EnableTool(tool, state)
            for menu, items in self.menu_item:
                for item in items:
                    menu.Enable(item, state)
            self._menu_toolbar_state = state
            self.tree.Show(state)
            self.empty.Show(not state)
            self.show_description(state and self.get_setting('description'))

    def enable_menu(self, state=True):
        self._menu_toolbar_state = None
        menu = self.frame_menubar
        for index in range(menu.GetMenuCount()):
            menu.EnableTop(index, state)

    def enable_toolbar(self, state=True):
        self._menu_toolbar_state = None
        for tool in self.tools_all:
            self.frame_toolbar.EnableTool(tool, state)

    def show_paint_message(self, message=None):
        if message == None:
            self.paint_message = self.DEFAULT_PAINT_MESSAGE
        else:
            self.paint_message = message
        self.Refresh()

#---menu events
    def on_menu_file_new(self, event=None):
        if self.is_save_not_ok():
            return
        self._set_filename(ct.UNKNOWN)
        self.description.SetValue(ct.ACTION_LIST_DESCRIPTION)
        self.saved_description = ct.ACTION_LIST_DESCRIPTION
        self._new()
        self.enable_actions(False)

    def on_menu_file_open_library(self, event):
        if self.is_save_not_ok():
            return
        if not self.dlg_library:
            self.dlg_library = imageFileBrowser.Dialog(
                parent=self,
                files=self.library_files_dictionary,
                title=_('Library Action Lists'),
                size=(self.GetSize()[0], 370),
                icon_size=(128, 128))
            self.dlg_library.image_list.Select(0)
        if self.dlg_library.ShowModal() == wx.ID_OK:
            filename = self.dlg_library.image_path.GetValue()
            filename = self.library_files_dictionary.get(filename, filename)\
                .replace('.png', '.phatch')
            #21/9/2009 may be removed
            #save_filename = os.path.join(ct.USER_ACTIONLISTS_PATH,
            #    os.path.basename(filename))
            self._open(filename)
        self.dlg_library.Hide()
        return

    def on_menu_file_open(self, event):
        if self.is_save_not_ok():
            return
        dlg = wx.FileDialog(self,
            message=_('Choose an Action List File...'),
            defaultDir=os.path.dirname(self.filename),
            wildcard=ct.WILDCARD,
            style=wx.OPEN,
        )
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            self._open(filename)
        dlg.Destroy()

    #def on_menu_file_library(self, event):
    #    if self.is_save_not_ok():
    #        return
    #    filename = self.library_files[event.GetId()]
    #    save_filename = os.path.join(ct.USER_ACTIONLISTS_PATH,
    #        os.path.basename(filename))
    #    self._open(filename, save_filename)
    def on_menu_file_save(self, event):
        if self.filename == ct.UNKNOWN \
                or self.is_protected_actionlist(self.filename):
            return self.on_menu_file_save_as()
        else:
            self._save()
            return True

    def on_menu_file_save_as(self, event=None):
        if self.is_protected_actionlist(self.filename) \
                or not os.path.isfile(self.filename):
            default_dir = ct.USER_ACTIONLISTS_PATH
        else:
            default_dir = os.path.dirname(self.filename)
        dlg = wx.FileDialog(self,
            message=_('Save Action List As...'),
            defaultDir=default_dir,
            wildcard=ct.WILDCARD,
            style=wx.SAVE | wx.OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() == wx.ID_OK:
            saved = True
            path = dlg.GetPath()
            if dlg.GetFilterIndex() == 0 \
                    and not os.path.splitext(path)[1]:
                path += ct.EXTENSION
                if os.path.exists(path) and self.show_question('%s %s'\
                        % (_('This file exists already.'),
                        _('Do you want to overwrite it?'))) == wx.ID_NO:
                    saved = False
            if saved:
                self._save(path)
        else:
            saved = False
        dlg.Destroy()
        return saved

    def on_menu_file_export_actionlist_to_clipboard(self, event):
        if self.is_save_not_ok():
            return
        copy_text(ct.COMMAND['DROP'] % self.filename)
        self.show_info(' '.join([CLIPBOARD_ACTIONLIST, COMMAND_PASTE]))

    def on_menu_file_export_recent_to_clipboard(self, event):
        if self.is_save_not_ok():
            return
        copy_text(ct.COMMAND['RECENT'])
        self.show_info(' '.join([CLIPBOARD_RECENT, COMMAND_PASTE]))

    def on_menu_file_export_inspector_to_clipboard(self, event):
        if self.is_save_not_ok():
            return
        copy_text(ct.COMMAND['INSPECTOR'])
        self.show_info(' '.join([CLIPBOARD_IMAGE_INSPECTOR,
            COMMAND_PASTE]))

    def on_menu_file_quit(self, event):
        self.on_close()

    def on_menu_file_history(self, event):
        if self.is_save_not_ok():
            return
        # get the file based on the menu ID
        filenum = event.GetId() - wx.ID_FILE1
        filename = self.filehistory.GetHistoryFile(filenum)
        self._open(filename)

    def on_menu_edit_add(self, event):
        settings = wx.GetApp().settings
        if not hasattr(self, 'dialog_actions'):
            self.dialog_actions = dialogs.ActionDialog(self,
                api.ACTIONS, settings['tag_actions'],
                size=(self._width, min(400, self._max_height)),
                title=_("%(name)s actions") % ct.INFO)
        if self.dialog_actions.ShowModal() == wx.ID_OK:
            self.set_dirty(True)
            label = self.dialog_actions.GetStringSelection()
            self.tree.append_form_by_label_to_selected(label)
            self.enable_actions(True)
        self.dialog_actions.Hide()

    def on_menu_edit_remove(self, event):
        if self.tree.remove_selected_form():
            if self.IsEmpty():
                self.enable_actions(False)
                self.set_dirty(False)
            else:
                self.set_dirty(True)

    def on_menu_edit_up(self, event):
        self.set_dirty(True)
        self.tree.move_form_selected_up()

    def on_menu_edit_down(self, event):
        self.set_dirty(True)
        self.tree.move_form_selected_down()

    def on_menu_edit_enable(self, event):
        self.tree.enable_selected_form(True)

    def on_menu_edit_disable(self, event):
        self.tree.enable_selected_form(False)

    def on_menu_view_droplet(self, event):
        self.show_droplet(event.IsChecked())

    def droplet_label_format(self, x):
        #return '123456789012345678901234567890'
        return x  # [:18]

    def on_menu_view_description(self, event):
        self.show_description(event.IsChecked())

    def on_menu_view_expand_all(self, event):
        self.tree.expand_forms()

    def on_menu_view_collapse_all(self, event):
        self.tree.collapse_forms()

    def on_menu_view_collapse_automatic(self, event):
        self.enable_collapse_automatic(event.IsChecked())

    def on_menu_tools_execute(self, event):
        actionlist = self.tree.export_forms()
        self._execute(actionlist)

    def on_menu_tools_safe(self, event):
        self.set_safe_mode(event.IsChecked())

    def on_menu_tools_image_inspector(self, event):
        frame = dialogs.ImageInspectorFrame(self,
            size=(470, dialogs.get_max_height(510)),
            icon=images.get_icon('inspector'))
        frame.Show()

    def on_menu_tools_browse_library_user(self, event):
        system.start(wx.GetApp().settings['USER_DATA_PATH'])

    def on_menu_tools_browse_library_phatch(self, event):
        system.start(wx.GetApp().settings['PHATCH_DATA_PATH'])

    def on_menu_tools_show_report(self, event):
        self.show_report()

    def on_menu_tools_show_log(self, event):
        self.show_log()

    def on_menu_tools_update_fonts(self, event):
        config.check_fonts(True)

    def on_menu_tools_python_shell(self, event):
        from lib.pyWx import shell
        self.tree.close_popup()
        if self.shell is None:
            title = ct.TITLE.lower()
            self.shell = shell.Frame(self,
                title=_('%(name)s Shell') % ct.INFO,
                intro='%(name)s ' % ct.INFO,
                values={
                    '%s_%s' % (title, _('application')): wx.GetApp(),
                    '%s_%s' % (title, _('frame')): self,
                    '%s_%s' % (title, _('actions')): self.tree.export_forms,
                    },
                icon=graphics.bitmap(images.ICON_PHATCH_64),
            )
        self.shell.Show(event.IsChecked())

    def on_menu_help_website(self, event):
        webbrowser.open('http://photobatch.stani.be')

    def on_menu_help_documentation(self, event):
        webbrowser.open('http://photobatch.stani.be/documentation')

    def on_menu_help_forum(self, event):
        webbrowser.open('http://photobatch.stani.be/forum')

    def on_menu_help_translate(self, event):
        webbrowser.open(
            'https://translations.launchpad.net/phatch/trunk/+pots/phatch')

    def on_menu_help_bug(self, event):
        webbrowser.open('https://bugs.launchpad.net/phatch')

    def on_menu_help_plugin(self, event):
        help_path = self.get_setting("PHATCH_DOCS_PATH")
        help_file = os.path.join(help_path, 'index.html')
        if not os.path.exists(help_file):
            #debian/ubuntu
            help_file = os.path.join(help_path, 'build', 'html',
                'index.html')
        if not os.path.exists(help_file):
            #ppa
            help_file = os.path.join(sys.prefix, 'share', 'phatch', 'docs',
                'index.html')
        webbrowser.open(help_file)
        dlg = dialogs.WritePluginDialog(self, '\n'.join([
            _('A html tutorial will open in your internet browser.'),
            '',
            _('You only need to know PIL to write a plugin for Phatch.'),
            _('Phatch will generate the user interface automatically.'),
            _('Study the action plugins in:') + ' ' + ct.PHATCH_ACTIONS_PATH,
            '',
            _('If you want to contribute a plugin for Phatch,'),
            _('please email: ') + ct.CONTACT]))
        dlg.ShowModal()
        #settings in mixin because now app bas, also config_path

    def on_menu_help_about(self, event):
        from lib.pyWx import about
        from data.info import all_credits
        dlg = about.Dialog(self,
            title='%(version)s' % ct.INFO,
            logo=graphics.bitmap(images.LOGO),
            description=_('PHoto bATCH Processor'),
            website=ct.INFO['url'],
            credits=all_credits(),
            license=ct.LICENSE,
        )
        dlg.ShowModal()
        dlg.Destroy()

    #---helper
    def _new(self):
        self.set_dirty(False)
        self.tree.delete_all_forms()

    def _open(self, filename):
        self._new()
        if not os.path.exists(filename):
            self.show_error(_('Sorry, "%s" is not a valid path.' % filename))
            return
        if system.file_extension(filename) in pil.IMAGE_READ_EXTENSIONS:
            self.show_error(NO_PHOTOS)
            filename = self.library_files_dictionary['Polaroid']\
                .replace('.png', '.phatch')
        data = self.load_actionlist_data(filename)
        if data:
            description = data.get('description', '')
            self.show_description(bool(description))
            if description:
                wx.FutureCall(5000, self.show_description, False)
            if not description:
                description = ct.ACTION_LIST_DESCRIPTION
            self.description.SetValue(description)
            self.saved_description = description
            if self.tree.append_forms(data['actions']):
                self.enable_actions(True)
            self._set_filename(filename)
            # add it to the history
            if not self.is_protected_actionlist(filename):
                self.filehistory.AddFileToHistory(filename)
        elif self.IsEmpty():
            self.enable_actions(False)
            self.set_dirty(False)

    def _save(self, filename=None):
        if filename:
            self._set_filename(filename)
        description = self.description.GetValue()
        self.saved_description = description
        if description == ct.ACTION_LIST_DESCRIPTION:
            description = ''
        data = {
            'description': description,
            'actions': self.tree.export_forms(),
        }
        api.save_actionlist(self.filename, data)
        self.set_dirty(False)
        if filename:
            # add it to the history
            self.filehistory.AddFileToHistory(filename)

    def _set_filename(self, filename):
        self.filename = filename
        self.set_dirty(False)

    #---view show/hide
    def enable_collapse_automatic(self, checked):
        self.set_setting('collapse_automatic', checked)
        self.menu_view.Check(self.menu_view_collapse_automatic.GetId(),
            checked)
        self.tree.enable_collapse_automatic(checked)

    def show_description(self, checked):
        self.set_setting('description', checked)
        self.description.Show(checked)
        self.menu_view.Check(self.menu_view_description.GetId(), checked)
        self.frame_toolbar.ToggleTool(self.toolbar_description.GetId(),
            checked)
        self.Layout()

    def show_droplet(self, checked):
        if checked:
            if api.check_actionlist(self.tree.export_forms(),
                    wx.GetApp().settings):
                self.droplet = droplet.Frame(self,
                    title=_("Drag & Drop") + ' - ' + ct.TITLE,
                    bitmap=graphics.bitmap(images.DROPLET),
                    method=self.on_drop,
                    label=self.droplet_label_format(
                        system.filename_to_title(self.filename)),
                    label_color=wx.Colour(217, 255, 186),
                    label_pos=(8, 8),
                    label_angle=0,
                    pos=self.GetPosition(),
                    auto=True,
                    OnShow=self.on_show_droplet,
                    tooltip=_(
                    "Drop any files and/or folders on this Phatch droplet\n"
                    "to batch process them.\n"
                    "Right-click or double-click to switch to normal view."))
            else:
                wx.CallAfter(self.on_show_droplet, False)
        else:
            if self.droplet:
                self.droplet.show(False)

    def on_show_droplet(self, bool):
        self.menu_view.Check(self.menu_view_droplet.GetId(), bool)
        if not bool:
            self.droplet = None  # don't keep a reference

    #---checks
    def append_save_action(self, actions):
        only_metadata = self.only_actions_with_tag(actions, 'metadata')
        message = ct.SAVE_ACTION_NEEDED + " " + \
            _("Phatch will add one for you, please check its settings.")
        if only_metadata:
            message += ' \n\n%s%s' % (\
            _('The action list only processes metadata.'),
            _('Phatch chooses the lossless "Save Tags" action.'))
        self.show_message(message)
        if only_metadata:
            self.tree.append_form_by_label_to_last('Save Tags')
        else:
            self.tree.append_form_by_label_to_last('Save')

    def only_actions_with_tag(self, actions, tag):
        for action in actions:
            if tag not in action.tags:
                return False
        return True

    #---other events
    def _events(self):
        #wxPython events
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.Bind(wx.EVT_SIZE, self.on_size, self)
        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.on_menu_tool_enter)
        self.Bind(wx.EVT_TOOL_ENTER, self.on_menu_tool_enter)
        self.Bind(wx.EVT_TEXT, self.on_description_text, self.description)
        self.tree.Bind(wx.EVT_TREE_END_DRAG, self.on_tree_end_drag, self.tree)
        self.tree.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu, self.tree)

    def on_description_text(self, event):
        if not self.dirty and event.GetString() != self.saved_description:
            self.set_dirty(True)

    def on_drop(self, filenames, x, y):
        api.apply_actions_to_photos(self.tree.export_forms(),
            wx.GetApp().settings, paths=filenames, drop=True)

    def on_menu_tool_enter(self, event):
        self.tree.close_popup()
        event.Skip()

    def on_tree_end_drag(self, event):
        event.Skip()
        wx.CallAfter(self.set_dirty, True)

    def on_context_menu(self, event):
        if self.tree.is_form_selected():
            self.tree.PopupMenu(self.menu_edit)

    def is_save_not_ok(self):
        if self.dirty:
            answer = self.show_message(_('Save last changes to') + '\n"%s"?'\
                % self.filename,
                style=wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)
            if answer == wx.ID_CANCEL:
                return True
            if answer == wx.ID_YES:
                return not self.on_menu_file_save(None)
        return False

    def on_close(self, event=None):
        if self.is_save_not_ok():
            return
        self.Hide()
        wx.GetApp()._saveSettings()
        #Destroy everything
        self.Destroy()

    def on_size(self, event):
        event.Skip()
        if self.IsEmpty():
            self.empty.Refresh()
        else:
            self.tree.resize_popup()

    def IsEmpty(self):
        return not self.tree.has_forms()

    #---file history
    def _get_file_history(self):
        result = []
        for index in range(self.filehistory.GetCount()):
            filename = self.filehistory.GetHistoryFile(index)
            if filename.strip():
                result.append(filename)
        return result

    def _set_file_history(self, files):
        files.reverse()
        for filename in files:
            if os.path.exists(filename):
                self.filehistory.AddFileToHistory(filename)

    #---settings
    def set_dirty(self, value):
        self.dirty = ('', '*')[value]
        self._title()

    def set_safe_mode(self, state):
        if state == False:
            answer = self.show_question(
                _('Safe mode protects you from the execution of possibly '\
                'harmful scripts.\nAre you sure you want to disable it?'),
                style=wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT)
            if answer != wx.ID_YES:
                self.menu_tools.Check(self.menu_tools_safe.GetId(), True)
                return
        formField.set_safe(state)

    #---droplet
    def get_droplet_folder(self):
        folder = self.show_dir_dialog(
            defaultPath=self.get_setting('droplet_path'),
            message=_('Choose the folder for the droplet'))
        if folder:
            self.set_setting('droplet_path', folder)
        return folder

    def menu_file_export_droplet(self, method, *args, **keyw):
        folder = self.get_droplet_folder()
        if folder is None:
            return
        try:
            method(folder=folder, *args)
            self.show_info(_('Phatch successfully created the droplet.'))
        except Exception, details:
            reason = exception_to_unicode(details, WX_ENCODING)
            self.show_error(_('Phatch could not create the droplet: ')\
                + '\n\n' + reason)

    def install_menu_item(self, menu, name, label, method, tooltip="",
            style=wx.ITEM_NORMAL):
        #item
        item = wx.MenuItem(menu, -1, label, tooltip, style)
        setattr(self, name, item)
        menu.InsertItem(0, item)
        #method
        method_name = 'on_' + name
        method = new.instancemethod(method, self, self.__class__)
        setattr(self, method_name, method)
        #bind item & method
        self.Bind(wx.EVT_MENU, method, item)
        #return id
        return item.GetId()

#---Image Inspector


class ImageInspectorApp(wx.App):

    def __init__(self, paths, *args, **keyw):
        self.paths = paths
        super(ImageInspectorApp, self).__init__(*args, **keyw)

    def OnInit(self):
        wx.InitAllImageHandlers()
        _theme()
        frame = dialogs.ImageInspectorFrame(None,
            size=dialogs.imageInspector.SIZE)
        images.set_icon(frame, 'inspector')
        frame.OpenImages(self.paths)
        frame.Show()
        self.SetTopWindow(frame)
        return 1


def inspect(paths):
    app = ImageInspectorApp(paths, 0)
    app.MainLoop()

#---Droplet


class DropletFrame(DialogsMixin, wx.Frame, FrameReceiver):

    def __init__(self, actionlist, paths, *args, **keyw):
        wx.Frame.__init__(self, *args, **keyw)
        self.filename = actionlist
        self._pubsub()
        data = self.load_actionlist_data(actionlist)
        if data:
            wx.CallAfter(self.execute, data['actions'], paths=paths)
        else:
            sys.exit(_('Impossible to load data from action list.'))

    def execute(self, actionlist, paths):
        self._execute(actionlist, paths=paths, drop=True)
        self.Destroy()


class DropletMixin:

    def OnInit(self):
        wx.InitAllImageHandlers()
        #do all application initialisation
        self.init()
        api.init()
        self.report = []
        #check for action list
        if self.actionlist == 'recent':
            self.actionlist = self.get_action_list(
                self.get_action_list_files() + \
                self.settings['file_history'])
        if self.actionlist is None:
            return 0
        #create frame
        frame = DropletFrame(self.actionlist, self.paths, None, -1, ct.TITLE)
        frame.Hide()
        self.SetTopWindow(frame)
        return 1

    def get_action_list_files(self):
        return glob.glob(os.path.join(ct.USER_ACTIONLISTS_PATH,
                '*' + ct.EXTENSION)) +\
            glob.glob(os.path.join(config.PHATCH_ACTIONLISTS_PATH,
                '*' + ct.EXTENSION))

    def get_action_list(self, file_list):
        if not file_list:
            file_list = self.get_action_list_files()
        d = {}
        for f in file_list:
            d[system.filename_to_title(f)] = f
        actionlists = d.keys()
        actionlists.sort()
        dlg = wx.SingleChoiceDialog(None, _('Select action list'), ct.TITLE,
            actionlists, wx.CHOICEDLG_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            actionlist = d[dlg.GetStringSelection()]
        else:
            actionlist = None
        dlg.Destroy()
        return actionlist

    def init(self):
        pass

    def _loadSettings(self, settings):
        self.settings = settings
        if os.path.exists(ct.USER_SETTINGS_PATH):
            f = open(ct.USER_SETTINGS_PATH, 'rb')
            #exclude paths as they should not be overwritten
            try:
                items = safe.eval_restricted(f.read(),
                    allowed=['True', 'False']).items()
            except:
                sys.stdout.write(' '.join([
                    _('Sorry, your settings seem corrupt.'),
                    _('Please delete "%s".' % ct.USER_SETTINGS_PATH),
                    _('Also check if your hard disk not full.\n')]))
                sys.exit()
            f.close()
            for key, value in items:
                #FIXME: paths should not be in settings
                if not 'PATH' in key:
                    self.settings[key] = value

    def _saveSettings(self):
        f = open(ct.USER_SETTINGS_PATH, 'wb')
        settings = self.settings.copy()
        # non permanent settings
        for key in ('desktop', 'safe', 'no_save'):
            if key in settings:
                del settings[key]
        f.write(pprint.pformat(settings))
        f.close()


class DropletApp(DropletMixin, wx.App):

    def __init__(self, actionlist, paths, settings, *args, **keyw):
        self.actionlist = actionlist
        self.paths = paths
        self._loadSettings(settings)
        super(DropletApp, self).__init__(*args, **keyw)


def drop(actionlist, paths, settings):
    app = DropletApp(actionlist, paths, settings, 0)
    app.MainLoop()

#---Application


class App(DropletMixin, wx.App):

    def __init__(self, settings, actionlist, *args, **keyw):
        self._loadSettings(settings)
        self.filename = actionlist
        super(App, self).__init__(*args, **keyw)

    def OnInit(self):
        wx.InitAllImageHandlers()
        #frame
        self.splash = self._splash()
        self.splash.CentreOnScreen()
        self.SetTopWindow(self.splash)
        self.splash.Show()
        self.report = []
        wx.CallAfter(self.show_frame)
        return 1

    def MacReopenApp(self):
        """Called when the doc icon is clicked, and ???"""
        #TODO: test if this is working
        self.GetTopWindow().Raise()

    def _splash(self):
        return droplet.Frame(None,
            title=ct.TITLE,
            bitmap=graphics.bitmap(images.SPLASH),
            splash=True,
        )

    def show_frame(self):
        #do all application initialisation
        self.init()
        api.init()
        #create frame
        frame = Frame(self.filename, None, -1, ct.TITLE)
        frame.menu_tools.Check(frame.menu_tools_safe.GetId(),
            formField.get_safe())
        frame.CentreOnScreen()
        frame.Show()
        self.SetTopWindow(frame)
        frame.enable_collapse_automatic(self.settings['collapse_automatic'])
        #delete splash
        self.splash.Hide()
        self.splash.Destroy()
        del self.splash

    def init(self):
        super(App, self).init()

    def _saveSettings(self):
        frame = self.GetTopWindow()
        self.settings['file_history'] = frame._get_file_history()
        if hasattr(frame, 'dialog_actions'):
            if frame.dialog_actions:
                self.settings['tag_actions'] = \
                    frame.dialog_actions.GetTagSelection()
        super(App, self)._saveSettings()


def main(settings, actionlist):
    app = App(settings, actionlist, 0)
    app.MainLoop()


if __name__ == "__main__":
    main()
