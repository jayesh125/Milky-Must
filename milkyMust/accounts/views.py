import random
from django.http import HttpResponse
from django.utils import timezone
from requests import request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, permissions, generics
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password

from .models import Profile, User, OTP
from .serializers import (
    SendOTPSerializer, VerifyOTPSerializer,
    ProfileSerializer, UserSerializer, SetPasswordSerializer
)

# Replace with Twilio/MSG91/etc in production
def send_sms(phone, code):
    print(f"[DEV SMS] OTP for {phone}: {code}")
    return True

def generate_otp():
    return str(random.randint(100000, 999999))

class SendOTPRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]

        # ❌ block if user already exists
        if User.objects.filter(phone=phone).exists():
            return Response(
                {"error": "User with this phone number already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        code = generate_otp()
        otp = OTP(phone=phone, code=code)
        otp.set_expiry(minutes=5)
        otp.save()

        send_sms(phone, code)
        return Response({"message": "OTP sent for registration"}, status=status.HTTP_200_OK)


class SendOTPLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]

        # ❌ block if user does not exist
        if not User.objects.filter(phone=phone).exists():
            return Response(
                {"error": "User with this phone number is not registered"},
                status=status.HTTP_404_NOT_FOUND
            )

        code = generate_otp()
        otp = OTP(phone=phone, code=code)
        otp.set_expiry(minutes=5)
        otp.save()

        send_sms(phone, code)
        return Response({"message": "OTP sent for login"}, status=status.HTTP_200_OK)

class VerifyOTPRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        otp_obj = OTP.objects.filter(
            phone=phone, code=code, is_used=False
        ).order_by('-created_at').first()

        if not otp_obj or otp_obj.is_expired():
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        # ❌ if user exists, block
        if User.objects.filter(phone=phone).exists():
            return Response({"error": "User already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ create new user and profile
        user = User.objects.create(phone=phone)
        profile, _ = Profile.objects.get_or_create(user=user)  # ensure profile is attached

        refresh = RefreshToken.for_user(user)

        # ✅ always include profile.is_complete in response
        return Response({
            "message": "OTP verified, new user created",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)

class VerifyOTPLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        otp_obj = OTP.objects.filter(phone=phone, code=code, is_used=False).order_by('-created_at').first()
        if not otp_obj or otp_obj.is_expired():
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        # ❌ if user not exist → fail
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({"error": "User not registered"}, status=status.HTTP_404_NOT_FOUND)

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "OTP verified, login successful",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"error": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Logged out"}, status=status.HTTP_200_OK)

class LogoutAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        tokens = OutstandingToken.objects.filter(user=user)
        for t in tokens:
            try:
                BlacklistedToken.objects.get_or_create(token=t)
            except Exception:
                pass
        return Response({"message": "Logged out from all devices"}, status=status.HTTP_200_OK)

class MyTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class ProfileUpdateView(generics.UpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # profile is auto-created via signal; but just in case:
        if not hasattr(self.request.user, "profile"):
            from .models import Profile
            Profile.objects.create(user=self.request.user)
        return self.request.user.profile

    def patch(self, request, *args, **kwargs):
        # allow partial updates easily
        return super().patch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        """
        Explicitly handle the OPTIONS preflight request.
        This is a failsafe to ensure CORS headers are correctly returned.
        """
        response = HttpResponse()
        response['Allow'] = ', '.join(['GET', 'OPTIONS', 'PATCH'])
        return response


class SetPasswordView(APIView):
    """
    Set (or reset) password AFTER OTP login.
    Use Authorization: Bearer <access>  
    Body: {"password": "..."}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        password = serializer.validated_data["password"]
        request.user.password = make_password(password)
        request.user.save(update_fields=["password"])
        return Response({"message": "Password set successfully"}, status=status.HTTP_200_OK)

class PhonePasswordLoginView(APIView):
    """
    Login with phone + password.
    Body: {"phone": "...", "password": "..."}
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = request.data.get("phone")
        password = request.data.get("password")

        if not phone or not password:
            return Response(
                {"error": "Phone and password required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user exists first
        try:
            user_obj = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {"error": "User not registered"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Authenticate user with password
        user = authenticate(request, username=phone, password=password)
        if not user:
            return Response(
                {"error": "Invalid password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Success → issue tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)
