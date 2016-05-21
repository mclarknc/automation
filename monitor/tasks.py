from __future__ import absolute_import
from django.core.mail import EmailMultiAlternatives, EmailMessage
from celery import shared_task
from monitor.models import Channel, Rule, User, Reading, Alert, Preference
from automation.settings import SERVER_URL
import datetime
import uuid

@shared_task
def process_reading(channel_id, reading_id):
    channel = Channel.objects.get(pk=channel_id)
    try:
        reading = Reading.objects.get(pk=reading_id)
    except:
        raise Exception("Reading {} does not exist".format(reading_id))
    rules = Rule.objects.filter(channel=channel)
    if len(rules) == 0:
           return 'channel {}: no rules'.format(channel_id)
    return_text = ''
    for rule in rules:
        # dont process inactive or paused rules
        if rule.state == Rule.RULE_INACTIVE:
            return_text += 'Rule {} inactive\n'.format(rule.id)
            continue
        if rule.state == Rule.RULE_PAUSED:
            return_text += 'Rule {} paused\n'.format(rule.id)

        # don't create a new alert if there is an existing, active alert for this rule and
        # channel. We'll just queue up the existing alert (if unacknowledged) to keep nagging
        # the contacts
        prev_alerts = Alert.objects.filter(channel=channel, rule=rule, active=True, alert_type=Alert.CHANNEL_ALERT)
        if len(prev_alerts) > 0: # we must have existing alerts for this channel/rule
            for alert in prev_alerts:
                if rule.evaluate(reading):
                    if not alert.acknowledged_by:
                        process_alert.delay(alert.id)
                    return_text += 'Channel {}: rule matched - active alert exists - value = {}\n'.format(channel.id, str(reading.value))
                else: # the condition that triggered the active alert must not be present any longer
                    alert.active = False
                    alert.resolved_time = datetime.datetime.now()
                    alert.save()
                    process_alert.delay(alert.id, restored=True)
                    return_text += 'Channel {}: rule matched - active alert cancelled\n'

        else:
            if reading.is_valid and rule.evaluate(reading):
                alert = Alert(alert_type = Alert.CHANNEL_ALERT,
                              monitor = channel.monitor,
                              channel = channel,
                              reading = reading,
                              rule = rule,
                              active = True,
                              )
                alert.save()
                process_alert.delay(alert.id)
                channel.last_alert = alert
                channel.save()
                return_text += 'Channel {}: rule {} matched value {} - alert created\n'.format(channel.id, rule.id, str(reading.value))
            else:
                return_text += "Channel {}: rule {} didn't match value {}\n".format(channel.id, rule.id, str(reading.value))

    return return_text

def make_alert_email(user, channel, rule, alert):
    to_addr = ['{} <{}>'.format(str(user.get_full_name()), user.email)]
    msg = 'The following rule was activated on monitor: {}, '.format(channel.monitor.name)
    msg = msg + 'channel: {}\n'.format(channel.name)
    msg = msg + '{}\n\n'.format(rule.descriptive_name)
    msg = msg + 'Current reading for {} is {}\n\n'.format(channel.name, channel.last_reading.value)
    msg = msg + 'To acknowledge this alert click '
    msg = msg + '<a href=https://{}/monitor/ack?aid={}&bid={}>here</a>'.format(SERVER_URL, alert.uuid, user.id)
    html = '<span style="font-size: 150%">The following rule was activated on monitor: {}, '.format(channel.monitor.name)
    html = html + 'channel: {}<br />'.format(channel.name)
    html = html + '<span style="color:red;">{}</span><br /><br />'.format(rule.descriptive_name())
    html = html + 'Current reading for {} is {}<br />'.format(channel.name, channel.last_reading.value)
    html = html + 'To acknowledge this alert click '
    html = html + '<a href=https://{}/monitor/ack?aid={}&bid={}>here</a></span>'.format(SERVER_URL, alert.uuid, user.id)
    subject = 'Alert from {} Monitor'.format(channel.monitor.name)
    from_addr = 'Syliant Monitor <admin@syliant.com>'
    
    email = EmailMultiAlternatives(subject, msg, from_addr, to_addr)
    email.attach_alternative(html, "text/html")
    return email

