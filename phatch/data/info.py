# -*- coding: UTF-8 -*-

# Phatch - Photo Batch Processor
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
#
# Phatch recommends SPE (http://pythonide.stani.be) for python editing.

"""Important: Run this file everytime info is changed."""


import codecs
import sys
import time


#constants
NAME = 'Phatch'
AUTHOR = 'Stani'
AUTHOR_EMAIL = 'spe.stani.be@gmail.com'
GPL_VERSION = '3'
STANI = {
    'name': AUTHOR,
    'email': AUTHOR_EMAIL,
    'url': 'www.stani.be',
}
NADIA = {
    'name': 'Nadia Alramli',
    'email': 'mail@nadiana.com',
    'url': 'http://nadiana.com',
}

SUPPORTED_LANGUAGES = ['Dutch', 'English']


from .version import VERSION, DATE

#credits
CREDITS = {
    'code': [
        STANI,
        NADIA,
        {'name': 'Erich Heine',
            'email':'sophacles@gmail.com'},
        {'name': 'Juho Vepsäläinen',
            'email':'bebraw@gmail.com'},
        {'name': 'Robin Mills',
            'email': 'robin@clanmills.com'},
        {'name': 'Bas van Oostveen',
            'email': 'v.oostveen@gmail.com'},
        {'name': 'Pawel T. Jochym',
            'email': 'jochym@gmail.com'},
                    ],
    'documentation': [
        STANI,
        {'name': 'Frédéric Mantegazza',
        'email': 'frederic.mantegazza@gbiloba.org',
        'url': 'http://www.gbiloba.org'},
        {'name': 'Dwarrel Egel',
        'email': 'dwarrel.egel@gmail.com'},
    ],
    'translation': [
        STANI,
        {'name': 'ad Madi'},
        {'name': 'abdessmed mohamed amine'},
        {'name': 'abuyop'},
        {'name': 'adaminikisi'},
        {'name': 'adura'},
        {'name': 'aeglos'},
        {'name': 'agatzebluz'},
        {'name': 'Ahmed Noor Kader Mustajir Md Eusoff'},
        {'name': 'Aktiwers'},
        {'name': 'Alan Teixeira'},
        {'name': 'Albert Cervin'},
        {'name': 'Alberto T.'},
        {'name': 'alex'},
        {'name': 'Alex Debian'},
        {'name': 'Alexandre Prokoudine'},
        {'name': 'Ali Sattari'},
        {'name': 'Anders'},
        {'name': 'Andras Bibok'},
        {'name': 'André Gondim'},
        {'name': 'Andrea (pikkio)'},
        {'name': 'Andrey Skuryatin'},
        {'name': 'Andrzej MoST (Marcin Ostajewski)'},
        {'name': 'Archie'},
        {'name': 'Ardaking'},
        {'name': 'Arielle B Cruz'},
        {'name': 'Aristotelis Grammatikakis'},
        {'name': 'arnau'},
        {'name': 'Arnaud Bonatti'},
        {'name': 'Aron Xu'},
        {'name': 'Artin'},
        {'name': 'Artur Chmarzyński'},
        {'name': 'Åskar'},
        {'name': "Balaam's Miracle"},
        {'name': 'Bjørn Sivertsen'},
        {'name': 'bt4wang'},
        {'name': 'Cedric Graebin'},
        {'name': 'César Flores'},
        {'name': 'Clovis Gauzy'},
        {'name': 'cumulus007'},
        {'name': 'Daniël H.'},
        {'name': 'Daniel Nylander'},
        {'name': 'Daniel Voicu'},
        {'name': 'Daniele de Virgilio'},
        {'name': 'Darek'},
        {'name': 'David A Páez'},
        {'name': 'David Machakhelidze'},
        {'name': 'deukek'},
        {'name': 'Diablo'},
        {'name': 'DiegoJ'},
        {'name': 'Dirk Tas'},
        {'name': 'Diska'},
        {'name': 'Dobrosław Żybort'},
        {'name': 'DPini'},
        {'name': 'Dr. Gráf'},
        {'name': 'Dread Knight'},
        {'name': 'Edgardo Fredz'},
        {'name': 'Emil Pavlov'},
        {'name': 'emil.s'},
        {'name': 'Emilio Pozuelo Monfort'},
        {'name': 'Emre Ayca'},
        {'name': 'EN'},
        {'name': 'Endresz_Z'},
        {'name': 'ercole'},
        {'name': 'Ervin Triana'},
        {'name': 'Ervin Triana'},
        {'name': 'Fabien Basmaison'},
        {'name': 'Federico Antón'},
        {'name': 'Felipe'},
        {'name': 'Gabriel Čenkei'},
        {'name': 'Gabriel Rota'},
        {'name': 'Galvin'},
        {'name': 'Gérard Duteil'},
        {'name': 'Giacomo Mirabassi'},
        {'name': 'Gianfranco Marino'},
        {'name': 'Guo Xi'},
        {'name': 'Guybrush88'},
        {'name': 'Halgeir'},
        {'name': 'Ionuț Jula'},
        {'name': 'Ivan Lucas'},
        {'name': 'Jan Tojnar'},
        {'name': 'Jaroslav Lichtblau'},
        {'name': 'Javier García Díaz'},
        {'name': 'jean-luc menut'},
        {'name': 'jgraeme'},
        {'name': 'Johannes'},
        {'name': 'John Lejeune'},
        {'name': 'jollyr0ger'},
        {'name': 'Juho Vepsäläinen'},
        {'name': 'Juss1962'},
        {'name': 'kasade'},
        {'name': 'kekeljevic'},
        {'name': 'kenan3008'},
        {'name': 'Koptev Oleg'},
        {'name': 'Kulcsár, Kázmér'},
        {'name': 'Lauri Potka'},
        {'name': 'liticovjesac'},
        {'name': 'Lomz'},
        {'name': 'Luca Livraghi'},
        {'name': 'luojie-dune'},
        {'name': 'madcore'},
        {'name': 'mahirgul'},
        {'name': 'Marcos'},
        {'name': 'Marielle Winarto'},
        {'name': 'Mario Ferraro'},
        {'name': 'Martin Lettner'},
        {'name': 'Matteo Ferrabone'},
        {'name': 'Matthew Gadd'},
        {'name': 'Mattias Ohlsson'},
        {'name': 'Maudy Pedrao'},
        {'name': 'MaXeR'},
        {'name': 'Michael Christoph Jan Godawski'},
        {'name': 'Michael Katz'},
        {'name': 'Michał Trzebiatowski'},
        {'name': 'Michal Zbořil'},
        {'name': 'Miguel Diago'},
        {'name': 'Mijia'},
        {'name': 'milboy'},
        {'name': 'Miroslav Koucký'},
        {'name': 'Miroslav Matejaš'},
        {'name': 'momou'},
        {'name': 'Mortimer'},
        {'name': 'Motin'},
        {'name': 'nEJC'},
        {'name': 'Newbuntu'},
        {'name': 'nicke'},
        {'name': 'Nicola Piovesan'},
        {'name': 'Nicolae Istratii'},
        {'name': 'Nicolas CHOUALI'},
        {'name': 'nipunreddevil'},
        {'name': 'Nizar Kerkeni'},
        {'name': 'Nkolay Parukhin'},
        {'name': 'orange'},
        {'name': 'Paco Molinero'},
        {'name': 'pasirt'},
        {'name': 'Pavel Korotvička'},
        {'name': 'pawel'},
        {'name': 'Petr Pulc'},
        {'name': 'petre'},
        {'name': 'Pierre Slamich'},
        {'name': 'Piotr Ożarowski'},
        {'name': 'Pontus Schönberg'},
        {'name': 'pveith'},
        {'name': 'pygmee'},
        {'name': 'qiuty'},
        {'name': 'quina'},
        {'name': 'rainofchaos'},
        {'name': 'Rodrigo Garcia Gonzalez'},
        {'name': 'rokkralj'},
        {'name': 'Roman Shiryaev'},
        {'name': 'royto'},
        {'name': 'Rune C. Akselsen'},
        {'name': 'rylleman'},
        {'name': 'Salandro'},
        {'name': 'Saša Pavić'},
        {'name': 'Sasha'},
        {'name': 'SebX86'},
        {'name': 'Sergiy Babakin'},
        {'name': 'Serhey Kusyumoff (Сергій Кусюмов)'},
        {'name': 'Shrikant Sharat'},
        {'name': 'skarevoluti'},
        {'name': 'Skully'},
        {'name': 'smo'},
        {'name': 'SnivleM'},
        {'name': 'stani'},
        {'name': 'Stephan Klein'},
        {'name': 'studiomohawk'},
        {'name': 'Svetoslav Stefanov'},
        {'name': 'Tao Wei'},
        {'name': 'tarih mehmet'},
        {'name': 'theli'},
        {'name': 'therapiekind'},
        {'name': 'Todor Eemreorov'},
        {'name': 'Tommy Brunn'},
        {'name': 'Tosszyx'},
        {'name': 'TuniX12'},
        {'name': 'ubby'},
        {'name': 'Vadim Peretokin'},
        {'name': 'VerWolF'},
        {'name': 'Vyacheslav S.'},
        {'name': 'w00binda'},
        {'name': 'Wander Nauta'},
        {'name': 'wang'},
        {'name': 'WangWenhui'},
        {'name': 'wcoqui'},
        {'name': 'Wiesiek'},
        {'name': 'Will Scott'},
        {'name': 'X_FISH'},
        {'name': 'Xandi'},
        {'name': 'xinzhi'},
        {'name': 'yoni'},
        {'name': 'zelezni'},
        {'name': 'zero'},
        {'name': 'Zirro'},
        {'name': 'Zoran Olujic'},
    ],
    'graphics': [
        {'name': 'Igor Kekeljevic',
            'email': 'admiror@nscable.net',
            'url': 'http://www.admiror-ns.co.yu',
        },
        NADIA,
        {'name': 'NuoveXt 1.6',
            'url': 'http://nuovext.pwsp.net',
            'author': 'Alexandre Moore',
        },
        {'name': 'Everaldo Coelho',
            'url': 'http://www.iconlet.com/info/9657_colorscm_128x128',
            'email': 'http://www.everaldo.com',
        },
        {'name': 'Open Clip Art Library',
            'url': 'http://www.openclipart.org',
        },
        {'name': 'Geotag Icon',
            'url': 'http://www.geotagicons.com',
        },
        STANI,
    ],
    'libraries': [
        {'name': 'Python %s' % sys.version.split(' ')[0],
            'url': 'http://www.python.org',
            'author': 'Guido Van Rossum',
            'license': 'Python license',
        },
        {'name': 'wxGlade',
            'url': 'http://wxglade.sourceforge.net/',
            'author': 'Alberto Griggio',
        },
        {'name': 'pubsub.py',
            'author': 'Oliver Schoenborn',
            'license': 'wxWidgets license',
        },
        {'name': 'TextCtrlAutoComplete.py',
            'author':\
            'Edward Flick (CDF Inc, http://www.cdf-imaging.com)',
            'license': 'wxWidgets license',
            'url': 'http://wiki.wxpython.org/TextCtrlAutoComplete',
        },
        {'name': 'PyExiv2',
            'url': 'http://tilloy.net/dev/pyexiv2/',
            'author': 'Olivier Somon',
            'license': 'GPL license',
        },
        {'name': 'python-nautilus',
            'url': 'http://www.gnome.org/projects/nautilus/',
            'license': 'GPL license',
        },
        {'name': 'tamogen.py',
            'url': 'http://sintixerr.wordpress.com/tone-altering-' \
                + 'mosaic-generator-tamogen-in-python/',
            'author': 'Jack Whitsitt, Juho Vepsäläinen',
            'license': 'GPL license',
        },
        {'name': 'python-dateutil: relativedelta.py',
            'url': 'http://labix.org/python-dateutil',
            'author': 'Gustavo Niemeyer',
            'license': 'Python license',
        },
        {'name': 'Tiff Tools',
            'url': 'http://www.remotesensing.org/libtiff/',
            'author': 'Sam Leffler',
            'license': 'FreeBSD license',
        },
        #{'name': 'EXIF.py',
        #    'url': 'http://www.gnome.org/projects/nautilus/',
        #    'author': 'Gene Cash, Ianaré Sévi',
        #    'license': 'FreeBSD license',
        #},
        {'name': 'ToasterBox',
            'url': 'http://xoomer.virgilio.it/infinity77/main/' \
                + 'ToasterBox.html',
            'author': 'Andrea Gavana',
            'license': 'wxWidgets license',
        },
    ],
    'sponsors': [
        {'name': 'Free Software web hosting',
            'url': 'http://bearstech.com',
            'email': 'John Lejeune <jlejeune@bearstech.com> & ' \
                + 'Cyberj <jcharpentier@bearstech.com>',
        },
    ]
}

