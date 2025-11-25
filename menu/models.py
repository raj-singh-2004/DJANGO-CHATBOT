# menu/models.py
from django.db import models
from restaurants.models import Restaurant

class MenuItem(models.Model):
    # Keep it small; add more ISO 4217 codes later if you need to.
    CURRENCY_CHOICES = [
        ("INR", "Indian Rupee"),
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
    ]

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="menu_items"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    

    # NEW
    category = models.CharField(max_length=50, blank=True, db_index=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="INR")
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    ingredients = models.JSONField(default=list, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["restaurant"]
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"
        indexes = [
            models.Index(fields=["restaurant", "name"]),
        ]
        # Optional: vegan implies vegetarian
        # constraints = [
        #     models.CheckConstraint(
        #         name="vegan_implies_vegetarian",
        #         check=~models.Q(is_vegan=True) | models.Q(is_vegetarian=True),
        #     ),
        # ]

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"
