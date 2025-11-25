# menu/admin.py
from django.contrib import admin
from .models import MenuItem
from .tasks import regenerate_menu_embeddings  # 👈 NEW


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "restaurant", "price", "available", "category")
    list_filter = ("available", "restaurant")
    search_fields = ("name", "description", "restaurant__name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("restaurant", "-category")

    # ---------- helper to trigger Celery ----------
    def _trigger_embeddings(self, restaurant_id):
        """
        Schedule a background task to regenerate embeddings
        for the given restaurant.
        """
        if restaurant_id:
            regenerate_menu_embeddings.delay(restaurant_id)

    # ---------- queryset scoping ----------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        # superuser / superadmin: see all menu items
        if user.is_superuser or getattr(user, "is_superadmin", False):
            return qs

        # restaurant admin: only items for their restaurant(s)
        if getattr(user, "is_restaurant_admin", False):
            return qs.filter(restaurant__owner=user)

        # others: nothing
        return qs.none()

    # ---------- view permission ----------
    def has_view_permission(self, request, obj=None):
        user = request.user

        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True

        if not getattr(user, "is_restaurant_admin", False):
            return False

        if obj is None:
            # changelist view; rows already filtered in get_queryset
            return True

        # Only view items belonging to their own restaurant(s)
        return obj.restaurant.owner_id == user.id

    # ---------- change permission ----------
    def has_change_permission(self, request, obj=None):
        user = request.user

        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True

        if not getattr(user, "is_restaurant_admin", False):
            return False

        if obj is None:
            # allow list page; individual rows checked below
            return True

        return obj.restaurant.owner_id == user.id

    # ---------- add permission ----------
    def has_add_permission(self, request):
        user = request.user
        # Usually: superadmins + restaurant admins can add menu items
        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True
        if getattr(user, "is_restaurant_admin", False):
            return True
        return False

    # ---------- delete permission ----------
    def has_delete_permission(self, request, obj=None):
        # Same rule as change_permission
        return self.has_change_permission(request, obj)

    # ---------- hook admin SAVE -> Celery ----------
    def save_model(self, request, obj, form, change):
        """
        Called when a single MenuItem is created/updated in admin.
        """
        super().save_model(request, obj, form, change)
        # After the item is saved, regenerate that restaurant's embeddings
        self._trigger_embeddings(obj.restaurant_id)

    # ---------- hook admin SINGLE DELETE -> Celery ----------
    def delete_model(self, request, obj):
        """
        Called when a single MenuItem is deleted from its detail page.
        """
        restaurant_id = obj.restaurant_id
        super().delete_model(request, obj)
        self._trigger_embeddings(restaurant_id)

    # ---------- hook admin BULK DELETE -> Celery ----------
    def delete_queryset(self, request, queryset):
        """
        Called when multiple MenuItems are deleted via the changelist
        (checkbox 'Delete selected menu items').
        We dedupe restaurant_ids so each restaurant gets only one task.
        """
        restaurant_ids = set(queryset.values_list("restaurant_id", flat=True))
        super().delete_queryset(request, queryset)

        for rid in restaurant_ids:
            self._trigger_embeddings(rid)
