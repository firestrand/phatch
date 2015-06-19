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

try:
    _
except NameError:
    __builtins__['_'] = unicode

#---import modules

#standard library
import codecs
import glob
import operator
import os
import pprint
import string
import time
import traceback
from cStringIO import StringIO
from datetime import timedelta

#gui-independent
from data.version import VERSION
from lib import formField
from lib import metadata
from lib import openImage
from lib import safe
from lib.odict import ReadOnlyDict
from lib.unicoding import ensure_unicode, exception_to_unicode, ENCODING

import ct
import pil
from message import send

#---constants
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
    from config import verify_app_user_paths
    verify_app_user_paths()
    import_actions()


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
        u'%s %d:%s' % (label, ERROR_LOG_COUNTER, message),
        details,
        os.linesep,
    ]))
    try:
        traceback.print_exc(file=ERROR_LOG_FILE)
    except UnicodeDecodeError:
        stringio = StringIO()
        traceback.print_exc(file=stringio)
        traceb = stringio.read()
        ERROR_LOG_FILE.write(unicode(traceb, ENCODING, 'replace'))
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
        for field in action._get_fields().values():
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
        for label, field in action._get_fields().items():
            if label.startswith('_') \
                    or isinstance(field, formField.BooleanField)\
                    or isinstance(field, formField.ChoiceField)\
                    or isinstance(field, formField.SliderField):
                continue
            try:
                field.assert_safe(label, test_info)
            except Exception, details:
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
    #check if extensions work ok! '.png' vs 'png'
    files.sort(key=string.lower)
    infos = []
    folder_index = 0
    for file in files:
        info = info_file.dump((os.path.join(folder, file), root))
        if os.path.isfile(info['path']) and info['type'].lower() in extensions:
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
    source_parent = folder  # do not change (independent of recursion!)
    # root = os.path.dirname(folder) #do not change (independent of recursion!)
    if recursive:
        image_infos = []
        for folder, dirs, files in os.walk(folder):
            image_infos.extend(filter_image_infos(folder, extensions,
                files, source_parent, info_file))
        return image_infos
    else:
        return filter_image_infos(folder, extensions, os.listdir(folder),
            source_parent, info_file)


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
    image_infos = []
    for path in paths:
        path = os.path.abspath(path.strip())
        if os.path.isfile(path):
            #single image file
            info = {'folderindex': 0}
            info.update(info_file.dump(path))
            image_infos.append(info)
        elif os.path.isdir(path):
            #folder of image files
            image_infos.extend(get_image_infos_from_folder(
                path, info_file, extensions, recursive))
        else:
            #not a file or folder?! probably does not exist
            send.frame_show_error('Sorry, "%s" is not a valid path.' \
                % ensure_unicode(path))
            return []
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
        if not ('file' in action.tags):
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
    #Check if there is something to do
    if actions == []:
        send.frame_show_error('%s %s' % (_('Nothing to do.'),
            _('The action list is empty.')))
        return None
    #Check if the actionlist is safe
    if formField.get_safe():
        warnings = assert_safe(actions)
        if warnings:
            send.frame_show_error('%s\n\n%s\n%s' % (
                ERROR_UNSAFE_ACTIONLIST_INTRO, warnings,
                ERROR_UNSAFE_ACTIONLIST_DISABLE_SAFE))
            return None
    #Skip disabled actions
    actions = [action for action in actions if action.is_enabled()]
    if actions == []:
        send.frame_show_error('%s %s' % (_('Nothing to do.'),
            _('There is no action enabled.')))
        return None
    #Check if there is a save statement
    last_action = actions[-1]
    if not (last_action.valid_last or check_actionlist_file_only(actions)\
            or settings['no_save']):
        send.frame_append_save_action(actions)
        return None
    #Check if overwrite is forced
    settings['overwrite_existing_images_forced'] = \
        (not settings['no_save']) and \
        actions[-1].is_overwrite_existing_images_forced()
    return actions


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


def get_photo(info_file, info_not_file, result):
    """Get a :class:`core.pil.Photo` instance from a file. If there is an
    error opening the file, func:`process_error` will be called.

    :param info_file: file information
    :type info_file: dictionary
    :param info_not_file: image information not related to file
    :type info_not_file: string
    :param result:

        settings to send to progress dialog box
        (such as ``stop for errors``)

    :type result: dict
    :returns: photo, result
    :rtype: tuple
    """
    try:
        photo = pil.Photo(info_file, info_not_file)
        result['skip'] = False
        result['abort'] = False
        return photo, result
    except Exception, details:
        reason = exception_to_unicode(details)
        #log error details
        message = u'%s: %s:\n%s' % (_('Unable to open file'),
            info_file['path'], reason)
    ignore = False
    action = None
    photo = None
    return process_error(photo, message, info_file['path'], action,
            result, ignore)

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


