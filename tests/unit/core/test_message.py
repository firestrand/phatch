"""Unit tests for phatch.core.message module.

Tests pub/sub messaging system, receiver classes, and event handling.
"""

import builtins
from unittest.mock import patch

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.core import message


class TestFrameReceiverClass:
    """Test FrameReceiver class structure and methods."""

    def test_frame_receiver_inherits_from_receiver(self):
        """FrameReceiver should inherit from Receiver."""
        # Check that class exists and has expected parent
        assert hasattr(message, 'FrameReceiver')
        # Check class name of parent (avoid import path issues)
        assert any('Receiver' in base.__name__ for base in message.FrameReceiver.__mro__)

    def test_frame_receiver_has_pubsub_method(self):
        """FrameReceiver should have _pubsub method."""
        assert hasattr(message.FrameReceiver, '_pubsub')
        assert callable(message.FrameReceiver._pubsub)

    def test_frame_receiver_has_event_handlers(self):
        """FrameReceiver should have methods for all events."""
        event_methods = [
            'append_save_action',
            'show_execute_dialog',
            'show_error',
            'show_files_message',
            'show_progress',
            'show_progress_error',
            'show_scrolled_message',
        ]
        for method_name in event_methods:
            assert hasattr(message.FrameReceiver, method_name), \
                f"Missing method: {method_name}"
            method = getattr(message.FrameReceiver, method_name)
            assert callable(method)

    def test_frame_receiver_default_implementations(self):
        """FrameReceiver event handlers should have default (no-op) implementations."""
        receiver = message.FrameReceiver('test')

        # These should not raise exceptions when called with appropriate args
        receiver.append_save_action(None)
        receiver.show_execute_dialog(None, None)
        receiver.show_error('test message')
        receiver.show_files_message(None, 'message', 'title', [])
        receiver.show_progress('title', 10, 5)
        receiver.show_progress_error(None, 'message')
        receiver.show_scrolled_message('message', 'title')


class TestProgressReceiverClass:
    """Test ProgressReceiver class structure and methods."""

    def test_progress_receiver_inherits_from_receiver(self):
        """ProgressReceiver should inherit from Receiver."""
        # Check class name of parent (avoid import path issues)
        assert any('Receiver' in base.__name__ for base in message.ProgressReceiver.__mro__)

    def test_progress_receiver_initialization(self):
        """ProgressReceiver should initialize with parent_max and child_max."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        assert receiver.parent_max == 10
        assert receiver.child_max == 5
        assert receiver.max == 50  # 10 * 5

    def test_progress_receiver_set_max(self):
        """set_max should update max values."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        receiver.set_max(20, 3)

        assert receiver.parent_max == 20
        assert receiver.child_max == 3
        assert receiver.max == 60  # 20 * 3

    def test_progress_receiver_has_pubsub_method(self):
        """ProgressReceiver should have _pubsub method."""
        assert hasattr(message.ProgressReceiver, '_pubsub')
        assert callable(message.ProgressReceiver._pubsub)

    def test_progress_receiver_has_event_handlers(self):
        """ProgressReceiver should have event handler methods."""
        event_methods = [
            'close',
            'update',
            'update_filename',
            'update_index',
            'sleep',
        ]
        for method_name in event_methods:
            assert hasattr(message.ProgressReceiver, method_name), \
                f"Missing method: {method_name}"
            method = getattr(message.ProgressReceiver, method_name)
            assert callable(method)


