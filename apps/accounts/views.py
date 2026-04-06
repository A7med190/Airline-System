from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .serializers import RegisterSerializer, UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "success": True,
            "message": "Registration successful",
            "data": {
                "user": UserSerializer(user).data,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"success": False, "error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth import authenticate
        user = authenticate(request, email=email, password=password)

        if not user:
            return Response({"success": False, "error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"success": False, "error": "Account is deactivated."}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            "success": True,
            "message": "Login successful",
            "data": {
                "user": UserSerializer(user).data,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }
        })


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response({"success": False, "error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"success": True, "message": "Logout successful"})
        except Exception:
            return Response({"success": False, "error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get(self, request):
        serializer = self.get_serializer(request.user)
        return Response({"success": True, "data": serializer.data})
