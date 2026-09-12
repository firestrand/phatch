# Phatch - Photo Batch Processor
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

# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.

# Follows PEP8

#---import modules

#standard library
import builtins
import codecs
import glob
import importlib
import operator
import os
import pprint
import traceback
from io import StringIO

#gui-independent
from lib import formField
from lib import metadata
from lib import openImage
from lib import safe
from lib.unicoding import ensure_unicode, exception_to_unicode, ENCODING

from . import ct
from . import pil
from .message import send

_ = getattr(builtins, '_', str)

#---constants
ACTIONS_LIST_FORMAT_VERSION = '2.0'  # JSON format (was '1.0' for pprint format)

# Action registry - populated by import_actions()
ACTIONS = None
ACTION_LABELS = None
ACTION_FIELDS = None

PROGRESS_MESSAGE = 'In: %s%s\nFile' % (' ' * 100, '.')
SEE_LOG = _('See "%s" for more details.') % _('Show Log')
TREE_HEADERS = ['filename', 'type', 'folder', 'subfolder', 'root',
    'foldername']
TREE_VARS = set(TREE_HEADERS).union(pil.BASE_VARS)
TREE_HEADERS += ['index', 'folderindex']
ERROR_INCOMPATIBLE_ACTIONLIST = \
_('Sorry, the action list seems incompatible with %(name)s %(version)s.')

ERROR_UNSAFE_ACTIONLIST_INTRO = _('This action list is unsafe:')
ERROR_UNSAFE_ACTIONLIST_DISABLE_SAFE = \
_('Disable Safe Mode in the Tools menu if you trust this action list.')
ERROR_UNSAFE_ACTIONLIST_ACCEPT = \
_("Never run action lists from untrusted sources.") + ' ' +\
_("Please check if this action list doesn't contain harmful code.")

#---classes


class PathError(Exception):

    def __init__(self, filename):
        """PathError for invalid path.

        :param filename: filename of the invalid path
        :type filename:string
        """
        self.filename = filename

    def __str__(self):
        return _('"%s" is not a valid path.') % self.filename

#---init/exit


def init():
    """Verify user paths and import all actions. This function should
    be called at the start."""
    from .config import verify_app_user_paths
    verify_app_user_paths()
    return import_actions()


#---error logs


def init_error_log_file():
    """Reset ERROR_LOG_COUNTER and create the ERROR_LOG_FILE."""
    global ERROR_LOG_FILE, ERROR_LOG_COUNTER
    ERROR_LOG_COUNTER = 0
    ERROR_LOG_FILE = codecs.open(ct.USER_LOG_PATH, 'wb',
                            encoding=ENCODING, errors='replace')


def log_error(message, filename, action=None, label='Error'):
    """Writer error message to log file.

    Helper function for :func:`flush_log`, :func:`process_error`.

    :param message: error message
    :type message: string
    :param filename: image filename
    :type filename: string
    :param label: ``'Error'`` or ``'Warning'``
    :type label: string
    :returns: error log details
    :rtype: string
    """
    global ERROR_LOG_COUNTER
    details = ''
    if action:
        details += os.linesep + 'Action:' + \
                    pprint.pformat(action.dump())
    ERROR_LOG_FILE.write(os.linesep.join([
        '%s %d:%s' % (label, ERROR_LOG_COUNTER, message),
        details,
        os.linesep,
    ]))
    try:
        traceback.print_exc(file=ERROR_LOG_FILE)
    except UnicodeDecodeError:
        stringio = StringIO()
        traceback.print_exc(file=stringio)
        traceb = stringio.read()
        ERROR_LOG_FILE.write(traceb)
    ERROR_LOG_FILE.write('*' + os.linesep)
    ERROR_LOG_FILE.flush()
    ERROR_LOG_COUNTER += 1
    return details

#---collect vars


def get_vars(actions):
    """Extract all used variables from actions.

    :param actions: list of actions
    :type actions: list of dict
    """
    vars = []
    for action in actions:
        vars.extend(action.metadata)
        for field in list(action._get_fields().values()):
            safe.extend_vars(vars, field.get_as_string())
    return vars


