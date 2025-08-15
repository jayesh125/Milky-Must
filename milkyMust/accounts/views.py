from django.shortcuts import render

# Create your views here.
import random
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import User, OTP
from .serializers import SendOTPSerializer, VerifyOTPSerializer

class SendOTPView(APIView): 
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            code = str(random.randint(100000, 999999))

            OTP.objects.create(phone=phone, code=code)

            # Simulate SMS sending (log it for now)
            print(f"OTP for {phone}: {code}")

            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            code = serializer.validated_data['code']

            otp_obj = OTP.objects.filter(phone=phone, code=code).order_by('-created_at').first()

            if otp_obj:
                user, created = User.objects.get_or_create(phone=phone)
                return Response({"message": "OTP verified", "user_id": str(user.id)}, status=status.HTTP_200_OK)

            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
