from garage import views
from django.conf.urls import url

urlpatterns = [
    url(r'^control/', views.control, name="control"),
    url(r'^particle_open', views.particle_open, name="particle_open"),
]
