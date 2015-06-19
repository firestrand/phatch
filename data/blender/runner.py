# -*- coding: utf-8 -*-
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

import imp
import os
import re
import sys
from Blender import Scene


class BlenderScript(object):

    def __init__(self):
        self.args = Arguments()
        self.render_path = os.path.dirname(self.args['render_path'])

    def render(self):
        scene = Scene.GetCurrent()

        script = imp.load_source(self.args['script'], self.args['script_path'])
        blender_initializer = script.BlenderInitializer()
        blender_initializer.set_up_render(self.args, scene)

        self.set_up_render_context(scene)

        blender_initializer.clean_up()

    def set_up_render_context(self, scene):
        context = scene.getRenderingContext()

        context.sFrame = 1
        context.eFrame = 1

        context.imageSizeX(int(self.args['render_width']))
        context.imageSizeY(int(self.args['render_height']))
        context.setRenderWinSize(100)

        context.oversampling = True
        context.OSALevel = 5

        if self.args['alpha']:
            context.alphaMode = 1
            context.enableRGBAColor()
        else:
            context.alphaMode = 0
            context.enableRGBColor()

        context.renderPath = self.render_path + os.path.sep
        context.renderAnim()


class Arguments(dict):

    def __init__(self):
        args = sys.argv[sys.argv.index('--') + 1:]
        for arg in args:
            parts = arg.split(':', 1)

            if len(parts) < 2:
                continue

            key, value = parts[0], parts[1]

            if re.search('^#[0-9A-Fa-f]{6}$', value):
                self[key] = color(value)
            elif value.lower() in ('no', 'false'):
                self[key] = False
            else:
                try:
                    float_val = float(value)
                    int_val = int(value)

                    if float_val == int_val:
                        self[key] = int_val
                    else:
                        self[key] = float_val
                except ValueError:
                    self[key] = value


def color(hex_color):
    # converts color str (#<three hex pairs>) to list of three floats
    # [0.0, 1.0] and returns it
    return [int(hex_color[1:][i:i + 2], 16) / 255.0 \
        for i in xrange(0, len(hex_color) - 1, 2)]

script = BlenderScript()
script.render()
