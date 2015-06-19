#!/usr/bin/python
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
# Follows PEP8

# A script to modify action tags
import pprint
import re
import glob
import os.path
import sys

ACTIONS_PATH = os.path.normpath('../phatch/actions')
reg = re.compile(r'(\s*tags\s*=\s*).+')


def parse_tags(tag_file):
    data = open(tag_file).read().split('\n\n')
    tag_lists = [map(str.strip, tags.split()) for tags in data]
    tags = {}
    for tag_list in tag_lists:
        for action in tag_list[1:]:
            if action in tags:
                tags[action].append(tag_list[0])
            else:
                tags[action] = [tag_list[0]]
    return tags


def tag_string(tags):
    return '[%s]' % ', '.join("_t('%s')" % tag.lower() for tag in tags)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        tag_file = sys.argv[1]
    else:
        tag_file = 'tag_list'

    tags = parse_tags(tag_file)

    actions = [
        action
        for action in glob.glob(os.path.join(ACTIONS_PATH, '*.py'))
        if action != '__init__'
    ]
    for action in actions:
        data = open(action).read()
        name = os.path.basename(action)

        def replace_tags(match):
            return match.group(1) + tag_string(tags[name])
        data = reg.sub(replace_tags, data)
        f = open(action, 'w')
        f.write(data)
        f.close()
