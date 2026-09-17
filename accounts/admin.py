from django.contrib import admin
from .models import UserAccessProfile,UserProjectAccess
class UserProjectAccessInline(admin.TabularInline):
    model=UserProjectAccess; extra=0; autocomplete_fields=['project']
@admin.register(UserAccessProfile)
class UserAccessProfileAdmin(admin.ModelAdmin):
    list_display=['user','role','active','scope']; list_filter=['role','active']; search_fields=['user__username','user__email']; inlines=[UserProjectAccessInline]
    def scope(self,obj): return 'Todos os projetos' if obj.can_query_all_projects else f'{obj.project_accesses.filter(can_query=True).count()} projeto(s)'
@admin.register(UserProjectAccess)
class UserProjectAccessAdmin(admin.ModelAdmin):
    list_display=['profile','project','can_query']; list_filter=['can_query']; search_fields=['profile__user__username','project__path_with_namespace']; autocomplete_fields=['profile','project']
