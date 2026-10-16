from django.urls import path

from .views import chat_stream, home

urlpatterns=[path('',home,name='home'),path('api/chat/stream/',chat_stream,name='chat_stream')]
