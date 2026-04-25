from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path
from django.urls import re_path
from django.views.static import serve


def frontend_app(request):
    index_path = settings.STATIC_ROOT / "index.html"
    if not index_path.exists():
        raise Http404("Frontend build not found.")
    return FileResponse(index_path.open("rb"), content_type="text/html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("kyc.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    re_path(r"^(?!static/|media/).*$", frontend_app, name="frontend-app"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
