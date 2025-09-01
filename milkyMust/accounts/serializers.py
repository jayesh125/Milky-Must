from rest_framework import serializers
from .models import User, Profile

class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must be numeric.")
        return value

    def already_exists(self, phone):
        
        return User.objects.filter(phone=phone).exists()

class ProfileSerializer(serializers.ModelSerializer):
    is_complete = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["first_name", "last_name", "address", "farm_name", "is_complete"]

    def get_is_complete(self, obj):
        return bool((obj.first_name or "").strip() and (obj.last_name or "").strip())

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    print(profile)

    class Meta:
        model = User
        fields = ["id", "phone", "profile"]

class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)
