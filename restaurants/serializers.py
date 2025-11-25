from rest_framework import serializers
from .models import Restaurant

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'owner','name', 'address', 'phone', 'logo', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

        def create(self,validated_data):
            restaurant = Restaurant(**validated_data)
            restaurant.save()
            return restaurant

# restaurants/serializers.py
from rest_framework import serializers
from .models import Restaurant
from django.core.exceptions import ValidationError

def validate_pdf(file):
    name = (file.name or "").lower()
    if not name.endswith(".pdf"):
        raise ValidationError("Only PDF files are allowed.")
    ct = getattr(file, "content_type", None)
    if ct and ct not in ("application/pdf", "application/x-pdf"):
        raise ValidationError("Invalid content type; must be PDF.")
    return file

class RestaurantMenuPDFUploadSerializer(serializers.ModelSerializer):
    menu_pdf = serializers.FileField(write_only=True, validators=[validate_pdf])

    class Meta:
        model = Restaurant
        fields = ["menu_pdf"]

        





      



