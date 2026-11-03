from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Application, Candidate, Job
from .screening import BulkScreener
from .serializers import (
    ApplicationSerializer, CandidateSerializer, JobSerializer, StatusChangeSerializer,
)


class JobViewSet(viewsets.ModelViewSet):
    """
    /api/jobs/              GET list, POST create
    /api/jobs/{id}/         GET, PUT, PATCH, DELETE
    /api/jobs/{id}/screen/  POST  -> multithreaded screening of every application
    Query params: ?is_open=true  ?search=django
    """

    serializer_class = JobSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "department", "description"]
    ordering_fields = ["created_at", "title"]

    def get_queryset(self):
        qs = Job.objects.annotate(application_count=Count("applications")).order_by("-created_at")
        is_open = self.request.query_params.get("is_open")
        if is_open is not None:
            qs = qs.filter(is_open=is_open.lower() in ("1", "true", "yes"))
        return qs

    @action(detail=True, methods=["post"])
    def screen(self, request, pk=None):
        job = self.get_object()
        sequential = str(request.data.get("sequential", "")).lower() in ("1", "true")
        # select_related loads candidate + job in the same query (avoids N+1)
        apps = job.applications.select_related("candidate", "job").exclude(
            status=Application.Status.REJECTED
        )
        report = BulkScreener().run(apps, sequential=sequential)
        return Response({
            "job": job.id,
            "screened": report.screened,
            "failed": report.failed,
            "workers": report.workers,
            "elapsed_ms": report.elapsed_ms,
            "results": [r.__dict__ for r in report.results],
        })


class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    queryset = Candidate.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name", "email"]


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    /api/applications/?job=1&status=interview
    /api/applications/{id}/advance/   POST  -> next step in the pipeline
    /api/applications/{id}/status/    POST {"status": "rejected"}
    """

    serializer_class = ApplicationSerializer

    def get_queryset(self):
        qs = Application.objects.select_related("candidate", "job")
        params = self.request.query_params
        if params.get("job"):
            qs = qs.filter(job_id=params["job"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("candidate"):
            qs = qs.filter(candidate_id=params["candidate"])
        return qs

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        app = self.get_object()
        try:
            app.advance()
        except DjangoValidationError as exc:
            raise ValidationError({"status": exc.messages}) from exc
        app.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(app).data)

    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, pk=None):
        app = self.get_object()
        ser = StatusChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.apply(app)
        return Response(self.get_serializer(app).data)


@api_view(["GET"])
def stats(request):
    """Dashboard numbers. One aggregate query using conditional Count()."""
    per_status = Application.objects.aggregate(
        **{s.value: Count("id", filter=Q(status=s.value)) for s in Application.Status}
    )
    return Response({
        "open_jobs": Job.objects.filter(is_open=True).count(),
        "candidates": Candidate.objects.count(),
        "applications": sum(per_status.values()),
        "by_status": per_status,
    })


@api_view(["GET"])
def health(request):
    """Cloud Run / load balancer health check."""
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


def spa_index(request, *args, **kwargs):
    """Serve the built React app for any non-API URL so client-side routing works."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        raise Http404("Frontend not built. Run `npm run build` in /frontend.")
    return FileResponse(open(index, "rb"), content_type="text/html")
