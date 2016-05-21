from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
import datetime
from dateutil import tz
import time
import json
from collections import OrderedDict
from monitor.models import Channel, Reading, Unit, Preference, Alert, User

@login_required
def index(request):
    channels = Channel.objects.filter(status__in=[Channel.ENABLED, Channel.PAUSED])
    latest_readings = {}
    user_system = Preference.objects.get(user=request.user).measurement_system

    # for time conversion  UTC to local
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz('America/New_York')

    for channel in channels:
        channel_system = channel.channel_type.measurement_system
        latest = Reading.objects.filter(channel=channel, is_valid=True).order_by('-monitor_time')
        if len(latest) > 0:
            reading = latest[0]
            if user_system == channel_system:
                value = reading.value
            elif user_system == Unit.IMPERIAL:
                value = channel.channel_type.units.m_to_i(reading.value)
            else:
                value = channel.channel_type.units.i_to_m(reading.value)

            utc = reading.monitor_time.replace(tzinfo=from_zone)
            eastern = utc.astimezone(to_zone).strftime("%b %d, %Y %H:%M:%S")
            units = channel.get_unit_abbrevs()[user_system]
            alerts = Alert.objects.filter(channel=channel, active=True)
            if len(alerts) > 0:
                status = 'alert'
            else:
                status = 'ok'
            latest_readings[channel.__str__()] = [value, channel.id, units, eastern, status]
    return render(request, 'monitor/dashboard.html', {'latest_readings': latest_readings})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect(request.POST['next'])
            else:
                # Return a 'disabled account' error message
                return HttpResponse('account disabled')
        else:
            next = request.GET.get('next', '/monitor/index')
            # Return an 'invalid login' error message.
            return render(request, 'monitor/login.html', {'next': next, 'invalid': True})

    else: # present the login page
        next = request.GET.get('next', '/monitor/index')
        return render(request, 'monitor/login.html', {'next':next})

def user_logout(request):
    logout(request)
    return render(request, 'monitor/login.html', {'next':'/monitor/index/'})

def channel(request, channel_id, days=30):
    chan = Channel.objects.get(pk=channel_id)

    units = chan.channel_type.units
    system = Preference.objects.get(user=request.user).measurement_system
    context = {'channel': chan, 'days': days, 'units': units, 'system': system}
    return render(request, 'monitor/channel_detail.html', context)
    
def get_readings(request, channel_id, days=30):
    chan = Channel.objects.get(pk=channel_id)
    days_ago = datetime.timedelta(days=int(days))
    earliest = datetime.datetime.now() - days_ago
    readings = Reading.objects.filter(channel=chan, monitor_time__gt=earliest, is_valid=True).order_by('monitor_time')
    response_data = OrderedDict()
    user_pref = Preference.objects.get(user = request.user)
    user_system = user_pref.measurement_system
    channel_system = chan.channel_type.measurement_system
    response_data['unit'] = chan.get_units()[user_system]

    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz('America/New_York')

    for reading in readings:
        if channel_system == user_system:
            value = reading.value
        elif user_system == Unit.IMPERIAL:
            value = reading.channel.channel_type.units.m_to_i(reading.value)
        else:
            value = reading.channel.channel_type.units.i_to_m(reading.value)
        
        utc = reading.monitor_time.replace(tzinfo=from_zone)
        eastern = utc.astimezone(to_zone)
        
        response_data[eastern.strftime("%Y-%m-%d %H:%M:%S")] = value
    
    return HttpResponse(json.dumps(response_data), content_type="application/json")
    
def ack(request):
    alert = Alert.objects.get(uuid=request.GET.get('aid'))
    if request.method == 'POST':
        user = User.objects.get(pk=request.GET.get('bid'))
        now = datetime.datetime.now()
        alert.acknowledged_by = user
        alert.acknowledged_time = now
        alert.save()
        context = {'alert': alert, 'user': user, 'success': True}

    elif alert.acknowledged_by:
        context = {'alert': alert, 'acknowledger': alert.acknowledged_by, 'acknowledged_time': alert.acknowledged_time, 'previously_acked': True}

    else:
        acknowledger = User.objects.get(pk=request.GET.get('bid'))
        context = {'alert': alert, 'acknowledger': acknowledger}

    return render(request, 'monitor/alert_ack.html', context)
