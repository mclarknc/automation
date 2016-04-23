from django.conf.urls import url, include
from monitor import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^index', views.index),
    url(r'^login', views.user_login),
    url(r'^logout', views.user_logout),
    url(r'^get_readings/(?P<channel_id>\d+)/(?P<days>\d+)/$', views.get_readings),
    url(r'^channel/(?P<channel_id>\d+)/$', views.channel),
    url(r'^channel/(?P<channel_id>\d+)/(?P<days>\d+)/$', views.channel),
]
