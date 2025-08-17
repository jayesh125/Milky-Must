from django.urls import path
from .views import SendOTPView, VerifyOTPView, LogoutView, LogoutAllView, MeView, MyTokenRefreshView

urlpatterns = [
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('token/refresh/', MyTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('logout-all/', LogoutAllView.as_view(), name='logout_all'),
    path('me/', MeView.as_view(), name='me'),
]
