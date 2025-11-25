# from django.contrib import admin
# from .models import Restaurant

# @admin.register(Restaurant)
# class RestaurantAdmin(admin.ModelAdmin):
    # list_display = ('id','name', 'email', 'phone', 'is_active', 'created_at')
#     list_filter = ('is_active', 'created_at')
#     search_fields = ('name', 'email', 'phone', 'address')
#     readonly_fields = ('created_at', 'updated_at')
# restaurants/admin.py
# restaurants/admin.py

from django.contrib import admin
from .models import Restaurant

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user


        # superuser / superadmin: see all
        if user.is_superuser or getattr(user, "is_superadmin", False):
            return qs
        
        

        # restaurant admin: only their restaurant(s)
        if getattr(user, "is_restaurant_admin", False):
            return qs.filter(owner=user)

        # others: nothing
        return qs.none()

    def has_view_permission(self, request, obj=None):
        user = request.user

        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True

        if not getattr(user, "is_restaurant_admin", False):
            return False

        if obj is None:
            # change list view; rows already filtered in get_queryset
            return True

        return obj.owner_id == user.id

    def has_change_permission(self, request, obj=None):
        user = request.user

        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True

        if not getattr(user, "is_restaurant_admin", False):
            return False

        if obj is None:
            # allow loading list page; edits are row-checked
            return True
        return obj.owner_id == user.id

    def has_add_permission(self, request):
        # usually only superadmins create restaurants
        user = request.user
        return user.is_superuser or getattr(user, "is_superadmin", False)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    list_display = ('id','name','phone', 'is_active', 'created_at')

