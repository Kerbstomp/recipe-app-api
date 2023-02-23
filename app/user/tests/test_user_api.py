'''
Tests for the User API
'''
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicUserAPITests(TestCase):
    '''Tests the public features of the User API'''

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        '''Tests creating a user successfully'''
        payload = {
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'test name',
        }

        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_create_user_with_email_exists_error(self):
        '''Tests error if user with email already exists'''
        payload = {
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'test name',
        }
        create_user(**payload)

        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_password_too_short_error(self):
        '''Tests error if users password is too short (< 5 chars)'''
        payload = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'test name',
        }

        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        '''Test generates token for valid credentials'''
        user_details = {
            'name': 'test name',
            'email': 'test@example.com',
            'password': 'password123',
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        '''Test returns error if credentials are invalid'''
        user_details = {
            'name': 'test name',
            'email': 'test@example.com',
            'password': 'password123',
        }
        create_user(**user_details)

        payload = {
            'email': 'test@example.com',
            'password': 'badpassword',
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        '''Test authentication is required for users'''
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserAPITests(TestCase):
    '''Tests the public features of the User API'''

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='password123',
            name='test name',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        '''Test retrieving profile for logged in user'''
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'email': self.user.email,
            'name': self.user.name,
        })

    def test_post_me_not_allowed(self):
        '''Test post is not allowed for me endpoint'''
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        '''Test updating user profile for authenticated user'''
        payload = {
            'name': 'updated name',
            'password': 'newpassword123',
        }
        res = self.client.patch(ME_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
