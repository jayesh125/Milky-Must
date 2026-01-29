# accounts/signals.py
import string, random
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import User, Profile, DistributorInfo, DeliveryBoyInfo


def generate_distributor_code(length=6):
    """Generate a random unique distributor code (e.g., ABC123)."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not DistributorInfo.objects.filter(distributor_code=code).exists():
            return code


@receiver(post_save, sender=User)
def create_profile_and_role_info(sender, instance, created, **kwargs):
    if created:
        # 1. Create shared Profile for every user
        profile = Profile.objects.create(user=instance)

        # 2. If user is a distributor → create DistributorInfo
        if instance.role == "DISTRIBUTOR":
            DistributorInfo.objects.create(
                profile=profile,
                distributor_code=generate_distributor_code()
                # qr_code will be generated later
            )

        # 3. If user is a delivery boy → create DeliveryBoyInfo (optional, later)
        if instance.role == "DELIVERY_BOY":
            DeliveryBoyInfo.objects.create(profile=profile)
