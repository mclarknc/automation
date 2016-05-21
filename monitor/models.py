from django.db import models
from django.contrib.auth.models import User
from tastypie.models import create_api_key
import uuid
import datetime

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
    rules = models.ManyToManyField('Rule', null=True, blank=True, db_index=True)
    status = models.IntegerField(choices=CHANNEL_STATUS_CHOICES)
    last_reading = models.ForeignKey('Reading', related_name='channel_last_reading', null=True, blank=True)
    last_alert = models.ForeignKey('Alert', related_name='channel_last_alert', null=True, blank=True)

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
    is_valid = models.BooleanField(default=True)

    def __str__(self):
        return ': '.join([self.monitor_time.strftime("%Y-%m-%d %H:%M:%S"), str(self.value)])

    def save(self, *args, **kwargs):
        from monitor.tasks import process_reading
        self.value = float(self.value) + self.offset_value
        # smooth out glitches
        if self.channel.last_reading:
            last_value = self.channel.last_reading.value
            if abs((self.value - last_value) / last_value) > 0.35:
                self.is_valid = False
            else:
                self.is_valid = True
        else:
            self.is_valid = True
            
        super(Reading, self).save(*args, **kwargs)

        process_reading.delay(self.channel.id, self.id)
        self.channel.last_reading = self
        self.channel.save()
        monitor = self.channel.monitor
        monitor.last_update = datetime.datetime.now()
        monitor.save()

class Preference(models.Model):
    EMAIL = 0
    SMS = 1
    BOTH = 2
    CONTACT_CHOICES = ((EMAIL, 'email'),
                       (SMS, 'text'),
                       (BOTH, 'email and text'))

    user = models.ForeignKey(User)
    contact_method = models.IntegerField(choices=CONTACT_CHOICES, default = EMAIL)
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
    SEND_EMAIL_TEXT_ALERT = 0
    SEND_GUI_ALERT = 1
    SEND_BOTH = 2
    ACTIONS = (
        (SEND_EMAIL_TEXT_ALERT, 'send email/text alert'),
        (SEND_GUI_ALERT, 'display gui alert'),
        (SEND_BOTH, 'send email/text and gui alert'),
    )

    name = models.CharField(max_length=100)
    rule_type = models.ForeignKey(RuleType)
    lower_threshold = models.FloatField(null=True, blank=True)
    upper_threshold = models.FloatField(null=True, blank=True)
    action = models.IntegerField(choices=ACTIONS)
    contacts = models.ManyToManyField(User, related_name = 'rules_rule_contacts')
    state = models.IntegerField(default=RULE_ACTIVE)

    def descriptive_name(self):
        val = ""
        if self.lower_threshold and not self.upper_threshold:
            val = "{} {}".format(self.name, self.lower_threshold)
        elif self.upper_threshold and not self.lower_threshold:
            val = "{} {}".format(self.name, self.upper_threshold)
        else:
            val = "{} {} and {}".format(self.name, self.lower_threshold, self.upper_threshold)
        
        return val

    def __str__(self):
        return self.name

    def evaluate(self, reading):
        # get the eval function by name
        func = getattr(self, self.rule_type.eval_func)
        # call the eval function and return its result
        return func(reading)

    def eval_lt(self, reading):
        return reading.value < self.lower_threshold

    def eval_lte(self, reading):
        return reading.value <= self.lower_threshold

    def eval_gt(self, reading):
        return reading.value > self.upper_threshold

    def eval_gte(self, reading):
        return reading.value >= self.upper_threshold

    def range(self, reading):
        return self.eval_lt() or self.eval_gt()

class Alert(models.Model):
    CHANNEL_ALERT = 0
    MONITOR_ALERT = 1
    MONITOR_OVERDUE_ALERT = 2

    alert_type = models.IntegerField(default=CHANNEL_ALERT)
    monitor = models.ForeignKey(Monitor, null=True, blank=True)
    channel = models.ForeignKey(Channel, null=True, blank=True)
    alert_time = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(User, null=True, blank=True)
    acknowledged_time = models.DateTimeField(null=True, blank=True)
    resolved_time = models.DateTimeField(null=True, blank=True)
    reading = models.ForeignKey(Reading, null=True)
    rule = models.ForeignKey(Rule, null=True, default=None)
    active = models.BooleanField(db_index=True)
    uuid = models.UUIDField(db_index=True, default=uuid.uuid4)

    def __str__(self):
        if self.channel:
            return ': '.join([self.channel.name, self.alert_time.strftime("%Y-%m-%d %H:%M:%S")])
        else:
            return ': '.join([self.monitor.name, self.alert_time.strftime("%Y-%m-%d %H:%M:%S")])
