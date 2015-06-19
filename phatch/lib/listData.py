# Copyright (C) 2009 www.stani.be
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

import operator
import os


class DataTuple(object):
    #not used by phatch
    def __init__(self, data=None):
        """Makes a data source which allows filtering independent of
        the gui toolkit. It is normally used in a list control.

        :param data: list of tuples
        :type data: list
        """
        self.amount = 0
        self.data = []
        self.filter = ''
        if data is None:
            data = []
        self.set_data(data)

    def __len__(self):
        """Returns the amount of data rows.

        >>> data = DataTuple([(0, )])
        >>> len(data)
        1
        """
        return len(self.data)

    def get(self, row, col):
        """Returns the cell value specified by the row and col.

        :param row: index of row
        :type row: int
        :param col: index of column
        :type col: int
        :returns: cell value

        >>> data = DataTuple([(0, 6)])
        >>> data.get(0,0)
        6
        """
        if row < self.amount:
            return self.data[row][col + 1]
        else:
            raise IndexError(row)

    def get_headers(self):
        """Get the headers of the columns.

        :returns: headers of the columns
        :rtype: list of strings

        >>> data = DataTuple([('id1','f1'),('id0','f2')])
        >>> data.get_headers()
        ['0']
        """
        return [str(x) for x in range(len(self.data[0][1:]))]

    def set_data(self, data, amount=None, sort=True):
        """The data is organised as tuple/list of tuples. Amount is how much
        is visible and not necessarily the length of the data tuple!

        :param data: data organized in rows
        :type data: tuple/list
        :param amount: amount of rows visible
        :type amount: int
        :returns: whether the underlying data has really changed
        :rtype: bool

        >>> data = DataTuple()
        >>> data.set_data([(6, ),(5, )], amount=1)
        True
        >>> data.set_data([(6, ),(5, )], amount=1)
        False
        >>> len(data) == data.amount
        False
        """
        if amount is None:
            amount = len(data)
        else:
            amount = amount
        if sort:
            data = self.sort(data)
        if self.data == data and self.amount == amount:
            return False
        self.data = data
        self.amount = amount
        return True

    def sort(self, data):
        """Sorts the data in place.

        >>> DataTuple().sort([('id1','f1'),('id0','f2')])
        [('id0', 'f2'), ('id1', 'f1')]
        """
        data.sort()
        return data

    def set_filter(self, filter):
        """Filters the data which is visible. It puts the visible data
        rows to the front and limits the amount. The visible data is
        automatically sorted.

        :param filter: substring which should appear in the data rows
        :type filter: string
        :returns: whether the filter has really changed
        :rtype: bool

        >>> data = DataTuple([(6, ),(5, )])
        >>> data.set_filter('6')
        True
        >>> data.set_filter('6')
        False
        >>> data.amount
        1
        >>> len(data)
        2
        """
        filter = filter.lower()
        if self.filter == filter:
            return False
        self.filter = filter
        include = []
        exclude = []
        for row in self.data:
            if filter in unicode(row).lower():
                include.append(row)
            else:
                exclude.append(row)
        include = self.sort(include)
        self.set_data(include + exclude, amount=len(include), sort=False)
        return True


class DataDict(DataTuple):
    #used by Phatch
    def __init__(self, data=None, headers=None, id='id'):
        """Makes a data source which allows filtering independent of
        the gui toolkit. It is normally used in a list control.

        :param data: list of tuples
        :type data: list
        :param headers: list of strings which are headers in the list
        :type headers: list
        """
        self.id = id
        DataTuple.__init__(self, data=data)
        if headers is None:
            headers = []
            all = True
        else:
            all = False
        self.update_headers(headers, all=all)

    def update_headers(self, headers=None, all=False):
        """Change sequence and find all headers (dict keys) in the data.

        >>> data = DataDict([{'id': 0, 'hello':'world'},
        ... {'id': 1, 'foo':'bar'}])
        >>> data.get_headers()
        ['foo', 'hello', 'id']
        >>> data.update_headers(['hello'])
        >>> data.get_headers()
        ['hello']
        >>> data.update_headers(['hello'], all=True)
        >>> data._headers
        ['hello', 'foo', 'id']
        """
        if all:
            if not(headers is None):
                self._fixed_headers = headers
            _headers = []
            for row in self.data:
                for header in row.keys():
                    if header not in self._fixed_headers + _headers:
                        _headers.append(header)
            _headers.sort()
            _headers = self._fixed_headers + _headers
            index = len(self._fixed_headers)
            self._headers = _headers[:index] + sorted(_headers[index:])
        elif headers:
            self._headers = headers

    def get(self, row, col, default=''):
        """Returns the cell value specified by the row and column index.

        :param row: index of row
        :type row: int
        :param col: index of column
        :type col: int
        :param default: value to return if column header does not exist
        :returns: cell value

        >>> data = DataDict([{'id': 0, 'hello':'world'},
        ... {'id': 1, 'foo':'bar'}])
        >>> data.get_headers()
        ['foo', 'hello', 'id']
        >>> data.get(0,0)
        ''
        >>> data.get(0,1)
        'world'
        >>> data.get(1,0)
        'bar'
        >>> data.get(1,1)
        ''
        >>> data.get(1,2)
        1
        """
        return self.get_by_header(row, self._headers[col], default)

    def get_by_header(self, row, header, default=''):
        """Returns the cell value specified by the row and column header.

        :param row: index of row
        :type row: int
        :param col: column header
        :type col: string
        :param default: value to return if column header does not exist
        :returns: cell value

        >>> data = DataDict([{'id': 0, 'hello':'world'},
        ... {'id': 1, 'foo':'bar'}], headers=['foo','hello'])
        >>> data.get_by_header(0,'foo')
        ''
        >>> data.get_by_header(0,'hello')
        'world'
        >>> data.get_by_header(1,'foo')
        'bar'
        """
        if row < self.amount:
            return self.data[row].get(header, default)
        else:
            raise IndexError(row)

    def get_headers(self):
        """Get the headers of the columns.

        :returns: headers of the columns
        :rtype: list of strings

        >>> data = DataDict([{'id': 0, 'hello':'world'},
        ... {'id': 1, 'foo':'bar', 'hello':'planet'}])
        >>> data.get_headers()
        ['foo', 'hello', 'id']
        """
        return self._headers

    def sort(self, data):
        """Sorts the data in place.

        >>> DataDict(id='path').sort([{'path': 'id1', 'name': 'f1'},
        ... {'path': 'id0', 'name': 'f2'}])
        [{'path': 'id0', 'name': 'f2'}, {'path': 'id1', 'name': 'f1'}]
        """
        return sorted(data, key=operator.itemgetter(self.id))


