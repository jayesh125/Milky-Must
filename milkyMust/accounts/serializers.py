# D:\MilkyMust\milkyMust\accounts\serializers.py
from rest_framework import serializers
from .models import CustomerDistributorLink, DeliveryBoyInfo, DistributorInfo, User, Profile

class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)  
    
    def validate(self, attrs):
        if not attrs.get('phone'):
            raise serializers.ValidationError({"phone": "This field is required."})
        if not attrs.get('role'):
            print(attrs.get('role'), "mandatory role")
            raise serializers.ValidationError({"role": "This field is required."})
        return super().validate(attrs)
    
class sendloginOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    
    def validate(self, attrs):
        if not attrs.get('phone'):
            raise serializers.ValidationError({"phone": "This field is required."})
        return super().validate(attrs)

class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must be numeric.")
        return value

    def already_exists(self, phone):
        
        return User.objects.filter(phone=phone).exists()

class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)

class ProfileSerializer(serializers.ModelSerializer):
    is_complete = serializers.SerializerMethodField()
    full_name = serializers.CharField(source="full_name", read_only=True)  # ✅ FIX
    
    def validate(self, attrs):
        if not attrs.get('first_name'):
            raise serializers.ValidationError({"first_name": "This field is required."})
        if not attrs.get('last_name'):
            raise serializers.ValidationError({"last_name": "This field is required."})
        if not attrs.get('address'):
            raise serializers.ValidationError({"address": "This field is required."})
        return attrs

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    class Meta:
        model = Profile
        fields = ["first_name", "last_name", "address", "full_name", "is_complete"]

    def get_is_complete(self, obj):
        return bool((obj.first_name or "").strip() and (obj.last_name or "").strip())

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    distributor_info = serializers.SerializerMethodField()
    delivery_info = serializers.SerializerMethodField()
    is_profile_complete = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "phone", "role", "profile",
            "distributor_info", "delivery_info", "is_profile_complete"
        ]

    def get_distributor_info(self, obj):
        if hasattr(obj, "profile") and hasattr(obj.profile, "distributor_info"):
            return DistributorInfoSerializer(obj.profile.distributor_info).data
        return None

    def get_delivery_info(self, obj):
        if hasattr(obj, "profile") and hasattr(obj.profile, "delivery_info"):
            return DeliveryBoyInfoSerializer(obj.profile.delivery_info).data
        return None

    def get_is_profile_complete(self, obj):
        # Customers can skip initially
        if obj.role == "CUSTOMER":
            return True  

        if obj.role == "DISTRIBUTOR":
            return hasattr(obj.profile, "distributor_info") and bool(obj.profile.distributor_info.distributor_code)

        if obj.role == "DELIVERY_BOY":
            return hasattr(obj.profile, "delivery_info") and bool(obj.profile.delivery_info.vehicle_number)

        return False

class DistributorInfoSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = DistributorInfo
        fields = ["first_name", "last_name", "farm_name", "distributor_code", "qr_code"]

    def validate(self, attrs):
        # Validate that farm_name and distributor_code are provided and not empty
        if not attrs.get('farm_name'):
            raise serializers.ValidationError({"farm_name": "This field is required."})
        if not attrs.get('distributor_code'):
            raise serializers.ValidationError({"distributor_code": "This field is required."})
        
        return attrs

    def update(self, instance, validated_data):
        # Extract profile fields
        profile = instance.profile
        profile.first_name = validated_data.pop('first_name', profile.first_name)
        profile.last_name = validated_data.pop('last_name', profile.last_name)
        profile.save()

        # Update distributor info fields
        return super().update(instance, validated_data)

class DeliveryBoyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryBoyInfo
        fields = ["vehicle_number"]

class CustomerDistributorLinkSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(source="customer.phone", read_only=True)
    distributor = serializers.CharField(source="distributor.phone", read_only=True)

    class Meta:
        model = CustomerDistributorLink
        fields = ["customer", "distributor", "created_at"]