def make_alert_text(user, channel, rule, alert):
    to_addr = ['{} <{}@{}>'.format(str(user.get_full_name()), user.text_number, user.text_provider)]
    msg = 'Monitor: {}, '.format(channel.monitor.name)
    msg = msg + '{}\n\n'.format(rule.descriptive_name())
    msg = msg + 'To acknowledge click link:'
    msg = msg + '<a href=https://{}/monitor/ack?aid={}&bid={}></a>'.format(SERVER_URL, alert.uuid, user.id)
    subject = 'Alert from {} Monitor'.format(channel.monitor.name)
    from_addr = 'Oldboy Monitor <admin@oldboy.net>'
    
    email = EmailMessage(subject, msg, from_addr, to_addr)
    return email

def make_restored_email(user, channel):
    to_addr = ['{} <{}>'.format(str(user.get_full_name()), user.email)]
    msg = 'Monitor: {}, '.format(channel.monitor.name)
    msg = msg + 'channel:{}\n'.format(channel.name)
    msg = msg + 'is reporting normal values.'
    html= '<span style="font-size: 150%;">Monitor: {}, '.format(channel.monitor.name)
    html = html + 'channel:{}<br />'.format(channel.name)
    html = html + 'is now reporting normal values.</span>'
    subject = 'Recovery Notice from Syliant Monitor'
    subject = 'Alert from {} Monitor'.format(channel.monitor.name)
    from_addr = 'Oldboy Monitor <admin@oldboy.net>'
    
    email = EmailMultiAlternatives(subject, msg, from_addr, to_addr)
    email.attach_alternative(html, "text/html")
    return email

def make_restored_text(user, channel):
    to_addr = ['{} <{}@{}>'.format(str(user.get_full_name()), user.text_number, user.text_provider)]
    msg = 'Monitor: {}, '.format(channel.monitor.name)
    msg = msg + 'channel:{}\n'.format(channel.name)
    msg = msg + 'is reporting normal values.'
    subject = 'Recovery Notice from {} Monitor'.format(channel.monitor.name)
    from_addr = 'Oldboy Monitor <admin@oldboy.net>'
    
    email = EmailMessage(subject, msg, from_addr, to_addr)
    return email

@shared_task
def process_alert(alert_id, restored=False):
    """ sends alerts to contacts associated with rules
    
    Inputs:
      alert_id - ID of the alert object
      restored - if the condition that caused the alert no longer exists, notify contacts about this

    Outputs:
      none
    """
    alert = Alert.objects.get(pk=alert_id)
    rule = alert.rule
    channel = alert.channel
    value = alert.reading.value
    print('processing alert {}'.format(alert_id))
    contacts = rule.contacts.all()
    if len(contacts) > 0 and (rule.action == Rule.SEND_EMAIL_TEXT_ALERT or rule.action == Rule.SEND_BOTH):
        for contact in contacts:
            emails = []
            if not contact.is_active:
                continue # don't send emails to inactive users
            preference = Preference.objects.get(user=contact)
            if preference.contact_method == Preference.EMAIL:
                if restored:
                    emails.append(make_restored_email(contact, channel))
                else:
                    emails.append(make_alert_email(contact, channel, rule, alert))
            elif preference.contact_method == Preference.TEXT:
                if restored:
                    emails.append(make_restored_text(contact, channel))
                else:
                    emails.append(make_alert_text(contact, channel, rule, alert))
            elif preference.contact_method == Preference.BOTH:
                if restored:
                    emails.append(make_restored_email(contact, channel))
                    emails.append(make_restored_text(contact, channel))
                else:
                    emails.append(make_alert_email(contact, channel, rule, alert))
                    emails.append(make_alert_text(contact, channel, rule, alert))

            for email in emails:
                if email.send() == 0:
                    return 'error'
                else:
                    print('Sent email to {}'.format(','.join(email.to)))

@shared_task
def unpause(rule_id):
    rule = Rule.objects.get(pk=rule_id)
    rule.state = Rule.RULE_ACTIVE
    rule.save()
    return 'rule #{} unpaused'.format(rule.id)
