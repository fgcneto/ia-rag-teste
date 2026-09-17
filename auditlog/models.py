from django.conf import settings
from django.db import models
class AuditEvent(models.Model):
 occurred_at=models.DateTimeField(auto_now_add=True,db_index=True); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
 event_type=models.CharField(max_length=80,db_index=True); decision=models.CharField(max_length=80,db_index=True); reason=models.CharField(max_length=1000,blank=True,default='')
 question_hash=models.CharField(max_length=64,blank=True,default=''); source_ids=models.JSONField(default=list)
