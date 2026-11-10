from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InstructorViewSet, CourseViewSet, RoomViewSet, TimetableSlotViewSet,
    SectionViewSet, SubjectViewSet, TeacherViewSet, PeriodViewSet,
    SectionSubjectViewSet, TeacherSubjectViewSet, CombinedTeachingGroupViewSet,
    TeacherAvailabilityViewSet,
    TimetableConstraintViewSet, ScheduleEntryViewSet, TimetableBreakViewSet,
)

router = DefaultRouter()
router.register(r'instructors', InstructorViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'rooms', RoomViewSet)
router.register(r'timetable', TimetableSlotViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'periods', PeriodViewSet)
router.register(r'timetable-breaks', TimetableBreakViewSet)
router.register(r'section-subjects', SectionSubjectViewSet)
router.register(r'teacher-subjects', TeacherSubjectViewSet)
router.register(r'combined-teaching-groups', CombinedTeachingGroupViewSet)
router.register(r'teacher-availability', TeacherAvailabilityViewSet)
router.register(r'constraints', TimetableConstraintViewSet)
router.register(r'schedule', ScheduleEntryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]