License and Copyright
*********************

License
=======

At the moment of this writing Phatch uses the `GPL 3 <http://www.gnu.org/licenses/gpl-3.0.html>`_. All code submitted to Phatch needs to use the same license or should be compatible.

Copyright
=========

All code submitted to Phatch should share its copyright with ``www.stani.be``. You keep the full copyright of your own code, but share it with the Phatch project. This keeps the management of the copyrights simple for packagers and allows us to change the license if needed for example:

* From GPL 3 to GPL 4.
* If certain modules would become part of eg. wxPython we can donate them under the wxPython license.

Phatch and your code will always be available as free software.

You can test the licenses from the ``tests`` folder::

    python license_test.py

.. note::

    If you forget the copyright or use the wrong copyright, the bazaar precommit hook will complain.

Documentation
=============

* The developers documentation ships with the Phatch application under the GPL. The developers documentation is generated with `Sphinx <http://sphinx.pocoo.org/>`_ and can be updated any time from the ``docs`` folder with the command::

    python update.py

* The html version of the user documentation will be accessible for everyone on the web and might be shown with ads. The pdf version of the manual might later be available as a reward to people who donate.

If you disagree with one of the above principles, please don't contribute code or documentation to Phatch.
