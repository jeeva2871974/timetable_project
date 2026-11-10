from datetime import datetime, timedelta
from django.db.models import Q
from rest_framework import serializers
from .models import (
    Instructor, Course, Room, TimetableSlot, Section, Subject, Teacher, Period,
    SectionSubject, TeacherSubject, CombinedTeachingGroup, TeacherAvailability, TimetableConstraint,
    ScheduleEntry, TimetableBreak,
)


def _minutes_between(start_time, end_time):
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    return end_minutes - start_minutes


def _break_gap_error(kind, after_period, periods):
    next_period = next(
        (period for period in periods if period['number'] > after_period['number']),
        None,
    )
    if next_period is None:
        return f"Add a later period after Period {after_period['number']} for this break."

    gap_minutes = _minutes_between(after_period['end_time'], next_period['start_time'])
    duration_minutes = TimetableBreak.DURATIONS[kind]
    if gap_minutes != duration_minutes:
        break_name = dict(TimetableBreak.KIND_CHOICES)[kind].lower()
        return (
            f"The gap after Period {after_period['number']} must be exactly "
            f"{duration_minutes} minutes for the {break_name}."
        )
    return None


def _period_records(replacement=None, exclude_id=None):
    periods = [
        {
            'id': period.id,
            'number': period.number,
            'start_time': period.start_time,
            'end_time': period.end_time,
        }
        for period in Period.objects.all()
        if period.id != exclude_id
    ]
    if replacement:
        periods.append(replacement)
    return sorted(periods, key=lambda period: period['number'])


class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