def assert_safe(actions):
    test_info = metadata.InfoTest()
    geek = False
    warning = ''
    for action in actions:
        warning_action = ''
        if action.label == 'Geek':
            geek = True
        for label, field in list(action._get_fields().items()):
            if label.startswith('_') \
                    or isinstance(field, formField.BooleanField)\
                    or isinstance(field, formField.ChoiceField)\
                    or isinstance(field, formField.SliderField):
                continue
            try:
                field.assert_safe(label, test_info)
            except Exception as details:
                warning_action += '  %s: %s\n'\
                    % (label, exception_to_unicode(details))
        if warning_action:
            warning += '%s %s:\n%s' % (_(action.label), _('Action'),
                warning_action)
    if warning:
        warning += '\n'
    if geek:
        warning += '%s\n' % (_('Geek actions are not allowed in safe mode.'))
    return warning

#---collect image files


def filter_image_infos(folder, extensions, files, root, info_file):
    """Filter image files by extension and verify if they are files. It
    returns a list of info dictionaries which are generated by
    :method:`InfoPil.dump`::

        {'day': 14,
         'filename': 'beach',
         'filesize': 9682,
         'folder': u'/home/stani',
         'foldername': u'stani',
         'hour': 23,
         'minute': 43,
         'month': 3,
         'monthname': 'March',
         'path': '/home/stani/beach.jpg',
         'root': '/home',
         'second': 26,
         'subfolder': u'',
         'type': 'jpg',
         'weekday': 4,
         'weekdayname': 'Friday',
         'year': 2008,
         '$': 0}

    ``$`` is the index of the file within a folder.

    Helper function for :func:`get_image_infos_from_folder`

    :param folder: folder path (recursion dependent)
    :type folder: string
    :param extensions: extensions (without ``.``)
    :type extensions: list of strings
    :param files: list of filenames without folder path
    :type files: list of strings
    :param root: root folder path (independent from recursion)
    :type root: string
    :returns: list of image file info
    :rtype: list of dictionaries
    """
    from pathlib import Path

    from phatch.services.file_discovery import (
        DirectoryListing,
        FileDiscovery,
        LocalDiscoveryFileSystem,
    )

    discovery = FileDiscovery(LocalDiscoveryFileSystem())
    listing = DirectoryListing(Path(folder), tuple(files))
    infos = []
    folder_index = 0
    normalized_extensions = frozenset(extension.lower() for extension in extensions)
    for candidate in discovery.candidates(listing, Path(root)):
        info = info_file.dump((str(candidate.path), str(candidate.source_root)))
        if discovery.is_file(candidate.path) and \
                info['type'].lower() in normalized_extensions:
            info['folderindex'] = folder_index
            infos.append(info)
            folder_index += 1
    return infos


def get_image_infos_from_folder(folder, info_file, extensions, recursive):
    """Get all image info dictionaries from a specific folder.

    :param folder: top folder path
    :type folder: string
    :param extensions: extensions (without ``.``)
    :type extensions: list of strings
    :param recursive: include subfolders
    :type recursive: bool
    :returns: list of image file info
    :rtype: list of dictionaries

    Helper function for :func:`get_image_infos`

    .. see also:: :func:`filter_image_infos`
    """
    from pathlib import Path

    from phatch.services.file_discovery import (
        FileDiscovery,
        LocalDiscoveryFileSystem,
    )

    discovery = FileDiscovery(LocalDiscoveryFileSystem())
    source_parent = Path(folder)  # do not change (independent of recursion!)
    image_infos = []
    for listing in discovery.listings(source_parent, recursive=recursive):
        image_infos.extend(filter_image_infos(
            str(listing.folder), extensions, list(listing.files),
            str(source_parent), info_file))
    return image_infos


def get_image_infos(paths, info_file, extensions, recursive):
    """Get all image info dictionaries from a mix of folder and file paths.

    :param paths: file and/or folderpaths
    :type paths: list of strings
    :param extensions: extensions (without ``.``)
    :type extensions: list of strings
    :param recursive: include subfolders
    :type recursive: bool
    :returns: list of image file info
    :rtype: list of dictionaries

    .. see also:: :func:`get_image_infos_from_folder`
    """
    from typing import assert_never

    from phatch.services.file_discovery import (
        FileDiscovery,
        InvalidDiscoveryPathError,
        LocalDiscoveryFileSystem,
        ResolvedFile,
        ResolvedFolder,
    )

    discovery = FileDiscovery(LocalDiscoveryFileSystem())
    image_infos = []
    for raw_path in paths:
        try:
            resolved = discovery.resolve(raw_path)
        except InvalidDiscoveryPathError as error:
            send.frame_show_error('Sorry, "%s" is not a valid path.' \
                % ensure_unicode(str(error.path)))
            return []
        match resolved:
            case ResolvedFile(path):
                info = {'folderindex': 0}
                info.update(info_file.dump(str(path)))
                image_infos.append(info)
            case ResolvedFolder(path):
                image_infos.extend(get_image_infos_from_folder(
                    str(path), info_file, extensions, recursive))
            case unreachable:
                assert_never(unreachable)
    image_infos.sort(key=operator.itemgetter('path'))
    return image_infos

