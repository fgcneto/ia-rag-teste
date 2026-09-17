from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from .models import UserAccessProfile, Role
@receiver(post_save, sender=get_user_model())
def ensure_profile(sender, instance, created, **kwargs):
    if created: UserAccessProfile.objects.get_or_create(user=instance, defaults={'role':Role.DEVELOPER})
@receiver(post_migrate)
def ensure_groups(sender, **kwargs):
    if sender.name=='accounts':
        Group.objects.get_or_create(name='Analista de Sistemas'); Group.objects.get_or_create(name='Desenvolvedor')