#year: automatically fetch copyright years
YEAR = time.localtime()[0]
if YEAR > 2007:
    CO_YEAR = '2007-%s' % YEAR
else:
    CO_YEAR = '2007'

#setup.py information
SETUP = {
    'name': NAME,
    'version': VERSION,
    'author': AUTHOR,
    'author_email': AUTHOR_EMAIL,
    'maintainer': AUTHOR,
    'maintainer_email': AUTHOR_EMAIL,
    'url': 'http://phatch.org',
    'description': 'PHoto bATCH Processor',
    'long_description': 'Phatch enables you to resize, rotate, mirror, '
        'apply watermarks, shadows, rounded courners, '
        'perspective, ... to any photo collection easily '
        'with a single mouse click. You can arrange your own'
        ' action lists and write plugins with PIL. \n\n'
        'Phatch can rename or copy images based on any EXIF '
        'or IPTC tag. In combination with pyexiv2 Phatch can'
        ' also save EXIF and IPTC metadata. \n\n'
        'Phatch has a wxPython GUI, but can also run as a '
        'console application on servers.',
    'classifiers': [
        'Development Status:: 4 - Beta',
        'Environment:: Console',
        'Environment:: MacOS X',
        'Environment:: Win32 (MS Windows)',
        'Environment:: X11 Applications',
        'Environment:: X11 Applications:: Gnome',
        'Environment:: X11 Applications:: GTK',
        'Intended Audience:: Developers',
        'Intended Audience:: End Users/Desktop',
        'License:: OSI Approved:: GNU General Public License (GPL)',
        'Operating System:: MacOS:: MacOS X',
        'Operating System:: Microsoft:: Windows',
        'Operating System:: OS Independent',
        'Operating System:: POSIX',
        'Operating System:: POSIX:: Linux',
        'Programming Language:: Python',
        'Topic:: Artistic Software',
        'Topic:: Multimedia:: Graphics',
        'Topic:: Multimedia:: Graphics:: Graphics Conversion',
        ] + ['Natural Language:: ' + \
            language for language in SUPPORTED_LANGUAGES],
}

