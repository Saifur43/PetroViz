from django.urls import path
from . import views

urlpatterns = [
    path('graph/', views.graph_view, name='graph_view'),
]
