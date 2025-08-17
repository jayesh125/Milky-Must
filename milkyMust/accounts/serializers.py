from rest_framework import serializers
from .models import User

class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "created_at")
