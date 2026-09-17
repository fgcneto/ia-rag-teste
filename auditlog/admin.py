from django.contrib import admin
from .models import AuditEvent
@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
 list_display=['occurred_at','user','event_type','decision']; list_filter=['event_type','decision']; search_fields=['user__username','question_hash']; readonly_fields=['occurred_at','user','event_type','decision','reason','question_hash','source_ids']
 def has_add_permission(self,request): return False
 def has_change_permission(self,request,obj=None): return False
