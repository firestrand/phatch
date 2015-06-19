#!/usr/bin/python

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

import logging
import time
import optparse
import sys
import os

from test_suite import config, utils, phatchtools

report = logging.getLogger('report')


def clean():
    """Clean generated files from previous run"""
    utils.remove_path(options.output)
    utils.remove_path(config.OUT_ACTIONLISTS_PATH)
    utils.remove_path(config.OUT_DIFF)
    utils.create_path(options.output)
    utils.create_path(config.OUT_ACTIONLISTS_PATH)


def set_logger(log_path):
    """Setup logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
    )
    #console = logging.StreamHandler()
    #console.setLevel(logging.INFO)
    #logging.getLogger('').addHandler(console)

    error_handler = logging.FileHandler(options.log, mode='w')
    error_handler.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(error_handler)

    report_handler = logging.FileHandler(options.report, mode='w')
    report.addHandler(report_handler)


if __name__ == '__main__':
    # Option parser
    parser = optparse.OptionParser()
    tags = sorted(phatchtools.get_action_tags().keys() + ['library', 'save'])
    parser.add_option(
        '-t', '--tag',
        default=None,
        choices=tags,
        help='Generate tests by tag',
    )
    actions = sorted(phatchtools.get_actions().keys())
    parser.add_option(
        '-s', '--select',
        action="append",
        choices=actions,
        default=None,
        help='Generate selected actions tests',
    )
    parser.add_option(
        '-a', '--all',
        action='store_true',
        default=False,
        help='Generate all tests',
    )
    parser.add_option(
        '-e', '--extended',
        action='store_true',
        default=False,
        help='Generate extended tests',
    )
    parser.add_option(
        '-c', '--compare',
        default=None,
        help='Comparison folder',
    )
    parser.add_option(
        '-i', '--input',
        default=config.DEFAULT_INPUT,
        help='Image input folder [default: %default]',
    )
    parser.add_option(
        '-o', '--output',
        default=config.DEFAULT_OUTPUT,
        help='Image output folder [default: %default]',
    )
    parser.add_option(
        '-l', '--log',
        default=config.DEFAULT_LOG,
        help='Log file path [default: %default]',
    )
    parser.add_option(
        '-r', '--report',
        default=config.DEFAULT_REPORT,
        help='Report file path [default: %default]',
    )
    parser.add_option(
        '--no-execute',
        action='store_true',
        default=False,
        help='Generate actionlists only, don\'t execute',
    )
    parser.add_option(
        '--no-clean',
        action='store_true',
        default=False,
        help='Don\'t remove previously generated files',
    )
    parser.add_option(
        '--clean',
        action='store_true',
        default=False,
        help='Remove previously generated files',
    )
    parser.add_option(
        '--options',
        action='store',
        default='',
        help='Command line options to pass to phatch',
    )
    options, args = parser.parse_args()
    if not options.no_execute and not os.path.exists(options.input):
        msg = 'The input directory "%s" is empty or doesn\'t exist'
        logging.error(
            msg % options.input,
        )
        sys.exit(1)
    choices_function = None
    start_time = time.time()
    if not options.no_clean:
        clean()
        if options.clean:
            # Only clean do nothing else
            sys.exit(0)
    set_logger(options.log)
    save_action = phatchtools.get_action('save')
    convert_mode_action = phatchtools.get_action('convert_mode')
    actions_by_tag = phatchtools.get_action_tags()
    all_actions = [
        action
        for name, action in phatchtools.get_actions().iteritems()
        if name not in config.DISABLE_ACTIONS]
    processing_actions = [
        action
        for name, action in phatchtools.get_actions().iteritems()
        if name not in config.DISABLE_ACTIONS
        and name not in actions_by_tag['metadata']]
    metadata_actions = actions_by_tag['metadata'].values()
    if options.tag == 'library':
        phatchtools.generate_library_actionlists(options.output)
    elif options.tag == 'save':
        actionlists = [[convert_mode_action, save_action]]
        phatchtools.generate_actionlists(
            options.output, actionlists, include_file_action=True,
        )
    elif options.tag:
        if options.extended and options.tag != 'metadata':
            actionlists = phatchtools.minimal_actionlists(
                actions_by_tag[options.tag].values(),
                save_action,
                [convert_mode_action],
            )
            choices_function = phatchtools.extended_choices
        else:
            actionlists = phatchtools.minimal_actionlists(
                actions_by_tag[options.tag].values(),
                save_action,
            )
        phatchtools.generate_actionlists(
            options.output,
            actionlists,
            choices_function=choices_function,
        )
    if options.select:
        if options.extended:
            actionlists = phatchtools.minimal_actionlists(
                [phatchtools.get_action(name) for name in options.select],
                save_action,
                [convert_mode_action],
            )
            choices_function = phatchtools.extended_choices
        else:
            actionlists = phatchtools.minimal_actionlists(
                [phatchtools.get_action(name) for name in options.select],
                save_action,
            )
        phatchtools.generate_actionlists(
            options.output,
            actionlists,
            choices_function=choices_function,
        )
    if options.all:
        if options.extended:
            actionlists = phatchtools.minimal_actionlists(
                processing_actions, save_action, [convert_mode_action],
            )
            actionlists.extend(
                phatchtools.minimal_actionlists(metadata_actions, save_action),
            )
            choices_function = phatchtools.extended_choices
        else:
            actionlists = phatchtools.minimal_actionlists(
                all_actions, save_action,
            )
        phatchtools.generate_actionlists(
            options.output,
            actionlists,
            choices_function=choices_function,
        )
        if not options.extended:
            actionlists = [[convert_mode_action, save_action]]
            phatchtools.generate_actionlists(
                options.output, actionlists, include_file_action=True,
            )
        phatchtools.generate_library_actionlists(options.output)
    if not options.no_execute:
        errors = phatchtools.execute_actionlists(
            options.input, options=options.options,
        )
        if errors:
            report.info('Number of errors: %s' % len(errors))
            report.info('Errors:\n\t%s' % '\n\t'.join(errors))
        else:
            logging.info('No errors')
    if options.compare:
        utils.create_path(config.OUT_DIFF)
        new = []
        mismatch = []
        output_files = [
            image
            for image in os.listdir(options.output)]
        for image in output_files:
            path1 = os.path.join(options.compare, image)
            if os.path.exists(path1):
                path2 = os.path.join(options.output, image)
                if not utils.compare(path1, path2):
                    result = utils.analyze(path1, path2)
                    report.info(
                        'Mismatch: %s\nreason: %s' % (image, result['reason']))
                    if 'diff' in result:
                        result['diff'].save(
                            os.path.join(config.OUT_DIFF, image) + '.png')
                    mismatch.append(image)
            else:
                new.append(image)
        if new:
            report.info('Number of new images: %s' % len(new))
            report.info('New:\n\t%s' % '\n\t'.join(new))
        if mismatch:
            report.info('Number of mismatches: %s' % len(mismatch))
            report.info('Mismatches:\n\t%s' % '\n\t'.join(mismatch))
        if not (new or mismatch):
            logging.info('No difference')
    logging.info('The report was saved to: %s' % options.report)
    logging.info('Execution took %.2f seconds' % (time.time() - start_time))