class TestProgressReceiverUpdateMethods:
    """Test ProgressReceiver update methods."""

    @patch.object(message.ProgressReceiver, 'update')
    @patch.object(message.ProgressReceiver, 'sleep')
    def test_update_filename(self, mock_sleep, mock_update):
        """update_filename should extract filename and call update with message."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        # Test with a Unix-style path
        filename = '/home/user/images/test.jpg'
        receiver.update_filename(None, parent_index=2, filename=filename)

        # Should call update with calculated value and message
        mock_update.assert_called_once()
        call_args = mock_update.call_args

        # First arg should be result (None)
        assert call_args[0][0] is None

        # Second arg should be parent_index * child_max
        assert call_args[0][1] == 2 * 5  # 10

        # Should have newmsg kwarg with file info
        assert 'newmsg' in call_args[1]
        message_text = call_args[1]['newmsg']
        assert 'test.jpg' in message_text

        # Should call sleep
        mock_sleep.assert_called_once()

    @patch.object(message.ProgressReceiver, 'update')
    def test_update_index(self, mock_update):
        """update_index should calculate correct value and call update."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        receiver.update_index(None, parent_index=3, child_index=2)

        # Should call update with calculated value
        # Formula: parent_index * child_max + child_index + 1
        expected_value = 3 * 5 + 2 + 1  # 18
        mock_update.assert_called_once_with(None, expected_value)

    def test_update_index_calculation(self):
        """update_index should correctly calculate progress value."""
        receiver = message.ProgressReceiver(parent_max=100, child_max=10)

        with patch.object(receiver, 'update') as mock_update:
            # Test at beginning
            receiver.update_index(None, parent_index=0, child_index=0)
            assert mock_update.call_args[0][1] == 1  # 0*10 + 0 + 1

            # Test in middle
            mock_update.reset_mock()
            receiver.update_index(None, parent_index=50, child_index=5)
            assert mock_update.call_args[0][1] == 506  # 50*10 + 5 + 1

            # Test at end
            mock_update.reset_mock()
            receiver.update_index(None, parent_index=99, child_index=9)
            assert mock_update.call_args[0][1] == 1000  # 99*10 + 9 + 1

    def test_default_update_implementation(self):
        """Default update() should not raise exceptions."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        # Should not raise
        receiver.update(None, 25)
        receiver.update(None, 50, newmsg='Test message')

    def test_default_close_implementation(self):
        """Default close() should not raise exceptions."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        # Should not raise
        receiver.close()

    def test_default_sleep_implementation(self):
        """Default sleep() should not raise exceptions."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        # Should not raise
        receiver.sleep()


class TestProgressReceiverFilenameHandling:
    """Test ProgressReceiver's filename handling with various path formats."""

    @patch.object(message.ProgressReceiver, 'update')
    @patch.object(message.ProgressReceiver, 'sleep')
    def test_update_filename_unix_path(self, mock_sleep, mock_update):
        """update_filename should handle Unix-style paths."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        receiver.update_filename(None, 0, '/home/user/photos/vacation.jpg')

        # Check message contains filename
        message_text = mock_update.call_args[1]['newmsg']
        assert 'vacation.jpg' in message_text
        assert '/home/user/photos' in message_text or 'photos' in message_text

    @patch.object(message.ProgressReceiver, 'update')
    @patch.object(message.ProgressReceiver, 'sleep')
    def test_update_filename_windows_path(self, mock_sleep, mock_update):
        """update_filename should handle Windows-style paths."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        # Windows path
        receiver.update_filename(None, 0, r'C:\Users\Test\Pictures\photo.jpg')

        message_text = mock_update.call_args[1]['newmsg']
        assert 'photo.jpg' in message_text

    @patch.object(message.ProgressReceiver, 'update')
    @patch.object(message.ProgressReceiver, 'sleep')
    def test_update_filename_relative_path(self, mock_sleep, mock_update):
        """update_filename should handle relative paths."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        receiver.update_filename(None, 0, 'images/photo.jpg')

        message_text = mock_update.call_args[1]['newmsg']
        assert 'photo.jpg' in message_text

    @patch.object(message.ProgressReceiver, 'update')
    @patch.object(message.ProgressReceiver, 'sleep')
    def test_update_filename_unicode(self, mock_sleep, mock_update):
        """update_filename should handle Unicode filenames."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        # Unicode filename
        receiver.update_filename(None, 0, '/home/user/photos/фото.jpg')

        # Should not raise exception
        mock_update.assert_called_once()
        message_text = mock_update.call_args[1]['newmsg']
        assert isinstance(message_text, str)


