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

import os
import re
import shutil
import subprocess
import sys
import types
import tempfile
import textwrap

import safe

VERBOSE = False
BIN = []  # executable
ARG_STR = '".+?"|\'.+\'|\S+'
RE_ARG = re.compile(ARG_STR)
RE_COMMAND = re.compile('^(%s)' % ARG_STR)
RE_NEED_QUOTES = re.compile('^[^\'"].+?\s.+?[^\'"]$')


if sys.platform.startswith('win'):
    _EXE = '.exe'
    import windows.locate
    WINDOWS = True

    def rename(src, dest):
        try:
            os.remove(dest)
        except:
            pass
        os.rename(src, dest)
else:
    _EXE = ''
    WINDOWS = False

    rename = os.rename

EXE_PATHS = {}


def wrap(text, fill=70):
    return '\n'.join([textwrap.fill(line, 70)
        for line in text.split('\n')])


def title(text):
    """Turns a text in a title

    :param text: text
    :type text: str
    :returns: title
    :rtype: str

    >>> title('hello_world')
    'Hello World'
    """
    return text.replace('_', ' ').replace('-', ' ').title()
#---os


def is_www_file(url):
    """Checks whether a file is remote (http or ftp).

    :param url: file path or url
    :type url: str
    :returns: True if remote, False if local
    :rtype: bool

    >>> is_www_file('http://www.foo.com/logo.png')
    True
    >>> is_www_file('ftp://foo.com/logo.png')
    True
    >>> is_www_file('logo.png')
    False
    """
    return url.startswith('http://') or url.startswith('ftp://')


def is_file(path):
    """Checks wether a path is a valid local or remote file.

    :param path: the path which has to be checked
    :type path: str
    :returns:
        True if path is a valid local or remote file, False otherwise
    :rtype: bool

    >>> is_file('http://www.foo.com/logo.png')
    True
    >>> is_file('ftp://foo.com/logo.png')
    True
    >>> is_file('/etc/fstab')
    True
    >>> is_file('/etc/fstap')
    False
    """
    return os.path.isfile(path) or is_www_file(path)


def file_extension(uri):
    return os.path.splitext(uri)[-1][1:].lower()


def filename_to_title(filename):
    """Converts a filename to a title. It replaces dashes with spaces
    and converts every first character to uppercase.

    :param filename: an absolute or relative path
    :type filename: str
    :returns: titled version of the filename
    :rtype: bool

    >>> filename_to_title('~/highlight_mask.png')
    'Highlight Mask'
    """
    return title(os.path.splitext(os.path.basename(filename))[0])


def ensure_path(path):
    """Ensure a path exists, create all not existing paths.

    It raises an OSError, if an invalid path is specified.

    :param path: the absolute folder path (not relative!)
    :type path: str
    """
    _ensure_path(os.path.abspath(path).rstrip('/').rstrip('\\'))


def _ensure_path(path):
    """Ensure a path exists, create all not existing paths.
    (Helper function for ensure_path.)"""
    if not os.path.exists(path):
        parent = os.path.dirname(path)
        if parent:
            _ensure_path(parent)
            os.mkdir(path)
        else:
            raise OSError("The path '%s' is not valid." % path)


def fix_quotes(text):
    """Fix quotes for a command line parameter. Only surround
    by quotes if a space is present in the filename.

    :param text: command line parameter
    :type text: string
    :returns: text with quotes if needed
    :rtype: string

    >>> fix_quotes('blender')
    'blender'
    >>> fix_quotes('/my programs/blender')
    '"/my programs/blender"'
    """
    if not RE_NEED_QUOTES.match(text):
        return text
    if not ('"' in text):
        return '"%s"' % text
    elif not ("'" in text):
        return "'%s'" % text
    else:
        return '"%s"' % text.replace('"', r'\"')


def set_bin_paths(paths=[]):
    """Initializes where binaries can be found.

    :param paths: list of paths where binaries might be found
    :type paths: list of strings
    """
    global BIN
    BIN = paths


def find_in(filename, paths):
    """Finds a filename in a list of paths.

    :param filename: filename
    :type filename: str
    :param paths: paths
    :type paths: list of strings
    :returns: found filename with path or None
    :rtype: string or None
    """
    for path in paths:
        p = os.path.join(path, filename)
        if os.path.isfile(p):
            return p
    return None


