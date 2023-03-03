'''
Tests for Tags API
'''
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag
from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    '''Create and return a tag detail url'''
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='user@example.com', password='password123'):
    '''Create and return a new user'''
    return get_user_model().objects.create_user(email, password)


class PublicTagsAPITests(TestCase):
    '''Test unauthenticated API requests'''

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        '''Test auth is required for retrieving tags'''
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITests(TestCase):
    '''Tests for authenticated Tags API requests'''

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags_for_user(self):
        '''Test retrieving tags for a user'''
        Tag.objects.create(user=self.user, name='Mexican')
        Tag.objects.create(user=self.user, name='Italian')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        '''Test list of tags is limited to authenticated user'''
        other_user = create_user(
            email='otheruser@example.com',
            password='otherpassword123',
        )
        Tag.objects.create(user=other_user, name='Dessert')
        tag = Tag.objects.create(user=self.user, name='Appetizer')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tags(self):
        '''Test updating a tag'''
        tag = Tag.objects.create(user=self.user, name='Appetizer')

        payload = {'name': 'Dessert'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tags(self):
        '''Test deleting a tag'''
        tag = Tag.objects.create(user=self.user, name='Entree')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(user=self.user).exists())
