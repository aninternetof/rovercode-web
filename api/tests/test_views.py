"""API test views."""
from unittest.mock import patch

from test_plus.test import TestCase

import dateutil.parser
import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from oauth2_provider.models import Application
from mission_control.models import BlockDiagram
from mission_control.models import Rover
from mission_control.models import Tag


class BaseAuthenticatedTestCase(TestCase):
    """Base class for all authenticated test cases."""

    def setUp(self):
        """Initialize the tests."""
        self.admin = get_user_model().objects.create_user(
            username='administrator',
            email='admin@example.com',
            password='password'
        )
        self.client = APIClient()

    def authenticate(self):
        """Authenticate the test client."""
        credentials = {
            'username': 'administrator',
            'password': 'password',
        }
        response = self.client.post(
            reverse('api:api-token-auth'),
            data=json.dumps(credentials),
            content_type='application/json')

        self.assertEqual(200, response.status_code)

        self.client.credentials(
            HTTP_AUTHORIZATION='JWT {0}'.format(response.json()['token']))


class TestRoverViewSet(BaseAuthenticatedTestCase):
    """Tests the rover API view."""

    def test_rover_create(self):
        """Test the rover registration interface."""
        self.authenticate()
        user1 = self.make_user('user1')
        user2 = self.make_user('user2')
        rover_info = {'name': 'Curiosity', 'local_ip': '192.168.0.10',
                      'shared_users': [user1.username, user2.username]}
        default_rover_config = {'some_setting': 'foobar'}
        # Create the rover
        with self.settings(DEFAULT_ROVER_CONFIG=default_rover_config):
            response = self.client.post(
                reverse('api:v1:rover-list'), rover_info)
        id = response.data['id']
        self.assertIn('client_id', response.data)
        self.assertIn('client_secret', response.data)
        creation_time = dateutil.parser.parse(response.data['last_checkin'])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['config'], default_rover_config)
        self.assertIn(user1.username, response.data['shared_users'])
        self.assertIn(user2.username, response.data['shared_users'])

        application = Application.objects.get(client_id=response.data['client_id'])
        self.assertEqual(application.user.id, self.admin.id)

        # Try and fail to create the same rover again
        response = self.client.post(reverse('api:v1:rover-list'), rover_info)
        self.assertEqual(response.status_code, 400)

        # Update the rover
        response = self.client.put(
            reverse('api:v1:rover-detail', kwargs={'pk': id}),
            json.dumps(rover_info), content_type='application/json'
        )
        checkin_time = dateutil.parser.parse(response.data['last_checkin'])
        self.assertEqual(response.status_code, 200)
        self.assertGreater(checkin_time, creation_time)

    def test_rover_create_custom_config(self):
        """Test the rover registration with a custom config."""
        self.authenticate()
        config = {'some_field': True}
        rover_info = {'name': 'Curiosity', 'local_ip': '192.168.0.10',
                      'config': json.dumps(config)}
        # Create the rover
        response = self.client.post(
            reverse('api:v1:rover-list'), rover_info)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['config'], config)

    def test_rover_create_invalid_config(self):
        """Test the rover registration with invalid config."""
        self.authenticate()
        rover_info = {'name': 'Curiosity', 'local_ip': '192.168.0.10',
                      'config': 'not-valid-json'}

        # Create the rover
        response = self.client.post(
            reverse('api:v1:rover-list'), rover_info)
        self.assertEqual(response.status_code, 400)

    def test_rover_create_invalid_shared(self):
        """Test the rover registration with invalid shared user."""
        self.authenticate()
        rover_info = {'name': 'Curiosity', 'local_ip': '192.168.0.10',
                      'shared_users': ['unknown']}

        # Create the rover
        response = self.client.post(
            reverse('api:v1:rover-list'), rover_info)
        self.assertEqual(response.status_code, 400)
        self.assertIn('shared_users', response.data)

    def test_rover(self):
        """Test the rover view displays the correct items."""
        self.authenticate()
        rover = Rover.objects.create(
            name='rover',
            owner=self.admin,
            local_ip='8.8.8.8'
        )
        other_user = self.make_user()
        Rover.objects.create(
            name='rover2',
            owner=other_user,
            local_ip='127.0.0.1'
        )
        other_rover = Rover.objects.create(
            name='shared',
            owner=other_user,
            local_ip='127.0.0.1'
        )
        rover.shared_users.add(other_user)
        other_rover.shared_users.add(self.admin)

        response = self.get(reverse('api:v1:rover-list'))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(2, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['name'], 'rover')
        self.assertEqual(response.json()['results'][0]['owner'], self.admin.id)
        self.assertEqual(response.json()['results'][0]['local_ip'], '8.8.8.8')
        self.assertListEqual(
            response.json()['results'][0]['shared_users'],
            [other_user.username]
        )
        self.assertEqual(response.json()['results'][1]['name'], 'shared')
        self.assertEqual(response.json()['results'][1]['owner'], other_user.id)
        self.assertEqual(response.json()['results'][1]['local_ip'], '127.0.0.1')
        self.assertListEqual(
            response.json()['results'][1]['shared_users'],
            [self.admin.username]
        )

    def test_rover_name_filter(self):
        """Test the rover view filters correctly on name."""
        self.authenticate()
        Rover.objects.create(
            name='rover',
            owner=self.admin,
            local_ip='8.8.8.8'
        )
        rover2 = Rover.objects.create(
            name='rover2',
            owner=self.admin,
            local_ip='8.8.8.8'
        )
        response = self.get(
            reverse('api:v1:rover-list') + '?name=' + rover2.name)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(1, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['name'], 'rover2')
        self.assertEqual(response.json()['results'][0]['owner'], self.admin.id)
        self.assertEqual(response.json()['results'][0]['local_ip'], '8.8.8.8')

    def test_rover_client_id_filter(self):
        """Test the rover view filters correctly on oauth application client id."""
        self.authenticate()
        Rover.objects.create(
            name='rover',
            owner=self.admin,
            local_ip='8.8.8.8',
            oauth_application = Application.objects.create(
                user=self.admin,
                authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
                client_type=Application.CLIENT_CONFIDENTIAL,
                name='rover'
            )
        )
        rover2 = Rover.objects.create(
            name='rover2',
            owner=self.admin,
            local_ip='8.8.8.8',
            oauth_application = Application.objects.create(
                user=self.admin,
                authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
                client_type=Application.CLIENT_CONFIDENTIAL,
                name='rover2'
            )
        )
        response = self.get(
            reverse('api:v1:rover-list') + '?client_id=' + rover2.oauth_application.client_id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(1, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['name'], 'rover2')
        self.assertEqual(response.json()['results'][0]['owner'], self.admin.id)
        self.assertEqual(response.json()['results'][0]['local_ip'], '8.8.8.8')

    def test_rover_update_remove_shared(self):
        """Test the rover update to remove shared user."""
        self.authenticate()
        other_user = self.make_user()
        rover = Rover.objects.create(
            name='rover',
            owner=self.admin,
            local_ip='8.8.8.8'
        )
        rover.shared_users.add(other_user)
        self.assertEqual(
            1, Rover.objects.get(id=rover.id).shared_users.count())

        # Remove the shared user
        data = {
            'shared_users': [],
        }
        response = self.client.patch(
            reverse('api:v1:rover-detail', kwargs={'pk': rover.pk}),
            json.dumps(data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            0, Rover.objects.get(id=rover.id).shared_users.count())

    def test_rover_update_add_shared(self):
        """Test the rover update to add shared user."""
        self.authenticate()
        user1 = self.make_user('user1')
        user2 = self.make_user('user2')
        rover = Rover.objects.create(
            name='rover',
            owner=self.admin,
            local_ip='8.8.8.8'
        )
        self.assertEqual(
            0, Rover.objects.get(id=rover.id).shared_users.count())

        # Add the shared user
        data = {
            'shared_users': [user1.username, user2.username],
        }
        response = self.client.patch(
            reverse('api:v1:rover-detail', kwargs={'pk': rover.pk}),
            json.dumps(data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            2, Rover.objects.get(id=rover.id).shared_users.count())

        response = self.client.get(
            reverse('api:v1:rover-detail', kwargs={'pk': rover.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(user1.username, response.data['shared_users'])
        self.assertIn(user2.username, response.data['shared_users'])

    def test_rover_update_add_invalid_shared(self):
        """Test the rover update to add invalid shared user."""
        self.authenticate()
        rover = Rover.objects.create(
            name='rover',
            owner=self.admin,
            local_ip='8.8.8.8'
        )
        self.assertEqual(
            0, Rover.objects.get(id=rover.id).shared_users.count())

        # Add the invalid shared user
        data = {
            'shared_users': ['unknown'],
        }
        response = self.client.patch(
            reverse('api:v1:rover-detail', kwargs={'pk': rover.pk}),
            json.dumps(data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('shared_users', response.data)
        self.assertEqual(
            0, Rover.objects.get(id=rover.id).shared_users.count())

    def test_rover_update_add_unauthorized_user(self):
        """Test the rover update by an unauthorized user."""
        self.authenticate()
        user1 = self.make_user('user1')
        user2 = self.make_user('user2')
        rover = Rover.objects.create(
            name='rover',
            owner=user1,
            local_ip='8.8.8.8'
        )
        rover.shared_users.add(user2)
        self.assertEqual(
            1, Rover.objects.get(id=rover.id).shared_users.count())

        # Add the invalid shared user
        data = {
            'shared_users': [self.admin.username],
        }
        response = self.client.patch(
            reverse('api:v1:rover-detail', kwargs={'pk': rover.pk}),
            json.dumps(data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            1, Rover.objects.get(id=rover.id).shared_users.count())

    def test_rover_not_logged_in(self):
        """Test the rover view denies unauthenticated user."""
        response = self.get(reverse('api:v1:rover-list'))
        self.assertEqual(401, response.status_code)


class TestBlockDiagramViewSet(BaseAuthenticatedTestCase):
    """Tests the block diagram API view."""

    def setUp(self):
        """Initialize the tests."""
        super().setUp()
        self.patcher = patch('requests.post')
        self.mock_post = self.patcher.start()
        self.mock_post.return_value.status_code = 404

    def tearDown(self):
        """Tear down the tests."""
        super().tearDown()
        self.patcher.stop()

    def test_bd(self):
        """Test the block diagram API view displays the correct items."""
        self.authenticate()
        user = self.make_user()
        bd1 = BlockDiagram.objects.create(
            user=self.admin,
            name='test',
            content='<xml></xml>'
        )
        bd2 = BlockDiagram.objects.create(
            user=user,
            name='test1',
            content='<xml></xml>'
        )
        response = self.get(reverse('api:v1:blockdiagram-list'))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(2, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['id'], bd1.id)
        self.assertDictEqual(response.json()['results'][0]['user'], {
            'username': self.admin.username,
        })
        self.assertEqual(response.json()['results'][0]['name'], 'test')
        self.assertEqual(
            response.json()['results'][0]['content'], '<xml></xml>')
        self.assertEqual(response.json()['results'][1]['id'], bd2.id)
        self.assertDictEqual(response.json()['results'][1]['user'], {
            'username': user.username,
        })
        self.assertEqual(response.json()['results'][1]['name'], 'test1')
        self.assertEqual(
            response.json()['results'][1]['content'], '<xml></xml>')

    def test_bd_user_filter(self):
        """Test the block diagram API view filters on user correctly."""
        self.authenticate()
        user1 = self.make_user('user1')
        BlockDiagram.objects.create(
            user=self.admin,
            name='test1',
            content='<xml></xml>'
        )
        bd = BlockDiagram.objects.create(
            user=user1,
            name='test2',
            content='<xml></xml>'
        )
        response = self.get(
            reverse('api:v1:blockdiagram-list') +
            '?user=' + str(user1.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(1, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['id'], bd.id)
        self.assertDictEqual(response.json()['results'][0]['user'], {
            'username': user1.username,
        })
        self.assertEqual(response.json()['results'][0]['name'], 'test2')
        self.assertEqual(
            response.json()['results'][0]['content'], '<xml></xml>')

    def test_bd_user_exclude_filter(self):
        """Test the block diagram API view filters on user exclude correctly."""
        self.authenticate()
        user1 = self.make_user('user1')
        bd = BlockDiagram.objects.create(
            user=self.admin,
            name='test1',
            content='<xml></xml>'
        )
        BlockDiagram.objects.create(
            user=user1,
            name='test2',
            content='<xml></xml>'
        )
        response = self.get(
            reverse('api:v1:blockdiagram-list') +
            '?user__not=' + str(user1.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(1, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['id'], bd.id)
        self.assertDictEqual(response.json()['results'][0]['user'], {
            'username': self.admin.username,
        })
        self.assertEqual(response.json()['results'][0]['name'], 'test1')
        self.assertEqual(
            response.json()['results'][0]['content'], '<xml></xml>')

    def test_bd_not_logged_in(self):
        """Test the block diagram view denies unauthenticated user."""
        response = self.get(reverse('api:v1:blockdiagram-list'))
        self.assertEqual(401, response.status_code)

    def test_bd_create(self):
        """Test creating block diagram sets user."""
        self.authenticate()
        data = {
            'name': 'test',
            'content': '<xml></xml>',
            'owner_tags': ['tag1', 'tag 2'],
        }
        response = self.client.post(
            reverse('api:v1:blockdiagram-list'), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(BlockDiagram.objects.last().user.id, self.admin.id)
        self.assertEqual(BlockDiagram.objects.last().name, data['name'])
        model_tags = [t.name for t in BlockDiagram.objects.last().tags.all()]
        self.assertIn('tag1', model_tags)
        self.assertIn('tag 2', model_tags)

    def test_bd_create_name_exist(self):
        """Test creating block diagram when name already exists."""
        BlockDiagram.objects.create(
            user=self.admin,
            name='test',
            content='<xml></xml>'
        )

        self.authenticate()
        data = {
            'name': 'test',
            'content': '<xml></xml>'
        }
        response = self.client.post(
            reverse('api:v1:blockdiagram-list'), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(BlockDiagram.objects.last().user.id, self.admin.id)
        self.assertEqual(
            BlockDiagram.objects.last().name, data['name'] + ' (1)')

    def test_bd_create_name_exist_with_number(self):
        """Test creating block diagram when name already exists with number."""
        user1 = self.make_user('user1')
        BlockDiagram.objects.create(
            user=self.admin,
            name='test (1) (2)',
            content='<xml></xml>'
        )
        BlockDiagram.objects.create(
            user=user1,
            name='test (1) (3)',
            content='<xml></xml>'
        )

        self.authenticate()
        data = {
            'name': 'test (1) (2)',
            'content': '<xml></xml>'
        }
        response = self.client.post(
            reverse('api:v1:blockdiagram-list'), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(BlockDiagram.objects.last().user.id, self.admin.id)
        self.assertEqual(BlockDiagram.objects.last().name, 'test (1) (3)')

    def test_bd_update_as_valid_user(self):
        """Test updating block diagram as owner."""
        self.authenticate()
        bd = BlockDiagram.objects.create(
            user=self.admin,
            name='test1',
            content='<xml></xml>'
        )
        data = {
            'name': 'test',
        }
        response = self.client.patch(
            reverse(
                'api:v1:blockdiagram-detail', kwargs={'pk': bd.pk}),
            json.dumps(data), content_type='application/json')
        self.assertEqual(200, response.status_code)
        self.assertEqual(BlockDiagram.objects.last().user.id, self.admin.id)
        self.assertEqual(BlockDiagram.objects.last().name, 'test')

    def test_bd_update_as_invalid_user(self):
        """Test updating block diagram as another user."""
        self.authenticate()
        user = self.make_user()
        bd = BlockDiagram.objects.create(
            user=user,
            name='test1',
            content='<xml></xml>'
        )
        data = {
            'name': 'test',
        }
        response = self.client.patch(
            reverse(
                'api:v1:blockdiagram-detail', kwargs={'pk': bd.pk}),
            json.dumps(data), content_type='application/json')
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            response.content,
            b'["You may only modify your own block diagrams"]')
        self.assertEqual(BlockDiagram.objects.last().user.id, user.id)
        self.assertEqual(BlockDiagram.objects.last().name, 'test1')

    def test_bd_update_add_tags(self):
        """Test updating block diagram to add tags."""
        self.authenticate()
        bd = BlockDiagram.objects.create(
            user=self.admin,
            name='test',
            content='<xml></xml>',
        )
        self.assertEqual(0, BlockDiagram.objects.get(id=bd.id).tags.count())

        # Add the tag
        data = {
            'owner_tags': ['test'],
        }
        response = self.client.patch(
            reverse('api:v1:blockdiagram-detail', kwargs={'pk': bd.pk}),
            json.dumps(data), content_type='application/json')
        self.assertEqual(200, response.status_code)
        self.assertEqual(BlockDiagram.objects.last().user.id, self.admin.id)
        self.assertEqual(BlockDiagram.objects.last().name, 'test')
        self.assertEqual(1, BlockDiagram.objects.last().tags.count())

        response = self.client.get(
            reverse('api:v1:blockdiagram-detail', kwargs={'pk': bd.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('test', response.data['tags'])

    def test_bd_update_remove_tags(self):
        """Test updating block diagram to remove tags."""
        self.authenticate()
        bd = BlockDiagram.objects.create(
            user=self.admin,
            name='test',
            content='<xml></xml>',
        )
        tag = Tag.objects.create(name='tag1')
        bd.owner_tags.add(tag)
        self.assertEqual(1, BlockDiagram.objects.get(id=bd.id).tags.count())

        # Remove the tag
        data = {
            'owner_tags': [],
        }
        response = self.client.patch(
            reverse('api:v1:blockdiagram-detail', kwargs={'pk': bd.pk}),
            json.dumps(data), content_type='application/json')
        self.assertEqual(200, response.status_code)
        self.assertEqual(BlockDiagram.objects.last().user.id, self.admin.id)
        self.assertEqual(BlockDiagram.objects.last().name, 'test')
        self.assertEqual(0, BlockDiagram.objects.last().tags.count())

    def test_bd_update_add_tag_too_long(self):
        """Test updating block diagram to add tag that is too long."""
        self.authenticate()
        bd = BlockDiagram.objects.create(
            user=self.admin,
            name='test',
            content='<xml></xml>',
        )
        self.assertEqual(0, BlockDiagram.objects.get(id=bd.id).tags.count())

        # Add the tag
        data = {
            'owner_tags': ['a'*100],
        }
        response = self.client.patch(
            reverse('api:v1:blockdiagram-detail', kwargs={'pk': bd.pk}),
            json.dumps(data), content_type='application/json')
        self.assertEqual(400, response.status_code)
        self.assertEqual(0, BlockDiagram.objects.get(id=bd.id).tags.count())

    def test_bd_update_add_tag_too_short(self):
        """Test updating block diagram to add tag that is too short."""
        self.authenticate()
        bd = BlockDiagram.objects.create(
            user=self.admin,
            name='test',
            content='<xml></xml>',
        )
        self.assertEqual(0, BlockDiagram.objects.get(id=bd.id).tags.count())

        # Add the tag
        data = {
            'owner_tags': ['a'],
        }
        response = self.client.patch(
            reverse('api:v1:blockdiagram-detail', kwargs={'pk': bd.pk}),
            json.dumps(data), content_type='application/json')
        self.assertEqual(400, response.status_code)
        self.assertEqual(0, BlockDiagram.objects.get(id=bd.id).tags.count())

    def test_bd_tag_filter(self):
        """Test the block diagram API view filters on tags correctly."""
        self.authenticate()
        user1 = self.make_user('user1')
        bd1 = BlockDiagram.objects.create(
            user=self.admin,
            name='test1',
            content='<xml></xml>'
        )
        bd2 = BlockDiagram.objects.create(
            user=user1,
            name='test2',
            content='<xml></xml>'
        )
        tag1 = Tag.objects.create(name='tag1')
        tag2 = Tag.objects.create(name='tag2')
        tag3 = Tag.objects.create(name='tag3')
        tag4 = Tag.objects.create(name='tag4')
        bd1.owner_tags.set([tag1, tag2])
        bd1.admin_tags.add(tag3)
        bd2.owner_tags.add(tag4)
        bd2.admin_tags.add(tag3)

        response = self.get(
            reverse('api:v1:blockdiagram-list') + '?tag={},{}'.format(
                tag1.name, tag2.name))

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(1, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['id'], bd1.id)
        self.assertDictEqual(response.json()['results'][0]['user'], {
            'username': self.admin.username,
        })
        self.assertEqual(response.json()['results'][0]['name'], 'test1')
        self.assertEqual(
            response.json()['results'][0]['content'], '<xml></xml>')

        response = self.get(
            reverse('api:v1:blockdiagram-list') + '?tag=' + tag3.name)

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(2, len(response.json()['results']))

        response = self.get(
            reverse('api:v1:blockdiagram-list') + '?tag={},{}'.format(
                tag2.name, tag3.name))

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(2, len(response.json()['results']))

        response = self.get(
            reverse('api:v1:blockdiagram-list') + '?owner_tags={},{}'.format(
                tag4.name, tag3.name))

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(1, len(response.json()['results']))
        self.assertEqual(response.json()['results'][0]['name'], 'test2')

        response = self.get(
            reverse('api:v1:blockdiagram-list') + '?admin_tags={}'.format(
                tag3.name))

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(2, len(response.json()['results']))

        response = self.get(
            reverse('api:v1:blockdiagram-list') + '?tag=' + 'nothing')

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()['total_pages'])
        self.assertEqual(0, len(response.json()['results']))

    def test_profanity_check(self):
        """Test that email is sent when profanity detected."""
        self.mock_post.return_value.status_code = 200
        self.mock_post.return_value.json.return_value = {
            'censored': 'profane-word',
            'original_profane_word': 'profane-word',
            'uncensored': 'profane-word',
        }

        self.assertEqual(0, len(mail.outbox))

        self.authenticate()
        data = {
            'name': 'profane-word',
            'content': '<xml></xml>',
        }
        response = self.client.post(reverse('api:v1:blockdiagram-list'), data)
        self.assertEqual(201, response.status_code)

        self.assertEqual(1, len(mail.outbox))
        self.assertIn(self.admin.username, mail.outbox[0].body)
        self.assertIn('profane-word', mail.outbox[0].body)

    @patch('mission_control.signals.handlers.LOGGER')
    def test_profanity_check_failure(self, mock_logger):
        """Test that error is logged if unable to contact profanity check."""
        self.assertEqual(0, len(mail.outbox))

        self.authenticate()
        data = {
            'name': 'profane-word',
            'content': '<xml></xml>',
        }
        response = self.client.post(reverse('api:v1:blockdiagram-list'), data)
        self.assertEqual(201, response.status_code)

        self.assertEqual(0, len(mail.outbox))
        self.assertTrue(mock_logger.error.called)
        self.assertEqual(404, mock_logger.error.call_args[0][1])

    def test_profanity_check_flag(self):
        """Test that program is flagged correctly."""
        profane_response = {
            'censored': 'profane-word',
            'original_profane_word': 'profane-word',
            'uncensored': 'profane-word',
        }
        normal_response = {
            'censored': 'word',
            'original_profane_word': None,
            'uncensored': 'word',
        }
        self.mock_post.return_value.status_code = 200
        self.mock_post.return_value.json.side_effect = [
            profane_response,
            normal_response,
            profane_response,
        ]

        self.assertEqual(0, len(mail.outbox))

        self.authenticate()
        data = {
            'name': 'profane-word',
            'content': '<xml></xml>',
        }
        response = self.client.post(reverse('api:v1:blockdiagram-list'), data)
        self.assertEqual(201, response.status_code)

        bd = BlockDiagram.objects.first()
        self.assertTrue(bd.flagged)

        data = {
            'name': 'word',
            'content': '<xml></xml>',
        }
        response = self.client.patch(
            reverse('api:v1:blockdiagram-detail', kwargs={'pk': bd.id}), data)
        self.assertEqual(200, response.status_code)

        bd = BlockDiagram.objects.first()
        self.assertFalse(bd.flagged)

        data = {
            'name': 'profane-word',
            'content': '<xml></xml>',
        }
        response = self.client.patch(
            reverse('api:v1:blockdiagram-detail', kwargs={'pk': bd.id}), data)
        self.assertEqual(200, response.status_code)

        bd = BlockDiagram.objects.first()
        self.assertTrue(bd.flagged)
