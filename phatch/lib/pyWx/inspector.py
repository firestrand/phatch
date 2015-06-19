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

"""This unites Table and Grid in one with the following presumptions:
- the grid only grows in rows"""

import wx
import  wx.grid as  gridlib

NUMBER_COLS = 3
TEST_DATA = [[str((row, col)) for col in range(NUMBER_COLS)]
                for row in range(100)]


class Table(gridlib.PyGridTableBase):

    def __init__(self, grid):
        gridlib.PyGridTableBase.__init__(self)
        self._grid = grid

    def GetGrid(self):
        return self._grid

    def GetAttr(self, row, col, kind):
        return self.GetGrid().GetTableAttr(row, col, kind)

    # This is all it takes to make a custom data table to plug into a
    # wxGrid.  There are many more methods that can be overridden, but
    # the ones shown below are the required ones.  This table simply
    # provides strings containing the row and column values.

    def GetNumberRows(self):
        return len(self.GetGrid().data)

    def GetNumberCols(self):
        return self.GetGrid()._number_cols

    def GetValue(self, row, col):
        return self.GetGrid().GetTableValue(row, col)

    def SetValue(self, row, col, value):
        self.GetGrid().SetTableValue(row, col, value)

    def IsEmptyCell(self, row, col):
        return self.GetGrid().IsTableEmptyCell()

    def DeleteRows(self, pos=0, numRows=1):
        self.GetGrid().DeleteTableRows(pos, numRows)


class Grid(gridlib.Grid):
    Table = Table
    _number_cols = NUMBER_COLS

    def __init__(self, parent, data, *arg, **keyw):
        gridlib.Grid.__init__(self, parent, *arg, **keyw)
        self.SetRowColours()
        self._table(data)
        self._layout()
        self._events()
        self._init()

    def _table(self, data):
        # The second parameter means that the grid is to take
        # ownership of the table and will destroy it when done.
        # Otherwise you would need to keep a reference to it and
        # call it's Destroy method later.
        self.data = self.all_data = data
        self.table = self.Table(self)
        self.SetTable(self.table, True)
        self._number_rows = self.table.GetNumberRows()

    def _layout(self):
        self.SetRowLabelSize(0)
        self.SetColLabelSize(0)
        self.DisableDragRowSize()
        self.SetColSize(0, 30)
        self.SetColSize(1, 240)
        self.SetColSize(2, 160)

    def _events(self):
        pass
        # self.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightDown)

    def _init(self):
        pass

    def OnRightDown(self, event):
        return
        print self.GetSelectedRows()

    def RefreshAll(self):
        self.BeginBatch()
        self.UpdateNumberRows()
        self.UpdateValues()
        self.EndBatch()
        self.AdjustScrollbars()
        self.ForceRefresh()

    def SetRowColours(self, odd=wx.Colour(250, 250, 250),
            even=wx.Colour(254, 255, 255)):
        self.odd_attr = gridlib.GridCellAttr()
        self.odd_attr.SetBackgroundColour(odd)
        self.even_attr = gridlib.GridCellAttr()
        self.even_attr.SetBackgroundColour(even)
        self.selected_attr = gridlib.GridCellAttr()
        self.selected_attr.SetBackgroundColour(
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.selected_attr.SetTextColour(
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

    def UpdateNumberRows(self):
        """Only consider adding or removing rows."""
        current, new, delmsg, addmsg =\
            (self._number_rows, self.table.GetNumberRows(),
            gridlib.GRIDTABLE_NOTIFY_ROWS_DELETED,
            gridlib.GRIDTABLE_NOTIFY_ROWS_APPENDED)
        if new < current:
            msg = gridlib.GridTableMessage(self.table, delmsg, new,
                current - new)
            self.ProcessTableMessage(msg)
        elif new > current:
            msg = gridlib.GridTableMessage(self.table, addmsg,
                new - current)
            self.ProcessTableMessage(msg)
        self._number_rows = new

    def UpdateValues(self):
        "Send an event to the grid table to update all displayed values"
        msg = gridlib.GridTableMessage(self.table,
            gridlib.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.ProcessTableMessage(msg)

    # ---table functions
    def GetTableValue(self, row, col):
        return self.data[row][col]

    def SetTableValue(self, row, col, value):
        self.data[row][col] = value

    def IsTableEmptyCell(self):
        return False

    def GetTableAttr(self, row, col, kind):
        attr = [self.even_attr, self.odd_attr][row % 2]
        self.AttrIncRef(attr)
        self.SetAttrReadOnly(attr)
        return attr

    def SetAttrReadOnly(self, attr, bool):
        # ugly hack to deal with unicode errors
        try:
            attr.SetReadOnly(bool)
        except UnicodeDecodeError:
            pass

    def AttrIncRef(self, attr):
        try:
            attr.IncRef()
        except UnicodeDecodeError:
            pass

# ---test


class TestFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "inspector", size=(640, 480))
        grid = Grid(self, TEST_DATA)

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = TestFrame(None)
    frame.Show(True)
    app.MainLoop()
