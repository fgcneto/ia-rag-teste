from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth import get_user_model
from accounts.models import Role,UserAccessProfile,UserProjectAccess
from knowledge.models import Project
class Command(BaseCommand):
 help='Cria/atualiza usuário com perfil ANALYST ou DEVELOPER e escopo opcional de projetos.'
 def add_arguments(self,p):
  p.add_argument('username');p.add_argument('--role',choices=['ANALYST','DEVELOPER'],required=True);p.add_argument('--email',default='');p.add_argument('--project',action='append',default=[]);p.add_argument('--password')
 def handle(self,*a,**o):
  U=get_user_model();u,_=U.objects.get_or_create(username=o['username'],defaults={'email':o['email']});
  if o['password']:u.set_password(o['password']);u.save()
  profile,_=UserAccessProfile.objects.get_or_create(user=u);profile.role=o['role'];profile.active=True;profile.save()
  if o['role']=='ANALYST': profile.project_accesses.all().delete()
  else:
   for name in o['project']:
    try:p=Project.objects.get(path_with_namespace=name)
    except Project.DoesNotExist:raise CommandError(f'Projeto não encontrado: {name}')
    UserProjectAccess.objects.update_or_create(profile=profile,project=p,defaults={'can_query':True})
  self.stdout.write(self.style.SUCCESS(f'{u.username}: {profile.get_role_display()}'))
