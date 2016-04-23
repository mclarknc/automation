from django.contrib import admin
from monitor.models import *

# Register your models here.
admin.site.register(Monitor)
admin.site.register(Unit)
admin.site.register(ChannelType)
admin.site.register(Channel)
admin.site.register(Reading)
admin.site.register(Preference)
