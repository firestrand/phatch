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
import types
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
from phatch.services import (
    ActionListService,
    IncompatibleActionListError,
    MissingRequiredActionError,
    UnsafeActionListError,
)
notify.init(ct.INFO['name'])

#gui-dependent
from lib.pyWx import droplet
from lib.pyWx import graphics
from lib.pyWx import imageFileBrowser
from lib.pyWx import imageInspector
from lib.pyWx import paint
from lib.pyWx.clipboard import copy_text

from . import images
from . import dialogs
from . import plugin
from .controller import ActionListController
from .droplet_manager import DropletManager
from phatch.services.action_advisor import ActionListAdvisor
from phatch.services.file_dialogs import FileDialogService
from phatch.services.shell_launcher import ShellLauncher
from .ui_descriptors import (
    HELP_LINKS,
    MENU_ENABLE_GROUPS,
    TOOLBAR_SPEC,
    build_menu_groups,
    build_toolbar,
)
from .wxGlade import frame


def _ensure_phatch_suffix(path):
    root, ext = os.path.splitext(path)
    if ext.lower() != ct.EXTENSION:
        return f"{path}{ct.EXTENSION}"
    return path

WX_ENCODING = 'utf-8'  # wxPython 4.x always uses UTF-8
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
        from .nuovext import Provider
        wx.ArtProvider.Push(Provider())

#---Functions


def findWindowById(id):
    return wx.GetApp().GetTopWindow().FindWindowById(id)


