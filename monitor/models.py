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

    def get_units(self):
        return [self.channel_type.units.unit_imperial, self.channel_type.units.unit_metric]

    def get_unit_abbrevs(self):
        return [self.channel_type.units.abbrev_imperial, self.channel_type.units.abbrev_metric]

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

class Preference(models.Model):
    user = models.ForeignKey(User)
    measurement_system = models.IntegerField(choices=Unit.UNIT_CHOICES, default=Unit.IMPERIAL)

    def __str__(self):
        return ' '.join([self.user.first_name, self.user.last_name])

class RuleType(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100)
    eval_func = models.CharField(max_length=100)
    template_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

class Rule(models.Model):
    # rule states
    RULE_ACTIVE = 0
    RULE_INACTIVE = 1
    RULE_PAUSED = 2

    # constants for specifying actions
    SEND_EMAIL_ALERT = 0
    SEND_TEXT_ALERT = 1
    SEND_BOTH = 2
    ACTIONS = (
        (SEND_EMAIL_ALERT, 'send email alert'),
        (SEND_TEXT_ALERT, ' send text alert'),
        (SEND_BOTH, 'send email and text alert'),
    )

    name = models.CharField(max_length=100)
    rule_type = models.ForeignKey(RuleType)
    lower_threshold = models.FloatField(null=True, blank=True)
    upper_threshold = models.FloatField(null=True, blank=True)
    action = models.IntegerField()
    contacts = models.ManyToManyField(User, related_name = 'rules_rule_contacts')
    state = models.IntegerField(default=RULE_ACTIVE)

    def descriptive_name(self):
        val = ""
        if self.lower_threshold and not self.upper_threshold:
            val = "{} {}".format(self.name, self.lower_threshold)
        elif self.upper_threshold and not self.lower_threshold:
            val = "{} {}".format(self.name, self.upper_threshold)
        else:
            val = "{} {} and {}".format(self.name, self.lower_threshold self.upper_threshold)
        
        return val

    def __str__(self):
        return self.name

    def evaluate(self, channel, reading):
        # get the eval function by name
        func = getattr(self, self.rule_type.eval_func)
        # call the eval function and return its result
        return func(channel, reading)

    def eval_lt(self, channel, reading):
        return reading.value < self.lower_threshold

    def eval_lte(self, channel, reading):
        return reading.value <= self.lower_threshold

    def eval_gt(self, channel, reading):
        return reading.value > self.upper_threshold

    def eval_gte(self, channel, reading):
        return reading.value >= self.upper_threshold

    def range(self, channel, reading):
        return self.eval_lt(channel, reading) or self.eval_gt(channel, reading)
