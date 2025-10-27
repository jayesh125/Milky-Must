# D:\MilkyMust\milkyMust\accounts\models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import uuid

# ----------------------------
# USER MANAGER
# ----------------------------
class UserManager(BaseUserManager):
    def create_user(self, phone, name="", surname="", password=None, role="CUSTOMER", **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        if role not in ["CUSTOMER", "DISTRIBUTOR", "DELIVERY_BOY"]:
            raise ValueError("Invalid role")

        user = self.model(phone=phone, role=role, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if password is None:
            raise ValueError("Superusers must have a password.")
        return self.create_user(phone=phone, password=password, role="DISTRIBUTOR", **extra_fields)


# ----------------------------
# USER MODEL
# ----------------------------
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("CUSTOMER", "Customer"),
        ("DISTRIBUTOR", "Distributor"),
        ("DELIVERY_BOY", "Delivery Boy"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CUSTOMER")

    username = None
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'phone'
    objects = UserManager()
    
    def is_profile_complete(self):
        """
        Check if this user has filled in mandatory fields 
        depending on their role.
        """
        if not hasattr(self, "profile"):
            return False

        profile = self.profile
        if not profile.first_name or not profile.last_name:
            return False

        if self.role == "DISTRIBUTOR":
            return hasattr(profile, "distributor_info") and profile.distributor_info.farm_name and profile.distributor_info.distributor_code

        if self.role == "DELIVERY_BOY":
            return hasattr(profile, "delivery_info") and profile.delivery_info.vehicle_number

        # CUSTOMER → only basic profile required
        return True

    def __str__(self):
        return f"{self.phone} ({self.role})"


# ----------------------------
# SHARED PROFILE
# ----------------------------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def __str__(self):
        return self.full_name or self.user.phone


# ----------------------------
# ROLE-SPECIFIC INFO
# ----------------------------
class DistributorInfo(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="distributor_info")
    farm_name = models.CharField(max_length=100, blank=True, null=True)
    distributor_code = models.CharField(max_length=10, unique=True, db_index=True)
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)  # will generate later

    def __str__(self):
        return f"Distributor: {self.profile.full_name or self.profile.user.phone}"


class DeliveryBoyInfo(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="delivery_info")
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Delivery Boy: {self.profile.full_name or self.profile.user.phone}"

# ----------------------------
# CUSTOMER-DISTRIBUTOR LINK
# ----------------------------
class CustomerDistributorLink(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="distributor_links")
    distributor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customer_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "distributor")

    def __str__(self):
        return f"{self.customer.phone} → {self.distributor.phone}"

# ----------------------------
# OTP SYSTEM
# ----------------------------
def default_expiry():
    return timezone.now() + timedelta(minutes=5)


class OTP(models.Model):
    phone = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default="CUSTOMER")  # ✅ Added role field
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)
    is_used = models.BooleanField(default=False)
    send_count_window = models.PositiveIntegerField(default=1)
    window_start = models.DateTimeField(default=timezone.now)

    def set_expiry(self, minutes=5):
        self.expires_at = timezone.now() + timedelta(minutes=minutes)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def within_window(self, minutes=10, limit=5):
        if timezone.now() - self.window_start > timedelta(minutes=minutes):
            self.window_start = timezone.now()
            self.send_count_window = 0
        return self.send_count_window < limit

    @classmethod
    def verify_otp(cls, phone, code):
        try:
            otp = cls.objects.get(phone=phone, code=code, is_used=False)
            if otp.is_expired():
                otp.delete()
                return None
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            return otp  # ✅ Return OTP instance instead of True
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return f"{self.phone} - {self.code} ({self.role})"
