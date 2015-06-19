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

# ---import modules

# gui-indepedent
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '..')

from lib import formField
from lib import metadata

# gui-dependent
import wx
import graphics
import popup
import treeDragDrop

if __name__ == '__main__':
    sys.path.insert(0, '../..')

from lib.unicoding import exception_to_unicode

FIELD_DELIMITER = ': '
WX_ENCODING = wx.GetDefaultPyEncoding()
IMAGE_TEST_INFO = metadata.InfoTest()

# ---functions

# ---tree
ITEM_HEIGHT = 28
ICON_SIZE = (ITEM_HEIGHT, ITEM_HEIGHT)
TR_DEFAULT_STYLE = wx.TR_HAS_BUTTONS | wx.TR_NO_LINES | \
            wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_HIDE_ROOT | \
            wx.TR_DEFAULT_STYLE | wx.SUNKEN_BORDER


def _do_nothing(*args, **keyw):
    pass


def rescale(image, x, y, filter=None):
    """For compatibility with wxPython 2.6"""
    if filter is None and hasattr(wx, 'IMAGE_QUALITY_HIGH'):
        filter = wx.IMAGE_QUALITY_HIGH
    if filter is None:
        image.Rescale(x, y)
    else:
        image.Rescale(x, y, filter)


def get_index(li, index, n=3):
    try:
        return li[index]
    except IndexError:
        return (None, ) * n


class TreeMixin(treeDragDrop.Mixin):
    """
    - form is like an action
    """
    def __init__(self, form_factory={}, CtrlMixin=[],
        icon_size=(28, 28), show_error=_do_nothing, set_dirty=_do_nothing):
        if wx.Platform == "__WXGTK__":
            # indentation
            self.SetIndent(int(self.GetIndent() * 1.5))
