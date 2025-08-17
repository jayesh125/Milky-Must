import random
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import User, OTP
from .serializers import SendOTPSerializer, VerifyOTPSerializer, UserSerializer

# Replace this with Twilio/MSG91 etc.
def send_sms(phone, code):
    # TODO: integrate real SMS. For dev: just log to console.
    print(f"[DEV SMS] OTP for {phone}: {code}")
    return True

def generate_otp():
    return str(random.randint(100000, 999999))

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]
        code = generate_otp()

        # Fetch last OTP row for this phone (if exists) to enforce rate limits
        last = OTP.objects.filter(phone=phone).order_by('-created_at').first()
        if last:
            # respect 10-minute window, max 5 sends
            if not last.within_window(minutes=10, limit=5):
                return Response({"error": "Too many OTP requests. Try again later."},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)
            # continue same window
            otp = OTP(phone=phone, code=code, window_start=last.window_start,
                      send_count_window=last.send_count_window + 1)
            otp.set_expiry(minutes=5)
            otp.save()
        else:
            otp = OTP(phone=phone, code=code)
            otp.set_expiry(minutes=5)
            otp.save()

        # send SMS
        send_sms(phone, code)
        return Response({"message": "OTP sent"}, status=status.HTTP_200_OK)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        otp_obj = OTP.objects.filter(phone=phone, code=code, is_used=False).order_by('-created_at').first()
        if not otp_obj:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.is_expired():
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

        # Mark OTP used
        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        user, _ = User.objects.get_or_create(phone=phone)

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({
            "message": "OTP verified",
            "user": UserSerializer(user).data,
            "access": str(access),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """
    Blacklist the provided refresh token (logout from this device).
    Body: {"refresh": "<refresh_token>"}
    """
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
    """
    Logout from all devices by blacklisting all outstanding tokens of the current user.
    """
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

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

# Optional: subclass refresh view so your route stays under /auth/
class MyTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
