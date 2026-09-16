from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"groups", views.GroupViewSet)
router.register(r"organs", views.OrganViewSet)
router.register(r"members", views.MemberViewSet)
router.register(r"positions", views.PositionViewSet)
router.register(r"meetings", views.MeetingViewSet)
router.register(r"meeting-entries", views.MeetingEntryViewSet)
router.register(r"contributions", views.ContributionViewSet)
router.register(r"documents", views.DocumentViewSet)
router.register(r"events", views.EventViewSet)
router.register(r"audit-logs", views.AuditLogViewSet)

urlpatterns = router.urls + [
    path("dashboard-summary/", views.dashboard_summary, name="dashboard_summary"),
]
