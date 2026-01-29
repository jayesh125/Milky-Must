from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, OTP, DistributorInfo, DeliveryBoyInfo, CustomerDistributorLink


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("phone",)
    list_display = ("phone", "role", "is_active", "is_staff", "created_at")
    fieldsets = (
        (None, {"fields": ("phone", "password", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2", "role", "is_staff", "is_superuser"),
        }),
    )
    search_fields = ("phone",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "last_name", "address")
    search_fields = ("user__phone", "first_name", "last_name")


@admin.register(DistributorInfo)
class DistributorInfoAdmin(admin.ModelAdmin):
    list_display = ("profile", "farm_name", "distributor_code")
    search_fields = ("farm_name", "distributor_code")


@admin.register(DeliveryBoyInfo)
class DeliveryBoyInfoAdmin(admin.ModelAdmin):
    list_display = ("profile", "vehicle_number")
    search_fields = ("vehicle_number", "profile__user__phone")


@admin.register(CustomerDistributorLink)
class CustomerDistributorLinkAdmin(admin.ModelAdmin):
    list_display = ("customer", "distributor", "created_at")
    search_fields = ("customer__phone", "distributor__phone")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "is_used", "created_at")
    search_fields = ("phone", "code")
