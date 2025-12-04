from django.urls import path
from . import views, bha_views, drilling_views

urlpatterns = [
    # BHA Management URLs
    path('bha/', bha_views.bha_list, name='bha_list'),
    path('bha/<int:bha_id>/', bha_views.bha_detail, name='bha_detail'),
    path('bha/create/', bha_views.bha_create, name='bha_create'),
    path('bha/designer/', bha_views.bha_designer, name='bha_designer'),
    path('bha/<int:bha_id>/edit/', bha_views.bha_edit, name='bha_edit'),
    path('bha/<int:bha_id>/add-component/', bha_views.add_component, name='bha_add_component'),
    path('bha/validate-compatibility/', bha_views.validate_component_compatibility, name='bha_validate_compatibility'),
    path('bha/<int:bha_id>/export-pdf/', bha_views.bha_export_pdf, name='bha_export_pdf'),
    path('bha/<int:bha_id>/designer/', bha_views.bha_edit_designer, name='bha_edit_designer'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('credits/', views.credits, name='credits'),
    path('graph/', views.graph_view, name='graph_view'),
    path('production_graph/', views.production_graph, name='production_graph'),
    # New redesigned production data section
    path('production/fields/', views.production_fields, name='production_fields'),
    path('production/fields/<int:field_id>/', views.production_field_detail, name='production_field_detail'),
    path('production/well/<int:well_id>/', views.production_well_detail, name='production_well_detail'),
    path('exploration_timeline/', views.exploration_timeline_js, name='exploration_timeline'),
    path('api/well-data/', views.get_well_data, name='well_data'),
    path('api/field-wells/', views.get_field_wells, name='field-wells'),
    # List of wells (index) and per-well drilling reports
    path('drilling-reports/', drilling_views.drilling_reports_index, name='drilling_reports_index'),
    path('drilling-reports/<int:well_id>/list/', drilling_views.drilling_reports_list, name='drilling_reports_list'),
    path('drilling-reports/detail/<int:report_id>/', drilling_views.drilling_report_detail, name='drilling_report_detail'),
    path('drilling-reports/<int:report_id>/gas-shows/', drilling_views.gas_show_measurements_view, name='gas_show_measurements'),
    path('drilling-reports/<int:well_id>/', drilling_views.drilling_reports, name='drilling_reports'),
    path('drilling-lithology/create/', drilling_views.create_drilling_lithology, name='create_drilling_lithology'),
    path('drilling-reports/create/', drilling_views.create_drilling_report, name='create_drilling_report'),
    path('drilling-reports/upload-pdf/', drilling_views.upload_pdf_drilling_report, name='upload_pdf_drilling_report'),
    path('drilling-lithology/upload-pdf/', drilling_views.upload_pdf_lithology, name='upload_pdf_lithology'),
    path('drilling-reports/survey-tools/', drilling_views.survey_tools, name='survey_tools'),
    path('drilling-reports/upload-survey/', drilling_views.upload_well_survey, name='upload_well_survey'),
    path('drilling-reports/convert-depth/', drilling_views.convert_depth, name='convert_depth'),
    path('drilling-reports/populate-prognosis-md/', drilling_views.populate_prognosis_md, name='populate_prognosis_md'),
    path('drilling-reports/pdf/', drilling_views.generate_drilling_reports_pdf, name='generate_drilling_reports_pdf'),
]
