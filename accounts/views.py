from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserCreateSerializer
from .permissions import IsSuperAdmin, IsRestaurantAdmin
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.views import APIView
from accounts.serializers import LoginSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
User = get_user_model()



# @permission_classes([AllowAny])
from rest_framework import viewsets
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserCreateSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # No explicit permission_classes here:
    # It will use global:
    # IsAuthenticated + DjangoModelPermissions

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        user = self.request.user

        # Superadmin (or Django superuser) → can see all
        if getattr(user, "is_superadmin", False) or user.is_superuser:
            return User.objects.all()

        # Admin → only see themselves
        if getattr(user, "is_restaurant_admin", False):
            return User.objects.filter(id=user.id)

        # Everyone else → nothing
        return User.objects.none()
# accounts/views.py
from django.views.generic import TemplateView

class LoginDemoView(TemplateView):
    template_name = "login_demo.html"

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    def post(self,request,*args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username,password=password)
        
        if user is not None:
            refresh = RefreshToken.for_user(user)
            user_serializer = UserSerializer(user)
            return Response({
                'refresh':str(refresh),
                'access':str(refresh.access_token),
                'user':user_serializer.data
            })
        else:
            return Response({'detail':'invalid credentials'},status=401)

