from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Usuario
from wallet.models import Wallet

@receiver(post_save, sender=Usuario)
def criar_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(
            usuario=instance
        )