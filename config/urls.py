from django.contrib import admin
from django.urls import include, path

urlpatterns=[path('admin/',admin.site.urls),path('accounts/',include('django.contrib.auth.urls')),path('',include('chatapp.urls')),path('health/',include('knowledge.health_urls'))]
