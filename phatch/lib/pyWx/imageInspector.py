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

if __name__ == '__main__':
    #add phatch to sys.path
    import sys
    sys.path.insert(0, '..')
    import gettext
    gettext.install('test')

#---modules
import cStringIO
import os
import zlib

import wx
import wx.grid as gridlib

import  wx.lib.newevent
UpdateEvent, UPDATE_EVENT = wx.lib.newevent.NewEvent()

from lib import imageTable
from lib import formField
from lib import metadata
from lib import system

import clipboard
import droplet
import graphics
import tag
import wildcard
import wxPil
import dialogsInspector

try:
    import pyexiv2
except ImportError:
    pyexiv2 = None

#---constants
ALL = _('All')
ALTERNATE_COLORS = (wx.Colour(254, 255, 255), wx.Colour(250, 250, 250))
COL_WIDTH = 140
CONFIRM_DELETE_TAG = \
    _('Are you sure you want to delete this tag from "%s"?')
CONFIRM_DELETE_TAG_ALL = \
    _('Are you sure you want to delete this tag from all images?')
FILENAME = '/home/stani/sync/Afbeeldingen/ubuntu_dog_1600x1200_3d.png'
#FILENAME = ''
GRAY = wx.Colour(112, 112, 112)
RED = wx.Colour(255, 230, 230)
SELECT = _('Select')
SIZE = (450, 510)
THUMB_SIZE = (128, 128)
TAGS = [SELECT, ALL, 'Pil']
if pyexiv2:
    TAGS.extend(['Exif', 'Iptc'])
TAGS.extend(['Pexif', 'Zexif'])  # 'EXIF',
TITLE = _('Image Inspector')

WX_ENCODING = wx.GetDefaultPyEncoding()


def empty_bitmap(width, height):
    dc = wx.MemoryDC()
    bmp = wx.EmptyBitmap(width, height)
    dc.SelectObject(bmp)
    dc.SetBrush(wx.TRANSPARENT_BRUSH)
    dc.Clear()
    return bmp


class AddTagDialog(dialogsInspector.AddTagDialog):

    def __init__(self, parent, keys, *args, **keyw):
        """This dialog pops up when the user want to add a new tag.

        :param parent: parent frame of the dialog
        :type parent: wx.Window
        :param keys:

            ``keys`` are metadata tags of images. ``tags`` appear in
            the combobox up left to organize in different categories.

        :type keys: list
        """
        super(AddTagDialog, self).__init__(parent, *args, **keyw)
        self.keys = keys
        self.OnTagText(None)

    def OnAdd(self, event):
        """This gets called when the ``Add`` button is pressed."""
        self.EndModal(wx.ID_ADD)

    def OnTagText(self, event):
        """This event is binded to the ``tag`` ``wx.TextCtrl``::

            self.Bind(wx.EVT_TEXT, self.OnTagText, self.tag)
        """
        key = self.tag.GetValue()
        valid = bool(metadata.RE_PYEXIV2_TAG_EDITABLE.match(key))
        exists = key in self.keys
        if not valid:
            self.warning.SetLabel(_('Tag should start with Exif_* or Iptc_*'))
        elif exists:
            self.warning.SetLabel(_('Tag exists already'))
        else:
            self.warning.SetLabel('')
        self.add.Enable(valid and not exists)

    def GetModal(self):
        """The dialog should be invoked by this method.

        :returns: tag, value
        :rtype: string, *
        """
        if self.ShowModal() == wx.ID_ADD:
            tag = self.tag.GetValue()
            value = self.value.GetValue()
        else:
            tag = None
            value = None
        self.Destroy()
        return tag, value


