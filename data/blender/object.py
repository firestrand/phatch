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

# Note that importing other modules (non Blender/Python) is somewhat
# problematic. See imp module and runner.py if you really want to do that.

import math
import os
import sys
import tempfile
from Blender import Camera, Image, Mathutils, Material, Object, Texture
from PIL import Image as PILImage
from PIL import ImageOps


def _get_image_extension(image, ext={'RGB': '.PNG', 'RGBA': '.PNG'}):
    if image.mode == 'LA' or \
            (image.mode == 'P' and 'transparency' in image.info):
        image = image.convert('RGBA')
    elif not image.mode.startswith('RGB'):
        image = image.convert('RGB')
    return image, ext[image.mode]


if sys.platform.startswith('win'):

    # BMP fails on Windows2000
    # PIL can't write to .bmp temp file (Fails with Error 0)
    get_image_extension = _get_image_extension

else:

    def get_image_extension(image):
        return _get_image_extension(image,
            ext={'RGB': '.BMP', 'RGBA': '.PNG'})


class Textures:

    def set_up(self, images):
        for i, image in enumerate(images):
            texture = Texture.Get('phatch_tex_' + str(i + 1))
            texture.image = image


class BlenderCamera:

    def set_up(self, args):
        camera_target = Object.Get('camera_target')
        camera_target.RotX = math.radians(args['rotation_x'])
        camera_target.RotY = -math.radians(args['rotation_y'])
        camera_target.RotZ = math.radians(args['rotation_z'])

        camera = Camera.Get('camera')
        camera.angle = args['camera_lens_angle']

        camera_ob = Object.Get('camera')
        camera_ob.LocX = args['camera_distance']


class Stars:

    def set_up(self, args, world):
        if args['stars']:
            mode = world.getMode()
            mode |= 2
            world.setMode(mode)

            self._set_stars_color(args, world)

    def _set_stars_color(self, args, world):
        old_options = world.getStar()
        new_options = args['stars_color'] + old_options[3:]
        world.setStar(new_options)


class Mist:

    def set_up(self, args, world):
        if args['mist']:
            mode = world.getMode()
            mode |= 1
            world.setMode(mode)


class World:
    stars = Stars()
    mist = Mist()

    def set_up(self, args, scene):
        if not args['alpha']:
            world = scene.world
            world.setZen(args['gradient_top'])
            world.setHor(args['gradient_bottom'])
            world.setSkytype(1)  # make sure sky gets blended

            self.stars.set_up(args, world)
            self.mist.set_up(args, world)


class Floor:

    def set_up(self, args, scene):
        if args['use_floor']:
            self._set_color(args)
            self._set_reflection(args)
            self._set_opacity(args)
        else:
            self._remove_floor(scene)

    def get_mode(self):
        return self.material.getMode()
    mode = property(get_mode)

    def _set_color(self, args):
        self.material = Material.Get('floor')
        self.material.setRGBCol(args['floor_color'])

    def _set_reflection(self, args):
        ref = int(args['floor_reflection'])

        if ref:
            self.material.setFresnelMirrFac(2 - ref / 100.0)
        else:
            self.material.setMode(self.mode ^ Material.Modes['RAYMIRROR'])

    def _set_opacity(self, args):
        #note that the idea is to fake it so that mirror still works
        #TODO: it probably would be nicer to handle this with compositing as
        #this solution does not work properly with stars option!
        opacity = int(args['floor_opacity']) / 100.0
        self.material.setMode(self.mode ^ Material.Modes['RAYTRANSP'])
        self.material.fresnelTrans = 5 * (1.0 - opacity)
        self.material.fresnelTransFac = 5 * (1.0 - opacity)
        self.material.spec *= opacity
        self.material.ref *= opacity
        self.material.alpha *= opacity

    def _remove_floor(self, scene):
        scene.objects.unlink(Object.Get('floor'))


class BlenderObjects(list):

    def __init__(self):
        self.extend([Book(), Box(), Can(), Cd(), Lcd(), Sphere()])

    def find(self, args):
        obj_name = args['object']

        for obj in self:
            if obj_name == obj.name:
                return obj


class BlenderObject:
    tex_ob_name = ''

    def __init__(self):
        if not self.tex_ob_name:
            self.tex_ob_name = self.name

        # TODO: generalize
        self.texface = TexFace(self.tex_ob_name, 'phatch_tex_1')

    def get_name(self):
        return self.__class__.__name__
    name = property(get_name)

    def initialize_images(self, args):
        pass

    def set_up(self, args, images):
        pass


