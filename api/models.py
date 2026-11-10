from django.db import models


class Instructor(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    credits = models.IntegerField()

    def __str__(self):
        return f"{self.code} - {self.name}"


class Room(models.Model):
    room_number = models.CharField(max_length=50, unique=True)
    building = models.CharField(max_length=100)
    capacity = models.IntegerField()

    def __str__(self):
        return f"{self.building} - {self.room_number}"


class TimetableSlot(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
    ]

    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    semester = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.day} ({self.start_time}-{self.end_time}): {self.course.name}"


class Section(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    BASIC = 'basic'
    ACTIVITY = 'activity'
    CATEGORY_CHOICES = [
        (BASIC, 'Basic'),
        (ACTIVITY, 'Activity'),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        default=BASIC,
    )

    def __str__(self):
        return self.name


class Teacher(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Period(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Period {self.number}"


class TimetableBreak(models.Model):
    BREAK = 'break'
    LUNCH = 'lunch'
    KIND_CHOICES = [
        (BREAK, 'Break'),
        (LUNCH, 'Lunch'),
    ]
    DURATIONS = {
        BREAK: 15,
        LUNCH: 45,
    }

    kind = models.CharField(max_length=10, choices=KIND_CHOICES, unique=True)
    after_period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name='timetable_breaks',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('after_period',),
                name='unique_timetable_break_after_period',
            ),
        ]
        ordering = ['after_period__number']

    @property
    def duration_minutes(self):
        return self.DURATIONS[self.kind]

    def __str__(self):
        return f"{self.get_kind_display()} after period {self.after_period.number}"


class SectionSubject(models.Model):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='section_assignments',
    )
    periods_per_week = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('section', 'subject'),
                name='unique_section_subject',
            ),
            models.CheckConstraint(
                condition=models.Q(periods_per_week__gt=0),
                name='section_subject_periods_positive',
            ),
        ]

    def __str__(self):
        return f"{self.section} - {self.subject}"


class TeacherSubject(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='subject_mappings',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='teacher_mappings',
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='teacher_subject_mappings',
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('teacher', 'subject', 'section'),
                name='unique_teacher_subject_section',
            ),
        ]

    def __str__(self):
        section_name = self.section.name if self.section_id else 'All classes'
        return f"{self.teacher} - {self.subject} - {section_name}"


class CombinedTeachingGroup(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='combined_teaching_groups',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='combined_teaching_groups',
    )
    sections = models.ManyToManyField(
        Section,
        related_name='combined_teaching_groups',
    )
    periods_per_week = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(periods_per_week__gt=0),
                name='combined_teaching_periods_positive',
            ),
        ]

    def __str__(self):
        return f"{self.subject} - {self.teacher} ({self.periods_per_week} periods/week)"


class TeacherAvailability(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='availability',
    )
    day = models.CharField(max_length=10, choices=TimetableSlot.DAYS_OF_WEEK)
    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name='teacher_availability',
    )
    is_available = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('teacher', 'day', 'period'),
                name='unique_teacher_availability',
            ),
        ]

    def __str__(self):
        return f"{self.teacher} - {self.day}, period {self.period.number}"


class SharedClassGroup(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=TimetableSlot.DAYS_OF_WEEK)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.subject} - {self.day}, period {self.period.number}"


class TimetableConstraint(models.Model):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='timetable_constraints',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='timetable_constraints',
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='timetable_constraints',
    )
    day = models.CharField(max_length=10, choices=TimetableSlot.DAYS_OF_WEEK)
    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name='timetable_constraints',
    )
    shared_group = models.ForeignKey(
        SharedClassGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='constraints',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('section', 'day', 'period'),
                name='unique_constraint_section_slot',
            ),
        ]

    def __str__(self):
        return f"{self.section} - {self.day}, period {self.period.number}"


class ScheduleEntry(models.Model):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='schedule_entries',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='schedule_entries',
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='schedule_entries',
    )
    day = models.CharField(max_length=10, choices=TimetableSlot.DAYS_OF_WEEK)
    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name='schedule_entries',
    )

    class Meta:
        ordering = ['section__name', 'day', 'period__number']
        constraints = [
            models.UniqueConstraint(
                fields=('section', 'day', 'period'),
                name='unique_schedule_section_slot',
            ),
        ]

    def __str__(self):
        return f"{self.section} - {self.subject} - {self.day}, period {self.period.number}"
