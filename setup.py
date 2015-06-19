#!/usr/bin/env python

# Phatch - Photo Batch Processor
# Copyright (C) 2007-2009  www.stani.be
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

import sys

WINDOWS = sys.platform.startswith('win')
MAC = sys.platform.startswith('darwin')
LINUX = sys.platform.startswith('linux')

NO_WINDOWS = '''
Sorry, the use of setup.py is not supported yet for Windows.
Please read the instructions at http://photobatch.wikidot.com/install#toc8
'''

if WINDOWS:
    sys.exit(NO_WINDOWS)

import glob
import os
import subprocess
from distutils.core import setup

sys.path.insert(0, 'phatch')

from data import info

#centralised info generates README and AUTHORS
#Temporarily execute the following statement if these files needs update.
#info.write_readme_credits()

write = sys.stdout.write
error = sys.stderr.write
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Environment :: MacOS X',
    'Environment :: Win32 (MS Windows)',
    'Environment :: X11 Applications',
    'Environment :: X11 Applications :: Gnome',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: Developers',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Natural Language :: Dutch',
    'Natural Language :: English',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: OS Independent',
    'Operating System :: POSIX',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Topic :: Artistic Software',
    'Topic :: Multimedia :: Graphics',
    'Topic :: Multimedia :: Graphics :: Graphics Conversion']
INSTALL = len(sys.argv) > 1 and sys.argv[1] == 'install'
CLEAN = len(sys.argv) > 1 and sys.argv[1] == 'clean'


if not WINDOWS:
    DATA_PATH = 'share/phatch/data'
    DOC_PATH = 'share/phatch/docs'
    LOCALE_PATH = 'share/'


def doc(path=''):
    return os.path.join(DOC_PATH, path)


def data(path=''):
    return os.path.join(DATA_PATH, path)


PACKAGES = ['phatch', 'phatch.actions', 'phatch.console', 'phatch.core',
    'phatch.data', 'phatch.lib', 'phatch.lib.pyWx',
    'phatch.other', 'phatch.other.pil_1_1_6', 'phatch.other.pyWx',
    'phatch.pyWx', 'phatch.pyWx.wxGlade', 'phatch.templates']

#Create an array with all the locale filenames
i18n_files = []
for filepath in glob.glob("locale/*/LC_MESSAGES/phatch.mo"):
    targetpath = os.path.dirname(os.path.join(LOCALE_PATH, filepath))
    i18n_files.append((targetpath, [filepath]))

#docs
doc_files = [
    (doc(), glob.glob('docs/build/html/*.html')),
    (doc('_static'),
        glob.glob('docs/build/html/_static/*')),
    (doc('_sources'),
        glob.glob('docs/build/html/sources/*.txt')),
]


#data
data_files = [
    (data(), ["data/geek.txt"]),  # eg geek.txt
    (data(), ["data/user.png"]),
    (data('actionlists'), glob.glob("data/actionlists/*.phatch")),
    (data('actionlists'), glob.glob("data/actionlists/*.png")),
    (data('blender'), glob.glob("data/blender/*.blend") +\
        glob.glob("data/blender/*.py")),
    (data('blender/preview/object'),
        glob.glob("data/blender/preview/object/*.jpg")),
    (data('fonts'), glob.glob("data/fonts/*.ttf")),
    (data('highlights'), glob.glob("data/highlights/*.png")),
    (data('masks'), glob.glob("data/masks/*.jpg") +\
        glob.glob("data/masks/*.png")),
    (data('perspective'), glob.glob("data/perspective/*.png")),
]

# TODO: make /data/blender construction dynamic!!! see os.walk
blender_previews = ('book', 'box', 'can', 'cd', 'lcd', 'sphere')

for blender_preview in blender_previews:
    data_files.append((data("blender/preview/rotation/%s" % blender_preview),
        glob.glob("data/blender/preview/rotation/%s/*.jpg" % blender_preview)))

#images, fonts & icons
if WINDOWS:
    #todo: fixme
    PACKAGES += ['phatch.windows', 'phatch.lib.windows']
    os_files = []

elif LINUX:
    # check for mac?
    PACKAGES += ['phatch.linux', 'phatch.lib.linux']
    os_files = [
        #desktop
        ('share/applications', glob.glob("linux/*.desktop")),
        #images
        ('share/phatch/images', glob.glob("images/*.png") +\
            glob.glob("images/phatch*.svg") +\
            glob.glob("images/icons/scalable/*.svg")),
        #for notification
        ('share/phatch/images/icons/48x48',
            glob.glob("images/icons/48x48/*.png")),
        #man page
        ('share/man/man1', ['linux/phatch.1']),
        #mime type
        ('share/mime/packages', ['linux/phatch.xml']),
    ]
    #icons
    icon_sizes = ['%dx%d' % (x, x)
        for x in (16, 24, 32, 48, 64, 96, 128, 192, 256)]
    icons = [('share/icons/hicolor/%s/apps' % x,
            glob.glob('images/icons/%s/*.png' % x)) for x in icon_sizes] + \
        [('share/icons/hicolor/scalable/apps',
            glob.glob('images/icons/scalable/*.svg')),
        ('share/pixmaps', glob.glob('images/icons/256x256/*.png'))]
    os_files.extend(icons)


# setup options
setup_options = {
    'packages': PACKAGES,
    'scripts': ['bin/phatch'],
    'data_files': i18n_files + doc_files + data_files + os_files,
    'classifiers': CLASSIFIERS}
setup_options.update(info.SETUP)

if __name__ == '__main__':
    #run the setup
    dist = setup(**setup_options)

    # disabled: distro maintainers do the right thing
    # non distro users, who don't use packages at all,
    # might need to enable it
    if 0 and LINUX:
        # Update the mime types
        ROOT = os.geteuid() == 0
        if ROOT and dist != None:

            #update the mimetypes database -> associate.phatch
            try:
                subprocess.call(["update-mime-database",
                    os.path.join(sys.prefix, "share/mime/")])
                write('Updating the mime types database.\n')
            except:
                error('Failed to update the mime types database.\n')

            #update the .desktop file database -> application menu
            try:
                subprocess.call(["update-desktop-database"])
                write('Updating the .desktop file database.\n')
            except:
                error('Failed to update the .desktop file database.\n')

    write("\nInstallation finished! "
        "You can now run Phatch by typing 'phatch' \n"
        "or through your applications menu.\n")
