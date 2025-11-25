from rest_framework import serializers
from .models import MenuItem
from restaurants.serializers import RestaurantSerializer
from django.db import IntegrityError, transaction
class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            'restaurant', 'name', 'description', 
            'price', 'available', 'category', 'currency',
            'is_vegetarian', 'is_vegan', 'ingredients',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['restaurant', 'created_at', 'updated_at']

    def create(self, validated_data):
        with transaction.atomic():
            menu = MenuItem(**validated_data)
            menu.save()
            return menu
