from django.conf import settings
from django.db import models

class Role(models.TextChoices):
    ANALYST='ANALYST','Analista de Sistemas'
    DEVELOPER='DEVELOPER','Desenvolvedor'

class UserAccessProfile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='access_profile')
    role=models.CharField(max_length=20,choices=Role.choices,default=Role.DEVELOPER,db_index=True)
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return f'{self.user.username} - {self.get_role_display()}'
    @property
    def can_query_all_projects(self): return self.active and self.role==Role.ANALYST

class UserProjectAccess(models.Model):
    profile=models.ForeignKey(UserAccessProfile,on_delete=models.CASCADE,related_name='project_accesses')
    project=models.ForeignKey('knowledge.Project',on_delete=models.CASCADE,related_name='user_accesses')
    can_query=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['profile','project'],name='uq_profile_project_access')]
    def __str__(self): return f'{self.profile.user.username} -> {self.project.path_with_namespace}'