# #        elif wx.Platform == "__WXMSW__":  # doesn't work
# #            self.SetIndent(int(self.GetIndent() / 2))
        # form factory
        self.form_factory = form_factory
        self.CtrlMixin = CtrlMixin
        # popup
        self.popup = None
        self.popup_item = None
        self._field_selected = False
        # methods
        self.show_error = show_error
        self.set_dirty = set_dirty
        # image list
        self.CreateImageList(icon_size)
        # drag & drop
        self.EnableDrag(dragTo=self.get_form_item)
        # collapse
        self.collapse_automatic = False
        self.evt_leave_window = False
        # clear
        self.delete_all_forms()
        # events
        self.events()

    def CreateImageList(self, icon_size):
        self.image_list = wx.ImageList(*icon_size)
        icon_disabled = graphics.bitmap(ICON_DISABLED)
        for form in self.form_factory.values():
            self._AddFormToImageList(form, icon_size, icon_disabled)
        self.SetImageList(self.image_list)

    def _AddFormToImageList(self, form, icon_size, icon_disabled):
        wx_image = graphics.image(form.icon, icon_size)
        form.icon_bitmap = wx.BitmapFromImage(wx_image)
        # rescale(image, icon_size[0], icon_size[1])
        import Image
        from wxPil import pil_wxImage, wxImage_pil
        wx_image = pil_wxImage(wxImage_pil(wx_image).resize(icon_size,\
                                                        Image.ANTIALIAS))
        form.icon_tree = wx.BitmapFromImage(wx_image)
        form.icon_tree_disabled = icon_disabled
        form.icon_tree_id = (
            self.image_list.Add(form.icon_tree_disabled),
            self.image_list.Add(form.icon_tree))

    def set_item_image(self, x, image):
        self.SetItemImage(x, image, wx.TreeItemIcon_Normal)

    def tree_label(self, name, value):
        return ''.join([_(name), FIELD_DELIMITER,
            self.CtrlMixin._to_local(value)])

    def delete_all_forms(self):
        self.DeleteAllItems()
        self.AddRoot('')

    # ---forms
    def append_form(self, form, item=-1):
        root = self.GetRootItem()
        if item is -1:
            item = self.AppendItem(root, _(form.label))
        else:
            item = self.InsertItem(root, item, _(form.label))
        self.set_item_image(item, form.icon_tree_id[True])
        self.SetItemBold(item, True)
        self.import_form(item, form)
        self.SelectItem(item)
        return item

    def append_forms(self, forms):
        collapse = len(forms) > 4
        for form in forms[: -1]:
            item = self.append_form(form)
            if collapse:
                self.Collapse(item)
        self.append_form(forms[-1])
        return forms

    def append_form_by_label(self, item, label):
        return self.append_form(self.form_factory[label](), item)

    def collapse_forms(self):
        root = self.GetRootItem()
        for child in self.GetItemChildren(root):
            self.Collapse(child)

    def enable_form(self, item, bool):
        self.enable_form_item(self.get_form_item(item), bool)

    def enable_form_item(self, item, bool):
        form = self.GetPyData(item)
        self.set_item_image(item, form.icon_tree_id[bool])
        self.SetItemTextColour(item, (wx.RED, wx.GREEN)[bool])
        if bool:
            self.Expand(item)
        else:
            self.Collapse(item)

    def expand_forms(self):
        root = self.GetRootItem()
        for child in self.GetItemChildren(root):
            self.Expand(child)

    def export_form(self, item, label=None):
        form = self.GetPyData(item)
        for field in self.GetItemChildren(item):
            label, value_as_string = self.GetPyData(field)
            form.set_field_as_string(label, value_as_string)
        form.set_field('__enabled__', self.is_form_enabled(item))
        return form

    def export_forms(self):
        root = self.GetRootItem()
        forms = []
        for child in self.GetItemChildren(root):
            forms.append(self.export_form(child))
        return forms

    def import_form(self, item, form):
        self.SetPyData(item, form)
        self.DeleteChildren(item)
        fields = form._get_fields()
        if not self.update_form_relevance(item):
            for label, field in fields.items():
                if field.visible:
                    self.append_field(item, label, field)
        enabled_field = form._get_fields()['__enabled__']
        self.enable_form_item(item, enabled_field.get())

    def append_field(self, parent, label, field, method=None, item=None):
        value_as_string = field.get_as_string()
        if method is None:
            new_item = self.AppendItem(parent,
                            self.tree_label(label, value_as_string))
        else:
            # print method, parent, item, self.tree_label(label,\
            #                                       value_as_string)
            # print
            new_item = method(parent, item,
                            self.tree_label(label, value_as_string))
        self.SetPyData(new_item, (label, value_as_string))
        return new_item

    def get_form(self, item, label=None):
        return self.export_form(self.get_form_item(item), label)

    def get_form_item(self, item):
        return self.GetRootChild(item)

    def get_form_field(self, item):
        label, value_as_string = self.GetPyData(item)
        return self.get_form(item, label)._get_field(label)

    def get_form_fields_visible(self, item, form):
        """Retrieves the visible fields and their values. If a field
        is dirty, its value will be overwritten with the newly given
        value.

        Very important: this handles the dirty fields.
        """
        form = self.GetPyData(item)
        fields = []
        for index, ui_field in enumerate(self.GetItemChildren(item)):
            label, value_as_string = self.GetPyData(ui_field)
            field = form._get_field(label)
            if field.dirty:
                # overrule if dirty
                value_as_string = field.get_as_string()
                self.SetItemText(ui_field,
                    self.tree_label(label, value_as_string))
                self.SetPyData(ui_field, (label, value_as_string))
                field.dirty = False
            fields.append((ui_field, label, value_as_string))
        return fields

    def has_forms(self):
        return self.GetCount()

    def toggle_form_item(self, item, event):
        root = self.GetRootItem()
        if item == root:
            event.Skip()
        else:
            parent = self.GetItemParent(item)
            if parent == root:
                image = self.GetItemImage(item, wx.TreeItemIcon_Normal)
                if image != -1:
                    self.enable_form_item(item,
                        not self.is_form_enabled(item))
                    self.set_dirty(True)

    def set_form_field_value(self, item, value_as_string):
        label, old = self.GetPyData(item)
        form = self.get_form(item, label)
        field = form._get_field(label)
        value_as_string = field.fix_string(value_as_string)
        if value_as_string != old:
            # test-validate the user input (see formField.Field.get)
            try:
                if isinstance(field, formField.PixelField):
                    field.get_size(IMAGE_TEST_INFO, 100, 100, label,
                        value_as_string)
                    # 100 is just some dummy value for base, dpi
                else:
                    field.get(IMAGE_TEST_INFO, label=label,
                        value_as_string=value_as_string, test=True)
                self.set_dirty(True)
            except formField.ValidationError, details:
                reason = exception_to_unicode(details, WX_ENCODING)
                self.show_error(reason)
                if formField.Field.safe:
                    return
            if value_as_string == '':
                # hack, fix me
                value_as_string = ' '
            self.SetPyData(item, (label, value_as_string))
            self.SetItemText(item, self.tree_label(label, value_as_string))
            form.set_field_as_string(label, value_as_string)

    def set_form_field_value_selected(self, value):
        item = self.GetSelection()
        if self.GetItemParent(item) == self.GetRootItem():
            return
        if item and self.GetPyData(item):
            field = self.get_form_field(item)
            if not (isinstance(field, formField.ChoiceField) \
                or  isinstance(field, formField.BooleanField) \
                or  isinstance(field, formField.ColorField) \
                or  isinstance(field, formField.SliderField)):
                self.set_form_field_value(item, value)

    # ---selected form
    def append_form_by_label_to_selected(self, label):
        item = self.get_form_selected()
        return self.append_form_by_label(item, label)

    def enable_selected_form(self, bool):
        self.enable_form_item(self.get_form_selected(), bool)

    def get_form_selected(self):
        if self.has_forms():
            return self.get_form_item(self.GetSelection())
        return -1

    def move_form_selected_down(self):
        self.MoveChildDown(self.get_form_selected())

    def move_form_selected_up(self):
        self.MoveChildUp(self.get_form_selected())

    def update_form_relevance(self, field_item):
        """Conditional form"""
        item = self.get_form_item(field_item)
        form = self.GetPyData(item)
        if not hasattr(form, 'get_relevant_field_labels'):
            return False
        all = form._get_fields()
        relevant = form.get_relevant_field_labels()
        ui_index = 0
        ui = self.get_form_fields_visible(item, form)
        ui_labels = [f[1] for f in ui]
        ui_field, ui_label, ui_value_as_string = get_index(ui, ui_index)
        ui_field_prev = None
        # print '_'*40
        for label, field in all.items():
            if not field.visible:
                continue
            # print 'item=', item, ', label=', label, ', ui_field=', field, ',\
            #   ui_label=', ui_label, ', child =', self.ItemHasChildren(item),\
            #   ', prev =', ui_field_prev
            # print
            next_ui = False
            deleted = False
            # relevant
            if label in relevant:
                if label == ui_label:
                    # already there
                    next_ui = True
                elif ui_field_prev:
                    # insert after previous ui field
                    # print 'prev value', self.GetPyData(ui_field_prev)
                    ui_field_prev = self.append_field(item, label, field,
                        self.InsertItem, ui_field_prev)
                elif self.ItemHasChildren(item):
                    # insert before first ui field
                    ui_field_prev = self.append_field(item, label, field,
                        self.InsertItemBefore, self.GetFirstChild(item))
                else:
                    # append as first element
                    ui_field_prev = self.append_field(item, label, field)
            # not relevant
            elif label in ui_labels:
                # save values
                form.set_field_as_string(ui_label, ui_value_as_string)
                # remove
                self.Delete(ui_field)
                next_ui = True
                deleted = True
            # next ui
            if next_ui:
                if ui_field and not deleted:
                    # deleted: we don't want to reference to dead objects
                    ui_field_prev = ui_field
                ui_index += 1
                ui_field, ui_label, ui_value_as_string = \
                    get_index(ui, ui_index)
        return True

    def remove_selected_form(self):
        form = self.get_form_selected()
        if form is -1:
            return False
        else:
            self.Delete(form)
            return True

    # ---last form
    def append_form_by_label_to_last(self, label):
        item = self.get_last_form()
        self.append_form_by_label(item, label)

    def get_last_form(self):
        return self.GetLastChild(self.GetRootItem())

    # ---popup
    def create_popup(self, item):
        """Connect formField.field to popup.Ctrl (VIP!)"""
        field = self.get_form_field(item)
        label, value = self.GetItemText(item).split(FIELD_DELIMITER, 1)
        pos, offset, size = self.get_popup_pos_offset_size(item)
        typ = field.__class__.__name__.replace('Field', '')

        def on_change(value_as_string):
            field.set_as_string(value_as_string)
            self.update_form_relevance(item)
        if isinstance(field, formField.SliderField):
            extra = {'minValue': field.min, 'maxValue': field.max}
        elif isinstance(field, formField.ChoiceField):
            extra = {'choices': field.choices, 'on_change': on_change}
            typ = 'Choice'
        elif isinstance(field, formField.DictionaryReadFileField):
            if field.dictionary is None:
                field.init_dictionary()
            extra = {'extensions': field.extensions,
                        'dictionary': field.dictionary}
            if isinstance(field, formField.ImageDictionaryField):
                extra['show_path'] = False
                extra['on_change'] = on_change
            if isinstance(field, formField.ImageDictionaryReadFileField):
                typ = 'ImageDictionaryFile'
                extra['dialog'] = field.dialog
                extra['icon_size'] = field.icon_size
            elif not isinstance(field, formField.FontFileField):
                typ = 'DictionaryFile'
        elif isinstance(field, formField.FileField):
            extra = {'extensions': field.extensions}
            typ = 'LabelFile'
        elif hasattr(field, 'choices'):
            extra = {'choices': field.choices, 'on_change': on_change}
        elif isinstance(field, formField.BooleanField):
            extra = {'on_change': on_change}
        else:
            extra = {}
        self.popup_item = item
        self.popup = popup.EditPanel(self, pos=pos, offset=offset,
                                size=size, label=_(label) + FIELD_DELIMITER,
                                value=value, extra=extra, typ=typ,
                                border=1, CtrlMixin=self.CtrlMixin)
        self.popup.Show()
        self.resize_popup()
        if not isinstance(field, formField.FontFileField):
            wx.GetTopLevelParent(self).Bind(wx.EVT_LEAVE_WINDOW,
                self.close_popup)
            self.evt_leave_window = True

    def create_popup_selected(self):
        item = self.GetSelection()
        if self.GetItemParent(item) == self.GetRootItem():
            return
        self.create_popup(item)

    def close_popup(self, event=None):
        frame = wx.GetTopLevelParent(self)
        if frame and self.evt_leave_window:
            frame.Unbind(wx.EVT_LEAVE_WINDOW)
            self.evt_leave_window = False
        if self.popup:
            value_as_string = self.popup.Close()
            self.set_form_field_value(self.popup_item, value_as_string)
            # self.update_form_relevance(self.popup_item)
        self.popup = self.popup_item = None

