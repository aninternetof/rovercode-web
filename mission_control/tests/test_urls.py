"""Mission Control test urls."""
from django.core.urlresolvers import reverse, resolve

from test_plus.test import TestCase


class TestMissionControlURLs(TestCase):
    """Tests the urls."""

    def test_home_reverse(self):
        """mission-control:home should reverse to /mission-control/."""
        self.assertEqual(reverse('mission-control:home'), '/mission-control/')

    def test_home_resolve(self):
        """/mission-control/ should resolve to mission-control:home."""
        self.assertEqual(
            resolve('/mission-control/').view_name,
            'mission-control:home')

    def test_home_load_reverse(self):
        """mission-control:home should reverse to /mission-control/load/1."""
        self.assertEqual(
            reverse('mission-control:home_with_load', kwargs={'bd': 1}),
            '/mission-control/load/1/')

    def test_home_load_resolve(self):
        """/mission-control/load/1 should resolve to mission-control:home."""
        match = resolve('/mission-control/load/1/')
        self.assertEqual(match.view_name, 'mission-control:home_with_load')
        self.assertEqual(match.kwargs['bd'], '1')

    def test_bd_list_reverse(self):
        """mission-control:bd_list should reverse to /mission-control/bd-list/.""" # noqa
        self.assertEqual(
            reverse('mission-control:bd_list'),
            '/mission-control/bd-list/')

    def test_bd_list_resolve(self):
        """/mission-control/bd-list/ should resolve to mission-control:bd_list.""" # noqa
        self.assertEqual(
            resolve('/mission-control/bd-list/').view_name,
            'mission-control:bd_list')

    def test_rover_list_reverse(self):
        """mission-control:rover_list should reverse to /mission-control/rover-list/.""" # noqa
        self.assertEqual(
            reverse('mission-control:rover_list'),
            '/mission-control/rover-list/')

    def test_rover_list_resolve(self):
        """/mission-control/rover-list/ should resolve to mission-control:rover_list.""" # noqa
        self.assertEqual(
            resolve('/mission-control/rover-list/').view_name,
            'mission-control:rover_list')

    def test_rovers_reverse(self):
        """mission-control:rover-list should reverse to /mission-control/rovers/.""" # noqa
        self.assertEqual(
            reverse('mission-control:rover-list'),
            '/mission-control/rovers/')

    def test_rovers_resolve(self):
        """/mission-control/rovers/ should resolve to mission-control:rover-list.""" # noqa
        self.assertEqual(
            resolve('/mission-control/rovers/').view_name,
            'mission-control:rover-list')

    def test_block_diagrams_reverse(self):
        """mission-control:blockdiagram-list should reverse to /mission-control/block-diagrams/.""" # noqa
        self.assertEqual(
            reverse('mission-control:blockdiagram-list'),
            '/mission-control/block-diagrams/')

    def test_block_diagrams_resolve(self):
        """/mission-control/block-diagrams/ should resolve to mission-control:blockdiagram-list.""" # noqa
        self.assertEqual(
            resolve('/mission-control/block-diagrams/').view_name,
            'mission-control:blockdiagram-list')

    def test_rover_settings_reverse(self):
        """'mission-control:rover_settings' should reverse to /mission-control/rover-settings/.""" # noqa
        self.assertEqual(
            reverse('mission-control:rover_settings', kwargs={'pk': 1}),
            '/mission-control/rover-settings/1/')

    def test_rover_settings_resolve(self):
        """/mission-control/rover-settings/ should resolve to mission-control:rover_settings."""  # noqa
        self.assertEqual(
            resolve('/mission-control/rover-settings/1/').view_name,
            'mission-control:rover_settings')