class DialogsMixin:
    _icon_filename = None

    @property
    def action_service(self):
        if not hasattr(self, '_action_service'):
            self._action_service = ActionListService()
        return self._action_service

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
        dialogs.ProgressDialog(self, title, parent_max, child_max,
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
            return None
        try:
            result = self.action_service.load(filename)
        except MissingRequiredActionError as details:
            original = getattr(details, 'original_exception', details)
            self.show_error(ERROR_INSTALL_ACTION % exception_to_unicode(
                original, WX_ENCODING))
            return None
        except UnsafeActionListError as details:
            self.show_error('%s\n\n%s\n%s' % (
                api.ERROR_UNSAFE_ACTIONLIST_INTRO,
                details.warning,
                api.ERROR_UNSAFE_ACTIONLIST_DISABLE_SAFE))
            return None
        except IncompatibleActionListError:
            self.show_error(api.ERROR_INCOMPATIBLE_ACTIONLIST % ct.INFO)
            return None

        data = dict(result.data)
        invalid_labels = list(result.invalid_labels)
        if invalid_labels:
            self.show_message('\n'.join([
                _('This action list was made by a different %(name)s version.')
                % ct.INFO + '\n\n' +
                WARNING_LOST_VALUES % ct.INFO + '\n',
                '\n'.join(invalid_labels)]))
        if result.warning:
            wx.CallAfter(self.show_error, '%s\n\n%s\n%s' % (
                api.ERROR_UNSAFE_ACTIONLIST_INTRO,
                result.warning,
                api.ERROR_UNSAFE_ACTIONLIST_ACCEPT))
        data['invalid labels'] = invalid_labels
        return data

    #---notification
    def _execute(self, actionlist, **keyw):
        app = wx.GetApp()
        self.set_report([])
        self.action_service.execute(
            actionlist,
            app.settings,
            update_callback=self._send_update_event,
            **keyw,
        )

    def _send_update_event(self):
        update_event = imageInspector.UpdateEvent()
        for window in wx.GetTopLevelWindows():
            if window != self:
                wx.PostEvent(window, update_event)

    def set_report(self, report):
        wx.GetApp().report = report

    def get_icon_filename(self):
        if self._icon_filename is None:
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

    @property
    def filename(self):
        return self.controller.state.filename

    @filename.setter
    def filename(self, value):
        self.controller.state.filename = value

    def __init__(self, actionlist, *args, **keyw):
        frame.Frame.__init__(self, *args, **keyw)
        _theme()
        self.dlg_library = None
        self.controller = ActionListController(self.tree)
        self.droplet_manager = DropletManager(
            export_actions=self.controller.export_actions,
            settings_provider=lambda: wx.GetApp().settings,
            check_actionlist=api.check_actionlist,
            create_frame=self._create_droplet_frame,
            schedule_hide=lambda: wx.CallAfter(self.on_show_droplet, False),
            state_callback=self._update_droplet_state,
        )
        self.action_advisor = ActionListAdvisor()
        self.file_dialogs = FileDialogService(wx.FileDialog)
        from lib.pyWx import shell
        self.shell_launcher = ShellLauncher(
            shell_factory=shell.Frame,
            icon_provider=lambda: graphics.bitmap(images.ICON_PHATCH_64),
            app_provider=wx.GetApp,
        )
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
        self._droplet_hint_shown = False
        if actionlist.endswith(ct.EXTENSION):
            self._open(actionlist)

    def _set_size(self):
        #make it eee pc friendly
        self._width = 600
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
        self.menu_file.Insert(2, wx.ID_REFRESH,
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
        #    id = wx.NewIdRef()
        #    label = actionlist[0]
        #    if prefix:
        #        label = '&%d %s' % (index + 1, label)
        #    item = library.Append(id, label)
        #    self.library_files[id] = actionlist[1]
        #    self.Bind(wx.EVT_MENU, self.on_menu_file_library, item)
        ##wx2.6 compatible
        #wx_ID_EDIT = 5030
        #self.menu_file.Insert(3, wx_ID_EDIT, _("Open &Library"),
        #   library, "")
        self.library_files_dictionary = formField.files_dictionary(
                    paths=[config.PATHS["PHATCH_ACTIONLISTS_PATH"],
                    ct.USER_ACTIONLISTS_PATH],
                    extensions=['png'])

        #shell launcher manages lifecycle
        self.menu_item = build_menu_groups(self, MENU_ENABLE_GROUPS)
        self.menu_view.Enable(self.menu_view_droplet.GetId(), True)
        self._update_droplet_state(False)
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
        state = self.controller.state
        path, filename = os.path.split(state.filename)
        self.SetTitle(ct.FRAME_TITLE\
            % (state.dirty_indicator(), os.path.splitext(filename)[0]))
        self.frame_statusbar.SetStatusText(path, 0)
        self.frame_statusbar.SetStatusText(ct.COPYRIGHT, 1)

    def is_protected_actionlist(self, filename):
        return config.PATHS["PHATCH_ACTIONLISTS_PATH"] == \
            os.path.dirname(filename)

    #---toolBar
    def add_tool(self, bitmap, label, tooltip, method, item=wx.ITEM_NORMAL):
        id = wx.NewIdRef()
        bitmap = graphics.bitmap(bitmap, self.tool_bitmap_size,
                    client=wx.ART_TOOLBAR)
        args = (id, label, bitmap, wx.NullBitmap, item,
                    tooltip, "")
        tool = self.frame_toolbar.AddTool(*args)
        self.Bind(wx.EVT_TOOL, method, id=id)
        return tool

    def _toolBar(self):
        self.tool_bitmap_size = (32, 32)
        self.frame_toolbar = wx.ToolBar(self, -1, style=wx.TB_FLAT)
        self.SetToolBar(self.frame_toolbar)
        self.frame_toolbar.SetToolBitmapSize(self.tool_bitmap_size)
        toggle_ids, all_ids = build_toolbar(self, self.frame_toolbar, TOOLBAR_SPEC)
        self.tools_item = toggle_ids
        self.tools_all = all_ids
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
        self.controller.state.has_actions = state

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
        if message is None:
            self.paint_message = self.DEFAULT_PAINT_MESSAGE
        else:
            self.paint_message = message
        self.Refresh()

#---menu events
    def on_menu_file_new(self, event=None):
        if self.is_save_not_ok():
            return
        state = self.controller.new_actionlist()
        self._set_filename(ct.UNKNOWN)
        self.description.SetValue(state.description)
        self.show_description(False)
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
        selection = self.file_dialogs.open_actionlist(
            parent=self,
            message=_('Choose an Action List File...'),
            default_dir=os.path.dirname(self.filename),
            wildcard=ct.WILDCARD,
            style=getattr(wx, 'FD_OPEN', 0),
        )
        if selection:
            self._open(selection.path)

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
        selection = self.file_dialogs.save_actionlist(
            parent=self,
            message=_('Save Action List As...'),
            default_dir=default_dir,
            wildcard=ct.WILDCARD,
            style=getattr(wx, 'FD_SAVE', 0),
        )
        if not selection:
            return False
        path = _ensure_phatch_suffix(selection.path)
        if os.path.exists(path) and self.show_question('%s %s' % (
                _('This file exists already.'),
                _('Do you want to overwrite it?'))) == wx.ID_NO:
            return False
        self._save(path)
        return True

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
            label = self.dialog_actions.GetStringSelection()
            self.controller.add_action_by_label(label)
            self.set_dirty(self.controller.state.dirty,
                description=self.description.GetValue())
            self.enable_actions(self.controller.state.has_actions)
        self.dialog_actions.Hide()

    def on_menu_edit_remove(self, event):
        if self.controller.remove_selected_action():
            self.enable_actions(self.controller.state.has_actions)
            self.set_dirty(self.controller.state.dirty,
                description=self.description.GetValue())

    def on_menu_edit_up(self, event):
        self.controller.move_selected_action_up()
        self.set_dirty(self.controller.state.dirty,
            description=self.description.GetValue())

    def on_menu_edit_down(self, event):
        self.controller.move_selected_action_down()
        self.set_dirty(self.controller.state.dirty,
            description=self.description.GetValue())

    def on_menu_edit_enable(self, event):
        self.controller.enable_selected_action(True)
        self.set_dirty(self.controller.state.dirty,
            description=self.description.GetValue())

    def on_menu_edit_disable(self, event):
        self.controller.enable_selected_action(False)
        self.set_dirty(self.controller.state.dirty,
            description=self.description.GetValue())

    def on_menu_view_droplet(self, event):
        self.show_droplet(event.IsChecked())

    def droplet_label_format(self, x):
        #return '123456789012345678901234567890'
        return x  # [:18]

    def on_menu_view_description(self, event):
        self.show_description(event.IsChecked())

    def on_menu_view_expand_all(self, event):
        self.controller.expand_all()

    def on_menu_view_collapse_all(self, event):
        self.controller.collapse_all()

    def on_menu_view_collapse_automatic(self, event):
        self.enable_collapse_automatic(event.IsChecked())

    def on_menu_tools_execute(self, event):
        actionlist = self.controller.export_actions()
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
        self.controller.close_context_popup()
        self.shell_launcher.toggle(self, self.controller, event.IsChecked())

    def on_menu_help_website(self, event):
        self.open_help_link('website')

    def on_menu_help_documentation(self, event):
        self.open_help_link('documentation')

    def on_menu_help_forum(self, event):
        self.open_help_link('forum')

    def on_menu_help_translate(self, event):
        self.open_help_link('translate')

    def on_menu_help_bug(self, event):
        self.open_help_link('bug')

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
    def open_help_link(self, key):
        webbrowser.open(HELP_LINKS[key])

    def _new(self):
        state = self.controller.new_actionlist()
        self.set_dirty(False, description=state.description)
        return state

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
            state = self.controller.apply_loaded_data(
                filename,
                data['actions'],
                description,
            )
            self.description.SetValue(state.description)
            self.enable_actions(state.has_actions)
            self._set_filename(filename)
            # add it to the history
            if not self.is_protected_actionlist(filename):
                self.filehistory.AddFileToHistory(filename)
        elif self.IsEmpty():
            self.enable_actions(False)
            self.set_dirty(False)

    def _save(self, filename=None):
        if filename:
            filename = _ensure_phatch_suffix(filename)
            self._set_filename(filename)
        raw_description = self.description.GetValue()
        if raw_description == ct.ACTION_LIST_DESCRIPTION:
            stored_description = ''
        else:
            stored_description = raw_description
        actions = list(self.controller.export_actions())
        self.action_service.save(self.filename, stored_description, actions)
        self.set_dirty(False, description=raw_description)
        if filename:
            # add it to the history
            self.filehistory.AddFileToHistory(self.filename)

    def _set_filename(self, filename):
        self.filename = _ensure_phatch_suffix(filename)
        self.set_dirty(False, description=self.description.GetValue())

    #---view show/hide
    def enable_collapse_automatic(self, checked):
        self.set_setting('collapse_automatic', checked)
        self.menu_view.Check(self.menu_view_collapse_automatic.GetId(),
            checked)
        self.controller.enable_collapse_automatic(checked)

    def show_description(self, checked):
        self.set_setting('description', checked)
        self.description.Show(checked)
        self.menu_view.Check(self.menu_view_description.GetId(), checked)
        self.frame_toolbar.ToggleTool(self.toolbar_description.GetId(),
            checked)
        self.Layout()

    def show_droplet(self, checked):
        self.droplet_manager.toggle(checked)

    def on_show_droplet(self, bool):
        self.droplet_manager.handle_show_event(bool)

    def _create_droplet_frame(self):
        parent = self

        class ManagedDroplet(droplet.Frame):
            def show(self_inner, bool=True):
                parent.Show(not bool)
                if bool:
                    self_inner.Show()
                else:
                    self_inner.Destroy()
                self_inner.OnShow(bool)

        label_text = self.droplet_label_format(
            system.filename_to_title(self.filename)
        )
        return ManagedDroplet(
            parent,
            title=_("Drag & Drop") + ' - ' + ct.TITLE,
            bitmap=graphics.bitmap(images.DROPLET),
            method=self.on_drop,
            label=f"{label_text}\n{_('Double-click to return to editor')}",
            label_color=wx.Colour(217, 255, 186),
            label_pos=(8, 8),
            label_angle=0,
            pos=self.GetPosition(),
            auto=True,
            OnShow=self.on_show_droplet,
            tooltip=_(
                "Drop any files and/or folders on this Phatch droplet\n"
                "to batch process them.\n"
                "Right-click or double-click to switch to normal view."),
        )

    def _update_droplet_state(self, visible):
        self.menu_view.Check(self.menu_view_droplet.GetId(), visible)
        if visible and not self._droplet_hint_shown:
            self.show_message(
                _('Droplet mode is active. Double-click the droplet window to return to the editor.'),
                title=_('Droplet Mode'),
            )
            self._droplet_hint_shown = True

    #---checks
    def append_save_action(self, actions):
        advice = self.action_advisor.recommend_save_action(actions)
        self.show_message(advice.message)
        self.controller.add_action_by_label_to_last(advice.action_label)

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
        text = event.GetString()
        self.controller.update_description(text)
        self.set_dirty(self.controller.state.dirty, description=text)

    def on_drop(self, filenames, x, y):
        self.action_service.execute(
            self.controller.export_actions(),
            wx.GetApp().settings,
            paths=filenames,
            drop=True,
        )

    def on_menu_tool_enter(self, event):
        self.controller.close_context_popup()
        event.Skip()

    def on_tree_end_drag(self, event):
        event.Skip()
        wx.CallAfter(self.set_dirty, True)

    def on_context_menu(self, event):
        if self.controller.has_selected_action():
            self.controller.show_context_menu(self.menu_edit)

    def is_save_not_ok(self):
        if self.controller.state.dirty:
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
            self.controller.resize_popup()

    def IsEmpty(self):
        return not self.controller.has_forms()

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
    def set_dirty(self, value, description=None):
        if value:
            self.controller.mark_dirty()
        else:
            if description is not None:
                self.controller.mark_clean(description)
            else:
                self.controller.state.dirty = False
        self._title()

    def set_safe_mode(self, state):
        if state is False:
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
        except Exception as details:
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
        method = types.MethodType(method, self)
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
        # wx.InitAllImageHandlers() not needed - wxPython 4.x auto-initializes
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
        # wx.InitAllImageHandlers() not needed - wxPython 4.x auto-initializes
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
        actionlists = list(d.keys())
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
            f = open(ct.USER_SETTINGS_PATH, 'r')
            #exclude paths as they should not be overwritten
            try:
                items = list(safe.eval_restricted(f.read(),
                    allowed=['True', 'False']).items())
            except:
                sys.stdout.write(' '.join([
                    _('Sorry, your settings seem corrupt.'),
                    _('Please delete "%s".' % ct.USER_SETTINGS_PATH),
                    _('Also check if your hard disk not full.\n')]))
                sys.exit()
            f.close()
            for key, value in items:
                #FIXME: paths should not be in settings
                if 'PATH' not in key:
                    self.settings[key] = value

    def _saveSettings(self):
        f = open(ct.USER_SETTINGS_PATH, 'w')
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
        # wx.InitAllImageHandlers() not needed - wxPython 4.x auto-initializes
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