def find_exe(executable, quote=True, use_which=True,
        raise_exception=False):
    """Finds an executable binary. Returns None if the binary can
    not be found.

    This method need some extra love for Windows and Mac.

    :param executable: binary which will be used as a plugin (eg imagemagick)
    :type executable: string
    :param quote: quote the path if it contains spaces
    :type quote: bool
    :param use_which: use the command ``which`` on non windows platforms
    :type use_which: bool
    :param raise_exception: raise exception if not found
    :type raise_exception: bool
    :returns: absolute path to the binary
    :rtype: string or None

    >>> find_exe('python')
    '/usr/bin/python'
    >>> find_exe('python', use_which=False)
    '/usr/bin/python'
    """
    try:
        return EXE_PATHS[executable]
    except KeyError:
        pass
    #executable with extension e.g. exe on windows
    executable_exe = executable
    if not executable_exe.endswith(_EXE):
        executable_exe += _EXE
    # try to first find in BIN
    executable_path = find_in(executable_exe, BIN)
    # try to find a system install (todo for windows)
    if not sys.platform.startswith('win') and use_which and \
            executable_path is None:
        path, err = shell('which %s' % executable_exe, shell=True)
        path = path.strip()
        if os.path.isfile(path):
            executable_path = path
    if executable_path is None:
        executable_path = find_in(executable_exe,
            os.environ['PATH'].split(os.pathsep))
        if (executable_path is None) and WINDOWS:
            executable_path = windows.locate.find_exe(executable)
    #quote if necessary
    if not (executable_path is None) and quote:
        executable_path = fix_quotes(executable_path)
    #cache and return the result
    EXE_PATHS[executable] = executable_path
    if executable_path is None and raise_exception:
        raise IOError('No such program: %s' % executable)
    return executable_path


def find_command(text):
    """Find command in text

    :param text: command line
    :type text: string
    :returns: text
    :rtype: text

    >>> find_command('convert image.jpg image.jpg')
    'convert'
    >>> find_command('"/my apps/convert" image.jpg image.jpg')
    '"/my apps/convert"'
    >>> find_command('/my apps/convert image.jpg image.jpg')
    '/my'
    """
    match = RE_COMMAND.match(text)
    if match:
        return match.group(0)
    return None


class TempFile:

    def __init__(self, suffix='', path=None):
        """Make a temporary file with :func:`tempfile.mkstemp`. Use
        the ``path`` attribute to get the filename.

        :param suffix:

            If suffix is specified, the file name will end with that
            suffix, otherwise there will be no suffix. ``TempFile`` does
            not put a dot between the file name and the suffix; if you
            need one, put it at the beginning of suffix.

        :type suffix: string
        :param path: prefabricated temp path
        :type path: string

        >>> t = TempFile('.png')
        >>> t.path.endswith('.png')
        True
        >>> t.close()
        """
        if path is None:
            self._fd, self.path = tempfile.mkstemp(suffix)
        else:
            self._fd = None
            self.path = path
        self._closed = False

    def close(self, force_remove=True, dest=''):
        """It is important to call this method when finished with
        the temporary file.

        :param force_remove:

            Remove temporary file and raise IOError when it does not exist
            anymore. Set to False too allow for processes that delete the
            temporary file when failing to exit succesfully.

        :type force_remove: boolean
        :param dest:

            This is eg used for thumbnails in order to rename them to
            their proper location

        :type dest: string

        """
        if self._closed:
            raise IOError("Temporary file '%s' is already closed." % self.path)
        self._closed = True
        if self._fd:
            os.close(self._fd)
        if not (force_remove or os.path.exists(self.path)):
            return
        if dest:
            shutil.move(self.path, dest)
        else:
            os.remove(self.path)