#---check


def check_actionlist_file_only(actions):
    """Check whether the action list only exist of file operations
    (such as copy, rename, ...)

    :param actions: actions of the action list
    :type: list of :class:`core.models.Action`
    :returns: True if only file operations, False otherwise
    :rtype: bool

    >>> from actions import canvas, rename
    >>> check_actionlist_file_only([canvas.Action()])
    False
    >>> check_actionlist_file_only([rename.Action()])
    True
    """
    for action in actions:
        if 'file' not in action.tags:
            return False
    return True


def check_actionlist(actions, settings):
    """Verifies action list before executing. It checks whether:

    * the action list is not empty
    * all actions are not disabled
    * if there is a save action at the end or only file actions
    * overwriting images is forced

    :param actions: actions of the action list
    :type actions: list of :class:`core.models.Action`
    :param settings: execution settings
    :type settings: dictionary

    >>> settings = {'no_save':False}
    >>> check_actionlist([], settings) is None
    True
    >>> from actions import canvas, save
    >>> canvas_action = canvas.Action()
    >>> save_action = save.Action()
    >>> check_actionlist([canvas_action,save_action],
    ... {'no_save':False}) is None
    False
    >>> check_actionlist([canvas_action], settings) is None
    True
    >>> settings = {'no_save':True}
    >>> check_actionlist([canvas_action], settings) is None
    False
    >>> settings['overwrite_existing_images_forced']
    False

    .. see also:: :func:`check_actionlist_file_only`
    """
    from typing import assert_never

    from phatch.core.execution_types import ExecutionOptions
    from phatch.services.action_validation import (
        AcceptedActionList,
        ActionListRejectionReason,
        RejectedActionList,
        SaveActionRequired,
        validate_actionlist,
    )

    result = validate_actionlist(
        tuple(actions),
        ExecutionOptions(
            extensions=(),
            require_save_action=not settings['no_save'],
            safe_mode=formField.get_safe(),
        ),
        assert_safe,
    )
    match result:
        case RejectedActionList(reason=reason, diagnostic=diagnostic):
            match reason:
                case ActionListRejectionReason.EMPTY:
                    send.frame_show_error('%s %s' % (_('Nothing to do.'),
                        _('The action list is empty.')))
                    return None
                case ActionListRejectionReason.UNSAFE:
                    send.frame_show_error('%s\n\n%s\n%s' % (
                        ERROR_UNSAFE_ACTIONLIST_INTRO, diagnostic,
                        ERROR_UNSAFE_ACTIONLIST_DISABLE_SAFE))
                    return None
                case ActionListRejectionReason.ALL_DISABLED:
                    send.frame_show_error('%s %s' % (_('Nothing to do.'),
                        _('There is no action enabled.')))
                    return None
                case unreachable:
                    assert_never(unreachable)
        case SaveActionRequired(enabled_actions=enabled_actions):
            send.frame_append_save_action(list(enabled_actions))
            return None
        case AcceptedActionList(
                enabled_actions=enabled_actions,
                overwrite_existing_forced=overwrite_existing_forced):
            settings['overwrite_existing_images_forced'] = \
                overwrite_existing_forced
            return list(enabled_actions)
        case unreachable:
            assert_never(unreachable)