INFO = {
    'copyright': '(c) %s www.stani.be' % CO_YEAR,
    'date': DATE,
    'description': 'Photo Batch Processor',
    'extension': '.' + NAME.lower(),
    'download_url': 'http://phatch.org',
    'gpl_version': GPL_VERSION,
    'license': 'GPL v.' + GPL_VERSION,
    'maintainer': 'Stani M',
    'fsf_adress': '51 Franklin Street, Fifth Floor, '
        'Boston, MA 02110-1301, USA',
}

INFO.update(SETUP)

README = \
"""%(name)s = PHoto bATCH Processor

%(url)s

Batch your photo's with one mouse click. Typical examples are resizing,
rotating, applying shadows, watermarks, rounded corners, EXIF renaming,
...

%(name)s was developed with the SPE editor (http://pythonide.stani.be)
on Ubuntu (GNU/Linux), but should run fine as well on Windows and
Mac Os X.

Please read first carefully the installation instructions for your
platform on the documentation website, which you can find at:
%(url)s > documentation > install

If you are a python developer, you can write easily your own plugins
with PIL (Python Image Library). Please send your plugins to
%(author_email)s You probably first want to read the developers
documentation:
%(url)s > documentation > developers

All credits are in the AUTHORS file or in the Help> About dialog box.

%(name)s is licensed under the %(license)s, of which you can find the
details in the COPYING file. %(name)s has no limitations, no time-outs,
no nags, no adware, no banner ads and no spyware. It is 100%% free and
open source.

%(copyright)s
""" % INFO

