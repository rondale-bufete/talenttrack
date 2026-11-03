from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from recruiting import views

router = DefaultRouter()
router.register("jobs", views.JobViewSet, basename="job")
router.register("candidates", views.CandidateViewSet, basename="candidate")
router.register("applications", views.ApplicationViewSet, basename="application")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/stats/", views.stats, name="stats"),
    path("api/health/", views.health, name="health"),
    # Everything else -> React app (client-side routes like /jobs, /pipeline)
    re_path(r"^(?!api/|admin/|static/).*$", views.spa_index, name="spa"),
]
