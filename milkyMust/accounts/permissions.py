# accounts/permissions.py
from rest_framework.permissions import BasePermission

class IsProfileComplete(BasePermission):
    """
    Blocks users who haven't completed their profile.
    Customers can skip until they try to purchase subscription.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        # Customers are allowed without full profile
        if user.role == "CUSTOMER":
            return True

        # For distributor & delivery → must complete profile
        return user.is_profile_complete()
