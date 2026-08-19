from django.urls import path

from .views import CircleDetailView, JoinCircleView

# Note: POST /api/circles (create) is registered directly in config/urls.py
# since it has no trailing segment, and this app's urls are all mounted
# under the 'api/circles/' prefix.
urlpatterns = [
    path('join', JoinCircleView.as_view(), name='circle-join'),
    path('<int:pk>', CircleDetailView.as_view(), name='circle-detail'),
]