def init_actions(actions):
    """Initializes all actions. Shows an error to the user if an
    action fails to initialize.

    :param actions: actions
    :type actions: list of :class:`core.models.Action`
    :returns: False, if one action fails, True otherwise
    :rtype: bool
    """
    for action in actions:
        try:
            action.init()
        except Exception, details:
            reason = exception_to_unicode(details)
            message = u'%s\n\n%s' % (
                _("Can not apply action %(a)s:") \
                % {'a': _(action.label)}, reason)
            send.frame_show_error(message)
            return False
    return True


def apply_action_to_photo(action, photo, read_only_settings, cache,
        image_file, result):
    """Apply a single action to a photo. It uses :func:`log_error` for
    non fatal errors or :func:`process_error` for serious errors. The
    settings are read only as the actions don't have permission to
    change them.

    :param action: action
    :type action: :class:`core.models.Action`
    :param photo: photo
    :type photo: :class:`core.pil.Photo`
    :param read_only_settings: read only settings
    :type read_only_settings: :class:`lib.odict.ReadOnlyDict`
    :param cache: cache for data which is usefull across photos
    :type cache: dictionary
    :param image_file: filename reference during error logging
    :type image_file: string
    :param result: settings for dialog (eg ``stop_for_errors``)
    :type result: dictionary
    """
    try:
        photo = action.apply(photo, read_only_settings, cache)
        result['skip'] = False
        result['abort'] = False
        #log non fatal errors/warnings
        flush_log(photo, image_file, action)
        return photo, result
    except Exception, details:
        flush_log(photo, image_file, action)
        folder, image = os.path.split(ensure_unicode(image_file))
        reason = exception_to_unicode(details)
        message = u'%s\n%s\n\n%s' % (
            _("Can not apply action %(a)s on image '%(i)s' in folder:")\
                % {'a': _(action.label), 'i': image},
            folder,
            reason,
        )
        return process_error(photo, message, image_file, action,
            result, ignore=True)


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
    # Start log file
    init_error_log_file()

    # Check action list
    actions = check_actionlist(actions, settings)
    if not actions:
        return

    # Get paths (and update settings) -> show execute dialog
    paths = get_paths_and_settings(paths, settings, drop=drop)
    if not paths:
        return

    # retrieve all necessary variables in one time
    vars = set(pil.BASE_VARS).union(get_vars(actions))
    if settings['check_images_first']:
        # we need some extra vars for the list control
        vars = TREE_VARS.union(vars)
    vars_file, vars_not_file = metadata.InfoFile.split_vars(list(vars))
    info_file = metadata.InfoFile(vars=list(vars_file))

    # Check if all files exist
    # folderindex is set here in filter_image_infos
    image_infos = get_image_infos(paths, info_file,
        settings['extensions'], settings['recursive'])
    if not image_infos:
        return

    # Check if all the images are valid
    #  -> show invalid to user
    #  -> show valid to user in tree dialog (optional)
    if settings['check_images_first']:
        image_infos = verify_images(image_infos, settings['repeat'])
        if not image_infos:
            return

    # Initialize actions
    if not init_actions(actions):
        return

    # Retrieve settings
    skip_existing_images = not (settings['overwrite_existing_images'] or\
        settings['overwrite_existing_images_forced']) and\
        not settings['no_save']
    result = {
        'stop_for_errors': settings['stop_for_errors'],
        'last_answer': None,
    }

    # only keep static vars
    vars_not_file = pil.split_vars_static_dynamic(vars_not_file)[0]

    # create parent info instance
    #  -> will be used by different files with the open method
    info_not_file = metadata.InfoExtract(vars=vars_not_file)

    # Execute action list
    image_amount = len(image_infos)
    actions_amount = len(actions) + 1  # open image is extra action
    cache = {}
    is_done = actions[-1].is_done  # checking method for resuming
    read_only_settings = ReadOnlyDict(settings)

    # Start progress dialog
    repeat = settings['repeat']
    send.frame_show_progress(title=_("Executing action list"),
        parent_max=image_amount * repeat,
        child_max=actions_amount,
        message=PROGRESS_MESSAGE)
    report = []
    start = time.time()
    for image_index, image_info in enumerate(image_infos):
        statement = apply_actions_to_photo(actions, image_info, info_not_file,
            cache, read_only_settings, skip_existing_images, result, report,
            is_done, image_index, repeat)
        # reraise statement
        if statement == 'return':
            send.progress_close()
            return
        elif statement == 'break':
            break
        if update:
            update()
    send.progress_close()
    if update:
        update()

    # mention amount of photos and duration
    delta = time.time() - start
    duration = timedelta(seconds=int(delta))
    if image_amount == 1:
        message = _('One image done in %s') % duration
    else:
        message = _('%(amount)d images done in %(duration)s')\
            % {'amount': image_amount, 'duration': duration}
    # add error status
    if ERROR_LOG_COUNTER == 1:
        message += '\n' + _('One issue was logged')
    elif ERROR_LOG_COUNTER:
        message += '\n' + _('%d issues were logged')\
            % ERROR_LOG_COUNTER

    # show notification
    send.frame_show_notification(message, report=report)

    # show status dialog
    if ERROR_LOG_COUNTER == 0:
        if settings['always_show_status_dialog']:
            send.frame_show_status(message, log=False)
    else:
        message = '%s\n\n%s' % (message, SEE_LOG)
        send.frame_show_status(message)


