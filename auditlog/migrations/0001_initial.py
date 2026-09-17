from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion
class Migration(migrations.Migration):
 initial=True;dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
 operations=[migrations.CreateModel(name='AuditEvent',fields=[('id',models.BigAutoField(primary_key=True,serialize=False)),('occurred_at',models.DateTimeField(auto_now_add=True,db_index=True)),('event_type',models.CharField(db_index=True,max_length=80)),('decision',models.CharField(db_index=True,max_length=80)),('reason',models.CharField(blank=True,default='',max_length=1000)),('question_hash',models.CharField(blank=True,default='',max_length=64)),('source_ids',models.JSONField(default=list)),('user',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL))])]
