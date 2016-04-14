from tastypie import fields
from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS
from monitor.models import Monitor, Channel, Reading, ChannelType
from tastypie.authorization import Authorization
from tastypie.authentication import ApiKeyAuthentication

class MonitorResource(ModelResource):
    class Meta:
        queryset = Monitor.objects.all()
        resource_name = 'monitor'
        allowed_methods = ['get']
        authentication = ApiKeyAuthentication()

class ChannelTypeResource(ModelResource):
    class Meta:
        queryset = ChannelType.objects.all()
        resource_name = 'channel_type'
        allowed_methods = ['get']
        authentication = ApiKeyAuthentication()

class ChannelResource(ModelResource):
    channel_type = fields.ForeignKey(ChannelTypeResource, 'channel_type')
    monitor = fields.ForeignKey(MonitorResource, 'monitor')
    class Meta:
        queryset = Channel.objects.all()
        resource_name = 'channel'
        allowed_methods = ['get']
        authentication = ApiKeyAuthentication()

        
class ReadingResource(ModelResource):
    channel = fields.ForeignKey("api.resources.ChannelResource", 'channel')
    class Meta:
        always_return_data = True
        queryset = Reading.objects.all()
        authorization = Authorization()
        authentication = ApiKeyAuthentication()
        allowed_methods = ['get', 'post']
        filtering = {
            'channel': ALL_WITH_RELATIONS,
            'monitor': ALL_WITH_RELATIONS,
        }
        resource_name = 'reading'
