Release Manager
***************

For every release we chose a release manager. If you want to volunteer please let us know.

These are the steps a release manager has to do:

#.  Check the code with these tools::

      pyflakes ../phatch/ | grep -v "undefined name '_'" | grep -v 'but unused'| grep -v redefinition > pyflakes.txt
      pylint --errors-only ../phatch/  | grep -v "Undefined variable '_'" | grep -v "already defined" > pylint.txt

    Do not fix any code in ``phatch/other``. Be carefull to fix errors to prevent breaking. For example if you remove an unused imported function ``bar`` in the module ``foo``, be sure to check it is nowhere used as ``foo.bar``. So ignore unused items unless you are 100% sure what you are doing.

#.  License and Copyrights

    Check license and copyrights of any new files::

      python license_test.py

    The above command will only check source code on Debian/Ubuntu, so please check other files manually (such as artwork, ...). Update the copyright file both in trunk as in the PAPT svn.

    Check if in the ``Help>About`` dialog box everyone with substantial contributions is listed. Otherwise add it to ``phatch/data/info.py``.

#.  Developer Documentation

    Update developer documentation, by running this command in the ``docs`` folder::

      python update.py

#.  Translations

    Download the latest ``po`` translations. Test them with `potest <https://launchpad.net/potest>`_ and fix any errors immediately in launchpad. When all errors are fixed download the latest ``po`` and ``mo`` translations to trunk.

#.  `PPA <https://help.launchpad.net/Packaging/PPA>`_ (Personal Package Archive)

    Build and upload to the Phatch PPA to check if no errors are thrown by the build systems and if Phatch can be correctly installed. Invite users to test the PPA and look for any user interface errors. Do not release a version in the PPA with the new version number yet.

#.  Version number

    Bump up the version number after PPA testing. In the file ``phatch/data/version.py`` the variables ``BASE`` and ``VERSION`` should be identical::

      BASE = "0.2.8"
      VERSION = "0.2.8"
      DATE = "Tue, 09 Mar 2010 21:01:25"

    Check in the ``Help>About`` dialog box if the version number is displayed correctly.

#.  Commit last changes if necessary. Tag the release, for example::

      bzr tag 0.2.8

#.  Export as zip::

      bzr export ../phatch-0.2.8.zip

#.  `PAPT <http://wiki.debian.org/Teams/PythonAppsPackagingTeam>`_ (Debian Python Application Package Team)

    Be sure you have an `alioth account <https://alioth.debian.org/account/register.php>`_. Update the Phatch files from the `PAPT svn <http://svn.debian.org/wsvn/python-apps/packages/phatch/trunk/debian/#_packages_phatch_trunk_debian_>`_ as far as you can:

    * copyright

      * check differences and sync both from the same file in trunk

    * changelog

      * create a new entry with the command::

          dch -v 0.2.8-1

      * change the entry in::

          phatch (0.2.8-1) UNRELEASED; urgency=low

      * mention all bug fixes
      * list new or removed dependencies
      * send a mail to POX with the subject "RFS: phatch 0.2.8-1" and mention the download url in the message

#.  If the package has been accepted by Debian, release with the new version number in the Phatch PPA.

#.  Ensure the Phatch website gets updated.

#.  Spread the word and announce the Phatch release on (ask help of others if needed):

    * http://freshmeat.net/
    * http://groups.google.com/group/comp.lang.python
    * http://groups.google.com/group/comp.lang.python.announce
    * http://pypi.python.org
    * http://groups.google.com/group/wxpython-users
    * http://ubuntuforums.org/forumdisplay.php?f=16
    * http://mail.python.org/mailman/listinfo/image-sig (PIL)
    * http://blenderartists.org/forum/forumdisplay.php?f=11

    If you have a blog, announce it there too.

    Specific annoucements by people:

    * Stani:

      * python-nl mailing list

#.  Give your feedback on this release documentation, so it can be improved.