PIL_CREDITS = {
    'name': 'Python Image Library',
    'url': 'http://www.pythonware.com/products/pil/',
    'author': 'Fredrik Lundh',
    'license': 'PIL license',
}

WXPYTHON_CREDITS = {
    'name': 'wxPython',
    'url': 'http://www.wxpython.org',
    'author': 'Robin Dunn',
    'license': 'wxWidgets license',
}

HEADER = "Phatch is the result of work by (in no particular order):"


def all_credits():
    #PIL - Python Image Library
    import Image
    pil_credits = PIL_CREDITS
    pil_credits['name'] += ' %s' % Image.VERSION
    if not (pil_credits in CREDITS['libraries']):
        CREDITS['libraries'].append(pil_credits)
    #wxPython
    import wx
    wxPython_credits = WXPYTHON_CREDITS
    wxPython_credits['name'] += ' %s' % wx.VERSION_STRING
    if not (wxPython_credits in CREDITS['libraries']):
        CREDITS['libraries'].append(wxPython_credits)
    return CREDITS


def write_readme():
    readme = open('../../README', 'w')
    readme.write(README)
    readme.close()


def write_credits():
    all_credits()
    authors = codecs.open('../../AUTHORS', 'wb', 'utf-8')
    authors.write(HEADER)
    tasks = list(CREDITS.keys())
    tasks.sort()
    for task in tasks:
        authors.write('\n\n\n%s:\n\n' % task.title())
        authors.write('\n'.join([' - '.join(list(person.values()))
            for person in CREDITS[task]]))
    authors.close()


def write_readme_credits():
    write_readme()
    write_credits()

if __name__ == '__main__':
    write_readme_credits()
