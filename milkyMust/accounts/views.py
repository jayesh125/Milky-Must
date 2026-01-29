# D:\MilkyMust\milkyMust\accounts\views.py
import random
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from .permissions import IsProfileComplete
from .models import CustomerDistributorLink, DeliveryBoyInfo, DistributorInfo, Profile, User, OTP
from .serializers import (
    CustomerDistributorLinkSerializer, DeliveryBoyInfoSerializer, DistributorInfoSerializer, SendOTPSerializer, VerifyOTPSerializer,
    ProfileSerializer, UserSerializer, SetPasswordSerializer, sendloginOTPSerializer
)

# Replace with Twilio/MSG91/etc in production
def send_sms(phone, code):
    print(f"[DEV SMS] OTP for {phone}: {code}")
    return True

def generate_otp():
    return str(random.randint(100000, 999999))

class SendOTPRegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    # print("SendOTPRegisterView initialized")

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]
        role = serializer.validated_data.get("role")

        if User.objects.filter(phone=phone).exists():
            return Response({"error": "User with this phone number already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        if role not in dict(User.ROLE_CHOICES):
            print(role, "invalid role")
            return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)
        
        code = generate_otp()
        otp = OTP(phone=phone, code=code, role=role)  # ✅ store role in OTP
        otp.set_expiry(minutes=5)
        otp.save()

        send_sms(phone, code)
        return Response({"message": "OTP sent for registration"}, status=status.HTTP_200_OK)

class SendOTPLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = sendloginOTPSerializer(data=request.data)
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

        otp_obj = OTP.objects.filter(phone=phone, code=code, is_used=False).order_by('-created_at').first()
        if not otp_obj or otp_obj.is_expired():
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        if User.objects.filter(phone=phone).exists():
            return Response({"error": "User already exists"}, status=status.HTTP_400_BAD_REQUEST)

        role = otp_obj.role  # retrieve role from OTP
        user = User.objects.create(phone=phone, role=role)  # use the role
        profile, _ = Profile.objects.get_or_create(user=user)

        refresh = RefreshToken.for_user(user)

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
    
class DistributorInfoUpdateView(generics.UpdateAPIView):
    serializer_class = DistributorInfoSerializer
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if self.request.user.role != "DISTRIBUTOR":
            raise PermissionError("Only distributors can update this info")
        distributor_info, _ = DistributorInfo.objects.get_or_create(profile=self.request.user.profile)
        return distributor_info

    def patch(self, request, *args, **kwargs):
        distributor_info = self.get_object()
        profile = self.request.user.profile

        # ✅ Extract profile fields and update them manually
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        address = request.data.get("address")

        if first_name is not None:
            profile.first_name = first_name
        if last_name is not None:
            profile.last_name = last_name
        if address is not None:
            profile.address = address

        profile.save()

        # ✅ Now update DistributorInfo fields using serializer
        serializer = self.get_serializer(distributor_info, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "Distributor profile updated successfully",
            "profile": {
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "address": profile.address
            },
            "distributor_info": serializer.data
        })

class DeliveryBoyInfoUpdateView(generics.UpdateAPIView):
    serializer_class = DeliveryBoyInfoSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if self.request.user.role != "DELIVERY_BOY":
            raise PermissionError("Only delivery boys can update this info")
        delivery_info, _ = DeliveryBoyInfo.objects.get_or_create(profile=self.request.user.profile)
        return delivery_info

class ConnectDistributorView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.role != "CUSTOMER":
            return Response({"detail": "Only customers can connect to a distributor"}, status=status.HTTP_403_FORBIDDEN)

        code = request.data.get("distributor_code")
        try:
            distributor = User.objects.get(
                role="DISTRIBUTOR", 
                profile__distributor_info__distributor_code=code
            )

        except User.DoesNotExist:
            return Response({"detail": "Invalid distributor code"}, status=status.HTTP_400_BAD_REQUEST)

        link, created = CustomerDistributorLink.objects.get_or_create(customer=request.user, distributor=distributor)
        return Response(CustomerDistributorLinkSerializer(link).data, status=status.HTTP_201_CREATED)

class DistributorCustomersView(generics.ListAPIView):
    serializer_class = CustomerDistributorLinkSerializer
    permission_classes = [IsAuthenticated, IsProfileComplete]

    def get_queryset(self):
        return CustomerDistributorLink.objects.filter(distributor=self.request.user)
    
class SubscriptionPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "CUSTOMER":
            return Response({"error": "Only customers can purchase subscriptions"}, status=403)

        if not request.user.is_profile_complete():
            return Response({"error": "Complete your profile before purchasing"}, status=400)

        # ✅ continue with subscription creation...

