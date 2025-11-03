from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('credits/', views.credits, name='credits'),
    path('graph/', views.graph_view, name='graph_view'),
    path('production_graph/', views.production_graph, name='production_graph'),
    path('exploration_timeline/', views.exploration_timeline_js, name='exploration_timeline'),
    path('api/well-data/', views.get_well_data, name='well_data'),
    path('api/field-wells/', views.get_field_wells, name='field-wells'),
    path('drilling-reports/', views.drilling_reports, name='drilling_reports'),
    path('drilling-reports/pdf/', views.generate_drilling_reports_pdf, name='generate_drilling_reports_pdf'),
]
