# Phatch - Photo Batch Processor
# Copyright (C) 2009 Nadia Alramli, Stani (www.stani.be)
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
# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.
#
# Follows PEP8

import re
import glob
import os.path
import sys
import logging
import subprocess

# Test suite modules
import utils
import config
import defaults
import gettext
gettext.install('_')

# Phatch modules
from lib.safe import eval_safe

#################################
#   Building Actions Hashtable  #
#################################
__DEFAULTS = {}


def get_defaults():
    """Get actions custom defaults
    Returns a dictionary that maps action names to defaults"""
    global __DEFAULTS
    if __DEFAULTS:
        return __DEFAULTS
    __DEFAULTS = dict(
        (action, getattr(defaults, action))
        for action in dir(defaults)
        if not action.startswith('__'))
    return __DEFAULTS


__ACTIONS = {}


def get_actions():
    """Get phatch actions
    Returns a dictionary that maps action names to objects"""
    global __ACTIONS
    if __ACTIONS:
        return __ACTIONS
    action_names = [utils.file_name(action_file) for action_file in
            glob.glob(os.path.join(config.PHATCH_ACTIONS_PATH, '*.py'))]
    default_values = get_defaults()
    __ACTIONS = dict(
        (
            name,
            __import__(
                'actions.%s' % name,
                name,
                fromlist=['actions']).Action())
        for name in action_names
        if name != '__init__')
    for name, fields in default_values.iteritems():
        set_action_fields(__ACTIONS[name], fields)
    return __ACTIONS


def get_action(action_name):
    """Get action object by name"""
    return get_actions()[action_name]

__FILE_ACTIONS = {}


def get_file_actions():
    """Get file actions i.e actions that are valid last"""
    global __FILE_ACTIONS
    if __FILE_ACTIONS:
        return __FILE_ACTIONS
    __FILE_ACTIONS = dict(
        (name, action)
        for name, action in get_actions().iteritems()
        if action.valid_last)
    return __FILE_ACTIONS

__LIBRARY_ACTIONLISTS = {}


def get_library_list():
    """Get library actionlists"""
    global __LIBRARY_ACTIONLISTS
    if __LIBRARY_ACTIONLISTS:
        return __LIBRARY_ACTIONLISTS
    pattern = os.path.join(config.PHATCH_ACTIONLISTS_PATH, '*.phatch')
    actionlist_paths = glob.glob(pattern)
    __LIBRARY_ACTIONLISTS = dict(
        (
            utils.file_name(actionlist_file),
            eval_safe(open(actionlist_file).read()))
        for actionlist_file in actionlist_paths)
    return __LIBRARY_ACTIONLISTS

__ACTIONS_BY_TAGS = {}


def get_action_tags():
    """Get actions by tags"""
    global __ACTIONS_BY_TAGS
    if __ACTIONS_BY_TAGS:
        return __ACTIONS_BY_TAGS
    for name, action in get_actions().iteritems():
        if name in config.DISABLE_ACTIONS:
            continue
        for tag in action.tags:
            if tag in __ACTIONS_BY_TAGS:
                __ACTIONS_BY_TAGS[tag][name] = action
            else:
                __ACTIONS_BY_TAGS[tag] = {name: action}
    return __ACTIONS_BY_TAGS


#########################################
#   ActionLists Generation Functions    #
#########################################

def generate_actionlists(output='', actionlists=None, file_action='save',
        choices_function=None, include_file_action=False):
    """Generate all possible actionlist files based on a choice_function and a
    list of actionlists
    :param output: processed images output path
    :type output: string
    :param actionlist: list of action lists
    :type actionlist: list
    :param file_action: the file action to use
    :type file_action: string
    :param choices_function: choice generation function
    :type choices_function: function
    :param include_file_action: whether to include the file action in the
    generated possiblities
    :type include_file_action: boolean"""

    logging.info('Generating actionlists...')
    if not choices_function:
        choices_function = possible_choices
    if not actionlists:
        file_action = get_action(file_action)
        actionlists = minimal_actionlists(get_actions().values(), file_action)
    actionlists_info = {}
    for actionlist in actionlists:
        if include_file_action or len(actionlist) == 1:
            possible_actionlist = actionlist
        else:
            possible_actionlist = actionlist[:-1]
        possibilities = utils.product_map(
            generator=choices_function,
            *possible_actionlist)
        for fields_list in possibilities:
            for (fields, action) in zip(fields_list, actionlist):
                set_action_fields(action, fields)
            filename = generate_name(possible_actionlist, fields_list)
            actionlist = set_file_actions(filename, actionlist, output)
            output_path = os.path.join(
                config.OUT_ACTIONLISTS_PATH, '%s.phatch' % filename)
            utils.write_file(output_path, repr(dump(actionlist)))
            actionlists_info[filename] = output_path
    return actionlists_info


def generate_library_actionlists(output=''):
    """Build library actionlists
    :param output: the processed image output path
    :type output: string"""
    logging.info('Generating library actionlists...')
    actionlists_info = {}
    for name, actionlist in get_library_list().iteritems():
        file_actions = [
            action
            for action in actionlist['actions']
            if action['label'].lower() in get_file_actions()]
        for index, file_action in enumerate(file_actions):
            file_action['fields']['In'] = '%s' % output
            file_action['fields']['File Name'] =\
                '<filename>_%s' % utils.indexed_name(name, index)
        output_path = os.path.join(
            config.OUT_ACTIONLISTS_PATH, '%s.phatch' % name)
        utils.write_file(output_path, repr(actionlist))
        actionlists_info[name] = output_path
    return actionlists_info


