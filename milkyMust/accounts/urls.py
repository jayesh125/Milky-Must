# milkyMust\accounts\urls.py
from django.urls import path
from .views import (
    DistributorInfoUpdateView, SendOTPLoginView, SendOTPRegisterView, VerifyOTPLoginView, VerifyOTPRegisterView, LogoutView, LogoutAllView,
    MeView, MyTokenRefreshView, ProfileUpdateView, DeliveryBoyInfoUpdateView,
    SetPasswordView, PhonePasswordLoginView
)

urlpatterns = [
    path("send-otp/register/", SendOTPRegisterView.as_view(), name="send_otp_register"),
    path("send-otp/login/", SendOTPLoginView.as_view(), name="send_otp_login"),
    path("verify-otp/register/", VerifyOTPRegisterView.as_view(), name="verify_otp_register"),
    path("verify-otp/login/", VerifyOTPLoginView.as_view(), name="verify_otp_login"),

    path('token/refresh/', MyTokenRefreshView.as_view(), name='token_refresh'),

    path('logout/', LogoutView.as_view(), name='logout'),
    path('logout-all/', LogoutAllView.as_view(), name='logout_all'),

    path("me/", MeView.as_view(), name="me"),
    path("profile/update/", ProfileUpdateView.as_view(), name="profile-update"),
    path("distributor/update/", DistributorInfoUpdateView.as_view(), name="distributor-update"),
    path("delivery-boy/update/", DeliveryBoyInfoUpdateView.as_view(), name="deliveryboy-update"),

    # Added for your flow
    path("set-password/", SetPasswordView.as_view(), name="set-password"),
    path("login/", PhonePasswordLoginView.as_view(), name="phone-password-login"),
]
