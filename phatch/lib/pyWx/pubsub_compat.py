# -*- coding: utf-8 -*-
"""
Compatibility layer for pubsub to work with both wxPython Phoenix and older versions.
"""

# Define ALL_TOPICS
ALL_TOPICS = 'all'

# Custom Publisher implementation
class Publisher:
    def __init__(self):
        self.listeners = {}
        
    def subscribe(self, listener, topic=ALL_TOPICS):
        if topic not in self.listeners:
            self.listeners[topic] = []
        self.listeners[topic].append(listener)
        
    def sendMessage(self, topic=ALL_TOPICS, **kwargs):
        # Process topic listeners
        if topic in self.listeners:
            for listener in self.listeners[topic]:
                try:
                    listener(**kwargs)
                except Exception as e:
                    print(f"Error in listener for topic {topic}: {e}")
        
        # Process 'all' topic listeners if the topic isn't 'all'
        if topic != ALL_TOPICS and ALL_TOPICS in self.listeners:
            for listener in self.listeners[ALL_TOPICS]:
                try:
                    listener(**kwargs)
                except Exception as e:
                    print(f"Error in 'all' listener for topic {topic}: {e}")
                
    def unsubscribe(self, listener, topic=ALL_TOPICS):
        if topic in self.listeners and listener in self.listeners[topic]:
            self.listeners[topic].remove(listener)
            
    def unsubAll(self, topic=ALL_TOPICS):
        if topic in self.listeners:
            self.listeners[topic] = []

# Create a global instance
Publisher = Publisher() 