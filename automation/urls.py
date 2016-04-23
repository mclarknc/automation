from django.conf.urls import url, include
from django.contrib import admin
from garage import views
from api.resources import *
from tastypie.api import Api

v1_api = Api(api_name='v1')
v1_api.register(MonitorResource())
v1_api.register(ChannelTypeResource())
v1_api.register(ChannelResource())
v1_api.register(ReadingResource())

urlpatterns = [
    url(r'^$', include('monitor.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^garage/', include('garage.urls')),
    url(r'^monitor/', include('monitor.urls')),
    url(r'^api/', include(v1_api.urls)),
]
