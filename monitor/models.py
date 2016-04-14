from django.db import models
from django.contrib.auth.models import User
from tastypie.models import create_api_key

models.signals.post_save.connect(create_api_key, sender=User)

class Monitor(models.Model):
    ACTIVE = 0
    INACTIVE = 1
    STATUS_CHOICES = ((ACTIVE, 'active'),
                      (INACTIVE, 'inactive'))
    
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=50)
    status = models.IntegerField(choices=STATUS_CHOICES,
                                 default=ACTIVE)
    last_update = models.DateTimeField(null=True, blank=True,db_index=True)

    def __str__(self):
        return self.name

class Unit(models.Model):
    IMPERIAL = 0
    METRIC = 1
    UNIT_CHOICES = ((IMPERIAL, 'imperial'),
                    (METRIC, 'metric'))

    name = models.CharField(max_length=32, default='')
    unit_metric = models.CharField(max_length=32, default='')
    unit_imperial = models.CharField(max_length=32, default='')
    abbrev_metric = models.CharField(max_length=32, default='')
    abbrev_imperial = models.CharField(max_length=32, default='')
    m_to_i_function = models.CharField(max_length=32, default='identity')
    i_to_m_function = models.CharField(max_length=32, default='identity')

    def m_to_i(self, x):
        func = getattr(self, self.m_to_i_function)
        return func(x)

    def i_to_m(self, x):
        func = getattr(self, self.i_to_m_function)
        return func(x)

    def identity(self, x):
        return x

    def celcius_to_fahrenheit(self, x):
        return x * 9 / 5 + 32

    def fahrenheit_to_celcius(self, x):
        return (x - 32) * 5 / 9

    def __str__(self):
        return self.name

class ChannelType(models.Model):
    sensor_name = models.CharField(max_length=200, default='')
    common_name = models.CharField(max_length=200, default='')
    units = models.ForeignKey(Unit)
    measurement_system = models.IntegerField(choices = Unit.UNIT_CHOICES, default=Unit.METRIC)

    def __str__(self):
        return self.common_name

class Channel(models.Model):
    ENABLED = 0
    DISABLED = 1
    PAUSED = 2
    CHANNEL_STATUS_CHOICES = ((ENABLED, 'enabled'),
                              (DISABLED, 'disabled'),
                              (PAUSED, 'paused'))

    monitor = models.ForeignKey(Monitor)
    channel_num = models.IntegerField()
    channel_type = models.ForeignKey(ChannelType)
    name = models.CharField(max_length=200)
    status = models.IntegerField(choices=CHANNEL_STATUS_CHOICES)

    def __str__(self):
        return ': '.join([self.monitor.name, self.name])

class Reading(models.Model):
    monitor_time = models.DateTimeField()
    transaction_time = models.DateTimeField(auto_now_add=True)
    channel = models.ForeignKey(Channel)
    value = models.FloatField()
    offset_value = models.FloatField(default = 0.0)

    def __str__(self):
        return ': '.join([self.monitor_time.strftime("%Y-%m-%d %H:%M:%S"), str(self.value)])
