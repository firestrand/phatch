# -*- coding: utf-8 -*-

import wx
from lib.pyWx.treeEdit import TreeMixin

class Tree(TreeMixin,wx.TreeCtrl):
    
    def __init__(self,parent,*args,**keyw):
        
        from core.api import ACTIONS
        from core.translation import to_local, to_english
        
        class I18n_CtrlMixin:
            """Fake example of a Mixin"""
            _to_local   = to_local
            _to_english = to_english
            _to_local   = staticmethod(_to_local)
            _to_english = staticmethod(_to_english)
            
        wx.TreeCtrl.__init__(self,parent,*args,**keyw)
        TreeMixin.__init__(self,
            form_factory= ACTIONS,
            CtrlMixin   = I18n_CtrlMixin,
            icon_size   = (28,28),
            show_error  = parent.show_error,
            set_dirty   = parent.set_dirty,
        )
        
    def OnCompareItems(self,item1,item2):
        """Unclear why this is necessary, because of mixin?"""
        return TreeMixin.OnCompareItems(self,item1,item2)


class Frame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Frame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        
        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        self.menu_file = wx.Menu()
        self.menu_file_new = wx.MenuItem(self.menu_file, wx.ID_NEW, _("&New\tCtrl-N"), _("Start a new action list"), wx.ITEM_NORMAL)
        self.menu_file.AppendItem(self.menu_file_new)
        self.menu_file_open = wx.MenuItem(self.menu_file, wx.ID_OPEN, _("&Open...\tCtrl-O"), _("Opens an actions list"), wx.ITEM_NORMAL)
        self.menu_file.AppendItem(self.menu_file_open)
        self.menu_file_open_library = wx.MenuItem(self.menu_file, wx.ID_PREVIEW_GOTO, _("Open &Library...\tCtrl-Shift-O"), _("Opens a ready-made actionlist from the library"), wx.ITEM_NORMAL)
        self.menu_file.AppendItem(self.menu_file_open_library)
        self.menu_file_save = wx.MenuItem(self.menu_file, wx.ID_SAVE, _("&Save\tCtrl-S"), _("Saves an action list"), wx.ITEM_NORMAL)
        self.menu_file.AppendItem(self.menu_file_save)
        self.menu_file_save_as = wx.MenuItem(self.menu_file, wx.ID_SAVEAS, _("Save &As...\tCtrl-Shift-S"), _("Saves an action list as"), wx.ITEM_NORMAL)
        self.menu_file.AppendItem(self.menu_file_save_as)
        self.menu_file.AppendSeparator()
        menu_file_export = wx.Menu()
        self.menu_file_export_actionlist_to_clipboard = wx.MenuItem(menu_file_export, wx.NewId(), _("Copy Actionlist as &Command to Clipboard"), _("Paste this command in a launcher"), wx.ITEM_NORMAL)
        menu_file_export.AppendItem(self.menu_file_export_actionlist_to_clipboard)
        self.menu_file_export_recent_to_clipboard = wx.MenuItem(menu_file_export, wx.NewId(), _("Copy R&ecent as Command to Clipboard"), _("Paste this command in a launcher"), wx.ITEM_NORMAL)
        menu_file_export.AppendItem(self.menu_file_export_recent_to_clipboard)
        self.menu_file_export_inspector_to_clipboard = wx.MenuItem(menu_file_export, wx.NewId(), _("Copy Image I&nspector as Command to Clipboard"), _("Paste this command in a launcher"), wx.ITEM_NORMAL)
        menu_file_export.AppendItem(self.menu_file_export_inspector_to_clipboard)
        self.menu_file.AppendMenu(wx.ID_FORWARD, _("&Export"), menu_file_export, "")
        self.menu_file_quit = wx.MenuItem(self.menu_file, wx.ID_EXIT, _("&Quit\tCtrl-Q"), _("Quit the application."), wx.ITEM_NORMAL)
        self.menu_file.AppendItem(self.menu_file_quit)
        self.frame_menubar.Append(self.menu_file, _("&Action List"))
        self.menu_edit = wx.Menu()
        self.menu_edit_add = wx.MenuItem(self.menu_edit, wx.ID_ADD, _("&Add...\tCtrl-+"), _("Add an action"), wx.ITEM_NORMAL)
        self.menu_edit.AppendItem(self.menu_edit_add)
        self.menu_edit_remove = wx.MenuItem(self.menu_edit, wx.ID_REMOVE, _("&Remove\tCtrl--"), _("Remove the selected action."), wx.ITEM_NORMAL)
        self.menu_edit.AppendItem(self.menu_edit_remove)
        self.menu_edit.AppendSeparator()
        self.menu_edit_enable = wx.MenuItem(self.menu_edit, wx.ID_APPLY, _("&Enable\tCtrl-1"), _("Enable action"), wx.ITEM_NORMAL)
        self.menu_edit.AppendItem(self.menu_edit_enable)
        self.menu_edit_disable = wx.MenuItem(self.menu_edit, wx.ID_CANCEL, _("&Disable\tCtrl-0"), _("Disable action"), wx.ITEM_NORMAL)
        self.menu_edit.AppendItem(self.menu_edit_disable)
        self.menu_edit.AppendSeparator()
        self.menu_edit_up = wx.MenuItem(self.menu_edit, wx.ID_UP, _("&Up\tCtrl-Up"), _("Move the selected action up"), wx.ITEM_NORMAL)
        self.menu_edit.AppendItem(self.menu_edit_up)
        self.menu_edit_down = wx.MenuItem(self.menu_edit, wx.ID_DOWN, _("&Down\tCtrl-Down"), _("Move the selected action down"), wx.ITEM_NORMAL)
        self.menu_edit.AppendItem(self.menu_edit_down)
        self.frame_menubar.Append(self.menu_edit, _("&Edit"))
        self.menu_view = wx.Menu()
        self.menu_view_droplet = wx.MenuItem(self.menu_view, wx.ID_HELP_PROCEDURES, _("&Droplet\tCtrl-D"), _("View as a droplet to drag and drop files"), wx.ITEM_CHECK)
        self.menu_view.AppendItem(self.menu_view_droplet)
        self.menu_view_description = wx.MenuItem(self.menu_view, wx.ID_PREVIEW, _("&Show Description\tCtrl-H"), _("Tools to handle the current action list"), wx.ITEM_CHECK)
        self.menu_view.AppendItem(self.menu_view_description)
        self.menu_view.AppendSeparator()
        self.menu_view_expand_all = wx.MenuItem(self.menu_view, wx.ID_INDENT, _("&Expand All\tCtrl-E"), _("Show all the parameters of the actions."), wx.ITEM_NORMAL)
        self.menu_view.AppendItem(self.menu_view_expand_all)
        self.menu_view_collapse_all = wx.MenuItem(self.menu_view, wx.ID_JUSTIFY_FILL, _("&Collapse All\tCtrl-Shift-E"), _("Show only the labels of the actions."), wx.ITEM_NORMAL)
        self.menu_view.AppendItem(self.menu_view_collapse_all)
        self.menu_view_collapse_automatic = wx.MenuItem(self.menu_view, wx.ID_NOTOALL, _("&Collapse Automatically"), _("Expanding one action collapses the others."), wx.ITEM_CHECK)
        self.menu_view.AppendItem(self.menu_view_collapse_automatic)
        self.frame_menubar.Append(self.menu_view, _("&View"))
        self.menu_tools = wx.Menu()
        self.menu_tools_execute = wx.MenuItem(self.menu_tools, wx.ID_OK, _("&Execute...\tCtrl-Return"), _("Execute the action list"), wx.ITEM_NORMAL)
        self.menu_tools.AppendItem(self.menu_tools_execute)
        self.menu_tools_safe = wx.MenuItem(self.menu_tools, wx.ID_YESTOALL, _("&Safe Mode (recommended)"), _("Allow Geek action and unsafe expressions"), wx.ITEM_CHECK)
        self.menu_tools.AppendItem(self.menu_tools_safe)
        self.menu_tools.AppendSeparator()
        self.menu_tools_image_inspector = wx.MenuItem(self.menu_tools, wx.ID_FIND, _("&Image Inspector (exif)\tCtrl-I"), _("Look up exif and iptc tags"), wx.ITEM_NORMAL)
        self.menu_tools.AppendItem(self.menu_tools_image_inspector)
        menu_tools_browse_library = wx.Menu()
        self.menu_tools_browse_library_user = wx.MenuItem(menu_tools_browse_library, wx.NewId(), _("&User"), _("Browse action lists, masks, highlights and fonts"), wx.ITEM_NORMAL)
        menu_tools_browse_library.AppendItem(self.menu_tools_browse_library_user)
        self.menu_tools_browse_library_phatch = wx.MenuItem(menu_tools_browse_library, wx.NewId(), _("&Phatch"), _("Browse action lists, masks, highlights and fonts"), wx.ITEM_NORMAL)
        menu_tools_browse_library.AppendItem(self.menu_tools_browse_library_phatch)
        self.menu_tools.AppendMenu(wx.ID_MORE, _("&Browse Library"), menu_tools_browse_library, "")
        self.menu_tools.AppendSeparator()
        self.menu_tools_show_report = wx.MenuItem(self.menu_tools, wx.ID_PROPERTIES, _("Show &Report...\tCtrl+R"), _("Show report of processed images"), wx.ITEM_NORMAL)
        self.menu_tools.AppendItem(self.menu_tools_show_report)
        self.menu_tools_show_log = wx.MenuItem(self.menu_tools, wx.ID_ZOOM_IN, _("Show &Log...\tCtrl-L"), _("Show log file"), wx.ITEM_NORMAL)
        self.menu_tools.AppendItem(self.menu_tools_show_log)
        self.menu_tools.AppendSeparator()
        menu_tools_update = wx.Menu()
        self.menu_tools_update_fonts = wx.MenuItem(menu_tools_update, wx.NewId(), _("&Fonts"), _("Scan for new fonts on your system"), wx.ITEM_NORMAL)
        menu_tools_update.AppendItem(self.menu_tools_update_fonts)
        self.menu_tools.AppendMenu(wx.NewId(), _("&Update"), menu_tools_update, "")
        self.frame_menubar.Append(self.menu_tools, _("&Tools"))
        self.menu_help = wx.Menu()
        self.menu_help_website = wx.MenuItem(self.menu_help, wx.ID_HOME, _("&Website...\tCtrl-W"), _("Go to the Phatch homepage."), wx.ITEM_NORMAL)
        self.menu_help.AppendItem(self.menu_help_website)
        self.menu_help_documentation = wx.MenuItem(self.menu_help, wx.ID_HELP, _("&Documentation...\tCtrl-M"), _("Go to the Phatch documentation."), wx.ITEM_NORMAL)
        self.menu_help.AppendItem(self.menu_help_documentation)
        self.menu_help_forum = wx.MenuItem(self.menu_help, wx.ID_SELECTALL, _("&Forum...\tCtrl-F"), _("Go to the Phatch forum"), wx.ITEM_NORMAL)
        self.menu_help.AppendItem(self.menu_help_forum)
        self.menu_help.AppendSeparator()
        self.menu_help_translate = wx.MenuItem(self.menu_help, wx.ID_ITALIC, _("&Translate Phatch...\tCtrl-T"), _("Translate Phatch in your native language."), wx.ITEM_NORMAL)
        self.menu_help.AppendItem(self.menu_help_translate)
        self.menu_help_bug = wx.MenuItem(self.menu_help, wx.ID_NO, _("&Report a Bug...\tCtrl-B"), _("Report a bug on launchpad."), wx.ITEM_NORMAL)
        self.menu_help.AppendItem(self.menu_help_bug)
        self.menu_help_plugin = wx.MenuItem(self.menu_help, wx.ID_INDEX, _("De&veloper Documentation...\tCtrl-P"), _("Learn to develop Phatch with Python and PIL."), wx.ITEM_NORMAL)
        self.menu_help.AppendItem(self.menu_help_plugin)
        self.menu_help.AppendSeparator()
        self.menu_help_about = wx.MenuItem(self.menu_help, wx.ID_ABOUT, _("&About Phatch...\tCtrl-Shift-A"), _("Displays information about this application."), wx.ITEM_NORMAL)
        self.menu_help.AppendItem(self.menu_help_about)
        self.frame_menubar.Append(self.menu_help, _("&Help"))
        self.SetMenuBar(self.frame_menubar)
        # Menu Bar end
        self.frame_statusbar = self.CreateStatusBar(1, 0)
        self.description = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE)
        self.tree = Tree(self, -1, style=wx.TR_HAS_BUTTONS|wx.TR_NO_LINES|wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER)
        self.empty = wx.Panel(self, -1)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_MENU, self.on_menu_file_new, self.menu_file_new)
        self.Bind(wx.EVT_MENU, self.on_menu_file_open, self.menu_file_open)
        self.Bind(wx.EVT_MENU, self.on_menu_file_open_library, self.menu_file_open_library)
        self.Bind(wx.EVT_MENU, self.on_menu_file_save, self.menu_file_save)
        self.Bind(wx.EVT_MENU, self.on_menu_file_save_as, self.menu_file_save_as)
        self.Bind(wx.EVT_MENU, self.on_menu_file_export_actionlist_to_clipboard, self.menu_file_export_actionlist_to_clipboard)
        self.Bind(wx.EVT_MENU, self.on_menu_file_export_recent_to_clipboard, self.menu_file_export_recent_to_clipboard)
        self.Bind(wx.EVT_MENU, self.on_menu_file_export_inspector_to_clipboard, self.menu_file_export_inspector_to_clipboard)
        self.Bind(wx.EVT_MENU, self.on_menu_file_quit, self.menu_file_quit)
        self.Bind(wx.EVT_MENU, self.on_menu_edit_add, self.menu_edit_add)
        self.Bind(wx.EVT_MENU, self.on_menu_edit_remove, self.menu_edit_remove)
        self.Bind(wx.EVT_MENU, self.on_menu_edit_enable, self.menu_edit_enable)
        self.Bind(wx.EVT_MENU, self.on_menu_edit_disable, self.menu_edit_disable)
        self.Bind(wx.EVT_MENU, self.on_menu_edit_up, self.menu_edit_up)
        self.Bind(wx.EVT_MENU, self.on_menu_edit_down, self.menu_edit_down)
        self.Bind(wx.EVT_MENU, self.on_menu_view_droplet, self.menu_view_droplet)
        self.Bind(wx.EVT_MENU, self.on_menu_view_description, self.menu_view_description)
        self.Bind(wx.EVT_MENU, self.on_menu_view_expand_all, self.menu_view_expand_all)
        self.Bind(wx.EVT_MENU, self.on_menu_view_collapse_all, self.menu_view_collapse_all)
        self.Bind(wx.EVT_MENU, self.on_menu_view_collapse_automatic, self.menu_view_collapse_automatic)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_execute, self.menu_tools_execute)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_safe, self.menu_tools_safe)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_image_inspector, self.menu_tools_image_inspector)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_browse_library_user, self.menu_tools_browse_library_user)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_browse_library_phatch, self.menu_tools_browse_library_phatch)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_show_report, self.menu_tools_show_report)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_show_log, self.menu_tools_show_log)
        self.Bind(wx.EVT_MENU, self.on_menu_tools_update_fonts, self.menu_tools_update_fonts)
        self.Bind(wx.EVT_MENU, self.on_menu_help_website, self.menu_help_website)
        self.Bind(wx.EVT_MENU, self.on_menu_help_documentation, self.menu_help_documentation)
        self.Bind(wx.EVT_MENU, self.on_menu_help_forum, self.menu_help_forum)
        self.Bind(wx.EVT_MENU, self.on_menu_help_translate, self.menu_help_translate)
        self.Bind(wx.EVT_MENU, self.on_menu_help_bug, self.menu_help_bug)
        self.Bind(wx.EVT_MENU, self.on_menu_help_plugin, self.menu_help_plugin)
        self.Bind(wx.EVT_MENU, self.on_menu_help_about, self.menu_help_about)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: Frame.__set_properties
        self.frame_statusbar.SetStatusWidths([-1])
        # statusbar fields
        frame_statusbar_fields = [""]
        for i in range(len(frame_statusbar_fields)):
            self.frame_statusbar.SetStatusText(frame_statusbar_fields[i], i)
        self.description.SetMinSize((300, 40))
        self.description.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_INFOBK))
        self.description.SetForegroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_INFOTEXT))
        self.empty.SetBackgroundColour(wx.Colour(255, 255, 255))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Frame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.description, 0, wx.EXPAND, 0)
        sizer_1.Add(self.tree, 1, wx.EXPAND, 0)
        sizer_1.Add(self.empty, 1, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade

    def on_menu_file_new(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_new' not implemented!"
        event.Skip()

    def on_menu_file_open(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_open' not implemented!"
        event.Skip()

    def on_menu_file_save(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_save' not implemented!"
        event.Skip()

    def on_menu_file_save_as(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_save_as' not implemented!"
        event.Skip()

    def on_menu_file_export_droplet_actionlist_to_clipboard(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_export_droplet_actionlist_to_clipboard' not implemented"
        event.Skip()

    def on_menu_file_export_droplet_recent_to_clipboard(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_export_droplet_recent_to_clipboard' not implemented"
        event.Skip()

    def on_menu_file_export_droplet_inspector_to_clipboard(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_export_droplet_inspector_to_clipboard' not implemented"
        event.Skip()

    def on_menu_file_quit(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_quit' not implemented!"
        event.Skip()

    def on_menu_edit_modify(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_edit_modify' not implemented!"
        event.Skip()

    def on_menu_edit_up(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_edit_up' not implemented!"
        event.Skip()

    def on_menu_edit_down(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_edit_down' not implemented!"
        event.Skip()

    def on_menu_edit_enable(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_edit_enable' not implemented!"
        event.Skip()

    def on_menu_edit_disable(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_edit_disable' not implemented!"
        event.Skip()

    def on_menu_edit_add(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_edit_add' not implemented!"
        event.Skip()

    def on_menu_edit_remove(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_edit_remove' not implemented!"
        event.Skip()

    def on_menu_view_droplet(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_view_droplet' not implemented!"
        event.Skip()

    def on_menu_view_description(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_view_description' not implemented!"
        event.Skip()

    def on_menu_tools_execute(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_execute' not implemented!"
        event.Skip()

    def on_menu_tools_show_log(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_show_log' not implemented!"
        event.Skip()

    def on_menu_tools_python_shell(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_python_shell' not implemented!"
        event.Skip()

    def on_menu_help_about(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_help_about' not implemented!"
        event.Skip()

    def on_menu_help_translate(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_help_translate' not implemented"
        event.Skip()

    def on_menu_help_plugin(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_help_plugin' not implemented"
        event.Skip()

    def on_menu_view_expand_all(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_view_expand_all' not implemented"
        event.Skip()

    def on_menu_view_collapse_all(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_view_collapse_all' not implemented"
        event.Skip()

    def on_menu_help_website(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_help_website' not implemented"
        event.Skip()

    def on_menu_help_documentation(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_help_documentation' not implemented"
        event.Skip()

    def on_menu_help_forum(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_help_forum' not implemented"
        event.Skip()

    def on_menu_help_bug(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_help_bug' not implemented"
        event.Skip()

    def on_menu_tools_image_inspector(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_image_inspector' not implemented"
        event.Skip()


    def on_menu_file_export_actionlist_to_clipboard(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_export_actionlist_to_clipboard' not implemented"
        event.Skip()

    def on_menu_file_export_recent_to_clipboard(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_export_recent_to_clipboard' not implemented"
        event.Skip()

    def on_menu_file_export_inspector_to_clipboard(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_export_inspector_to_clipboard' not implemented"
        event.Skip()

    def on_menu_tools_browse_user_library(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_browse_user_library' not implemented"
        event.Skip()

    def on_menu_tools_browse_system_library(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_browse_system_library' not implemented"
        event.Skip()

    def on_menu_tools_browse_library_user(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_browse_library_user' not implemented"
        event.Skip()

    def on_menu_tools_browse_library_phatch(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_browse_library_phatch' not implemented"
        event.Skip()

    def on_menu_tools_show_report(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_show_report' not implemented"
        event.Skip()

    def on_menu_tools_update_fonts(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_update_fonts' not implemented"
        event.Skip()

    def on_menu_tools_safe(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_tools_safe' not implemented"
        event.Skip()

    def on_menu_file_open_library(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_file_open_library' not implemented"
        event.Skip()

    def on_menu_collapse_automatic(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_collapse_automatic' not implemented"
        event.Skip()

    def on_menu_view_collapse_automatic(self, event): # wxGlade: Frame.<event_handler>
        print "Event handler `on_menu_view_collapse_automatic' not implemented"
        event.Skip()

# end of class Frame


class App(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        frame = Frame(None, -1, "")
        self.SetTopWindow(frame)
        frame.Show()
        return 1

# end of class App

if __name__ == "__main__":
    import gettext
    gettext.install("app") # replace with the appropriate catalog name

    app = App(0)
    app.MainLoop()
