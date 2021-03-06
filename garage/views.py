from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from automation.settings import PARTICLE_DEVICE_ID, PARTICLE_ACCESS_TOKEN
import requests
import json

@login_required
def control(request):
    return render(request, 'garage/control.html', {})

@login_required
def particle_open(request):
    url = "https://api.particle.io/v1/devices/"
    url += PARTICLE_DEVICE_ID
    url += "/led?access_token="
    url += PARTICLE_ACCESS_TOKEN
    data = {'command': 'on'}
    r = requests.post(url, data=data)
    result = json.loads(r.text)
    # if not result['ok']:
    #     context = {'failure': True, 'result': result}
    # else:
    context = {'success': True, 'result': result}
    return render(request, 'garage/result.html', context)