class TexFace:

    def __init__(self, tex_ob_name, name):
        self.tex_ob_name = tex_ob_name
        self.name = name
        self._width = None
        self._height = None

    def get_width(self):
        self._calculate_edge_width_and_height()

        return self._width
    width = property(get_width)

    def get_height(self):
        self._calculate_edge_width_and_height()

        return self._height
    height = property(get_height)

    def _calculate_edge_width_and_height(self):
        # cache -> to decorator?
        if self._width is not None and self._height is not None:
            return

        ob = Object.Get(self.tex_ob_name)
        me = ob.getData(mesh=True)

        tex_group = VertexGroup(me, self.name)
        tex_corner = VertexGroup(me, self.name + '_corner')

        connected_edges = tex_corner.find_connected_edges()
        common_edges = connected_edges.intersection(tex_group.edges)

        cross_product = cross(tex_corner.vertices.pop(), common_edges)
        face_normal = tex_group.faces.pop().no

        common_edges = list(common_edges)

        if vectors_on_same_side(cross_product, face_normal):
            e1, e2 = common_edges[0], common_edges[1]
        else:
            e1, e2 = common_edges[1], common_edges[0]

        # TODO: it would be better to use avg of edges
        # (top/bottom, left/right) here

        self._width, self._height = get_length(e1, ob), get_length(e2, ob)


class VertexGroup:

    def __init__(self, mesh, name):
        self.mesh = mesh
        self.vertex_ids = mesh.getVertsFromGroup(name)

    def find_connected_edges(self):
        ret = set()

        for vertex_id in self.vertex_ids:
            for e in self.mesh.edges:
                if e.v1.index == vertex_id:
                    ret.add(e)

                if e.v2.index == vertex_id:
                    ret.add(e)

        return ret

    def get_edges(self):
        ret = set()

        for e in self.mesh.edges:
            found_v1 = False
            found_v2 = False

            for index in self.vertex_ids:
                if e.v1.index == index:
                    found_v1 = True
                if e.v2.index == index:
                    found_v2 = True

            if found_v1 and found_v2:
                ret.add(e)

        return ret
    edges = property(get_edges)

    def get_faces(self):
        ret = set()

        for face in self.mesh.faces:
            found_vertices = 0

            for index in self.vertex_ids:
                for vertex in face.verts:
                    if vertex.index == index:
                        found_vertices += 1

            if found_vertices == len(face.verts):
                ret.add(face)

        return ret
    faces = property(get_faces)

    def get_vertices(self):
        ret = set()

        for vertex in self.mesh.verts:
            for index in self.vertex_ids:
                if vertex.index == index:
                    ret.add(vertex)

        return ret
    vertices = property(get_vertices)


def cross(v_id, edges):

    def get_vec(edge):
        if edge.v1 == v_id:
            return edge.v2.co + edge.v1.co
        return edge.v1.co + edge.v2.co

    edges = list(edges)

    vec1 = get_vec(edges[0])
    vec2 = get_vec(edges[1])

    return Mathutils.CrossVecs(vec1, vec2).normalize()


def vectors_on_same_side(v1, v2):
    # checks if the vec are on the same side of a ball. expects that v1
    # and v2 have been normalized already
    return math.acos(Mathutils.DotVecs(v1, v2)) < math.pi


def get_length(edge, ob):
    v1_world = edge.v1.co * ob.matrix
    v2_world = edge.v2.co * ob.matrix

    return (v1_world - v2_world).length


class Box(BlenderObject):

    def set_up(self, args, images):
        set_material_color('box', args['box_color'])
        self._adapt_proportions(args, images[0])

    def _adapt_proportions(self, args, image):
        ob = Object.Get(self.name).getParent()

        width, height = image.getSize()
        fac = height / 0.8
        box_width = width / fac
        box_height = height / fac
        box_depth = max(float(args['box_depth']) / fac, 0.001)
        ob.setSize(box_depth, box_width, box_height)


class Book(BlenderObject):

    def initialize_images(self, args):

        def initialize_page(box, image_arg, ext):
            temporary_image = TempFile(ext)
            left_page = im.crop(box)
            left_page.save(temporary_image.path)
            args[image_arg] = temporary_image.path

        if args['page_mapping'].startswith('Wrap'):
            im_path = args['input_image_1']
            im = PILImage.open(im_path)
            width, height = im.size
            im, ext = get_image_extension(im)

            initialize_page((width / 2 + 1, 0, width, height), \
                'input_image_1', ext)
            initialize_page((0, 0, width / 2, height), 'input_image_2', ext)

    def set_up(self, args, images):
        set_material_color('cover', args['cover_color'])


def set_material_color(material_name, color):
    material = Material.Get(material_name)
    material.setRGBCol(color)


class Can(BlenderObject):
    pass


class Cd(BlenderObject):
    tex_ob_name = 'cd_lid'

    def set_up(self, args, images):
        cd_lid = Object.Get('cd_lid')
        cd_lid.RotZ -= math.radians(args['lid_rotation'])


class Lcd(BlenderObject):
    pass


class Sphere(BlenderObject):
    pass


class Modes(dict):

    def __init__(self):
        modes = (Fit(), LetterBox(), ScaleImage(), ScaleModel(), )

        for mode in modes:
            self[mode.name] = mode