def apply_actions_to_photo(actions, image_info, info_not_file,
        cache, read_only_settings, skip_existing_images, result, report,
        is_done, image_index, repeat):
    """Apply the action list to one photo."""
    image_info['index'] = image_index
    #open image and check for errors
    photo, result = get_photo(image_info, info_not_file, result)
    if result['abort']:
        photo.close()
        return 'return'
    elif not photo or result['skip']:
        photo.close()
        return 'continue'
    info = photo.info
    info.set('imageindex', image_index)
    image = photo.get_layer().image
    for r in range(repeat):
        info.set('index', image_index * repeat + r)
        info.set('repeatindex', r)
        #update image file & progress dialog box
        progress_result = {}
        send.progress_update_filename(progress_result, info['index'],
            info['path'])
        if progress_result and not progress_result['keepgoing']:
            photo.close()
            return 'return'
        #check if already not done
        if skip_existing_images and is_done(photo):
            continue
        if r == repeat - 1:
            photo.get_layer().image = image
        elif r > 0:
            photo.get_layer().image = image.copy()
        #do the actions
        for action_index, action in enumerate(actions):
            #update progress
            progress_result = {}
            send.progress_update_index(progress_result, info['index'],
                action_index)
            if progress_result and not progress_result['keepgoing']:
                photo.close()
                return 'return'
            #apply action
            photo, result = apply_action_to_photo(action, photo,
                read_only_settings, cache, image_info['path'], result)
            if result['abort']:
                photo.close()
                return 'return'
            elif result['skip']:
                #skip to next image immediately
                continue
    report.extend(photo.report_files)
    photo.close()
    if result['abort']:
        return 'return'


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
        return __import__(module)
    return getattr(__import__('%s.%s' % (folder.replace(os.path.sep, '.'),
        module)), module)


def import_actions():
    """Import all actions from the ``ct.PHATCH_ACTIONS_PATH``."""
    global ACTIONS, ACTION_LABELS, ACTION_FIELDS
    modules = \
        [import_module(os.path.basename(os.path.splitext(filename)[0]),
            'actions') for filename in \
            glob.glob(os.path.join(ct.PHATCH_ACTIONS_PATH, '*.py'))] + \
        [import_module(os.path.basename(os.path.splitext(filename)[0])) for
            filename in glob.glob(os.path.join(ct.USER_ACTIONS_PATH, '*.py'))]
    ACTIONS = {}
    for module in modules:
        try:
            cl = getattr(module, ct.ACTION)
        except AttributeError:
            continue
        #register action
        ACTIONS[cl.label] = cl
    #ACTION_LABELS
    ACTION_LABELS = ACTIONS.keys()
    ACTION_LABELS.sort()
    #ACTION_FIELDS
    ACTION_FIELDS = {}
    for label in ACTIONS:
        ACTION_FIELDS[label] = ACTIONS[label]()._fields


def save_actionlist(filename, data):
    """Save actionlist ``data`` to ``filename``.

    :param filename:

        filename of the actionlist, if it has no extension ``.phatch``
        will be added automatically.

    :type filename: string
    :param data: action list data
    :type data: dictionary

    Actionlists are stored as dictionaries::

        data = {'actions':[...], 'description':'...'}
    """
    #add version number
    data['version'] = VERSION
    #check filename
    if os.path.splitext(filename)[1].lower() != ct.EXTENSION:
        filename += ct.EXTENSION
    #prepare data
    data['actions'] = [action.dump() for action in data['actions']]
    #backup previous
    previous = filename + '~'
    if os.path.exists(previous):
        os.remove(previous)
    if os.path.isfile(filename):
        os.rename(filename, previous)
    #write it
    f = open(filename, 'wb')
    f.write(pprint.pformat(data))
    f.close()


def open_actionlist(filename):
    """Open the action list from a file.

    :param filename: the filename of the action list
    :type filename: string
    :returns: action list
    :rtype: dictionary
    """
    #read source
    f = open(filename, 'rb')
    source = f.read()
    f.close()
    #load data
    data = safe.eval_safe(source)
    if not data.get('version', '').startswith('0.2'):
        send.frame_show_error(ERROR_INCOMPATIBLE_ACTIONLIST % ct.INFO)
        return None
    result = []
    invalid_labels = []
    actions = data['actions']
    for action in actions:
        actionLabel = action['label']
        actionFields = action['fields']
        newAction = ACTIONS[actionLabel]()
        invalid_labels.extend(['- %s (%s)' % (label, actionLabel)
                                for label in newAction.load(actionFields)])
        result.append(newAction)
    warning = assert_safe(result)
    data['actions'] = result
    data['invalid labels'] = invalid_labels
    return data, warning
