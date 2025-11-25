from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RestaurantViewSet,RestaurantMenuPDFUploadView,UploadAPIVIEw,MenuPDFUploadDemoView

router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('upload-restaurant-menu/',RestaurantMenuPDFUploadView.as_view()),
    path("upload/",UploadAPIVIEw.as_view()),
    path("upload-demo/", MenuPDFUploadDemoView.as_view(), name="menu-pdf-upload-demo"),
]

