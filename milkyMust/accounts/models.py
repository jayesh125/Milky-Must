from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import uuid

class UserManager(BaseUserManager):
    def create_user(self, phone, name="", surname="", password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        user = self.model(phone=phone, **extra_fields)
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
        return self.create_user(phone=phone, password=password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, db_index=True)
    username = None
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'phone'
    objects = UserManager()

    def __str__(self):
        return f"User ({self.phone})"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    farm_name = models.CharField(max_length=100, blank=True, null=True)
    
    @property
    def is_complete(self):
        return bool((self.first_name or "").strip() and (self.last_name or "").strip())

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return name or self.user.phone

def default_expiry():
    return timezone.now() + timedelta(minutes=5)

class OTP(models.Model):
    phone = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)
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
                return False
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            return True
        except cls.DoesNotExist:
            return False

    def __str__(self):
        return f"{self.phone} - {self.code}"
