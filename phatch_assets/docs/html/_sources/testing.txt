Testing
*******

Phatch uses two strategies for testing:

* acceptance testing for all possible image processing pipelines
* unit tests by doctests

Acceptance testing
==================

The acceptance testing uses the images inside the ``tests/input`` folder. To get all options for image acceptance testing, run this command from the ``tests`` folder::

    python acceptance_test.py --help

Here are some examples, choose one of the two listed commands ...

* To run all tests use::

    python acceptance_test.py --all
    python acceptance_test.py -a

* To run only the library tests use::

    python acceptance_test.py --tag=library
    python acceptance_test.py -t library

* To run only tests with a certain tag use::

    python acceptance_test.py --tag=tag_name
    python acceptance_test.py -t tag_name

* To test only one action::

    python acceptance_test.py --select=action_name
    python acceptance_test.py -s action_name


Doctests
========

We chose for doctests as it saves time by being both unit tests and documentation. Please add doctests to the code you contribute.

Run the doctests inside the ``tests`` folder::

    python doc_test.py

This will automatically also be run by the bzr precommit hook.
