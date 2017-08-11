"""Mission Control test utils."""
from test_plus.test import TestCase

from mission_control.models import Rover
from mission_control.utils import remove_old_rovers

import time
from datetime import timedelta


class TestRemoveOldRovers(TestCase):
    """Tests removing old rovers."""

    def test_rover(self):
        """Test the remove_old_rovers method."""
        Rover.objects.create(
            name='rover',
            owner=self.make_user(username='user1'),
            local_ip='8.8.8.8'
        )
        self.assertEqual(1, Rover.objects.count())
        time.sleep(1)
        Rover.objects.create(
            name='rover2',
            owner=self.make_user(username='user2'),
            local_ip='8.8.8.8'
        )
        remove_old_rovers(timedelta(seconds=-1))
        self.assertEqual(1, Rover.objects.count())