# #    This would be logical but only works in wxPython2.6
# #    def get_popup_pos_offset_size(self, item):
# #        text_only_rect = self.GetBoundingRect(item, textOnly=True)
# #        rect = self.GetBoundingRect(item, textOnly=False)
# #        pos = rect.GetPosition()
# #        size = rect.GetSize()
# #        offset = text_only_rect.GetPosition()[0] - pos[0]
# #        print self.GetClientSize(), self.GetSize(), self.GetRect(),\
# #                                                text_only_rect, rect
# #        return pos, offset, size
# #

    # A bit unlogical but works both in wxPython2.6 and 2.8
    def get_popup_pos_offset_size(self, item):
        text_only_rect = self.GetBoundingRect(item, textOnly=True)
        rect = self.GetRect()
        pos = rect[0], text_only_rect[1]
        offset = text_only_rect[0] - rect[0]
        size = self.GetClientSize()[0], text_only_rect.GetSize()[1]
        return pos, offset, size

    def resize_popup(self):
        if not(self.popup is None):
            item = self.GetSelection()
            pos, offset, size = self.get_popup_pos_offset_size(item)
            popup = self.popup
            popup.Freeze()
            popup.SetSize(size)
            popup.SetPosition(pos)
            popup.Layout()
            popup.Thaw()

    # ---events
    def events(self):
        # events
        self.Bind(wx.EVT_TREE_SEL_CHANGING, self.on_sel_changing, self)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_sel_changed, self)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_item_activated, self)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_select, self)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down, self)

    def enable_collapse_automatic(self, state):
        if state:
            if not self.collapse_automatic:
                self.collapse_forms()
                self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_item_expanding)
                self.collapse_automatic = True
        elif self.collapse_automatic:
            self.Unbind(wx.EVT_TREE_ITEM_EXPANDING)
            self.collapse_automatic = False

    def on_item_expanding(self, event):
        item = event.GetItem()
        root = self.GetItemParent(item)
        for child in self.GetItemChildren(root):
            if child != item and self.IsExpanded(child):
                self.Collapse(child)

    def on_left_down(self, event):
        self.close_popup()
        event.Skip()

    def on_item_activated(self, event):
        item = event.GetItem()
        if self.is_form(item):
            self.toggle_form_item(item, event)
        else:
            self.on_sel_changed(event)

    def on_sel_changing(self, event):
        self.close_popup()

    def on_sel_changed(self, event):
        self.close_popup()
        item = event.GetItem()
        self._field_selected = self.is_field(item)
        if self._field_selected:
            self.create_popup(item)
        elif self.collapse_automatic:
            # maybe better always
            self.Expand(item)

    def on_select(self, event):
        self.on_sel_changing(event)
        self.SelectItem(event.GetItem(), True)
        event.Skip()

    # ---checks
    def is_field(self, item):
        return self.GetItemParent(item) != self.GetRootItem() and \
                item != self.GetRootItem()

    def is_field_selected(self):
        return self._field_selected

    def is_form(self, item):
        return self.GetItemParent(item) == self.GetRootItem()

    def is_form_enabled(self, item):
        form = self.GetPyData(item)
        return self.GetItemImage(item, wx.TreeItemIcon_Normal) ==\
                                            form.icon_tree_id[True]

    def is_form_selected(self):
        return not self._field_selected


