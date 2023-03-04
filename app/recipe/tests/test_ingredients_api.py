'''
Tests for Ingredients API
'''
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    '''Create and return ingredient detail url'''
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com', password='password123'):
    '''Create and return a new user'''
    return get_user_model().objects.create_user(email, password)


class PublicIngredientsAPITest(TestCase):
    '''Test unauthenticated API requests'''

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        '''Test auth is required for retrieving ingredients'''
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsAPITest(TestCase):
    '''Tests for authenticated API requests'''

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_ingredients_for_user(self):
        '''Test retrieving ingredients'''
        Ingredient.objects.create(user=self.user, name='Chicken')
        Ingredient.objects.create(user=self.user, name='Tomato')

        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_ingredients_limited_to_user(self):
        '''Test only ingredients associated to authenticated user returned'''
        other_user = create_user(
            email='otheruser@example.com',
            password='otherpassword123',
        )
        Ingredient.objects.create(user=other_user, name='Beef')
        ingredient = Ingredient.objects.create(user=self.user, name='Chicken')

        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        '''Test updating an ingredient'''
        ingredient = Ingredient.objects.create(user=self.user, name='Chicken')

        payload = {'name': 'Turkey'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        '''Test deleting an ingredient'''
        ingredient = Ingredient.objects.create(user=self.user, name='Chicken')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(user=self.user).exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        '''Test listing ingredients by those assigned to recipes'''
        ingredient1 = Ingredient.objects.create(user=self.user, name='Apple')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Turkey')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Sample title',
            price=Decimal('5.99'),
            time_minutes=5,
        )
        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(ingredient1)
        s2 = IngredientSerializer(ingredient2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        '''Test filtered ingredients return a unique list'''
        ingredient = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Beans')
        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Sample title',
            time_minutes=10,
            price=Decimal('7.00'),
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Another title',
            time_minutes=60,
            price=Decimal('20.99'),
        )
        recipe1.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