def _from_file_list(files, get_filename):
    """Helper function for file_data_tuple and file_data_dict.

    :param files: list of tuples or dictionaries
    :type files: list
    :param get_filename: returns the filename from a files item
    :type get_filename: function
    :returns: folder hierarchy
    :rtype: dict
    """

    def new_child():
        return {'children': {}, 'data': []}

    grandparents = []
    root = new_child()
    root_name = ''

    def find_parent(f, folder_name, parent, parent_name):
        if folder_name == parent_name:
            return parent, parent_name
        elif folder_name.startswith(parent_name):
            #create child (this will happen on first time)
            child = new_child()
            parent['children'][folder_name] = child
            grandparents.append({'name': parent_name, 'parent': parent})
            return child, folder_name
        else:
            #go up in hierarchy
            while not folder_name.startswith(grandparents[-1]['name']):
                grandparents.pop()
            data = grandparents[-1]
            parent = data['parent']
            parent_name = data['name']
            return find_parent(f, folder_name, parent, parent_name)

    files.sort(key=get_filename)
    parent = root
    parent_name = root_name
    for f in files:
        folder_name = os.path.dirname(get_filename(f)) + os.path.sep
        parent, parent_name = find_parent(f, folder_name, parent, parent_name)
        parent['data'].append(f)
    return root['children']


def files_data_tuple(files):
    """Turns a flat file list into a hierarchical one, of which the data
    values can be fed to the DataTuple Class (not the whole hierarchy).

    :param files:

        rows which consists of tuples, each tuples contains
        the full filename as the first element before other data

    :type files: list
    :returns: folder hierarchy
    :rtype: dict

    >>> import pprint
    >>> files = [('f0/i00', 0), ('f0/i01', 1),
    ... ('f1/i10', 2), ('f1/f2/i120', 3),]
    >>> pprint.pprint(files_data_tuple(files),width=60)
    {'f0/': {'children': {},
             'data': [('f0/i00', 0), ('f0/i01', 1)]},
     'f1/': {'children': {}, 'data': [('f1/i10', 2)]},
     'f1/f2/': {'children': {}, 'data': [('f1/f2/i120', 3)]}}
    """

    def get_filename(f):
        return f[0]

    return _from_file_list(files, get_filename)


def files_data_dict(files):
    """Turns a flat file list into a hierarchical one , of which the data
    values can be fed to the DataDict Class (not the whole hierarchy).

    :param files:

        rows which consists of tuples, each tuples contains
        the full filename as the first element before other data

    :type files: list
    :returns: folder hierarchy
    :rtype: dict

    >>> import pprint
    >>> files = [{'path': 'f0/i00', 'size': '5kb'},
    ... {'path': 'f0/i01', 'size': '1kb'},
    ... {'path': 'f1/i10', 'size': '2kb'},
    ... {'path': 'f1/f2/i120', 'size': '3kb'}]
    >>> pprint.pprint(files_data_dict(files),width=60)
    {'f0/': {'children': {},
             'data': [{'path': 'f0/i00', 'size': '5kb'},
                      {'path': 'f0/i01', 'size': '1kb'}]},
     'f1/': {'children': {},
             'data': [{'path': 'f1/i10', 'size': '2kb'}]},
     'f1/f2/': {'children': {},
                'data': [{'path': 'f1/f2/i120',
                          'size': '3kb'}]}}
    """

    def get_filename(f):
        return f['path']

    return _from_file_list(files, get_filename)