class TimetableSlotSerializer(serializers.ModelSerializer):
    course_detail = CourseSerializer(source='course', read_only=True)
    instructor_detail = InstructorSerializer(source='instructor', read_only=True)
    room_detail = RoomSerializer(source='room', read_only=True)

    class Meta:
        model = TimetableSlot
        fields = '__all__'

    def validate(self, attrs):
        day = attrs.get('day', getattr(self.instance, 'day', None))
        start_time = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = attrs.get('end_time', getattr(self.instance, 'end_time', None))

        if day and start_time and end_time:
            conflicts = TimetableSlot.objects.filter(
                day=day,
                start_time=start_time,
                end_time=end_time,
            )
            if self.instance:
                conflicts = conflicts.exclude(pk=self.instance.pk)

            if conflicts.exists():
                raise serializers.ValidationError(
                    f"A slot is already scheduled on {day} from "
                    f"{start_time:%H:%M} to {end_time:%H:%M}. "
                    "Choose a different time."
                )

        return attrs


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = '__all__'


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = '__all__'

    def validate(self, attrs):
        start_time = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({'end_time': 'End time must be later than start time.'})
        if start_time and end_time:
            overlapping_periods = Period.objects.filter(
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if self.instance:
                overlapping_periods = overlapping_periods.exclude(pk=self.instance.pk)
            if overlapping_periods.exists():
                raise serializers.ValidationError(
                    {'start_time': 'Period times cannot overlap another configured period.'}
                )

        replacement = {
            'id': self.instance.id if self.instance else None,
            'number': attrs.get('number', getattr(self.instance, 'number', None)),
            'start_time': start_time,
            'end_time': end_time,
        }
        periods = _period_records(
            replacement,
            exclude_id=self.instance.id if self.instance else None,
        )
        for timetable_break in TimetableBreak.objects.select_related('after_period'):
            after_period = next(
                (period for period in periods if period['id'] == timetable_break.after_period_id),
                None,
            )
            if after_period is None:
                continue
            error = _break_gap_error(timetable_break.kind, after_period, periods)
            if error:
                raise serializers.ValidationError({'start_time': error})
        return attrs


class TimetableBreakSerializer(serializers.ModelSerializer):
    after_period = serializers.PrimaryKeyRelatedField(queryset=Period.objects.all())
    after_period_number = serializers.IntegerField(source='after_period.number', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = TimetableBreak
        fields = (
            'id',
            'kind',
            'after_period',
            'after_period_number',
            'duration_minutes',
            'start_time',
            'end_time',
        )

    def get_duration_minutes(self, instance):
        return instance.duration_minutes

    def get_start_time(self, instance):
        return instance.after_period.end_time.strftime('%H:%M:%S')

    def get_end_time(self, instance):
        start = datetime.combine(datetime.min.date(), instance.after_period.end_time)
        end = start + timedelta(minutes=instance.duration_minutes)
        return end.time().strftime('%H:%M:%S')

    def validate(self, attrs):
        kind = attrs.get('kind', getattr(self.instance, 'kind', None))
        after_period = attrs.get('after_period', getattr(self.instance, 'after_period', None))
        periods = _period_records()
        after_record = next(
            (period for period in periods if period['id'] == after_period.id),
            None,
        )
        if after_record is None:
            raise serializers.ValidationError({'after_period': 'Select an existing period.'})

        error = _break_gap_error(kind, after_record, periods)
        if error:
            raise serializers.ValidationError({'after_period': error})
        return attrs


class SectionSubjectSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = SectionSubject
        fields = '__all__'

    def validate_periods_per_week(self, value):
        available_periods = Period.objects.count() * len(TimetableSlot.DAYS_OF_WEEK)
        if value > available_periods:
            raise serializers.ValidationError(
                f"Weekly periods cannot exceed the {available_periods} available periods."
            )
        return value

    def validate(self, attrs):
        section = attrs.get('section', getattr(self.instance, 'section', None))
        subject = attrs.get('subject', getattr(self.instance, 'subject', None))
        periods_per_week = attrs.get(
            'periods_per_week',
            getattr(self.instance, 'periods_per_week', None),
        )
        if section is None or periods_per_week is None:
            return attrs

        other_assignments = SectionSubject.objects.filter(section=section)
        if self.instance:
            other_assignments = other_assignments.exclude(pk=self.instance.pk)
        already_assigned = sum(
            other_assignments.values_list('periods_per_week', flat=True)
        )
        available_periods = Period.objects.count() * len(TimetableSlot.DAYS_OF_WEEK)
        total_required = already_assigned + periods_per_week
        if total_required > available_periods:
            raise serializers.ValidationError({
                'periods_per_week': (
                    f"{section.name} already has {already_assigned} weekly periods assigned. "
                    f"This would total {total_required}, exceeding the "
                    f"{available_periods} available periods. Reduce or remove another "
                    "subject requirement first."
                )
            })
        fixed_classes = TimetableConstraint.objects.filter(
            section=section,
            subject=subject,
        )
        if self.instance:
            if (
                (self.instance.section_id != section.id or self.instance.subject_id != subject.id)
                and TimetableConstraint.objects.filter(
                    section=self.instance.section,
                    subject=self.instance.subject,
                ).exists()
            ):
                raise serializers.ValidationError({
                    'section': (
                        'Remove fixed classes for this section and subject before changing '
                        'the weekly assignment.'
                    )
                })
        fixed_count = fixed_classes.count()
        if fixed_count > periods_per_week:
            raise serializers.ValidationError({
                'periods_per_week': (
                    f"{fixed_count} fixed classes already reference this section and subject. "
                    f"The weekly requirement cannot be reduced below {fixed_count}."
                )
            })
        return attrs


class TeacherSubjectSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True, allow_null=True)
    section = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(),
        required=True,
        allow_null=False,
    )

    class Meta:
        model = TeacherSubject
        fields = '__all__'

    def validate(self, attrs):
        teacher = attrs.get('teacher', getattr(self.instance, 'teacher', None))
        subject = attrs.get('subject', getattr(self.instance, 'subject', None))
        section = attrs.get('section', getattr(self.instance, 'section', None))
        if section is None:
            raise serializers.ValidationError({'section': 'Select a class for this mapping.'})
        if self.instance and (
            teacher != self.instance.teacher
            or subject != self.instance.subject
            or section != self.instance.section
        ) and self.instance.section_id and CombinedTeachingGroup.objects.filter(
            teacher=self.instance.teacher,
            subject=self.instance.subject,
            sections=self.instance.section,
        ).exists():
            raise serializers.ValidationError(
                'Remove the combined class group before changing this teacher mapping.'
            )
        duplicate = TeacherSubject.objects.filter(
            teacher=teacher,
            subject=subject,
            section=section,
        )
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError(
                'This teacher is already mapped to this subject for the selected class.'
            )
        if self.instance and (
            teacher != self.instance.teacher
            or subject != self.instance.subject
            or section != self.instance.section
        ):
            fixed_classes = TimetableConstraint.objects.filter(
                teacher=self.instance.teacher,
                subject=self.instance.subject,
            )
            if self.instance.section_id:
                fixed_classes = fixed_classes.filter(
                    section_id=self.instance.section_id,
                )
            elif teacher == self.instance.teacher and subject == self.instance.subject:
                fixed_classes = fixed_classes.exclude(section=section)
            if fixed_classes.exists():
                raise serializers.ValidationError(
                    'Remove fixed classes using this mapping before changing it.'
                )
        return attrs


class CombinedTeachingGroupSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    section_names = serializers.SerializerMethodField()

    class Meta:
        model = CombinedTeachingGroup
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'subject',
            'subject_name',
            'sections',
            'section_names',
            'periods_per_week',
        )
        read_only_fields = fields

    def get_section_names(self, instance):
        return list(instance.sections.order_by('name').values_list('name', flat=True))


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    period_number = serializers.IntegerField(source='period.number', read_only=True)

    class Meta:
        model = TeacherAvailability
        fields = '__all__'

    def validate(self, attrs):
        teacher = attrs.get('teacher', getattr(self.instance, 'teacher', None))
        day = attrs.get('day', getattr(self.instance, 'day', None))
        period = attrs.get('period', getattr(self.instance, 'period', None))
        is_available = attrs.get(
            'is_available',
            getattr(self.instance, 'is_available', True),
        )
        if not is_available and teacher and day and period and TimetableConstraint.objects.filter(
            teacher=teacher,
            day=day,
            period=period,
        ).exists():
            raise serializers.ValidationError({
                'is_available': 'Remove the fixed class before marking this teacher unavailable.'
            })
        return attrs


class TimetableConstraintSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    period_number = serializers.IntegerField(source='period.number', read_only=True)
    shared_group = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TimetableConstraint
        fields = '__all__'

    def validate(self, attrs):
        if self.instance and self.instance.shared_group_id:
            raise serializers.ValidationError(
                'Edit or remove a combined fixed class through its participating sections.'
            )

        section = attrs.get('section', getattr(self.instance, 'section', None))
        subject = attrs.get('subject', getattr(self.instance, 'subject', None))
        teacher = attrs.get('teacher', getattr(self.instance, 'teacher', None))
        day = attrs.get('day', getattr(self.instance, 'day', None))
        period = attrs.get('period', getattr(self.instance, 'period', None))

        assignment = None
        if section and subject:
            assignment = SectionSubject.objects.filter(
                section=section,
                subject=subject,
            ).first()
        if section and subject and assignment is None:
            raise serializers.ValidationError(
                {'subject': 'Assign this subject to the selected section in the weekly teaching plan first.'}
            )
        if section and subject and CombinedTeachingGroup.objects.filter(
            subject=subject,
            sections=section,
        ).exists():
            raise serializers.ValidationError(
                {'subject': 'Remove the combined class group before fixing this class.'}
            )
        if section and subject and teacher and not TeacherSubject.objects.filter(
            subject=subject,
            teacher=teacher,
        ).filter(Q(section=section) | Q(section__isnull=True)).exists():
            raise serializers.ValidationError(
                {'teacher': 'Map this teacher to the selected subject before adding a fixed class.'}
            )
        if teacher and day and period and TeacherAvailability.objects.filter(
            teacher=teacher,
            day=day,
            period=period,
            is_available=False,
        ).exists():
            raise serializers.ValidationError(
                {'period': 'This teacher is marked unavailable at the selected time.'}
            )

        if section and day and period:
            section_slot_constraints = TimetableConstraint.objects.filter(
                section=section,
                day=day,
                period=period,
            )
            teacher_slot_constraints = TimetableConstraint.objects.filter(
                teacher=teacher,
                day=day,
                period=period,
            )
            if self.instance:
                section_slot_constraints = section_slot_constraints.exclude(pk=self.instance.pk)
                teacher_slot_constraints = teacher_slot_constraints.exclude(pk=self.instance.pk)
            if section_slot_constraints.exists():
                raise serializers.ValidationError(
                    {'period': 'This section already has a fixed class at the selected time.'}
                )
            if teacher_slot_constraints.exists():
                raise serializers.ValidationError(
                    {'teacher': 'This teacher is already fixed to another section at the selected time.'}
                )

        if assignment and section and subject:
            fixed_classes = TimetableConstraint.objects.filter(
                section=section,
                subject=subject,
            )
            if self.instance:
                fixed_classes = fixed_classes.exclude(pk=self.instance.pk)
            if fixed_classes.count() >= assignment.periods_per_week:
                raise serializers.ValidationError({
                    'period': (
                        f"The weekly teaching plan allows {assignment.periods_per_week} "
                        f"{subject.name} periods for {section.name}, and all are already fixed."
                    )
                })

        return attrs


class ScheduleEntrySerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    period_number = serializers.IntegerField(source='period.number', read_only=True)
    start_time = serializers.TimeField(source='period.start_time', read_only=True)
    end_time = serializers.TimeField(source='period.end_time', read_only=True)

    class Meta:
        model = ScheduleEntry
        fields = '__all__'

    def validate(self, attrs):
        section = attrs.get('section', getattr(self.instance, 'section', None))
        subject = attrs.get('subject', getattr(self.instance, 'subject', None))
        teacher = attrs.get('teacher', getattr(self.instance, 'teacher', None))
        day = attrs.get('day', getattr(self.instance, 'day', None))
        period = attrs.get('period', getattr(self.instance, 'period', None))

        if section and subject and not SectionSubject.objects.filter(
            section=section,
            subject=subject,
        ).exists():
            raise serializers.ValidationError({'subject': 'This subject is not assigned to the section.'})
        if section and subject and teacher and not TeacherSubject.objects.filter(
            subject=subject,
            teacher=teacher,
        ).filter(Q(section=section) | Q(section__isnull=True)).exists():
            raise serializers.ValidationError({'teacher': 'This teacher is not mapped to the subject.'})
        if teacher and day and period and TeacherAvailability.objects.filter(
            teacher=teacher,
            day=day,
            period=period,
            is_available=False,
        ).exists():
            raise serializers.ValidationError({'period': 'This teacher is marked unavailable at that time.'})

        if section and day and period:
            section_conflicts = ScheduleEntry.objects.filter(
                section=section,
                day=day,
                period=period,
            )
            if self.instance:
                section_conflicts = section_conflicts.exclude(pk=self.instance.pk)
            if section_conflicts.exists():
                raise serializers.ValidationError({'period': 'This section already has a class at that time.'})

            constraint = TimetableConstraint.objects.filter(
                section=section,
                day=day,
                period=period,
            ).first()
            if constraint and (constraint.subject_id != subject.id or constraint.teacher_id != teacher.id):
                raise serializers.ValidationError(
                    {'period': 'This time is reserved by a timetable constraint.'}
                )

        if self.instance:
            original_constraint = TimetableConstraint.objects.filter(
                section=self.instance.section,
                day=self.instance.day,
                period=self.instance.period,
            ).first()
            if original_constraint and (
                original_constraint.subject_id != subject.id
                or original_constraint.teacher_id != teacher.id
                or original_constraint.day != day
                or original_constraint.period_id != period.id
                or original_constraint.section_id != section.id
            ):
                raise serializers.ValidationError(
                    {'period': 'This class is fixed by a timetable constraint and cannot be moved.'}
                )

        if teacher and day and period:
            teacher_conflicts = ScheduleEntry.objects.filter(
                teacher=teacher,
                day=day,
                period=period,
            )
            if self.instance:
                teacher_conflicts = teacher_conflicts.exclude(pk=self.instance.pk)
            shared_group_id = None
            if section:
                fixed_constraint = TimetableConstraint.objects.filter(
                    section=section,
                    day=day,
                    period=period,
                ).first()
                if (
                    fixed_constraint
                    and fixed_constraint.shared_group_id
                    and fixed_constraint.subject_id == subject.id
                    and fixed_constraint.teacher_id == teacher.id
                ):
                    shared_group_id = fixed_constraint.shared_group_id
            if teacher_conflicts.exists():
                conflict_constraints = {
                    constraint.section_id: constraint.shared_group_id
                    for constraint in TimetableConstraint.objects.filter(
                        section_id__in=teacher_conflicts.values('section_id'),
                        day=day,
                        period=period,
                    )
                }
                can_share_teacher_slot = (
                    shared_group_id is not None
                    and all(
                        conflict_constraints.get(conflict.section_id) == shared_group_id
                        for conflict in teacher_conflicts
                    )
                )
                if not can_share_teacher_slot:
                    raise serializers.ValidationError(
                        {'teacher': 'This teacher already has a class at that time.'}
                    )
        return attrs