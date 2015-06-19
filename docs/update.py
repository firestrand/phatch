#!/usr/bin/python

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

import glob
import os
from subprocess import call

TOC = '''
.. toctree::
   :maxdepth: 2

%s

'''

AUTO = '''
.. automodule:: %s
   :members:
   :undoc-members:
   :show-inheritance:
'''


def title(header):
    """Formats a header title.

    :param header: header text
    :type header: str
    :returns: header text
    :rtype: str

    >>> title('header')
    'header\\n******\\n'
    """
    return '%s\n%s\n' % (header, '*' * len(header))


def auto(module):
    """Returns sphinx code to automatically document the module.

    :param module: module name
    :type module: str
    :returns: sphinx code
    :rtype: str

    >>> print(auto('module'))
    <BLANKLINE>
    .. automodule:: module
       :members:
       :undoc-members:
       :show-inheritance:
    <BLANKLINE>
    """
    return AUTO % module


def toc(modules):
    """Return sphinx code for module table of contents

    :param modules: module names
    :type modules: list of str
    :returns: sphinx code
    :rtype: str

    >>> toc([])
    ''
    >>> print(toc(['foo', 'bar']))
    <BLANKLINE>
    .. toctree::
       :maxdepth: 2
    <BLANKLINE>
       bar
       foo
    <BLANKLINE>
    <BLANKLINE>
    """
    modules.sort()
    if not modules:
        return ''
    contents = '\n'.join(['   ' + m for m in modules])
    return TOC % contents


def write(filename, module, children):
    """Write sphinx code for auto documented module to a file

    :param filename: filename for the sphinx code
    :type filename: str
    :param module: name of the module
    :type module: str
    :param children: package modules
    :type children: list of str
    """
    f = open(filename, 'w')
    f.write(title(module.split('.')[-1]) + auto(module) + toc(children))
    f.close()


def update(py_root, rst_root='source', not_overwrite=['index.rst'],
        index='index2'):
    """Generate sphinx rst files from python source files.

    :param py_root: root folder of python source files
    :type py_root: str
    :param rst_root: root folder of rst source files
    :type rst_root: str
    :param not_overwrite: list of rst files which can't be overwritten
    :type not_overwrite: list of str
    :param index: base filename for the rst index
    :type index: str
    """

    def get_rst_file(module):
        return os.path.join(rst_root, module + '.rst')

    for f in [f for f in glob.glob(os.path.join(rst_root, '*.rst'))
        if not os.path.basename(f) in not_overwrite]:
        os.remove(f)

    root = py_root
    n = len(root)
    for parent, dirs, files in os.walk(root):
        modules = []
        rel_path = parent[n:].strip(os.path.sep)

        def get_module(path, append=True):
            """Transforms a path in a modulename and its rst location.
            """
            if append:
                parent = rel_path
            else:
                parent = ''
            module = os.path.join(parent, os.path.splitext(path)[0])\
                .replace(os.path.sep, '.')
            if append:
                modules.append(module)
            rst_file = get_rst_file(module)
            return module, rst_file

        #add subpackage dirs
        for d in dirs:
            module, rst_file = get_module(d)
        #add module files
        if '__init__.py' in files:
            files.remove('__init__.py')
        for file in files:
            if not (file.endswith('.py') and rel_path):
                continue
            module, rst_file = get_module(file)
            write(rst_file, module, [])
        # is this the index or the root module?
        if rel_path:
            module, rst_file = get_module(rel_path, append=False)
        else:
            module = index
            rst_file = get_rst_file(module)
        write(rst_file, module, modules)


def switch_colors(css, colors):
    #open
    f = open(css, 'rb')
    source = f.read()
    f.close()
    #switch
    for color_couple in colors:
        source = source.replace(*color_couple)
    #close
    f = open(css, 'wb')
    f.write(source)
    f.close()


def main(py_root, rst_root, not_overwrite, index, colors):
    """Generate sphinx rst files and html documentation.

    :param py_root: root folder of python source files
    :type py_root: str
    :param rst_root: root folder of rst source files
    :type rst_root: str
    :param not_overwrite: list of rst files which can't be overwritten
    :type not_overwrite: list of str
    :param index: base filename for the rst index
    :type index: str
    """
    update(py_root, rst_root, not_overwrite, index)
    call('make html', shell=True)
    switch_colors(os.path.join('build', 'html', '_static', 'default.css'),
        colors)
    switch_colors(os.path.join('build', 'html', '_static', 'pygments.css'),
        colors)


if __name__ == '__main__':
    main(
        py_root=os.path.abspath('../phatch'),
        rst_root='source',
        not_overwrite=['index.rst', 'bazaar.rst', 'pep8.rst', 'lico.rst',
            'testing.rst', 'release.rst'],
        index='index2',
        colors=(
            ('background-color: #eee;',
                'background-color: #252527; color: #ffa;'),
            ('background-color: #ffe4e4;',
                'background-color: #252527; color: #ffe4e4;'),
            ('#ecf0f3', '#1f1f21'),
            ('#303030', '#eee'),
            ('#f2f2f2', '#000'),
        )
    )
    #update(py_root)
