from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from datetime import timedelta
import uuid

class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)   # <-- allow setting password
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra_fields)

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)      
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'phone'
    objects = UserManager()
    
    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True     

    def __str__(self):
        return self.phone

def default_expiry():
    # OTP expires after 5 minutes
    return timezone.now() + timedelta(minutes=5)

class OTP(models.Model):
    phone = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)
    is_used = models.BooleanField(default=False)
    send_count_window = models.PositiveIntegerField(default=1)  # how many sent in the current window
    window_start = models.DateTimeField(default=timezone.now)

    def set_expiry(self, minutes=5):
        self.expires_at = timezone.now() + timedelta(minutes=minutes)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def within_window(self, minutes=10, limit=5):
        # reset window if window expired
        if timezone.now() - self.window_start > timedelta(minutes=minutes):
            self.window_start = timezone.now()
            self.send_count_window = 0
        return self.send_count_window < limit
    
    def verify_otp(phone, code):
        try:
            otp = OTP.objects.get(phone=phone, code=code, is_used=False)
            if otp.is_expired():
                otp.delete()  # cleanup expired
                return False
            otp.is_used = True
            otp.save()
            return True
        except OTP.DoesNotExist:
            return False

    def __str__(self):
        return f"{self.phone} - {self.code}"
