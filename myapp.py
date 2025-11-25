# menu/services.py
import json
from typing import Union

from django.db import transaction

from menu.models import MenuItem
from restaurants.models import Restaurant


def build_menu_from_json(json_filename: str, restaurant: Union[Restaurant, int]):
    """
    Import menu items from JSON into MenuItem for a given restaurant.

    Flow:
    - Mark all existing items for that restaurant as available=False
    - For each JSON item (from MenuExtractor):
        - get_or_create by (restaurant, name, category)
        - update price, veg flags, ingredients/tags
        - set available=True
    - After commit, trigger a Celery task to regenerate embeddings
      so the chatbot stays in sync with the MenuItem table.
    """

    # Allow passing restaurant id instead of object
    if isinstance(restaurant, int):
        restaurant = Restaurant.objects.get(id=restaurant)

    # Load JSON
    with open(json_filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of items")

    with transaction.atomic():
        # Soft-deactivate all current items for this restaurant
        MenuItem.objects.filter(restaurant=restaurant).update(available=False)

        for item in data:
            name = (item.get("name") or "").strip()
            if not name:
                continue  # skip weird/empty entries

            category = item.get("category") or "General"
            price = item.get("price") or 0

            # Prefer explicit ingredients; fall back to 'tags' from extractor
            ingredients = item.get("ingredients")
            if not ingredients:
                ingredients = item.get("tags", [])

            mi, created = MenuItem.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                category=category,
                defaults={
                    "price": price,
                    "is_vegetarian": item.get("is_vegetarian", True),
                    "is_vegan": item.get("is_vegan", False),
                    "available": True,
                    "ingredients": ingredients,
                },
            )

            if not created:
                mi.price = price
                mi.is_vegetarian = item.get("is_vegetarian", mi.is_vegetarian)
                mi.is_vegan = item.get("is_vegan", getattr(mi, "is_vegan", False))

                if hasattr(mi, "contains_egg"):
                    mi.contains_egg = item.get(
                        "contains_egg", getattr(mi, "contains_egg", False)
                    )

                if hasattr(mi, "ingredients"):
                    mi.ingredients = ingredients

                mi.available = True
                mi.save()

        # Count how many items are now available for this restaurant
        total_items = MenuItem.objects.filter(
            restaurant=restaurant,
            available=True,
        ).count()

        # Only trigger embeddings regen if we actually have items
        if total_items > 0:
            from menu.tasks import regenerate_menu_embeddings

            def _trigger():
                # Run in background via Celery AFTER this transaction commits
                regenerate_menu_embeddings.delay(restaurant.id)

            transaction.on_commit(_trigger)

    print(
        f"Menu import done for restaurant {restaurant.id} from {json_filename} "
        f"(available items: {total_items})"
    )