class Table(gridlib.PyGridTableBase):

    def __init__(self, thumb_size=THUMB_SIZE):
        """This forms a bridge between :class:`imageTable.Table`` and
        the virtual wxPython :class:`Grid`.

        :param thumb_size: size of the thumbnails
        :type thumb_size: tuple of ints
        """
        gridlib.PyGridTableBase.__init__(self)
        self.table = imageTable.Table(thumb_size)
        self.SetRowColours()
        self.log = ''

    def GetAttr(self, row, col, kind):
        """Get the attribute of a grid cell. The attribute defines:

        * color (odd/even rows)
        * read-only

        :param row: row
        :type row: int
        :param col: column
        :type col: int
        :param kind: not used (but obligatory for wxPython)
        :returns: attribute
        """
        if self.table.is_cell_empty(row, col):
            attr = self.missing_attr.Clone()
        else:
            attr = [self.even_attr, self.odd_attr][row % 2].Clone()
        attr.IncRef()
        attr.SetReadOnly(self.IsEditableCell(row, col))
        return attr

    def SetRowColours(self, colors=ALTERNATE_COLORS):
        """Define the base attribute for odd and even rows:

        * background color
        * text color
        * selected color

        The selected color is based on the system (gtk, windows or
        mac os x).
        """
        #odd rows
        self.odd_attr = gridlib.GridCellAttr()
        self.odd_attr.SetBackgroundColour(colors[1])
        #even rows
        self.even_attr = gridlib.GridCellAttr()
        self.even_attr.SetBackgroundColour(colors[0])
        #missing_rows
        self.missing_attr = gridlib.GridCellAttr()
        self.missing_attr.SetBackgroundColour(RED)
        #selected rows
        self.selected_attr = gridlib.GridCellAttr()
        self.selected_attr.SetBackgroundColour(
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.selected_attr.SetTextColour(
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

    # This is all it takes to make a custom data table to plug into a
    # wxGrid.  There are many more methods that can be overridden, but
    # the ones shown below are the required ones.  This table simply
    # provides strings containing the row and column values.
    def DeleteRows(self, pos=0, num=1):
        return self.table.delete_rows(pos, num)

    def GetRowLabelValue(self, row):
        return self.table.get_row_label(row)

    def SetRowLabelValue(self, row, value):
        return self.table.set_row_label(row, value)

    def GetNumberRows(self):
        return self.table.get_row_amount()

    def GetColLabelValue(self, col):
        return self.table.get_col_label(col)

    def GetNumberCols(self):
        return self.table.get_col_amount()

    def DeleteCols(self, pos=0, num=1):
        return self.table.delete_cols(pos, num)

    def GetValue(self, row, col):
        return self.table.get_cell_value(row, col)

    def SetValue(self, row, col, value):
        self.log = self.table.set_cell_value(row, col, value)

    def IsEmptyCell(self, row, col):
        return self.table.is_cell_empty(row, col)

    def IsEditableCell(self, row, col):
        return not self.table.is_cell_editable(row, col)


class Grid(droplet.Mixin, gridlib.Grid):
    border = 4
    Table = Table
    wildcard = '|'.join([wildcard.wildcard_list(_('Images'),
        formField.IMAGE_READ_EXTENSIONS), _('All files'), '*'])
    corner_logo = _corner_logo = None

    def __init__(self, parent, thumb_size=THUMB_SIZE):
        super(Grid, self).__init__(parent)
        #table
        self.table = self.Table(thumb_size)
        self.image_table = self.table.table
        self.SetTable(self.table, True)
        self.SetRowLabelSize(260)
        self._rows_number = self.GetNumberRows()
        self._cols_number = self.GetNumberCols()
        self._cols_sized = []
        #bitmap
        self.PENCIL_BITMAP = getPencilBitmap()
        self.PENCIL_BITMAP_SIZE = self.PENCIL_BITMAP.GetSize()
        self.GRAY_BRUSH = wx.Brush("WHEAT", wx.TRANSPARENT)
        self.GRAY_PEN = wx.Pen(GRAY)
        #editor
        self.SetDefaultEditor(gridlib.GridCellTextEditor())
        #drop
        self.SetAsFileDropTarget(self, self.OnDrop)
        self.SetAsFileDropTarget(self.GetEmpty(), self.OnDrop)
        self.SetAsFileDropTarget(self.GetTopLevelParent(), self.OnDrop)
        #events
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(gridlib.EVT_GRID_CELL_CHANGE, self.OnGridCellChange)
        self.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK,
            self.OnGridCellLeftClick)
        self.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK,
            self.OnGridCellRightClicked)
        self.Bind(gridlib.EVT_GRID_CMD_LABEL_RIGHT_CLICK,
            self.OnGridLabelRightClicked)
        self.Bind(gridlib.EVT_GRID_LABEL_LEFT_DCLICK,
            self.OnGridLabelLeftDclicked)
        self.GetGridRowLabelWindow().Bind(wx.EVT_PAINT,
            self.OnRowLabelPaint)
        self.GetGridColLabelWindow().Bind(wx.EVT_PAINT,
            self.OnColLabelPaint)
        #FIXME: logo might get corrupted
        #self.GetGridCornerLabelWindow().Bind(wx.EVT_PAINT,
        #    self.OnCornerLabelPaint)
        self.Bind(gridlib.EVT_GRID_EDITOR_HIDDEN,
            self.OnGridEditorHidden)

    def OnGridEditorHidden(self, evt):
        wx.CallAfter(self.ShowLog)

    def ShowLog(self):
        log = self.table.log
        self.table.log = ''
        if log:
            self.ShowError(log)

    #---refresh
    def UpdateIfNeeded(self):
        needs_update = False
        for image in self.image_table.images:
            needs_update = needs_update or image.update_if_modified()
        if needs_update:
            self.RefreshAll(update_column=True, force_thumbs=True)

    def UpdateRowsColsNumbers(self):
        """Only consider adding or removing rows."""
        for current, new, delmsg, addmsg in [
            (self._rows_number, self.table.GetNumberRows(),
                gridlib.GRIDTABLE_NOTIFY_ROWS_DELETED,
                gridlib.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self._cols_number, self.table.GetNumberCols(),
                gridlib.GRIDTABLE_NOTIFY_COLS_DELETED,
                gridlib.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:
            if new < current:
                msg = gridlib.GridTableMessage(self.table, delmsg, new,
                    current - new)
                self.ProcessTableMessage(msg)
            elif new > current:
                msg = gridlib.GridTableMessage(self.table, addmsg,
                    new - current)
                self.ProcessTableMessage(msg)
        self._rows_number = self.GetNumberRows()
        self._cols_number = self.GetNumberCols()

    def UpdateValues(self):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = gridlib.GridTableMessage(self.table,
            gridlib.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.ProcessTableMessage(msg)

    def UpdateThumbs(self, force_thumbs=False):
        if self.image_table.images:
            heights = []
            for image in self.image_table.images:
                if force_thumbs or not hasattr(image, 'thumb_wx'):
                    image.thumb_wx = wxPil.pil_wxBitmap(image.thumb)
                heights.append(image.thumb.size[1])
            self.SetColLabelSize(max(heights) + 2 * self.border)

    def RefreshAll(self, update_column=False, force_thumbs=False):
        self.BeginBatch()
        self.UpdateThumbs(force_thumbs)
        self.GetGridColLabelWindow().Refresh()
        self.UpdateRowsColsNumbers()
        self.UpdateValues()
        self.EndBatch()
        self.AdjustScrollbars()
        if update_column:
            for col in range(self.GetNumberCols()):
                if col not in self._cols_sized:
                    self.SetColSize(col, COL_WIDTH)
                    self._cols_sized.append(col)
        self.ForceRefresh()

    #---events
    def OnGridCellLeftClick(self, evt):
        col = evt.GetCol()
        self.SetTitleFilename(self.image_table.images[col].filename)
        evt.Skip()

    def SetTitleFilename(self, filename):
        wx.GetTopLevelParent(self).SetTitleFilename(filename)

    def OnColLabelPaint(self, evt):
        window = self.GetGridColLabelWindow()
        rect = window.GetClientRect()
        dc = wx.PaintDC(window)
        dc.Clear()
        pen = dc.GetPen()
        dc.SetPen(self.GRAY_PEN)
        dc.DrawLine(rect[0], rect[1] + rect[3] - 1,
            rect[0] + rect[2], rect[1] + rect[3] - 1)

        def label_rect(position, col):
            col_width = self.GetColSize(col)
            col_height = self.GetColLabelSize()
            return (position, 0, col_width, col_height)

        def get_bitmap(index):
            return self.image_table.images[index].thumb_wx

        self._LabelPaint(dc, co=0, amount=self.GetNumberCols(),
            label_rect=label_rect, get_size=self.GetColSize,
            get_label=None,  # self.GetColLabelValue,
            get_bitmap=get_bitmap, border=False, center_bitmap=True,
            pen=pen)

    def OnCornerLabelPaint(self, evt):
        if not self.corner_logo:
            return evt.Skip()
        if not self._corner_logo:
            self._corner_logo = graphics.bitmap(self.corner_logo)
        window = self.GetGridCornerLabelWindow()
        rect = window.GetClientRect()
        dc = wx.PaintDC(window)
        pen = dc.GetPen()
        dc.SetPen(self.GRAY_PEN)
        dc.DrawLine(rect[0], rect[1] + rect[3] - 1,
            rect[0] + rect[2], rect[1] + rect[3] - 1)

        def label_rect(position, col):
            return rect

        def get_bitmap(index):
            return self._corner_logo

        self._LabelPaint(dc, co=0, amount=1,
            label_rect=label_rect, get_size=self.GetColSize,
            get_label=None,  # self.GetColLabelValue,
            get_bitmap=get_bitmap, border=False, center_bitmap=True,
            pen=pen)

    def CopyCellValue(self, row, col):
        if self.table.GetNumberCols():
            clipboard.copy_text(unicode(self.table.GetValue(row, col)))

    def OnDrop(self, filenames, x, y):
        self.OpenImages(filenames)

    def OnGridCellChange(self, event):
        wx.CallAfter(self.RefreshAll)

    def OnGridCellRightClicked(self, event):
        """(row, evt) -> display a popup menu when a row label is
        right clicked"""
        # Did we click on a row or a column?
        event.Skip()
        row, col = event.GetRow(), event.GetCol()
        #bind menu events

        def on_copy(event):
            self.CopyCellValue(row, col)

        def on_add(event):
            self.AddColumnRow(col)

        def on_delete_cell(event):
            self.DeleteCell(row, col)

        #build menu control
        menu = wx.Menu()
        self._AppendMenuItem(menu, _('&Copy Value'), on_copy,
            id=wx.ID_COPY)
        if pyexiv2:
            self._AppendMenuItem(menu, _('&Add Tag'), on_add, 'Ctrl+N',
                id=wx.ID_ADD)
        if self.image_table.is_cell_deletable(row, col):
            self._AppendMenuItem(menu, _("&Delete Tag"), on_delete_cell,
                'Del', id=wx.ID_DELETE)
        #show menu
        self.PopupMenu(menu)
        menu.Destroy()

    def OnGridLabelRightClicked(self, event):
        event.Skip()
        row, col = event.GetRow(), event.GetCol()
        if row == -1:
            self.OnGridColLabelRightClicked(col)
        else:
            self.OnGridRowLabelRightClicked(row)

    def OnGridLabelLeftDclicked(self, event):
        event.Skip()
        row, col = event.GetRow(), event.GetCol()
        if row == -1:
            system.start(self.image_table.get_image_filename(col))

    def OnGridColLabelRightClicked(self, col):
        menu = wx.Menu()
        #open
        self._AppendMenuItem(menu, _('&Open...'), self.OnOpen,
            id=wx.ID_OPEN)
        #open url
        self._AppendMenuItem(menu, _('Open &Url...'), self.OnOpenUrl,
            'Shift+Ctrl+O')
        #remove image

        def on_remove(event):
            self.DeleteCols(col)

        self._AppendMenuItem(menu, _('&Remove Image'), on_remove)
        #show menu
        self.PopupMenu(menu)
        menu.Destroy()

    def _AppendMenuItem(self, menu, label, method, shortcut='', id=None):
        if id is None:
            id = wx.NewId()
        menu.Append(id, '%s\t%s' % (label, shortcut))
        self.Bind(wx.EVT_MENU, method, id=id)

    def OnGridRowLabelRightClicked(self, row):
        #build menu control
        menu = wx.Menu()
        self.CreateRowLabelMenu(menu, row)
        #show menu
        self.PopupMenu(menu)
        menu.Destroy()

    def CreateRowLabelMenu(self, menu, row):
        #bind menu events
        def on_add(event):
            self.AddRow()

        def on_copy(event):
            self.CopyRowLabel(row)

        def on_delete_row(event):
            self.DeleteRows(row)

        def on_set_row_label(event):
            self.RenameRowLabelValue(row)

        def on_set_row_values(event):
            self.ChangeRowValues(row)

        self._AppendMenuItem(menu, _('&Copy Tag'), on_copy,
            'Shift+Ctrl+C')
        if pyexiv2:
            self._AppendMenuItem(menu,
                _('&Add Tag to All Images...'),
                on_add, 'Shift+Ctrl+N')
        if self.image_table.is_row_editable(row) and pyexiv2:
            self._AppendMenuItem(menu,
                _("&Delete Tag from All Images..."),
                on_delete_row, 'Shift+Del')
            self._AppendMenuItem(menu,
                _("&Rename Tag for All Images..."),
                on_set_row_label, 'Shift+Ctrl+R')
            self._AppendMenuItem(menu,
                _("&Modify Value for All Images..."),
                on_set_row_values, 'Shift+Ctrl+M')

    def CopyRowLabel(self, row):
        clipboard.copy_text('<%s>' % self.table.GetRowLabelValue(row))

    def AddRow(self):
        key, value = AddTagDialog(self, self.image_table.keys).GetModal()
        if key:
            row = self.table.GetNumberRows()
            col = self.GetGridCursorCol()
            log = self.image_table.add_key(key, value)
            if log:
                self.ShowError(log, _('Unable to add tag <%s>') % key)
            self.RefreshAll()
            wx.CallAfter(self.MakeCellVisible, row, col)

    def AddColumnRow(self, col):
        key, value = AddTagDialog(self, self.image_table.keys).GetModal()
        if key:
            row = self.table.GetNumberRows()
            image = self.image_table.images[col]
            log = self.image_table.add_image_key(image, key, value)
            if log:
                self.ShowError(log, _('Unable to add tag <%s>') % key)
            self.RefreshAll()
            wx.CallAfter(self.MakeCellVisible, row, col)

    def DeleteCell(self, row, col):
        key = self.GetRowLabelValue(row)
        image_name = self.GetColLabelValue(col)
        if self.Ask('%s\n<%s>' % (CONFIRM_DELETE_TAG % image_name, key)) \
                == wx.ID_YES:
            log = self.image_table.delete_cell(row, col)
            if log:
                self.ShowError(log, _('Unable to delete tag <%s>') % key)
            self.RefreshAll()

    def DeleteRows(self, pos=0, num=1):
        key = self.GetRowLabelValue(pos)
        if self.Ask('%s\n<%s>' % (CONFIRM_DELETE_TAG_ALL, key)) \
                == wx.ID_YES:
            log = self.table.DeleteRows(pos, num)
            if log:
                self.ShowError(log, _('Unable to delete tag <%s>') % key)
            self.RefreshAll()

    def DeleteCols(self, pos=0, num=1):
        log = self.table.DeleteCols(pos, num)
        if log:
            self.ShowError(log, _('Unable to remove image'))
        if not self.CheckEmpty():
            self.RefreshAll()

    def RenameRowLabelValue(self, row):
        key_old = self.GetRowLabelValue(row)
        key_new = self.AskText(_('Rename tag for all images to:'),
            title=TITLE, value=key_old)
        if key_new:
            log = self.table.SetRowLabelValue(row, key_new)
            if log:
                self.ShowError(log, _('Unable to rename tag <%s>')\
                    % key_old)
            self.RefreshAll()

    def ChangeRowValues(self, row):
        value = self.AskText(_('Change value for all images to:'),
            title=TITLE)
        if value:
            key = self.GetRowLabelValue(row)
            log = self.image_table.set_key_value(key, value)
            if log:
                self.ShowError(log, _('Unable to change tag <%s>')\
                    % key)
            self.RefreshAll()

    def OnKeyDown(self, event):
        key_code = event.GetKeyCode()
        #print key_code
        row, col = self.GetCellRowCol()
        shift = event.ShiftDown()
        ctrl = event.ControlDown()
        alt = event.AltDown()
        if self.ProcessKey(key_code, row, col, shift, ctrl, alt):
            event.Skip()

    def ProcessKey(self, key_code, row, col, shift, ctrl, alt):
        if key_code == 127 \
                and self.image_table.is_cell_deletable(row, col):
            if shift:
                self.DeleteRows(row)
            else:
                self.DeleteCell(row, col)
        elif ctrl:
            if key_code == 67:
                #Ctrl+C
                if shift:
                    self.CopyRowLabel(row)
                else:
                    self.CopyCellValue(row, col)
            elif key_code == 78:
                #Ctrl+N
                if shift:
                    self.AddRow()
                else:
                    self.AddColumnRow(col)
            elif key_code == 82 and shift:
                #Ctrl+R
                self.RenameRowLabelValue(row)
            elif key_code == 77 and shift:
                #Ctrl+M
                self.ChangeRowValues(row)
        else:
            return True

    def OnRowLabelPaint(self, evt):
        window = self.GetGridRowLabelWindow()
        rect = window.GetClientRect()
        dc = wx.PaintDC(window)
        pen = dc.GetPen()
        dc.SetPen(self.GRAY_PEN)
        dc.DrawLine(rect[0] + rect[2] - 1, rect[1],
            rect[0] + rect[2] - 1, rect[1] + rect[3])

        def label_rect(position, row):
            row_width = self.GetRowLabelSize()
            row_height = self.GetRowSize(row)
            return (0, position, row_width, row_height)

        def get_bitmap(index):
            if self.image_table.is_row_editable(index):
                return self.PENCIL_BITMAP

        self._LabelPaint(dc, co=1, amount=self.GetNumberRows(),
            label_rect=label_rect, get_size=self.GetRowSize,
            get_label=self.GetRowLabelValue,
            get_bitmap=get_bitmap, border=True, center_bitmap=False,
            pen=pen)

    #---paint
    def _LabelPaint(self, dc, co, amount, label_rect, get_size,
            get_label, get_bitmap, border, center_bitmap, pen):
        position = -self.GetViewStart()[co]\
            * self.GetScrollPixelsPerUnit()[co]
        dc.SetBrush(self.GRAY_BRUSH)
        for index in range(amount):
            size = get_size(index)
            rect = label_rect(position, index)
            position += size
            if position < 0:
                continue
            if border:
                dc.DrawLine(rect[0], rect[1] + rect[3] - 1,
                    rect[0] + rect[2], rect[1] + rect[3] - 1)
            bitmap = get_bitmap(index)
            if bitmap:
                bitmap_size = bitmap.GetSize()
                if center_bitmap:
                    #centered
                    offset_x = (rect[2] - bitmap_size[0]) / 2
                else:
                    #right aligned
                    offset_x = rect[2] - bitmap_size[0] - self.border
                offset_y = (rect[3] - bitmap_size[1]) / 2
                dc.DrawBitmap(bitmap,
                    rect[0] + offset_x,
                    rect[1] + offset_y,
                    True)
            else:
                offset_y = (rect[3] - self.PENCIL_BITMAP_SIZE[1]) / 2
            dc.SetPen(pen)
            if get_label:
                dc.DrawText(get_label(index), rect[0] + self.border,
                    rect[1] + offset_y)

    #---dialogs
    def Ask(self, message, title=''):
        return self.ShowMessage(message, title,
            style=wx.YES_NO | wx.ICON_QUESTION)

    def AskText(self, question, value='', title=''):
        dlg = wx.TextEntryDialog(self, question, title, value)
        if dlg.ShowModal() == wx.ID_OK:
            answer = dlg.GetValue()
        else:
            answer = None
        dlg.Destroy()
        return answer

    def ShowMessage(self, message, title='',
            style=wx.OK | wx.ICON_EXCLAMATION):
        dlg = wx.MessageDialog(self,
                message,
                title,
                style,
        )
        answer = dlg.ShowModal()
        dlg.Destroy()
        return answer

    def ShowError(self, message, title=TITLE):
        return self.ShowMessage(message, title, style=wx.OK | wx.ICON_ERROR)

    def OpenImage(self, filename):
        try:
            self.image_table.open_image(filename, encoding=WX_ENCODING)
        except IOError, message:
            self.show_error(_('Sorry, %s.') % str(message),
                title=_('Image Inspector'))
            return
        self.image_table.update()
        self.UpdateThumbs()
        self.SetTitleFilename(filename)
        self.RefreshAll(update_column=True)

    def OpenImages(self, filenames):
        wx.BeginBusyCursor()
        invalid = self.image_table.open_images(filenames,
            encoding=WX_ENCODING)
        if invalid:
            wx.CallAfter(wx.EndBusyCursor)
            self.show_error('%s:\n\n%s' % (
                    _('Sorry, unable to open these images:'),
                    '\n'.join(invalid)), title=TITLE)
            wx.BeginBusyCursor()
        if len(invalid) != len(filenames):
            self.UpdateThumbs()
            if len(filenames) == 1:
                self.SetTitleFilename(filenames[0])
            self.RefreshAll(update_column=True)
        wx.CallAfter(wx.EndBusyCursor)

    def GetCellRowCol(self, event=None):
        if event:
            x, y = event.GetPosition()
            return self.XToCol(x), self.YToRow(y)
        else:
            return self.GetGridCursorRow(), self.GetGridCursorCol()

    def show_error(self, message, title):
        return self.show_message(message, title, style=wx.OK | wx.ICON_ERROR)

    def show_message(self, message, title='',
            style=wx.OK | wx.ICON_EXCLAMATION):
        if self.IsShown():
            parent = wx.GetTopLevelParent(self)
        else:
            parent = None
        dlg = wx.MessageDialog(parent,
                message,
                title,
                style,
        )
        answer = dlg.ShowModal()
        dlg.Destroy()
        return answer


class OpenMixin(object):

    def OnOpen(self, event):
        style = wx.OPEN | wx.CHANGE_DIR
        if hasattr(wx, 'FD_PREVIEW'):
            style |= wx.FD_PREVIEW
        path = os.path.dirname(self.image_table.images[-1].filename)
        dlg = wx.FileDialog(self, _("Choose an image"),
            defaultDir=path,
            wildcard=self.wildcard,
            style=style)
        if dlg.ShowModal() == wx.ID_OK:
            self.OpenImage(dlg.GetPath())
        dlg.Destroy()

    def OnOpenUrl(self, event):
        dlg = wx.TextEntryDialog(self, _("Enter an image url"))
        if dlg.ShowModal() == wx.ID_OK:
            self.OpenImage(dlg.GetValue())
        dlg.Destroy()

    def OpenImage(self, filename):
        super(OpenMixin, self).OpenImage(filename)
        self.GetTopLevelParent().SetTitleFilename(filename)
        self.SetTag(None)
        self.SetFilter(None)

    def OpenImages(self, filenames):
        super(OpenMixin, self).OpenImages(filenames)
        self.SetTag(None)
        self.SetFilter(None)

    def GetTopLevelParent(self):
        return wx.GetTopLevelParent(self)


class GridTag(OpenMixin, tag.ContentMixin, Grid):

    def IsEmpty(self):
        return 0 in (self.image_table.get_image_amount(),
            self.image_table.get_key_amount())

    def SetTag(self, tag):
        """Filters from all_data to tag_data"""
        if not (tag is None):
            super(GridTag, self).SetTag(tag)
        self.image_table.set_tag(tag)
        self.image_table.set_filter()
        self.GetFilter().SetValue('')
        if not self.CheckEmpty():
            self.RefreshAll()

    def SetFilter(self, filter=None):
        self.image_table.set_filter(filter)
        if not self.CheckEmpty():
            self.RefreshAll()


class Browser(tag.Browser):
    ContentCtrl = GridTag

    def _init(self):
        self.GetContent().SetTag(SELECT)

    def GetPaintMessage(self):
        content = self.GetContent()
        if not content.image_table.images:
            return _('drag & drop any images here')
        tag = self.tag.GetStringSelection().lower()
        if tag == 'Exif' and not pyexiv2:
            return _('please install pyexiv2')
        if content.image_table.key_amount_tag:
            return _('broaden your search')
        return _('no %s tags found') % tag


class Frame(wx.Frame):
    Browser = Browser

    def __init__(self, parent, filename='', icon=None,
            thumb_size=THUMB_SIZE, *args, **kwds):
        #adapt style
        if not('style' in kwds) and parent:
            kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | \
                wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_NO_TASKBAR | \
                wx.MAXIMIZE_BOX
        super(Frame, self).__init__(parent, *args, **kwds)
        if icon:
            self.SetIcon(icon)
        self._create_controls(TAGS, thumb_size)
        self._layout()
        #open filenames
        if os.path.isfile(filename):
            self.GetGrid().OpenImage(filename)
        elif os.path.isdir(filename):
            self.GetGrid().OpenImages([filename])
        #bind events
        self.browser.EnableResize()
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        self.Bind(UPDATE_EVENT, self.UpdateIfNeeded)

    def OnActivate(self, event):
        if event.GetActive():
            self.UpdateIfNeeded()

    def UpdateIfNeeded(self, event=None):
        if self.GetGrid().UpdateIfNeeded():
            wx.CallAfter(self.browser.filter.SetFocus)

    def _create_controls(self, tags, thumb_size):
        self.panel = wx.Panel(self, -1)
        self.browser = self.Browser(self.panel, tags,
            {'thumb_size': thumb_size})

    def _layout(self):
        #main_sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        #browser
        main_sizer.Add(self.browser, 1, wx.ALL | wx.EXPAND, 4)
        #layout
        self.panel.SetSizer(main_sizer)
        #panel_sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.panel, 1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(panel_sizer)
        #layout
        self.Layout()

    def GetGrid(self):
        return self.browser.GetContent()

    def OpenImage(self, filename):
        self.GetGrid().OpenImage(filename)

    def OpenImages(self, filenames):
        self.GetGrid().OpenImages(filenames)

    def SetTitleFilename(self, filename):
        """To be called from the grid."""
        if filename.strip():
            di, ba = os.path.split(filename)
            self.SetTitle('%s %s' % (ba, di))
        else:
            self.SetTitle(TITLE)


def getPencilData():
    # Embedded icon from the openclipart gallery
    return zlib.decompress(
'x\xda\x01\x88\x01w\xfe\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\
\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\
\x08\x08\x08|\x08d\x88\x00\x00\x01?IDAT8\x8d\x8d\xd1\xbdj\x94A\x14\x06\xe0gc\
4\x12\xe3\x8aM\xb0N\xa1M\xb0\xb3K\x04+\x03{\x0b\xa2!F\xc5\xe3\r\xe4\n\xbc\
\x84\x93?"\xa4P\xb0\xb4\xd8"\x85`k#6\x16Z$\x85\xd8l D\x8c\x04!\xf1\xb3\x99\r\
\x1f\xeb\xeefO73<\xef\x9c9\xd3\xa8\xaa\xca\xa8\x15\x11\x15\xbe\xe0\x06\xd6\
\xf0\xb21J@D\\\xc2\x1f|\xc2\x0b\x1c\xe0+\x8c\x8d\x80\'\n\xfe\x8em\xecf\xe67\
\xccb\x7fh\x07\x11q\x19\xc7\xd8\xc1;\xcc\x17x\x173x30 "&\xf1\x1bo\xf1 3O\xca\
\xfe+\xfc\xc0\x1d\xdc\x1f\x1f\x80\xaf\xe0\x08\xaf\xf1(3Ok\xc7\x1f\xcaS\xe0\
\xe2\x7f3\x88\x88\xa9\x82\xb7\xf1\xb0\x8e#\xa2\x81{ey53O\xc6zp\x13\xbf\xb0\
\x85\xa5\xcc\xfc\xdb\x83W\xb1X\xf0\x11\xb5_\x88\x88k\xf8\x89u<\xe9\x83\xd7\
\xf0\xac\x8e\xcf\x02"\xe2:\x0e\x91x\x9e\x99U\x0f^\xc7\xd3^\x0c\xdd!\x1e\xe0#\
V\xfa\xe0\r,\xf7\xc3p\xa1\xd3\xe9T\xe8`\x0f\xb3\xedv\xfb\xb4\xd5j\xed\x16\
\xbc9\x0c\xd7;\x98\xc6\x02n\x96\x9b\xdf\x17\xfcx\x18\xae\x07tk\x06s\xf8\x8c\
\xdb\xe7\xe1~\x01p\x0b\xcdQ\xf0\xa0\x80ff6\xce\x83\xdd\xfa\x07\xca\x88\x87\
\x90\xc0\xf9\xffl\x00\x00\x00\x00IEND\xaeB`\x82A.\xa9\xf2')


def getPencilBitmap():
    return wx.BitmapFromImage(getPencilImage())


def getPencilImage():
    stream = cStringIO.StringIO(getPencilData())
    return wx.ImageFromStream(stream)


if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = Frame(None, FILENAME, size=SIZE)
    frame.Show(True)
    app.MainLoop()
