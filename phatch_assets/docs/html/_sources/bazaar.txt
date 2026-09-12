Bazaar and Launchpad
********************

For Phatch we use `bazaar <http://bazaar.canonical.com>`_ (distributed version control) and `launchpad <https://launchpad.net/phatch>`_. We will describe the steps here to get you up and running for Phatch development.

Launchpad
=========

1. To `create a new Launchpad account <https://help.launchpad.net/YourAccount/NewAccount>`_, visit the account `sign-up page <https://launchpad.net/+login>`_. All you need is an email address that Launchpad can use to contact you.

2. Create a ssh key and `upload <https://help.launchpad.net/YourAccount/CreatingAnSSHKeyPair>`_ it to your launchpad profile.

3. Apply for membership of the `phatch-dev <https://launchpad.net/~phatch-dev>`_ team.

4. This last step is optional. If you want to stay up to date with all bug reports, blueprints (new features), ... apply for membership of the `phatch-launchpad <https://launchpad.net/~phatch-launchpad>`_ team. Warning: this might flood your inbox with a lot of email!

.. note::

    It is very important that you not only log any activity you do for Phatch on launchpad as bugs or blueprints, but also report progress and de-assign yourself if you quit working on something.

Bazaar
======

Getting Started with Bazaar
---------------------------

1.  Download and install bazaar.

    * Windows: Download the `standalone installer <http://wiki.bazaar.canonical.com/WindowsDownloads>`_.

    * Mac OS X: Download the `application bundle <http://wiki.bazaar.canonical.com/MacOSXDownloads>`_.

    * Linux: Get bazaar from the repositories, for example for Ubuntu/Debian ...

      If you want only the command line version::

        sudo apt-get install bzr

      If you want to use bzr with a GUI and nautilus integration, you could install (some only available from Ubuntu Lucid)::

        sudo apt-get install bzr bzr-gtk bzr-explorer nautilus-bzr

2.  Tell bazaar who you are::

        bzr whoami "Your name <email@adress>"

3.  Login to launchpad::

        bzr launchpad-login

4.  Install the Phatch precommit hook.

    This will check your code before committing to your branch. It tests your code it follows `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_, does not break any doctests and has the right copyright and license. The precommit hook is the file ``tests/test_suite/bzr_precommit_test.py`` and should be placed in your bazaar plugin folder. In order to get your code accepted, you **must** use the precommit hook.

    * Linux and Mac OS X:

      1. Install ``nosetests`` and ``licensecheck``::

        sudo apt-get install python-nose devscripts

      2. Symlink ``bzr_precommit_test.py`` to ``~/.bazaar/plugins/``

    * Windows:

      1. Install ``nosetests`` (see `nose <http://somethingaboutorange.com/mrl/projects/nose>`_ website for more info)::

        easy_install nose

      2. Copy ``bzr_precommit_test.py`` to ``C:\Program Files\Bazaar\plugins`` and update it every time it changes.

Using Bazaar
------------

1.  For every new feature or bugfix you need to start a separate branch::

      bzr branch lp:phatch

    Or if you want to give it a specific name::

      bzr branch lp:phatch name_of_branch

    So it is not unusual that one user works on more than one branch. We prefer to merge branches as soon as they are stable to prevent large differences.

2.  To let other developers follow your progress, push your branch to launchpad::

      bzr push lp:~user_name/phatch/name_of_branch

3.  Merge regularly with the main branch so it does not divert. At least merge every time before you start coding. The command is::

      bzr merge lp:phatch

    Do not use the command ``bzr update`` or ``bzr pull``.

4.  When your branch is ready file a merge request. To do so, visit your branch's overview page, click *Propose for merging into another branch*, then follow the on-screen instructions.
