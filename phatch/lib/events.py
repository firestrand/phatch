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

"""The aim of this library is to abstract pubsub."""
#check this for the console version (wx should dissappear)
try:
    from other.pubsub import ALL_TOPICS, Publisher
except ImportError:
    from wx.lib.pubsub import ALL_TOPICS, Publisher


#---Send
class SendListener:
    def __init__(self, topic=ALL_TOPICS):
        self.topic = topic

    def __call__(self, *args, **keyw):
        data = (args, keyw)  # pack (see ReceiveListener.__call__)
        return Publisher().sendMessage(self.topic, data)


class Sender:
    def __getattr__(self, topic):
        return SendListener(topic)

send = Sender()

#---Receive


def subscribe(method, obj):
    Publisher().subscribe(method, getattr(obj, method))


class ReceiveListener:
    def __init__(self, obj, method):
        self.method = getattr(obj, method)

    def __call__(self, message):
        args, keyw = message.data  # unpack (see SendListener.__call__)
        return self.method(*args, **keyw)


class Receiver:
    def __init__(self, name):
        self._pubsub_name = name
        self._listeners = []

    def subscribe(self, method):
        """Subscribe with some class magic.
        Example: self.subscribe('error') -> subscribe('frame.error')
        Afterwars you can call it with send.frame_error()"""
        listener = ReceiveListener(self, method)
        self._listeners.append(listener)
        Publisher().subscribe(listener, '%s_%s' % (self._pubsub_name, method))

    def unsubscribe(self, method):
        """Subscribe with some class magic.
        Example: self.subscribe('error') -> subscribe('frame.error')"""
        listener = ReceiveListener(self, method)
        self._listeners.remove(listener)
        Publisher().unsubscribe(listener,
                                '%s_%s' % (self._pubsub_name, method))

    def unsubscribe_all(self):
        for listener in self._listeners:
            Publisher().unsubscribe(listener)
        self._listeners = []


def example():
    import sys

    class Test(Receiver):
        def __init__(self):
            #register an instance
            Receiver.__init__(self, 'test')
            #register the method send.test_write -> self.write
            self.subscribe('write')
            self.phrase = 'planet'

        def write(self, phrase, error):
            sys.stdout.write(phrase + '\n')
            sys.stderr.write(error)
            self.phrase = phrase

    demo = Test()
    phrase = 'hello world'
    send.test_write(phrase, error='(No error.)')
    assert demo.phrase == phrase

if __name__ == '__main__':
    example()
