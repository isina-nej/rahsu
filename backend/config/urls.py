from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.geo.views import ObstacleListView, ObstacleReportView, ModerateReportsView
from apps.operations.views import LiveView, ReadyView, LogsView, VersionView
from apps.operations.views_metrics import MetricsView
from apps.routing.views import EstimateView
from apps.vehicles.views import VehicleListView
from apps.calibration.views import ObservedTripView, HoldoutMetricsView
from apps.routing.geocoding import GeocodeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/health/live", LiveView.as_view()),
    path("metrics/", MetricsView.as_view()),
    path("api/v1/health/ready", ReadyView.as_view()),
    path("api/v1/meta/version", VersionView.as_view()),
    path("api/v1/vehicles/", VehicleListView.as_view()),
    path("api/v1/trips/observations/", ObservedTripView.as_view()),
    path("api/v1/admin/calibration/metrics/", HoldoutMetricsView.as_view()),
    path("api/v1/geocode/", GeocodeView.as_view()),
    path("api/v1/estimates/", EstimateView.as_view()),
    path("api/v1/obstacles/", ObstacleListView.as_view()),
    path("api/v1/obstacle-reports/", ObstacleReportView.as_view()),
    path("api/v1/admin/obstacle-reports/", ModerateReportsView.as_view()),
    path("api/v1/admin/observability/logs", LogsView.as_view()),
]