class Mode:
    name = ''

    def execute(self, input_image_path, blender_object):
        return Image.Load(input_image_path)

    def clean_up(self):
        pass


class TemporaryImages(list):

    def close(self):
        for image in self:
            image.close()


class InputManipulationMode:
    temporary_images = TemporaryImages()

    def execute(self, input_image_path, blender_object):
        im = PILImage.open(input_image_path)
        new_im_width, new_im_height = self._get_new_im_dimensions(im,
            blender_object)

        result_im = self._execute_hook(im, new_im_width, new_im_height)

        return self._pil_im_to_blender_disk(result_im)

    def clean_up(self):
        self.temporary_images.close()

    def _comparator(self, new_im_height, im_height):
        pass

    def _execute_hook(self, im, new_im_width, new_im_height):
        pass

    def _get_new_im_dimensions(self, im, blender_object):
        im_width, im_height = im.size
        tex_width = blender_object.texface.width
        tex_height = blender_object.texface.height

        # figure out the scaling factor between widths and calculate new height
        new_im_height = im_width / tex_width * tex_height

        if self._comparator(new_im_height, im_height):
            new_im_width = im_width
        else:
            # scale width instead
            new_im_width = im_height / tex_height * tex_width
            new_im_height = im_height

        return int(new_im_width), int(new_im_height)

    def _pil_im_to_blender_disk(self, im):
        im, ext = get_image_extension(im)

        temporary_image = TempFile(ext)
        self.temporary_images.append(temporary_image)

        im.save(temporary_image.path)

        ret_im = Image.Load(temporary_image.path)

        return ret_im


class Fit(InputManipulationMode):
    name = 'Fit Image'

    def _comparator(self, new_im_height, im_height):
        return new_im_height < im_height

    def _execute_hook(self, im, new_im_width, new_im_height):
        fit_im = ImageOps.fit(im, (int(new_im_width), int(new_im_height)))
        fit_im.format = im.format

        return fit_im


class LetterBox(InputManipulationMode):
    name = 'Letterbox'

    def _comparator(self, new_im_height, im_height):
        return new_im_height > im_height

    def _execute_hook(self, im, new_im_width, new_im_height):

        def split(pixels):
            return pixels / 2, pixels / 2

        im_width, im_height = im.size
        left, top, right, bottom = 0, 0, im_width, im_height

        if im_width == new_im_width:
            extra_pixels = new_im_height - im_height
            top, bottom = split(extra_pixels)
            bottom += im_height
        else:
            extra_pixels = new_im_width - im_width
            left, right = split(extra_pixels)
            right += im_width

        lb_im = PILImage.new(im.mode, (new_im_width, new_im_height))
        lb_im.format = im.format
        lb_im.paste(im, (left, top, right, bottom))

        return lb_im


class ScaleImage(Mode):
    name = 'Scale Image'


class ScaleModel(Mode):
    name = 'Scale Model'

    def execute(self, input_image_path, blender_object):
        im = Image.Load(input_image_path)

        im_width, im_height = im.getSize()
        im_size_ratio = im_width / im_height

        tex_width = blender_object.texface.width
        tex_height = blender_object.texface.height
        tex_size_ratio = tex_width / tex_height

        ob = Object.Get(blender_object.name).getParent()
        if tex_size_ratio > im_size_ratio:
            # scale width
            scaling_ratio = im_size_ratio / tex_size_ratio
            ob.SizeY *= scaling_ratio
        else:
            # scale height
            scaling_ratio = tex_size_ratio / im_size_ratio
            ob.SizeZ *= scaling_ratio

        return im


class BlenderInitializer:
    blender_objects = BlenderObjects()
    modes = Modes()
    selected_mode = Mode()
    textures = Textures()
    camera = BlenderCamera()
    world = World()
    floor = Floor()

    def set_up_render(self, args, scene):
        blender_object = self.blender_objects.find(args)
        image_size = args['image_size']
        images = []

        # TODO: handle object, image init here! -> ie. book crop
        blender_object.initialize_images(args)

        if image_size not in self.modes:
            print 'No suitable "Image Size" provided! Got ' + image_size + \
                '! Using Scale Image instead.'
            image_size = 'Scale Image'

        self.selected_mode = self.modes[image_size]

        for i in range(1, args['amount_of_input_images'] + 1):
            input_image = args['input_image_' + str(i)]
            image = self.selected_mode.execute(input_image, blender_object)
            images.append(image)

        self.textures.set_up(images)
        blender_object.set_up(args, images)

        self.camera.set_up(args)
        self.world.set_up(args, scene)
        self.floor.set_up(args, scene)

    def clean_up(self):
        self.selected_mode.clean_up()

#FIXME: duplicate code from lib/system.py (should be imported)


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

    def close(self):
        """It is important to call this method when finished with
        the temporary file.
        """
        if self._fd:
            os.close(self._fd)
        os.remove(self.path)