def shell(*args, **options):
    """Runs a shell command and captures the output.

    :param args: the command to be executed in the shell
    :type args: tuple of strings
    :returns: stdout and stdout
    :rtype: typle of strings

    >>> shell('echo world', shell=True)
    ('world\\n', '')
    """
    # TODO: 'shell': True IS REMOVED AND HAST BE MENTIONED EXPLICITLY
    options.update({'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE})
    pipe = subprocess.Popen(*args, **options)
    return pipe.stdout.read(), pipe.stderr.read()


def shell_cache(args, cache='', key=None, validate=None, **options):
    """Runs a shell command and captures the output. It uses a caching system
    so that cached results don't need to run a subprocess anymore. The results
    are cached by sys.platform

    :param args: the command to be executed in the shell
    :type args: tuple of strings
    :param cache: the filename of the cache file
    :type cache: string
    :param validate: a validate (eg mtime) to validate the cache result
    :returns: stdout and stdout
    :rtype: typle of strings

    >>> shell('echo world', shell=True)
    ('world\\n', '')
    """
    # Initialize cache_dict
    args = tuple(args)
    cache_dict = {}
    if key is None:
        key = args
    # Try to load from cache file
    if os.path.isfile(cache):
        f = open(cache, 'rb')
        source = f.read()
        f.close()
        try:
            cache_dict = safe.eval_safe(source)
        except SyntaxError:
            pass
    # Initialize result
    result = None
    # Is it cached already?
    if key in cache_dict:
        x = cache_dict[key]
        if sys.platform in x:
            x = x[sys.platform]
            if validate:
                if validate == x['validate']:
                    result = x
            else:
                result = x
    if result is None:
        # Add to cache
        result = {'validate': validate}
        result['stdout'], result['stderr'] = shell(args, **options)
        if not key in cache_dict:
            cache_dict[key] = {}
        cache_dict[key][sys.platform] = result
        # Save to cache
        ensure_path(os.path.dirname(cache))
        f = open(cache, 'wb')
        f.write(unicode(cache_dict))
        f.close()
    return result['stdout'], result['stderr']


def shell_returncode(*args, **options):
    """Runs a shell command and returns it's exit code.

    :param args: the command to be executed in the shell
    :type args: tuple of strings
    :returns: command exit code
    :rtype: integer
    """
    options.update({'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE})
    return subprocess.call(*args, **options)


def split_command(text):
    """Breaks a single command line into a list of string arguments.

    :param text: command line text
    :type text: str
    :returns: list of arguments
    :rtype: list of str

    >>> split_command('blender file_in.png file_out.png')
    ['blender', 'file_in.png', 'file_out.png']
    >>> split_command('"/my progs/blender" file_in.png file_out.png')
    ['"/my progs/blender"', 'file_in.png', 'file_out.png']
    """
    return RE_ARG.findall(text)


def call(args, **keyw):
    """Same as subprocess.call, but if only a command line text is
    given it breaks it in a list of arguments so it can be used
    also with ``shell=False`` on Unix.
    """
    if 'shell' in keyw:
        if not WINDOWS and type(args) in types.StringTypes and \
            not keyw['shell']:
            args = split_command(args.replace('\\\n', ' '))
    else:
        keyw['shell'] = not WINDOWS
    verbose = False
    if 'verbose' in keyw:
        if keyw['verbose']:
            verbose = True
        del keyw['verbose']
    if VERBOSE or verbose:
        print(args)
    subprocess.call(args, **keyw)


def start(path):
    """Open a file or browse a folder.

    :param path: location of the file
    :type path: string
    """
    if hasattr(os, 'startfile'):
        #windows
        os.startfile(path)
    else:
        if sys.platform.startswith('darwin'):
            #mac
            command = 'open'
        else:
            #linux
            command = 'xdg-open'
        subprocess.call('%s "%s"' % (command, path), shell=True)


class MethodRegister:

    def __init__(self):
        """Creates a register where methods to open files are registered
        by the extensions.

        >>> m = MethodRegister()
        >>> m.register(['bmp','png'], abs)
        >>> m.register(['png'], open)
        >>> m.register(['bmp'], None)
        >>> 'bmp' in m.extensions
        True
        >>> m.get_methods('bmp')
        [<built-in function abs>]
        >>> m.get_methods('png')
        [<built-in function abs>, <built-in function open>]
        >>> m.unregister_method(abs)
        >>> m.get_methods('bmp')
        []
        >>> 'bmp' in m.extensions
        False
        >>> m.get_methods('png')
        [<built-in function open>]
        """
        self._dict = {}
        self._methods = {}
        self._extensions = {}
        self.extensions = []

    def register(self, extensions, method):
        """Register one method for multiple extensions. If the method
        is None, it will cancel the registration.

        :param extensions: list of file extensions
        :type extensions: list of strings
        :param method: method to open a file
        :param method: function
        """
        if method is None:
            return
        for extension in extensions:
            if not(extension in self._methods):
                self._methods[extension] = []
            self._methods[extension].append(method)
        if not (method in self._extensions):
            self._extensions[method] = []
        self._extensions[method].extend(extensions)
        self._update()

    def does_process(self, filename):
        """Check if the filename can be processed by any of the
        registered methods.

        :param filename: filename
        :type filename: string
        """
        return file_extension(filename) in self.extensions

    def get_methods(self, extension):
        """Get all methods registered for an extension.

        :param extension: file extension
        :type extension: string
        :returns: list of methods registered for the extension
        :rtype: list
        """
        return self._methods.get(extension, [])

    def unregister_method(self, method):
        """Unregister a method from all extensions.

        :param method: method to open a file
        :param method: function
        """
        self._unregister(method, self._extensions, self._methods)

    def unregister_extension(self, extension):
        """Unregister an extension from all methods.

        :param extensions: list of file extensions
        :type extensions: list of strings
        """
        self._unregister(extension, self._methods, self._extensions)

    def _unregister(self, key, d, values):
        """Helper method for :ref:`unregister_method` and
        :ref:`unregister_extension`.

        :param key: method/extension
        :param d: self._extensions/self._methods
        :type d: dict
        :param values: self._methods/self._extensions
        :type values: dict
        """
        if key in d:
            for value in values.keys():
                values[value] = [x for x in values[value] if x != key]
                if not values[value]:
                    del values[value]
            del d[key]
            self._update()

    def _update(self):
        """Updates the list of extension after each change. Helper
        function for :ref:`register` and :ref:`_unregister`."""
        self.extensions = self._methods.keys()
