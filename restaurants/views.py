from rest_framework import viewsets, permissions
from .models import Restaurant
from accounts.permissions import IsSuperAdmin, IsRestaurantAdmin,IsAdmin,IsAdminOrSuperAdmin
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .models import Restaurant

from django.conf import settings
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from restaurants.models import Restaurant
# from .menu_extractor import extract_menu_to_json  # <-- AI pipeline helper

import os, json
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from restaurants.models import Restaurant
from menu.models import MenuItem
from menu.serializers import MenuItemSerializer
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import os, json
from decimal import Decimal, InvalidOperation

from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from django.db import transaction
from decimal import Decimal, InvalidOperation
import os
from accounts.permissions import *
from .models import Restaurant
from restaurants.serializers import RestaurantSerializer, RestaurantMenuPDFUploadSerializer
from accounts.permissions import IsSuperAdmin
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Restaurant
from .serializers import RestaurantMenuPDFUploadSerializer
from menu.models import MenuItem
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from django.shortcuts import get_object_or_404

from restaurants.models import Restaurant
from .serializers import RestaurantMenuPDFUploadSerializer
from restaurants.menu_extractor import MenuExtractor, MenuItem

# 👇 import your extractor + asdict # adjust path if different
from dataclasses import asdict


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions, IsOwnerOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'superadmin':
            return Restaurant.objects.all()
        elif user.role == 'admin':
            return Restaurant.objects.filter(owner=user)
        return Restaurant.objects.none()
    
    
    
    def perform_create(self, serializer):
        if serializer.is_valid():
            serializer.save(owner=self.request.user)


