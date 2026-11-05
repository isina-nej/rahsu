from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.geo.views import ObstacleListView, ObstacleReportView, ModerateReportsView
from apps.operations.views import LiveView, ReadyView, LogsView, VersionView, MetricsSummaryView, TraceView
from apps.operations.views_metrics import MetricsView
from apps.routing.views import EstimateView
from apps.vehicles.views import VehicleListView
from apps.calibration.views import ObservedTripView, HoldoutMetricsView
from apps.operations.auth import CsrfView, AuthStatusView, LoginView, LogoutView, RegisterView
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
    path("api/v1/auth/csrf/", CsrfView.as_view()),
    path("api/v1/auth/me/", AuthStatusView.as_view()),
    path("api/v1/auth/login/", LoginView.as_view()),
    path("api/v1/auth/logout/", LogoutView.as_view()),
    path("api/v1/auth/register/", RegisterView.as_view()),
    path("api/v1/trips/observations/", ObservedTripView.as_view()),
    path("api/v1/admin/calibration/metrics/", HoldoutMetricsView.as_view()),
    path("api/v1/geocode/", GeocodeView.as_view()),
    path("api/v1/estimates/", EstimateView.as_view()),
    path("api/v1/obstacles/", ObstacleListView.as_view()),
    path("api/v1/obstacle-reports/", ObstacleReportView.as_view()),
    path("api/v1/admin/obstacle-reports/", ModerateReportsView.as_view()),
    path("api/v1/admin/observability/logs", LogsView.as_view()),
    path("api/v1/admin/observability/metrics/summary", MetricsSummaryView.as_view()),
    path("api/v1/admin/observability/traces/<str:trace_id>", TraceView.as_view()),
]
