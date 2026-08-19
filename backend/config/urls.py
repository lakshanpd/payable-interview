from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.circles.views import CreateCircleView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/auth/token/refresh', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/circles', CreateCircleView.as_view(), name='circle-create'),
    path('api/circles/', include('apps.circles.urls')),
    path('api/rounds/', include('apps.rounds.urls')),
]
