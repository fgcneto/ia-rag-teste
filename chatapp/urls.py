from django.urls import path
from .views import home,chat_stream
urlpatterns=[path('',home,name='home'),path('api/chat/stream/',chat_stream,name='chat_stream')]
