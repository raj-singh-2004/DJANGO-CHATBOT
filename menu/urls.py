# menu/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MenuItemViewSet,ApiDemoView

router = DefaultRouter()
router.register(r"menu-items", MenuItemViewSet, basename="menuitem")

urlpatterns = [
    path("", include(router.urls)),
    path("demo/", ApiDemoView.as_view(), name="api-demo"),
]