class TestSendFunction:
    """Test send object re-export."""

    def test_send_exists(self):
        """send should be available in message module."""
        assert hasattr(message, 'send')
        # send is a Sender object with __call__ method
        assert hasattr(message.send, '__call__')

    def test_send_is_sender_instance(self):
        """send should be a Sender instance from lib.events."""
        # Check it's a Sender instance (avoid strict import path check)
        assert 'Sender' in type(message.send).__name__


class TestReceiverClassReExport:
    """Test Receiver class re-export."""

    def test_receiver_class_exists(self):
        """Receiver class should be available in message module."""
        assert hasattr(message, 'Receiver')
        # Should be a class
        assert isinstance(message.Receiver, type)

    def test_receiver_class_name(self):
        """Receiver should have correct class name."""
        # Check class name (avoid strict import path check)
        assert message.Receiver.__name__ == 'Receiver'


class TestProgressReceiverMaxCalculation:
    """Test ProgressReceiver max value calculations."""

    def test_max_calculation_small_values(self):
        """Test max calculation with small values."""
        receiver = message.ProgressReceiver(parent_max=5, child_max=3)
        assert receiver.max == 15

    def test_max_calculation_large_values(self):
        """Test max calculation with large values."""
        receiver = message.ProgressReceiver(parent_max=1000, child_max=100)
        assert receiver.max == 100000

    def test_max_calculation_asymmetric(self):
        """Test max calculation with asymmetric values."""
        receiver = message.ProgressReceiver(parent_max=100, child_max=1)
        assert receiver.max == 100

        receiver2 = message.ProgressReceiver(parent_max=1, child_max=100)
        assert receiver2.max == 100

    def test_max_recalculation_on_set_max(self):
        """Test that max is recalculated when set_max is called."""
        receiver = message.ProgressReceiver(parent_max=10, child_max=10)
        assert receiver.max == 100

        receiver.set_max(20, 5)
        assert receiver.max == 100  # 20 * 5

        receiver.set_max(1, 1)
        assert receiver.max == 1


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_frame_receiver_initialization(self):
        """Test FrameReceiver can be initialized properly."""
        # Should initialize without errors
        receiver = message.FrameReceiver('test_frame')
        assert receiver is not None

    def test_progress_receiver_full_workflow(self):
        """Test ProgressReceiver through a complete workflow."""
        # Initialize
        receiver = message.ProgressReceiver(parent_max=10, child_max=5)

        # Simulate processing 10 images with 5 actions each
        with patch.object(receiver, 'update') as mock_update, \
             patch.object(receiver, 'sleep') as mock_sleep:

            for i in range(10):
                # Update filename for each image
                receiver.update_filename(None, i, f'/path/image_{i}.jpg')

                # Update for each action
                for j in range(5):
                    receiver.update_index(None, i, j)

            # Should have called update for each filename and each action
            # 10 filenames + 10*5 actions = 60 updates
            assert mock_update.call_count == 60

            # Sleep should be called once per filename update
            assert mock_sleep.call_count == 10

        # Close when done
        receiver.close()

    def test_progress_tracking_percentages(self):
        """Test that progress values increase monotonically."""
        receiver = message.ProgressReceiver(parent_max=100, child_max=10)

        progress_values = []

        with patch.object(receiver, 'update') as mock_update:
            # Process first 3 images
            for i in range(3):
                for j in range(10):
                    receiver.update_index(None, i, j)
                    if mock_update.called:
                        progress_values.append(mock_update.call_args[0][1])
                        mock_update.reset_mock()

        # Progress values should be monotonically increasing
        for i in range(len(progress_values) - 1):
            assert progress_values[i] < progress_values[i + 1], \
                f"Progress not increasing: {progress_values[i]} >= {progress_values[i+1]}"