class RestaurantMenuPDFUploadView(APIView):
    queryset = Restaurant.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = RestaurantMenuPDFUploadSerializer
    permission_classes=[IsAuthenticated,IsOwnerOrSuperAdmin]
    
    def post(self, request):
        restaurant = get_object_or_404(Restaurant, owner=request.user)
        self.check_object_permissions(request, restaurant)
        serializer = self.serializer_class(instance=restaurant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        restaurant = serializer.save()  # saving menu_pdf triggers the signal

        return Response(
            {
                "detail": "Menu PDF received; extraction scheduled.",
                "menu_pdf_url": restaurant.menu_pdf.url,
                "extract_status": restaurant.menu_extract_status,  # should be 'pending' → 'processing' → 'succeeded/failed'
            },
            status=status.HTTP_202_ACCEPTED,
        )


    
# views.py (or wherever your UploadAPIVIEw lives)



# class UploadAPIVIEw(APIView):
#     queryset = Restaurant.objects.all()
#     parser_classes = [MultiPartParser, FormParser]
#     serializer_class = RestaurantMenuPDFUploadSerializer
#     permission_classes = [IsAuthenticated, IsOwnerOrSuperAdmin]

#     def post(self, request):
#         # 1) Get the restaurant belonging to the logged-in user
#         restaurant = get_object_or_404(Restaurant, owner=request.user)
#         self.check_object_permissions(request, restaurant)

#         # 2) Bind & validate the uploaded file using the serializer
#         serializer = self.serializer_class(
#             instance=restaurant,  # update this restaurant
#             data=request.data,    # expects "menu_pdf" in form-data
#             partial=True,
#         )
#         serializer.is_valid(raise_exception=True)

#         # 3) Save the file onto the Restaurant (restaurant.menu_pdf)
#         restaurant = serializer.save()
#         pdf_file = restaurant.menu_pdf  # Django FieldFile

#         # Safety check
#         if not pdf_file:
#             return Response(
#                 {"detail": "menu_pdf was not uploaded or saved correctly."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         # 4) Run the extractor on the file object
#         extractor = OCREnhancedMenuExtractor(debug=True, use_ocr=True)
#         try:
#             items = extractor.extract_from_pdf(pdf_file)
#         except Exception as e:
#             return Response(
#                 {"detail": f"Error while extracting menu: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         # 5) If no items, mimic your old CLI behaviour
#         if not items:
#             return Response(
#                 {
#                     "detail": (
#                         "No items could be extracted. "
#                         "Possible reasons: unusual PDF, poor OCR, or non-standard layout."
#                     )
#                 },
#                 status=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             )

#         # 6) 💾 Save JSON next to the uploaded PDF inside MEDIA_ROOT/restaurant_menu/...
#         # pdf_file.path -> absolute path, e.g. /.../media/restaurant_menu/menu_4.pdf
#         pdf_path = pdf_file.path
#         print(pdf_path)
#         output_dir = os.path.dirname(pdf_path)  # /.../media/restaurant_menu
#         # optional: make filename unique per restaurant
#         json_filename = f"menu_structured_{restaurant.id}.json"
#         output_path = os.path.join(output_dir, json_filename)

#         extractor.save_to_json(items, output_path)

#         # Build a URL to access JSON via MEDIA_URL (if media is served)
#         # /absolute/path/to/media/restaurant_menu/menu_structured_4.json
#         #  -> restaurant_menu/menu_structured_4.json (relative)
#         relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
#         relative_url = relative_path.replace("\\", "/")  # for Windows

#         json_file_url = request.build_absolute_uri(
#             settings.MEDIA_URL + relative_url
#         )

#         # 7) Prepare data for response
#         items_data = [asdict(item) for item in items]

#         return Response(
#             {
#                 "restaurant_id": restaurant.id,
#                 "items_count": len(items_data),
#                 "json_file_path": output_path,   # filesystem path
#                 "json_file_url": json_file_url,  # HTTP URL (if MEDIA_URL served)
#                 "items_sample": items_data[:10],
#             },
#             status=status.HTTP_200_OK,
#         )
# e.g. in restaurants/views.py
from django.views.generic import TemplateView

class MenuPDFUploadDemoView(TemplateView):
    template_name = "menu_pdf_upload_demo.html"

class UploadAPIVIEw(APIView):
    queryset = Restaurant.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = RestaurantMenuPDFUploadSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrSuperAdmin]

    def post(self, request):
        # 1) Get the restaurant belonging to the logged-in user
        restaurant = get_object_or_404(Restaurant, owner=request.user)
        self.check_object_permissions(request, restaurant)

        # 2) Bind & validate the uploaded file using the serializer
        serializer = self.serializer_class(
            instance=restaurant,  # update this restaurant
            data=request.data,    # expects "menu_pdf" in form-data
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        # 3) Save the file onto the Restaurant (restaurant.menu_pdf)
        restaurant = serializer.save()
        pdf_file = restaurant.menu_pdf  # Django FieldFile

        # Safety check
        if not pdf_file or not hasattr(pdf_file, "path"):
            return Response(
                {"detail": "menu_pdf was not uploaded or saved correctly."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pdf_path = pdf_file.path  # absolute path on disk
        print("PDF PATH:", pdf_path)

        # 4) Run YOUR new MenuExtractor (pdfplumber-based)
        extractor = MenuExtractor()
        try:
            items = extractor.extract(pdf_path)  # returns List[MenuItem]
        except Exception as e:
            return Response(
                {"detail": f"Error while extracting menu: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 5) If no items, mimic your old behaviour
        if not items:
            return Response(
                {
                    "detail": (
                        "No items could be extracted. "
                        "Possible reasons: unusual PDF or non-standard layout."
                    )
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # 6) 💾 Save JSON next to the uploaded PDF inside MEDIA_ROOT/restaurant_menu/...
        pdf_dir = os.path.dirname(pdf_path)  # e.g. /.../media/restaurant_menu
        json_filename = f"menu_structured_{restaurant.id}.json"
        output_path = os.path.join(pdf_dir, json_filename)

        extractor.save_json(items, output_path)

        # Build a URL to access JSON via MEDIA_URL (if media is served)
        relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
        relative_url = relative_path.replace("\\", "/")  # for Windows

        json_file_url = request.build_absolute_uri(
            settings.MEDIA_URL + relative_url
        )

        # 7) Prepare data for response
        items_data = [asdict(item) for item in items]

        return Response(
            {
                "restaurant_id": restaurant.id,
                "items_count": len(items_data),
                "json_file_path": output_path,   # filesystem path
                "json_file_url": json_file_url,  # HTTP URL (if MEDIA_URL served)
                "items_sample": items_data[:10],  # first 10 items as preview
            },
            status=status.HTTP_200_OK,
        )