def verify_images(image_infos, repeat):
    """Filter invalid images out.

    Verify if images are not corrupt. Show the invalid images to
    the user. If no valid images are found, show an error to the user.
    Otherwise show the valid images to the user.

    :param image_infos: list of image info dictionaries
    :type image_infos: list of dictionaries
    :returns: None for error, valid image info dictionaries otherwise
    """
    #show dialog
    send.frame_show_progress(title=_("Checking images"),
        parent_max=len(image_infos),
        message=PROGRESS_MESSAGE)
    #verify files
    valid = []
    invalid = []
    for index, image_info in enumerate(image_infos):
        result = {}
        send.progress_update_filename(result, index, image_info['path'])
        if not result['keepgoing']:
            return
        openImage.verify_image(image_info, valid, invalid)
    send.progress_close()
    #show invalid files to the user
    if invalid:
        result = {}
        send.frame_show_files_message(result,
            message=_('Phatch can not handle %d image(s):') % len(invalid),
            title=ct.FRAME_TITLE % ('', _('Invalid images')),
            files=invalid)
        if result['cancel']:
            return
    #Display an error when no files are left
    if not valid:
        send.frame_show_error(_("Sorry, no valid files found"))
        return
    #number valid items
    for index, image_info in enumerate(valid):
        image_info['index'] = index * repeat
    #show valid images to the user in tree structure
    result = {}
    send.frame_show_image_tree(result, valid,
        widths=(200, 40, 200, 200, 200, 200, 60),
        headers=TREE_HEADERS,
        ok_label=_('C&ontinue'), buttons=True)
    if result['answer']:
        return valid

#---get


def get_paths_and_settings(paths, settings, drop=False):
    """Ask the user for paths and settings. In the GUI this shows
    the execute dialog box.

    :param paths: initial value of the paths (eg to fill in dialog)
    :type paths: list of strings
    :param settings: settings
    :type settings: dictionary
    :param drop:

        True in case files were dropped or phatch is started as a
        droplet.

    :type drop: bool
    """
    if drop or (paths is None):
        result = {}
        send.frame_show_execute_dialog(result, settings, paths)
        if result['cancel']:
            return
        paths = settings['paths']
        if not paths:
            send.frame_show_error(_('No files or folder selected.'))
            return None
    return paths


#---apply


def process_error(photo, message, image_file, action, result, ignore):
    """Logs error to file with :func:`log_error` and show dialog box
    allowing the user to skip, abort or ignore.

    Helper function for :func:`get_photo` and `apply_action`.

    :param photo: photo
    :type photo: class:`core.pil.Photo`
    :param message: error message
    :type message: string
    :param image_file: absolute path of the image
    :type image_file: string
    :param result: settings for dialog (eg ``stop_for_errors``)
    :type result: dictionary
    :returns: photo, result
    :rtype: tuple
    """
    log_error(message, image_file, action)
    #show error dialog
    if result['stop_for_errors']:
        send.frame_show_progress_error(result, message, ignore=ignore)
        #if result:
        answer = result['answer']
        if answer == _('abort'):
            #send.progress_close()
            result['skip'] = False
            result['abort'] = True
            return photo, result
        result['last_answer'] = answer
        if answer == _('skip'):
            result['skip'] = True
            result['abort'] = False
            return photo, result
    elif result['last_answer'] == _('skip'):
        result['skip'] = True
        result['abort'] = False
        return photo, result
    result['skip'] = False
    result['abort'] = False
    return photo, result


def flush_log(photo, image_file, action=None):
    """Flushes non fatal errors/warnings with :func:`log_error`
    and warnings that have been logged from the photo to the error log
    file.

    :param photo: photo which has photo.log
    :type photo: class:`core.pil.Photo`
    :param image_file: absolute path of the image
    :type image_file: string
    :param action: action which was involved in the error (optional)
    :type action: :class:`core.models.Action`
    """
    log = photo.get_log()
    if log:
        log_error(log, image_file, action, label='Warning')
        photo.clear_log()


def apply_actions_to_photos(actions, settings, paths=None, drop=False,
        update=None):
    """Apply all the actions to the photos in path.

    :param actions: actions
    :type actions: list of :class:`core.models.Action`
    :param settings: process settings (writable, eg recursion, ...)
    :type settings: dictionary
    :param paths:

        paths where the images are located. If they are not specified,
        Phatch will ask them to the user.

    :type paths: list of strings
    :param drop:

        True in case files were dropped or phatch is started as a
        droplet.

    :type drop: bool
    """
    from phatch.services.legacy_execution import apply_actions_to_photos as execute

    execute(actions, settings, paths, drop, update)


def apply_actions_to_photos_with_recovery(actions, settings, recovery, paths=None,
        drop=False, update=None):
    """Apply actions with durable completed-output recovery."""
    from phatch.services.legacy_recovery import execute_with_recovery as execute

    return execute(actions, settings, recovery, paths, drop, update)


#---common

#---classes

def import_module(module, folder=None):
    """Import a module, mostly used for actions.

    :param module: module/action name
    :type module: string
    :param folder: folder where the module is situated
    :type folder: string
    """
    if folder is None:
        return importlib.import_module(module)
    return importlib.import_module('%s.%s' % (
        folder.replace(os.path.sep, '.'), module))


