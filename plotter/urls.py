from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_csv, name='upload_csv'),
    path('visualize/', views.visualize_data, name='visualize'),
    path('graph/', views.graph_view, name='graph_view'),
]
