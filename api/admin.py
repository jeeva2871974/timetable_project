from django.contrib import admin
from .models import (
    Instructor, Course, Room, TimetableSlot, Section, Subject, Teacher, Period,
    SectionSubject, TeacherSubject, TeacherAvailability, TimetableConstraint,
    SharedClassGroup,
    ScheduleEntry,
)

admin.site.register(Instructor)
admin.site.register(Course)
admin.site.register(Room)
admin.site.register(TimetableSlot)
admin.site.register(Section)
admin.site.register(Subject)
admin.site.register(Teacher)
admin.site.register(Period)
admin.site.register(SectionSubject)
admin.site.register(TeacherSubject)
admin.site.register(TeacherAvailability)
admin.site.register(TimetableConstraint)
admin.site.register(SharedClassGroup)
admin.site.register(ScheduleEntry)