def import_actions():
    """Import all actions from the ``ct.PHATCH_ACTIONS_PATH``."""
    from pathlib import Path
    from typing import assert_never

    from phatch.core.action_registry import (
        ActionCatalogSources,
        ActionRegistryBuildError,
        ActionRegistryBuildFailure,
        ActionRegistryBuildSuccess,
        build_action_registry,
    )

    global ACTIONS, ACTION_LABELS, ACTION_FIELDS
    sources = ActionCatalogSources(
        built_in=tuple(Path(filename) for filename in
            glob.glob(os.path.join(ct.PHATCH_ACTIONS_PATH, '*.py'))),
        user=tuple(Path(filename) for filename in
            glob.glob(os.path.join(ct.USER_ACTIONS_PATH, '*.py'))),
        action_attribute=ct.ACTION,
    )
    result = build_action_registry(sources)
    match result:
        case ActionRegistryBuildFailure(issues=issues):
            raise ActionRegistryBuildError(issues)
        case ActionRegistryBuildSuccess(registry=registry):
            actions = dict(registry.factories)
            action_labels = list(registry.labels())
            action_fields = dict(registry.fields)
        case unreachable:
            assert_never(unreachable)
    ACTIONS, ACTION_LABELS, ACTION_FIELDS = actions, action_labels, action_fields
    return registry


def save_actionlist(filename, data):
    """Save actionlist ``data`` to ``filename`` in JSON format.

    :param filename:

        filename of the actionlist, if it has no extension ``.phatch``
        will be added automatically.

    :type filename: string
    :param data: action list data
    :type data: dictionary

    Actionlists are stored as dictionaries::

        data = {'actions':[...], 'description':'...'}
    """
    #check filename
    if os.path.splitext(filename)[1].lower() != ct.EXTENSION:
        filename += ct.EXTENSION
    from phatch.services.action_schema import (
        ActionDocument,
        ActionField,
        ActionSpec,
        normalize_identifier,
        serialize_action_list,
    )

    dumped_actions = [action.dump() for action in data['actions']]
    document = ActionDocument(
        3,
        data.get('description', ''),
        tuple(
            ActionSpec(
                normalize_identifier(action['label']),
                tuple(
                    ActionField(normalize_identifier(label), value)
                    for label, value in action.get('fields', {}).items()
                ),
            )
            for action in dumped_actions
        ),
    )
    #backup previous
    previous = filename + '~'
    if os.path.exists(previous):
        os.remove(previous)
    if os.path.isfile(filename):
        os.rename(filename, previous)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(serialize_action_list(document))


def open_actionlist(filename, registry=None, plugin_context=None):
    """Open the action list from a file (supports both JSON and legacy formats).

    :param filename: the filename of the action list
    :type filename: string
    :returns: action list tuple (data, warning) or None if incompatible
    :rtype: tuple or None
    """
    #read source
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()

    from pathlib import Path

    from phatch.core.action_registry import ImmutableActionRegistry
    from phatch.core.plugin_context import default_plugin_context
    from phatch.services.action_schema import (
        RegistrySchemaCatalog,
        SchemaValidationError,
        construct_document_actions,
        migrate_action_list,
        parse_action_list,
    )

    active_registry = registry
    if active_registry is None and ACTIONS:
        assert ACTION_FIELDS is not None
        context = default_plugin_context() if plugin_context is None else plugin_context
        active_registry = ImmutableActionRegistry(
            ACTIONS,
            {label: Path('<legacy>') for label in ACTIONS},
            {label: ACTION_FIELDS[label] for label in ACTIONS},
            context,
        )
    if active_registry is None:
        send.frame_show_error(ERROR_INCOMPATIBLE_ACTIONLIST % ct.INFO)
        return None
    catalog = RegistrySchemaCatalog(active_registry)
    try:
        parsed = parse_action_list(source)
    except SchemaValidationError:
        send.frame_show_error(ERROR_INCOMPATIBLE_ACTIONLIST % ct.INFO)
        return None
    document = migrate_action_list(parsed, catalog)
    result = list(construct_document_actions(document, catalog, active_registry))
    warning = assert_safe(result)
    return {
        'schema_version': document.schema_version,
        'description': document.description,
        'actions': result,
        'invalid labels': [],
    }, warning
