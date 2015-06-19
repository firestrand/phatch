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


from version import VERSION, DATE

#credits
CREDITS = {
    'code': [
        STANI,
        NADIA,
        {'name': u'Erich Heine',
            'email':'sophacles@gmail.com'},
        {'name': u'Juho Vepsäläinen',
            'email':'bebraw@gmail.com'},
        {'name': u'Robin Mills',
            'email': 'robin@clanmills.com'},
        {'name': 'Bas van Oostveen',
            'email': 'v.oostveen@gmail.com'},
        {'name': 'Pawel T. Jochym',
            'email': 'jochym@gmail.com'},
                    ],
    'documentation': [
        STANI,
        {'name': u'Frédéric Mantegazza',
        'email': 'frederic.mantegazza@gbiloba.org',
        'url': 'http://www.gbiloba.org'},
        {'name': 'Dwarrel Egel',
        'email': 'dwarrel.egel@gmail.com'},
    ],
    'translation': [
        STANI,
        {'name': u'ad Madi'},
        {'name': u'abdessmed mohamed amine'},
        {'name': u'abuyop'},
        {'name': u'adaminikisi'},
        {'name': u'adura'},
        {'name': u'aeglos'},
        {'name': u'agatzebluz'},
        {'name': u'Ahmed Noor Kader Mustajir Md Eusoff'},
        {'name': u'Aktiwers'},
        {'name': u'Alan Teixeira'},
        {'name': u'Albert Cervin'},
        {'name': u'Alberto T.'},
        {'name': u'alex'},
        {'name': u'Alex Debian'},
        {'name': u'Alexandre Prokoudine'},
        {'name': u'Ali Sattari'},
        {'name': u'Anders'},
        {'name': u'Andras Bibok'},
        {'name': u'André Gondim'},
        {'name': u'Andrea (pikkio)'},
        {'name': u'Andrey Skuryatin'},
        {'name': u'Andrzej MoST (Marcin Ostajewski)'},
        {'name': u'Archie'},
        {'name': u'Ardaking'},
        {'name': u'Arielle B Cruz'},
        {'name': u'Aristotelis Grammatikakis'},
        {'name': u'arnau'},
        {'name': u'Arnaud Bonatti'},
        {'name': u'Aron Xu'},
        {'name': u'Artin'},
        {'name': u'Artur Chmarzyński'},
        {'name': u'Åskar'},
        {'name': u"Balaam's Miracle"},
        {'name': u'Bjørn Sivertsen'},
        {'name': u'bt4wang'},
        {'name': u'Cedric Graebin'},
        {'name': u'César Flores'},
        {'name': u'Clovis Gauzy'},
        {'name': u'cumulus007'},
        {'name': u'Daniël H.'},
        {'name': u'Daniel Nylander'},
        {'name': u'Daniel Voicu'},
        {'name': u'Daniele de Virgilio'},
        {'name': u'Darek'},
        {'name': u'David A Páez'},
        {'name': u'David Machakhelidze'},
        {'name': u'deukek'},
        {'name': u'Diablo'},
        {'name': u'DiegoJ'},
        {'name': u'Dirk Tas'},
        {'name': u'Diska'},
        {'name': u'Dobrosław Żybort'},
        {'name': u'DPini'},
        {'name': u'Dr. Gráf'},
        {'name': u'Dread Knight'},
        {'name': u'Edgardo Fredz'},
        {'name': u'Emil Pavlov'},
        {'name': u'emil.s'},
        {'name': u'Emilio Pozuelo Monfort'},
        {'name': u'Emre Ayca'},
        {'name': u'EN'},
        {'name': u'Endresz_Z'},
        {'name': u'ercole'},
        {'name': u'Ervin Triana'},
        {'name': u'Ervin Triana'},
        {'name': u'Fabien Basmaison'},
        {'name': u'Federico Antón'},
        {'name': u'Felipe'},
        {'name': u'Gabriel Čenkei'},
        {'name': u'Gabriel Rota'},
        {'name': u'Galvin'},
        {'name': u'Gérard Duteil'},
        {'name': u'Giacomo Mirabassi'},
        {'name': u'Gianfranco Marino'},
        {'name': u'Guo Xi'},
        {'name': u'Guybrush88'},
        {'name': u'Halgeir'},
        {'name': u'Ionuț Jula'},
        {'name': u'Ivan Lucas'},
        {'name': u'Jan Tojnar'},
        {'name': u'Jaroslav Lichtblau'},
        {'name': u'Javier García Díaz'},
        {'name': u'jean-luc menut'},
        {'name': u'jgraeme'},
        {'name': u'Johannes'},
        {'name': u'John Lejeune'},
        {'name': u'jollyr0ger'},
        {'name': u'Juho Vepsäläinen'},
        {'name': u'Juss1962'},
        {'name': u'kasade'},
        {'name': u'kekeljevic'},
        {'name': u'kenan3008'},
        {'name': u'Koptev Oleg'},
        {'name': u'Kulcsár, Kázmér'},
        {'name': u'Lauri Potka'},
        {'name': u'liticovjesac'},
        {'name': u'Lomz'},
        {'name': u'Luca Livraghi'},
        {'name': u'luojie-dune'},
        {'name': u'madcore'},
        {'name': u'mahirgul'},
        {'name': u'Marcos'},
        {'name': u'Marielle Winarto'},
        {'name': u'Mario Ferraro'},
        {'name': u'Martin Lettner'},
        {'name': u'Matteo Ferrabone'},
        {'name': u'Matthew Gadd'},
        {'name': u'Mattias Ohlsson'},
        {'name': u'Maudy Pedrao'},
        {'name': u'MaXeR'},
        {'name': u'Michael Christoph Jan Godawski'},
        {'name': u'Michael Katz'},
        {'name': u'Michał Trzebiatowski'},
        {'name': u'Michal Zbořil'},
        {'name': u'Miguel Diago'},
        {'name': u'Mijia'},
        {'name': u'milboy'},
        {'name': u'Miroslav Koucký'},
        {'name': u'Miroslav Matejaš'},
        {'name': u'momou'},
        {'name': u'Mortimer'},
        {'name': u'Motin'},
        {'name': u'nEJC'},
        {'name': u'Newbuntu'},
        {'name': u'nicke'},
        {'name': u'Nicola Piovesan'},
        {'name': u'Nicolae Istratii'},
        {'name': u'Nicolas CHOUALI'},
        {'name': u'nipunreddevil'},
        {'name': u'Nizar Kerkeni'},
        {'name': u'Nkolay Parukhin'},
        {'name': u'orange'},
        {'name': u'Paco Molinero'},
        {'name': u'pasirt'},
        {'name': u'Pavel Korotvička'},
        {'name': u'pawel'},
        {'name': u'Petr Pulc'},
        {'name': u'petre'},
        {'name': u'Pierre Slamich'},
        {'name': u'Piotr Ożarowski'},
        {'name': u'Pontus Schönberg'},
        {'name': u'pveith'},
        {'name': u'pygmee'},
        {'name': u'qiuty'},
        {'name': u'quina'},
        {'name': u'rainofchaos'},
        {'name': u'Rodrigo Garcia Gonzalez'},
        {'name': u'rokkralj'},
        {'name': u'Roman Shiryaev'},
        {'name': u'royto'},
        {'name': u'Rune C. Akselsen'},
        {'name': u'rylleman'},
        {'name': u'Salandro'},
        {'name': u'Saša Pavić'},
        {'name': u'Sasha'},
        {'name': u'SebX86'},
        {'name': u'Sergiy Babakin'},
        {'name': u'Serhey Kusyumoff (Сергій Кусюмов)'},
        {'name': u'Shrikant Sharat'},
        {'name': u'skarevoluti'},
        {'name': u'Skully'},
        {'name': u'smo'},
        {'name': u'SnivleM'},
        {'name': u'stani'},
        {'name': u'Stephan Klein'},
        {'name': u'studiomohawk'},
        {'name': u'Svetoslav Stefanov'},
        {'name': u'Tao Wei'},
        {'name': u'tarih mehmet'},
        {'name': u'theli'},
        {'name': u'therapiekind'},
        {'name': u'Todor Eemreorov'},
        {'name': u'Tommy Brunn'},
        {'name': u'Tosszyx'},
        {'name': u'TuniX12'},
        {'name': u'ubby'},
        {'name': u'Vadim Peretokin'},
        {'name': u'VerWolF'},
        {'name': u'Vyacheslav S.'},
        {'name': u'w00binda'},
        {'name': u'Wander Nauta'},
        {'name': u'wang'},
        {'name': u'WangWenhui'},
        {'name': u'wcoqui'},
        {'name': u'Wiesiek'},
        {'name': u'Will Scott'},
        {'name': u'X_FISH'},
        {'name': u'Xandi'},
        {'name': u'xinzhi'},
        {'name': u'yoni'},
        {'name': u'zelezni'},
        {'name': u'zero'},
        {'name': u'Zirro'},
        {'name': u'Zoran Olujic'},
    ],
    'graphics': [
        {'name': u'Igor Kekeljevic',
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
    from PIL import Image
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
    tasks = CREDITS.keys()
    tasks.sort()
    for task in tasks:
        authors.write('\n\n\n%s:\n\n' % task.title())
        authors.write(u'\n'.join([' - '.join(person.values())
            for person in CREDITS[task]]))
    authors.close()


def write_readme_credits():
    write_readme()
    write_credits()

if __name__ == '__main__':
    write_readme_credits()
