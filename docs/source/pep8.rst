Code Style: PEP8
****************

http://www.python.org/dev/peps/pep-0008/

Any code submitted to Phatch **must** follow the PEP8 code style, which is used in the standard library of the main Python distribution.

You can test if your code follows PEP8 by running the following script in the ``tests`` folder::

    python pep8_test.py

As you should have installed the bazaar precommit hook for Phatch, this test will also be enforced before you are able to commit to your branch.

.. warning::

    If you use Windows make sure that you save your code with ``\n`` line endings. Code with ``\r\n`` line endings will be refused.
