from django.urls import path

from .views import ApproveRoundView, ContributeView, RoundDetailView

urlpatterns = [
    path('<int:pk>', RoundDetailView.as_view(), name='round-detail'),
    path('<int:pk>/contribute', ContributeView.as_view(), name='round-contribute'),
    path('<int:pk>/approve', ApproveRoundView.as_view(), name='round-approve'),
]