def execute_actionlist(input, actionlist, options):
    """Execute the actionlist on input path"""
    output, error = subprocess.Popen(
        ['python', config.PHATCH_APP_PATH, '-c', options, actionlist, input],
        stderr=subprocess.PIPE).communicate()

    logs_file = open(config.USER_LOG_PATH)
    logs = logs_file.read()
    logs_file.close()
    if logs:
        logging.error(
            '\nactionlist: %s\n%s\n'
            % (actionlist, logs))
    if error:
        logging.error(
            '\nactionlist: %s\n%s\n'
            % (actionlist, error))
    return not(error or logs)


def execute_actionlists(input, actionlists=None, options=''):
    """Execute a list of actionlists on input path.
    If no actionlist was given all actionlists will be executed"""
    errors = []
    if not actionlists:
        actionlists = dict(
            (
                utils.file_name(path),
                os.path.join(config.OUT_ACTIONLISTS_PATH, path))
            for path in os.listdir(config.OUT_ACTIONLISTS_PATH))

    total = len(actionlists)
    for i, name in enumerate(sorted(actionlists)):
        sys.stdout.write(
            '\rRunning %s/%s %s' % (
                i + 1,
                total,
                name[:50].ljust(50)))
        sys.stdout.flush()
        if not execute_actionlist(input, actionlists[name], options):
            errors.append(name)
    print
    return errors


#################################
#   Actions Helper Functions    #
#################################
def minimal_actionlists(actions, file_action, extra=None):
    """Convert a single action into a minimal actionlist"""
    if not extra:
        extra = []
    return [
        utils.inline_if(
            action.valid_last,
            extra + [action],
            extra + [action, file_action])
        for action in actions]


def set_action_fields(action, fields):
    """Set action fields"""
    for field_name, field_value in fields.iteritems():
        action.set_field(field_name, field_value)


def set_file_actions(name, actionlist, output):
    """Set file actions output path"""
    file_actions = [action for action in actionlist if action.valid_last]
    for index, file_action in enumerate(file_actions):
        file_action.set_field(
            'In',
            '%s' % output)
        file_action.set_field(
            'File Name',
            '<filename>_%s' % utils.indexed_name(name, index))
    return actionlist


def generate_name(actionlists, fields_list):
    """Generate file names based on field values"""
    fields_name = '_'.join(
        '%s=%s' % (
            field_name.strip().replace(' ', ''),
            ('%s' % field_value).strip().replace(' ', ''))
        for fields in fields_list
        for field_name, field_value in fields.iteritems())
    filename = '_'.join(
        '_'.join(map(str.lower, action.label.split()))
        for action in actionlists)
    if fields_name:
        filename = '%s_%s' % (filename, fields_name)
    return shorten(filename)


REMOVE_PARENTHESES = re.compile(r'\([^)]*\)')


def shorten(filename):
    """Shorten a filename into a managable length"""
    filename = REMOVE_PARENTHESES.sub('', filename)
    return utils.replace_all(filename, config.SHORTNAME_MAP)


def dump(actions):
    """Dump a list of actions into an actionlist dictionary"""
    data = [action.dump() for action in actions]
    return {'description': '', 'actions': data, 'version': '0.2.0.test'}


def possible_choices(action):
    """Generate all possible choices based on boolean and choice fields"""
    choices = []
    possible_choices_helper(action, choices)
    return choices


def possible_choices_helper(action, choices):
    """Generate all possible action choices based on boolean and choice fields
    This is a helper function"""
    if hasattr(action, 'get_relevant_field_labels'):
        relevant = action.get_relevant_field_labels()
    else:
        relevant = action._fields.keys()
    choice_fields = dict(
        (name, field) for name, field in action._fields.iteritems()
        if isinstance(field, (action.BooleanField, action.ChoiceField))
        and not isinstance(field, (
            action.ImageFilterField,
            action.ImageResampleField,
            action.ImageResampleAutoField))
        and name != '__enabled__'
        and name in relevant)
    choice = dict(
        (fname, field.get())
        for fname, field in choice_fields.iteritems())
    if choice in choices:
        return
    choices.append(choice)
    for fname, field in choice_fields.iteritems():
        default = field.get()
        if isinstance(field, action.BooleanField):
            options = [True, False]
        else:
            options = field.choices
        for option in options:
            if option == default:
                continue
            action.set_field(fname, option)
            possible_choices_helper(action, choices)


def extended_choices(action):
    """Generate all possible choices based on boolean and choice fields"""
    choices = []
    extended_choices_helper(action, choices)
    return choices


def extended_choices_helper(action, choices):
    """Generate all possible action choices based on boolean and choice fields
    This is a helper function"""
    if hasattr(action, 'get_relevant_field_labels'):
        relevant = action.get_relevant_field_labels()
    else:
        relevant = action._fields.keys()
    choice_fields = dict(
        (name, field) for name, field in action._fields.iteritems()
        if isinstance(
            field,
            (action.BooleanField, action.ChoiceField, action.SliderField))
        and not isinstance(field, (
            action.ImageFilterField,
            action.ImageResampleField,
            action.ImageResampleAutoField))
        and name != '__enabled__'
        and name in relevant)
    choice = dict(
        (fname, field.get())
        for fname, field in choice_fields.iteritems())
    if choice in choices:
        return
    choices.append(choice)
    for fname, field in choice_fields.iteritems():
        default = field.get()
        if isinstance(field, action.BooleanField):
            options = [True, False]
        elif isinstance(field, action.SliderField):
            options = [field.max, (field.max + field.min) / 2, field.min]
        else:
            options = field.choices
        for option in options:
            if option == default:
                continue
            action.set_field(fname, option)
            extended_choices_helper(action, choices)