def example():
    global _
    _ = str
    import sys

    class Form1(formField.Form):
        label = 'form1'

        def __init__(self):
            formField.Form.__init__(self,
                foo1=formField.ChoiceField(value='a', choices=('a', 'b')))

    class Form2(formField.Form):
        label = 'form2'

        def __init__(self):
            formField.Form.__init__(self,
                foo2=formField.PixelField(value='100'))

    class Form3(formField.Form):
        label = 'form3'

        def __init__(self):
            formField.Form.__init__(self,
                foo2=formField.FileSizeField(value='100'))

    form_factory = {
        'form1': Form1,
        'form2': Form2,
        'form3': Form3,
    }
    form4 = formField.Form(foo3=formField.SliderField(value='100',
                    minValue=0, maxValue=100))
    forms = [x() for x in form_factory.values()]  # + [form4]

    class Tree(wx.TreeCtrl, TreeMixin):

        def __init__(self, parent, form_factory, *args, **keyw):

            class I18n_CtrlMixin:
                """Fake example of a Mixin"""
                _to_local = str
                _to_english = str
                _to_local = staticmethod(_to_local)
                _to_english = staticmethod(_to_english)

            wx.TreeCtrl.__init__(self, parent, style=TR_DEFAULT_STYLE, *args,\
                                                                        **keyw)
            TreeMixin.__init__(self,
                form_factory=form_factory,
                CtrlMixin=I18n_CtrlMixin,
                icon_size=(28, 28),
                show_error=parent.show_error,
                set_dirty=parent.set_dirty,)

    class Frame(wx.Frame):
        def show_error(self, message):
            sys.stdout.write(message + '\n')

        def set_dirty(self, bool):
            self.SetTitle(['', '*'][bool] + 'treeEdit test')

    class App(wx.App):
        def OnInit(self, *args, **keyw):
            frame = Frame(None)
            frame.set_dirty(False)

            sizer = wx.BoxSizer(wx.VERTICAL)
            self.tree = Tree(frame, form_factory)
            self.tree.append_forms(forms)
            sizer.Add(self.tree, proportion=1, flag=wx.EXPAND)
            frame.SetSizer(sizer)
            sizer.Fit(frame)

            frame.SetSize((300, 300))
            frame.Layout()
            frame.Show()
            self.SetTopWindow(frame)
            return True

    app = App(0)
    app.MainLoop()

