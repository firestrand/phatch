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

import locale
import sys
import wx
import graphics
from other.pyWx.TextCtrlAutoComplete import TextCtrlAutoComplete

if hasattr(wx, "PopupWindow"):

    class AutoCompleteTextCtrl(TextCtrlAutoComplete):
        def __init__(self, parent, id, value, style, choices):
            #ignore style
            TextCtrlAutoComplete.__init__(self, parent, choices=choices)
            self.initialize(value, choices)

        def initialize(self, value, choices):
            self.all_choices = choices
            self.SetValue(value)
            self.SetEntryCallback(self.setDynamicChoices)
            self.SetMatchFunction(self.match)
            self.setDynamicChoices()
            wx.CallAfter(self._showDropDown)

        def match(self, text, choice):
            '''
            Demonstrate "smart" matching feature,
            by ignoring http:// and www. when doing matches.
            '''
            t = text.strip().lower()
            c = choice.lower()
            if c.startswith(t):
                return True
            if c.startswith(r'http://'):
                c = c[7:]
            if c.startswith(t):
                return True
            if c.startswith('www.'):
                c = c[4:]
            return c.startswith(t)

        def setDynamicChoices(self):
            text = self.GetValue().lower()
            current_choices = self.GetChoices()
            choices = [choice for choice in self.all_choices
                if self.match(text, choice)]
            if choices != current_choices:
                self.SetChoices(choices)

        def _showDropDown(self, state=True):
            if not self.dropdown.IsShown():
                TextCtrlAutoComplete._showDropDown(self, True)

        def onControlChanged(self, event):
            if self:
                TextCtrlAutoComplete._showDropDown(self, False)
            event.Skip()

        def onClickToggleDown(self, event):
            TextCtrlAutoComplete.onClickToggleDown(self, event)
            self._showDropDown()

        def onListClick(self, evt):
            TextCtrlAutoComplete.onListClick(self, evt)
            self._setValueFromSelected()

        def _setValueFromSelected(self):
            TextCtrlAutoComplete._setValueFromSelected(self)
            TextCtrlAutoComplete._showDropDown(self, False)

        def StartEvents(self):
            p = wx.GetTopLevelParent(self)
            p.Bind(wx.EVT_ACTIVATE, self.onControlChanged)
            p.Bind(wx.EVT_MOVE, self.onControlChanged)

        def StopEvents(self):
            p = wx.GetTopLevelParent(self)
            p.Unbind(wx.EVT_ACTIVATE)
            p.Unbind(wx.EVT_MOVE)

        def onActivate(self, evt):
            if evt.GetActive():
                self._showDropDown()
            else:
                self.onControlChanged(evt)

    class AutoCompleteIconCtrl(AutoCompleteTextCtrl):
        def __init__(self, parent, id, value, style, choices,
                colNames=None, multiChoices=None, showHead=True,
                dropDownClick=True, colFetch=-1, colSearch=0,
                hideOnNoMatch=True, selectCallback=None, entryCallback=None,
                matchFunction=None, **therest):
            '''
            Constructor works just like wx.TextCtrl except you can pass in a
            list of choices.  You can also change the choice list at any time
            by calling setChoices.
            '''

            if 'style' in therest:
                therest['style'] = wx.TE_PROCESS_ENTER | therest['style']
            else:
                therest['style'] = wx.TE_PROCESS_ENTER

            wx.TextCtrl.__init__(self, parent, **therest)

            #Some variables
            self._dropDownClick = dropDownClick
            self._colNames = colNames
            self._multiChoices = multiChoices
            self._showHead = showHead
            self._choices = choices
            self._lastinsertionpoint = 0
            self._hideOnNoMatch = hideOnNoMatch
            self._selectCallback = selectCallback
            self._entryCallback = entryCallback
            self._matchFunction = matchFunction

            self._screenheight = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)

            #sort variable needed by listmix
            self.itemDataMap = dict()

            #Load and sort data
            if not (self._multiChoices or self._choices):
                raise ValueError(
                    "Pass me at least one of multiChoices OR choices")

            #widgets

            #Control the style
            self.dropdown = wx.PopupWindow(self, wx.SIMPLE_BORDER)
            flags = wx.NO_BORDER | wx.LC_ICON | wx.LC_SINGLE_SEL \
                | wx.LC_SORT_ASCENDING
            #if not (showHead and multiChoices) :
            #    flags = flags | wx.LC_NO_HEADER

            #Create the list and bind the events
            size = (64, 64)
            self.il = wx.ImageList(*size)
            self.sm_dn = self.il.Add(graphics.bitmap('ART_FOLDER', size))
            self.sm_up = self.il.Add(graphics.bitmap('ART_FOLDER', size))

            self.dropdownlistbox = wx.ListCtrl(self.dropdown, style=flags,
                                     pos=wx.Point(0, 0))

            self.dropdownlistbox.SetImageList(self.il, wx.IMAGE_LIST_NORMAL)

            if sys.platform.startswith('linux'):
                self.dropdownlistbox.SetBackgroundColour(
                    wx.SystemSettings_GetColour(wx.SYS_COLOUR_INFOBK))
            #initialize the parent
            if multiChoices:
                ln = len(multiChoices)
            else:
                ln = 1
            #else: ln = len(choices)

            #load the data
            if multiChoices:
                self.SetMultipleChoices(multiChoices, colSearch=colSearch,
                    colFetch=colFetch)
            else:
                self.SetChoices(choices)

            gp = wx.GetTopLevelParent(self)
            #while ( gp != None ) :
            gp.Bind(wx.EVT_MOVE, self.onControlChanged, gp)
            gp.Bind(wx.EVT_SIZE, self.onControlChanged, gp)
                #gp = gp.GetParent()

            self.Bind(wx.EVT_KILL_FOCUS, self.onControlChanged, self)
            self.Bind(wx.EVT_TEXT, self.onEnteredText, self)
            self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown, self)

            #If need drop down on left click
            if dropDownClick:
                self.Bind(wx.EVT_LEFT_DOWN, self.onClickToggleDown, self)
                self.Bind(wx.EVT_LEFT_UP, self.onClickToggleUp, self)

            self.dropdown.Bind(wx.EVT_LISTBOX, self.onListItemSelected,
                self.dropdownlistbox)
            self.dropdownlistbox.Bind(wx.EVT_LEFT_DOWN, self.onListClick)
            self.dropdownlistbox.Bind(wx.EVT_LEFT_DCLICK, self.onListDClick)
            self.dropdownlistbox.Bind(wx.EVT_LIST_COL_CLICK,
                self.onListColClick)

            self._ascending = True

            self.initialize(value, choices)

            self.dropdown.SetSize((self.dropdown.GetSize()[0], 500))

        def match(self, text, choice):
            '''
            Demonstrate "smart" matching feature,
            by ignoring http:// and www. when doing matches.
            '''
            return text.strip().lower() in choice.lower()

        def SetChoices(self, choices):
            '''
            Sets the choices available in the popup wx.ListBox.
            The items will be sorted case insensitively.
            '''
            choices = choices[:34]
            self._choices = choices
            self._multiChoices = None
            flags = wx.LC_ICON | wx.LC_SINGLE_SEL \
                | wx.LC_SORT_ASCENDING | wx.LC_NO_HEADER
            self.dropdownlistbox.SetWindowStyleFlag(flags)

            if not isinstance(choices, list):
                self._choices = [x for x in choices]

            #prevent errors on "old" systems
            if sys.version.startswith("2.3"):
                self._choices.sort(lambda x, y: cmp(x.lower(), y.lower()))
            else:
                self._choices.sort(key=lambda x: locale.strxfrm(x).lower())

            self._updateDataList(self._choices)

            self.dropdownlistbox.InsertColumn(0, "")

            for num, colVal in enumerate(self._choices):
                index = self.dropdownlistbox.InsertImageStringItem(
                    sys.maxint, colVal, self.sm_dn)

                self.dropdownlistbox.SetStringItem(index, 0, colVal)
                self.dropdownlistbox.SetItemData(index, num)

            self._setListSize()

            # there is only one choice for both search
            # and fetch if setting a single column:
            self._colSearch = 0
            self._colFetch = -1

else:
    AutoCompleteTextCtrl = AutoCompleteIconCtrl = wx.ComboBox
