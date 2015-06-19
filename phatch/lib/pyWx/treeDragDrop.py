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
import wx


class Mixin:
    def GetItemChildren(self, item):
        child, cookie = self.GetFirstChild(item)
        children = []
        while child:
            children.append(child)
            child = self.GetNextSibling(child)
        return children

    def GetRootChild(self, item):
        root = self.GetRootItem()
        if item == root:
                return -1
        parent = self.GetItemParent(item)
        while parent != root:
            item = parent
            parent = self.GetItemParent(item)
        return item

    def MoveChildUp(self, item):
        if item == self.GetRootItem():
            return
        parent = self.GetItemParent(item)
        children = self.GetItemChildren(parent)
        if item in children:
            index = children.index(item)
            if index > 0:
                children.remove(item)
                self._order = children[:index - 1] + \
                                    [item] + children[index - 1:]
                self.SortChildren(parent)
                #print 'SortChildren', \
                #         parent,self.GetItemParent(parent),self.GetRootItem()
                self._order = []

    def MoveChildDown(self, item):
        if item == self.GetRootItem():
            return
        parent = self.GetItemParent(item)
        children = self.GetItemChildren(parent)
        n = self.GetChildrenCount(parent, recursively=False)
        if item in children:
            index = children.index(item)
            if index < n - 1:
                children.remove(item)
                self._order = children[:index + 1] + \
                                    [item] + children[index + 1:]
                self.SortChildren(parent)
                self._order = []

    def OnCompareItems(self, item1, item2):
        if hasattr(self, '_order') and \
                (item1 in self._order) and (item2 in self._order):
            index1 = self._order.index(item1)
            index2 = self._order.index(item2)
            if index1 < index2:
                return -1
            if index1 == index2:
                return 0
            return 1
        else:
            raise 'no order'

    # Drag & drop
    def EnableDrag(self, dragTo=None):
        if dragTo is None:
            self._dragTo = self.GetRootChild
        else:
            self._dragTo = dragTo
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag, self)
        self.Bind(wx.EVT_TREE_END_DRAG, self.OnEndDrag, self)

    def DisableDrag(self):
        self.Unbind(wx.EVT_TREE_BEGIN_DRAG, self)
        self.Unbind(wx.EVT_TREE_END_DRAG, self)

    def OnBeginDrag(self, event):
        '''Allow drag-and-drop.'''
        item = event.GetItem()
        if item.IsOk() and item != self.GetRootItem():
            event.Allow()
            self._dragItem = item

    def OnEndDrag(self, event):
        '''Do the re-organization if possible'''
        # If we dropped somewhere that isn't on top
        # of an item, ignore the event.
        target = event.GetItem()
        if not (target.IsOk() and target != self.GetRootItem() and \
                hasattr(self, '_dragItem') and self._dragItem):
            return
        items = [self._dragItem, target]
        if self._dragTo:
            items = [self._dragTo(item) for item in items]
        parent, parentTarget = [self.GetItemParent(item) for item in items]
        if parent.IsOk() and parentTarget.IsOk() and parent == parentTarget:
            children = self.GetItemChildren(parent)
            if (items[0] in children) and (items[1] in children):
                # Move
                old, new = [children.index(item) for item in items]
                temp = children[new]
                children[new] = children[old]
                children[old] = temp
                self._order = children
                self.SortChildren(parent)
                self._order = []
        self._dragItem = None