# ---disabled
ICON_DISABLED = \
'x\xda\x01I\x03\xb6\xfc\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x1c\
\x00\x00\x00\x1c\x08\x06\x00\x00\x00r\r\xdf\x94\x00\x00\x00\x04sBIT\x08\x08\
\x08\x08|\x08d\x88\x00\x00\x03\x00IDATH\x89\xed\x94\xcfk\\U\x18\x86\x9f\xef\
\xdc\x99If\x98\xdc\xab\xf7\xb6\xbak\xa9\x01\xb9\xc5(\xed\xa2T\x14QAt\xad\xab\
l\xe2\xff\xe0\xda\xc4q`p\xe1\xc6\xff\xa1\xb3\xe9NA\x97\x82u\'-\xa2\x8bB\xa20\
I\x8b\xd4\xaa\xc9$\xce\x9da2?\xee9\x9f\x8b$\x9a\xdc\xdc\x9bQ\xe8\xc6\xd2\x17\
>\x0e\x9c\xf3\xf2>\x9c\xc3w>x\xa2\xc7^z\xfe|\xe9QzeF\xc0e \x04\xee\xc9\xf6\
\xf6\x83\x19\xde\x0b\xc0E`G\xb6\xb7\xd7\xff3pz\xee\xdc[\n\x1f\x00\xcf\x00\
\xdf\x0b|V\xde\xd9\xf9\xa9\xc0\x1b+\xac\x01W\x81\xadC\xef\xd7y\xde\xdc\'\x18\
F\xd1\xcbS\xd5\x8f\x81W\x81\x14\xb8\x02\x04\xc3(j\xd6\xba\xdd\x8d\x8c7\x9e\
\xaa6\x80e@\x81\xcb\x87\xdeA\xad\xdb\xfd.\x9bm\xb2\x1bI\x18V-\xbc\x94\xaa\
\xc6\xa9*\xa9j\xe9\xb0\x96-4\xfaQ\x14\x1fy\xfbQ\x14[h\xa4\xaa\xcb\x87^9\\\
\x17Sx!\t\xc3\xea\xcc\x1b\xfa\xbb\xbb\xfb\xbbax\x1f\xe8*D\'\x0eU\x97\x05\xf8\
3\x0c\x9b\x00S\xd5\x86\x1e\xdc\xec\xb8\x9c\xc0\x03\xa3\xda\t<o\x94\xcd\xf7\
\xb2\x1b\x00+\xe5\xf2VM\xa4\xef\xe0E\x07\xa1\x03\x8e\xd5\x92\x83\xe7,\xbcc\
\xe1\xdd\xcc\x19\n\x9b\n\x9f>\xb4\xf6\xcbg\xf7\xf64\x9b]\xd84[A\xe0U\x8dYq\
\xaa\xab\n\x8bE\xbeLX\xc7\x88\xb4\xf6\x9dk_\xea\xf5l\x81\xa7X[A\xe0UDV,\xcc\
\x84\nt<hMT\x0ba3\x81GPOd%Um*\\(\x08\xf9\xa5$\xf2\x91\x9d\x01\x83\x9c.\xcd\
\xeaR\xafg\x15n[x8U%\xaf,\xfc\xaap{\x16\xec_\x017\x83 \x1e9\xb76V\xbd\x9er\
\xf0)\xb35V\xbd>rnm3\x08\xe2\xb3\xb2`\xc6\x93\xfe\x1c\x04\xf1T\xb51U\xcd\xb6\
~\xae\xca"7\xcb"\xcd\xe7{\xbd\x8d"O!p\xc3\xf7\xe3\x89jc\x92\x033\xf0\x07\x80\
;\x18{\'T\x11\xb9Y\x11i\xc6I\x92\x0b\xcd\x05\xae\xfb\xfe\xe2H\xb55\xce\x81y\
\xd0\x99\x17\xf9\x04\xd0\x91\xea\x876\xa7{\xe7DnTE\x1aq\x92\xdc\xcb\x9e\x9d\
\x9a4w}\x7f~\xa2\xfa\xda\xbesog;\xa0\x04\x9d\x8a1\xad\xba1m\x00\xe7\x9c\x0e\
\x9d[M\x8fA\x05\x9cS}\xc33\xe6\x95\xbb\xbe\xff\xdbR\x92\x8c2\x19\xa7Bu\ni\n\
\xd6\xea?\x83\xa2$\xd2\x993\xe6\xc4?\xbbS\xaf\xb7\xe7\x8c!un5U=\x82\x1a\x03\
\xf3\x16L\xe5`\x98\x9f\xd0\xa9.\x8d\x93d,p\xab\x04\x9f[\x988H\x04\xd6\xab"-\
\xab\xda\xbe6\x18\xfc}\xf1k\x83\x81\xb5\xaa\xed\xaaHK\xa0cadaR\x16\xf9B\xe0V\
\x9c$\xe3l~a\xd3\xfc\xb0\xb0pq\xe4\xdc\xfb\x0e\x9e\xaa\x88|[5\xe6\xab\xa5$qy\
\xde;\xf5\xba\xa7\xf0\xdeD\xf5u\x0f~\x9f7\xe6\xc6\xd5~\xff~\x9e\xf7\xcco\xf1\
\xe3\xc2\x82\x0fT\xf6\xac\xed\xbe9\x1c\x9ez\x9e\xe3\xfa\xa6V\x93\xa7=/\x02&W\
\xfa\xfd\xe4,\xef\x13\xfd\xbf\xf5\x17\xcf\xbe\x8a\xda\xa5\xa7Q\xf6\x00\x00\
\x00\x00IEND\xaeB`\x82\xc7,\x94\xd8'

if __name__ == '__main__':
    example()
