from django.shortcuts import get_object_or_404

# Create your views here.
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import (
    Instructor, Course, Room, TimetableSlot, Section, Subject, Teacher, Period,
    SectionSubject, TeacherSubject, CombinedTeachingGroup, TeacherAvailability, TimetableConstraint,
    SharedClassGroup,
    ScheduleEntry, TimetableBreak,
)
from .serializers import (
    InstructorSerializer, CourseSerializer, 
    RoomSerializer, TimetableSlotSerializer, SectionSerializer, SubjectSerializer,
    TeacherSerializer, PeriodSerializer, SectionSubjectSerializer,
    TeacherSubjectSerializer, CombinedTeachingGroupSerializer, TeacherAvailabilitySerializer,
    TimetableConstraintSerializer, ScheduleEntrySerializer,
    TimetableBreakSerializer,
)
from .scheduler import build_schedule, distribute_weekly_periods


def _plan_adjustment_details(adjustments):
    assignments = SectionSubject.objects.select_related(
        'section',
        'subject',
    ).filter(id__in=adjustments).order_by('section__name', 'subject__name')
    return [
        {
            'section': assignment.section.name,
            'subject': assignment.subject.name,
            'from_periods_per_week': assignment.periods_per_week,
            'to_periods_per_week': adjustments[assignment.id],
        }
        for assignment in assignments
    ]


class InstructorViewSet(viewsets.ModelViewSet):
    queryset = Instructor.objects.all()
    serializer_class = InstructorSerializer

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

class TimetableSlotViewSet(viewsets.ModelViewSet):
    queryset = TimetableSlot.objects.all()
    serializer_class = TimetableSlotSerializer


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.order_by('name')
    serializer_class = SectionSerializer


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.order_by('name')
    serializer_class = SubjectSerializer


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.order_by('name')
    serializer_class = TeacherSerializer


class PeriodViewSet(viewsets.ModelViewSet):
    queryset = Period.objects.order_by('number')
    serializer_class = PeriodSerializer

    def perform_destroy(self, instance):
        periods = list(Period.objects.exclude(pk=instance.pk).order_by('number'))
        for timetable_break in TimetableBreak.objects.select_related('after_period'):
            if timetable_break.after_period_id == instance.id:
                raise ValidationError({
                    'detail': (
                        f"Move or remove the {timetable_break.get_kind_display().lower()} "
                        f"configured after Period {instance.number} before deleting it."
                    )
                })

            next_period = next(
                (
                    period for period in periods
                    if period.number > timetable_break.after_period.number
                ),
                None,
            )
            if next_period is None:
                raise ValidationError({
                    'detail': (
                        f"Deleting Period {instance.number} would leave the configured "
                        f"{timetable_break.get_kind_display().lower()} without a later period."
                    )
                })

            gap_minutes = (
                next_period.start_time.hour * 60 + next_period.start_time.minute
                - timetable_break.after_period.end_time.hour * 60
                - timetable_break.after_period.end_time.minute
            )
            if gap_minutes != timetable_break.duration_minutes:
                raise ValidationError({
                    'detail': (
                        f"Deleting Period {instance.number} would change the gap for the "
                        f"configured {timetable_break.get_kind_display().lower()}. "
                        "Adjust the break placement first."
                    )
                })
        instance.delete()


class TimetableBreakViewSet(viewsets.ModelViewSet):
    queryset = TimetableBreak.objects.select_related('after_period').order_by(
        'after_period__number',
    )
    serializer_class = TimetableBreakSerializer


class SectionSubjectViewSet(viewsets.ModelViewSet):
    queryset = SectionSubject.objects.select_related('section', 'subject').order_by('section__name', 'subject__name')
    serializer_class = SectionSubjectSerializer

    def perform_destroy(self, instance):
        if TimetableConstraint.objects.filter(
            section=instance.section,
            subject=instance.subject,
        ).exists():
            raise ValidationError(
                {'detail': 'Remove fixed classes for this subject before deleting its weekly assignment.'}
            )
        instance.delete()

    @action(detail=False, methods=['post'], url_path='configure-section')
    def configure_section(self, request):
        section_id = request.data.get('section')
        subject_ids = request.data.get('subject_ids')
        if not isinstance(subject_ids, list) or not subject_ids:
            raise ValidationError({'subject_ids': 'Select at least one subject.'})
        if any(not isinstance(subject_id, int) or isinstance(subject_id, bool) for subject_id in subject_ids):
            raise ValidationError({'subject_ids': 'Subject IDs must be integers.'})
        if len(subject_ids) != len(set(subject_ids)):
            raise ValidationError({'subject_ids': 'Each subject can only be selected once.'})

        section = get_object_or_404(Section, pk=section_id)
        subjects_by_id = Subject.objects.in_bulk(subject_ids)
        missing_ids = sorted(set(subject_ids) - set(subjects_by_id))
        if missing_ids:
            raise ValidationError({'subject_ids': f'Unknown subject IDs: {missing_ids}.'})

        capacity = Period.objects.count() * len(TimetableSlot.DAYS_OF_WEEK)
        if not capacity:
            raise ValidationError({'detail': 'Configure periods before setting a weekly teaching plan.'})
        if len(subject_ids) > capacity:
            raise ValidationError({
                'subject_ids': f'Select no more than {capacity} subjects for this section.'
            })

        fixed_counts = {}
        fixed_classes = TimetableConstraint.objects.filter(section=section)
        for constraint in fixed_classes:
            fixed_counts[constraint.subject_id] = fixed_counts.get(constraint.subject_id, 0) + 1
        unselected_fixed_subjects = set(fixed_counts) - set(subject_ids)
        if unselected_fixed_subjects:
            names = sorted(
                subjects_by_id[subject_id].name
                if subject_id in subjects_by_id
                else Subject.objects.get(pk=subject_id).name
                for subject_id in unselected_fixed_subjects
            )
            raise ValidationError({
                'subject_ids': (
                    f'Remove or keep the fixed classes for {", ".join(names)} in this plan.'
                )
            })
        if sum(fixed_counts.values()) > capacity:
            raise ValidationError({
                'detail': 'The section has more fixed classes than available weekly periods.'
            })

        ordered_subject_ids = sorted(subject_ids)
        categories = {
            subject_id: subjects_by_id[subject_id].category
            for subject_id in ordered_subject_ids
        }
        try:
            allocations = distribute_weekly_periods(
                ordered_subject_ids,
                fixed_counts,
                capacity,
                categories,
            )
        except ValueError as error:
            raise ValidationError({'subject_ids': str(error)}) from error

        existing = {
            assignment.subject_id: assignment
            for assignment in self.get_queryset().filter(section=section)
        }
        with transaction.atomic():
            SectionSubject.objects.filter(section=section).exclude(
                subject_id__in=ordered_subject_ids,
            ).delete()
            for subject_id, periods_per_week in allocations.items():
                assignment = existing.get(subject_id)
                if assignment:
                    assignment.periods_per_week = periods_per_week
                    assignment.save(update_fields=['periods_per_week'])
                else:
                    SectionSubject.objects.create(
                        section=section,
                        subject=subjects_by_id[subject_id],
                        periods_per_week=periods_per_week,
                    )

        assignments = self.get_queryset().filter(section=section)
        return Response(
            self.get_serializer(assignments, many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path='recalculate-all')
    def recalculate_all(self, request):
        capacity = Period.objects.count() * len(TimetableSlot.DAYS_OF_WEEK)
        if not capacity:
            raise ValidationError({'detail': 'Configure periods before recalculating weekly plans.'})

        updated_assignments = []
        with transaction.atomic():
            for section in Section.objects.order_by('name'):
                assignments = list(
                    self.get_queryset().filter(section=section).order_by('subject_id')
                )
                if not assignments:
                    continue
                if len(assignments) > capacity:
                    raise ValidationError({
                        'detail': (
                            f"{section.name} has {len(assignments)} assigned subjects but only "
                            f"{capacity} weekly class slots. Remove subjects before recalculating."
                        )
                    })

                fixed_counts = {}
                for constraint in TimetableConstraint.objects.filter(section=section):
                    fixed_counts[constraint.subject_id] = (
                        fixed_counts.get(constraint.subject_id, 0) + 1
                    )
                categories = {
                    assignment.subject_id: assignment.subject.category
                    for assignment in assignments
                }
                try:
                    allocations = distribute_weekly_periods(
                        [assignment.subject_id for assignment in assignments],
                        fixed_counts,
                        capacity,
                        categories,
                    )
                except ValueError as error:
                    raise ValidationError({'detail': f'{section.name}: {error}'}) from error

                for assignment in assignments:
                    assignment.periods_per_week = allocations[assignment.subject_id]
                    assignment.save(update_fields=['periods_per_week'])
                    updated_assignments.append(assignment)

        return Response(self.get_serializer(updated_assignments, many=True).data)


class TeacherSubjectViewSet(viewsets.ModelViewSet):
    queryset = TeacherSubject.objects.select_related(
        'teacher', 'subject', 'section',
    ).order_by('teacher__name', 'subject__name', 'section__name')
    serializer_class = TeacherSubjectSerializer

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        section_ids = request.data.get('sections')
        if not isinstance(section_ids, list) or not section_ids:
            raise ValidationError({'sections': 'Select at least one class.'})
        subject_ids = request.data.get('subjects')
        if not isinstance(subject_ids, list) or not subject_ids:
            raise ValidationError({'subjects': 'Select at least one subject.'})
        try:
            section_ids = [int(section_id) for section_id in section_ids]
            subject_ids = [int(subject_id) for subject_id in subject_ids]
        except (TypeError, ValueError) as error:
            raise ValidationError({'sections': 'Select valid classes and subjects.'}) from error
        if any(section_id <= 0 for section_id in section_ids):
            raise ValidationError({'sections': 'Select valid classes.'})
        if any(subject_id <= 0 for subject_id in subject_ids):
            raise ValidationError({'subjects': 'Select valid subjects.'})
        if len(set(section_ids)) != len(section_ids):
            raise ValidationError({'sections': 'Select each class only once.'})
        if len(set(subject_ids)) != len(subject_ids):
            raise ValidationError({'subjects': 'Select each subject only once.'})
        if Section.objects.filter(id__in=section_ids).count() != len(section_ids):
            raise ValidationError({'sections': 'One or more selected classes do not exist.'})
        if Subject.objects.filter(id__in=subject_ids).count() != len(subject_ids):
            raise ValidationError({'subjects': 'One or more selected subjects do not exist.'})
        combine_classes = request.data.get('combine_classes', False)
        if not isinstance(combine_classes, bool):
            raise ValidationError({'combine_classes': 'Select whether these classes are combined.'})
        combined_periods = None
        if combine_classes:
            if len(section_ids) < 2:
                raise ValidationError({
                    'sections': 'Select at least two classes to combine.'
                })
            try:
                combined_periods = int(request.data.get('combined_periods_per_week'))
            except (TypeError, ValueError) as error:
                raise ValidationError({
                    'combined_periods_per_week': 'Enter the number of shared periods per week.'
                }) from error
            if combined_periods < 1:
                raise ValidationError({
                    'combined_periods_per_week': 'Shared periods per week must be at least 1.'
                })
            if combined_periods > Period.objects.count() * len(TimetableSlot.DAYS_OF_WEEK):
                raise ValidationError({
                    'combined_periods_per_week': 'Shared periods exceed the available weekly slots.'
                })

        with transaction.atomic():
            existing_mappings = list(
                TeacherSubject.objects.filter(
                    teacher_id=request.data.get('teacher'),
                    section_id__in=section_ids,
                    subject_id__in=subject_ids,
                )
            )
            existing_subject_ids = {
                (mapping.section_id, mapping.subject_id)
                for mapping in existing_mappings
            }
            mappings = [
                {
                    'teacher': request.data.get('teacher'),
                    'section': section_id,
                    'subject': subject_id,
                }
                for section_id in section_ids
                for subject_id in subject_ids
                if (section_id, subject_id) not in existing_subject_ids
            ]
            created_mappings = []
            if mappings:
                serializer = self.get_serializer(data=mappings, many=True)
                serializer.is_valid(raise_exception=True)
                created_mappings = serializer.save()

            combined_groups = []
            if combine_classes:
                selected_sections = Section.objects.filter(id__in=section_ids)
                selected_subjects = Subject.objects.filter(id__in=subject_ids)
                if TimetableConstraint.objects.filter(
                    section_id__in=section_ids,
                    subject_id__in=subject_ids,
                ).exists():
                    raise ValidationError({
                        'combine_classes': (
                            'Remove fixed classes for the selected sections and subjects '
                            'before combining them.'
                        )
                    })

                for subject in selected_subjects:
                    is_shared_yoga = (
                        subject.category == Subject.ACTIVITY
                        and subject.name.strip().casefold() == 'yoga'
                    )
                    if subject.category == Subject.BASIC:
                        minimum_periods = 5
                    elif is_shared_yoga:
                        minimum_periods = 1
                    else:
                        minimum_periods = 2
                    plan_periods = max(combined_periods, minimum_periods)
                    existing_groups = list(
                        CombinedTeachingGroup.objects.filter(
                            subject=subject,
                        ).prefetch_related('sections')
                    )
                    selected_section_set = set(section_ids)
                    matching_group = None
                    for group in existing_groups:
                        group_section_ids = set(
                            group.sections.values_list('id', flat=True)
                        )
                        if group_section_ids == selected_section_set and group.teacher_id == int(request.data['teacher']):
                            matching_group = group
                        elif group_section_ids.intersection(selected_section_set):
                            raise ValidationError({
                                'combine_classes': (
                                    f'{subject.name} already has a combined group that overlaps '
                                    'with one or more selected classes.'
                                )
                            })

                    for section_id in section_ids:
                        assignment, _ = SectionSubject.objects.get_or_create(
                            section_id=section_id,
                            subject=subject,
                            defaults={'periods_per_week': plan_periods},
                        )
                        if (
                            assignment.periods_per_week < plan_periods
                            or (
                                is_shared_yoga
                                and assignment.periods_per_week != plan_periods
                            )
                        ):
                            assignment.periods_per_week = plan_periods
                            assignment.save(update_fields=['periods_per_week'])

                    if matching_group:
                        matching_group.periods_per_week = combined_periods
                        matching_group.save(update_fields=['periods_per_week'])
                        combined_groups.append(matching_group)
                    else:
                        group = CombinedTeachingGroup.objects.create(
                            teacher_id=request.data['teacher'],
                            subject=subject,
                            periods_per_week=combined_periods,
                        )
                        group.sections.set(selected_sections)
                        combined_groups.append(group)

            saved_mappings = list(
                TeacherSubject.objects.filter(
                    teacher_id=request.data.get('teacher'),
                    section_id__in=section_ids,
                    subject_id__in=subject_ids,
                ).select_related('teacher', 'subject', 'section')
            )
            saved_mappings.sort(key=lambda mapping: (
                section_ids.index(mapping.section_id),
                subject_ids.index(mapping.subject_id),
            ))
        return Response(
            {
                'mappings': self.get_serializer(saved_mappings, many=True).data,
                'created_count': len(created_mappings),
                'existing_count': len(existing_mappings),
                'combined_groups': CombinedTeachingGroupSerializer(
                    combined_groups,
                    many=True,
                ).data,
            },
            status=(
                status.HTTP_201_CREATED
                if created_mappings
                else status.HTTP_200_OK
            ),
        )

    def perform_destroy(self, instance):
        if instance.section_id and CombinedTeachingGroup.objects.filter(
            teacher=instance.teacher,
            subject=instance.subject,
            sections=instance.section,
        ).exists():
            raise ValidationError(
                {'detail': 'Remove the combined class group before deleting this mapping.'}
            )
        if TimetableConstraint.objects.filter(
            teacher=instance.teacher,
            subject=instance.subject,
        ).filter(
            Q(section_id=instance.section_id)
            if instance.section_id
            else Q()
        ).exists():
            raise ValidationError(
                {'detail': 'Remove fixed classes using this mapping before deleting it.'}
            )
        instance.delete()


class CombinedTeachingGroupViewSet(viewsets.ModelViewSet):
    queryset = CombinedTeachingGroup.objects.select_related(
        'teacher', 'subject',
    ).prefetch_related('sections').order_by('subject__name', 'teacher__name')
    serializer_class = CombinedTeachingGroupSerializer
    http_method_names = ['get', 'delete', 'head', 'options']


class TeacherAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = TeacherAvailability.objects.select_related('teacher', 'period').order_by(
        'teacher__name', 'day', 'period__number'
    )
    serializer_class = TeacherAvailabilitySerializer


class TimetableConstraintViewSet(viewsets.ModelViewSet):
    queryset = TimetableConstraint.objects.select_related(
        'section', 'subject', 'teacher', 'period'
    ).order_by('section__name', 'day', 'period__number')
    serializer_class = TimetableConstraintSerializer

    @action(detail=False, methods=['post'], url_path='create-shared')
    def create_shared(self, request):
        section_ids = request.data.get('sections')
        if not isinstance(section_ids, list) or len(section_ids) < 2:
            raise ValidationError({
                'sections': 'Select at least two different sections for a combined class.'
            })
        if any(isinstance(value, bool) or not isinstance(value, (int, str)) for value in section_ids):
            raise ValidationError({'sections': 'Section IDs must be valid integers.'})
        try:
            section_ids = [int(value) for value in section_ids]
        except ValueError as error:
            raise ValidationError({'sections': 'Section IDs must be valid integers.'}) from error
        if len(set(section_ids)) != len(section_ids):
            raise ValidationError({
                'sections': 'Select each section only once for a combined class.'
            })

        sections = list(Section.objects.filter(id__in=section_ids).order_by('name'))
        if len(sections) != len(section_ids):
            raise ValidationError({'sections': 'One or more selected sections do not exist.'})

        related_models = (
            ('subject', Subject),
            ('teacher', Teacher),
            ('period', Period),
        )
        related_objects = {}
        for field, model in related_models:
            try:
                object_id = int(request.data.get(field))
            except (TypeError, ValueError) as error:
                raise ValidationError({field: 'Select a valid value.'}) from error
            try:
                related_objects[field] = model.objects.get(pk=object_id)
            except model.DoesNotExist as error:
                raise ValidationError({field: 'The selected item does not exist.'}) from error
        subject = related_objects['subject']
        teacher = related_objects['teacher']
        period = related_objects['period']
        if CombinedTeachingGroup.objects.filter(
            subject=subject,
            sections__in=sections,
        ).exists():
            raise ValidationError({
                'subject': 'Remove the combined class group before creating fixed classes for it.'
            })
        day = request.data.get('day')
        if day not in dict(TimetableSlot.DAYS_OF_WEEK):
            raise ValidationError({'day': 'Select a valid weekday.'})
        if not all(
            TeacherSubject.objects.filter(
                subject=subject,
                teacher=teacher,
            ).filter(Q(section=section) | Q(section__isnull=True)).exists()
            for section in sections
        ):
            raise ValidationError({'teacher': 'Map this teacher to the selected subject first.'})
        if TeacherAvailability.objects.filter(
            teacher=teacher,
            day=day,
            period=period,
            is_available=False,
        ).exists():
            raise ValidationError({'period': 'This teacher is marked unavailable at the selected time.'})
        if TimetableConstraint.objects.filter(
            teacher=teacher,
            day=day,
            period=period,
        ).exists():
            raise ValidationError({
                'teacher': 'This teacher already has a fixed class at the selected time.'
            })

        assignments = {
            assignment.section_id: assignment
            for assignment in SectionSubject.objects.filter(
                section__in=sections,
                subject=subject,
            )
        }
        missing_sections = [
            section.name for section in sections if section.id not in assignments
        ]
        if missing_sections:
            raise ValidationError({
                'subject': (
                    f"Assign {subject.name} to every selected section first. "
                    f"Missing: {', '.join(missing_sections)}."
                )
            })

        for section in sections:
            if TimetableConstraint.objects.filter(
                section=section,
                day=day,
                period=period,
            ).exists():
                raise ValidationError({
                    'period': f"{section.name} already has a fixed class at this time."
                })
            fixed_count = TimetableConstraint.objects.filter(
                section=section,
                subject=subject,
            ).count()
            assignment = assignments[section.id]
            if fixed_count >= assignment.periods_per_week:
                raise ValidationError({
                    'subject': (
                        f"The weekly plan allows {assignment.periods_per_week} "
                        f"{subject.name} periods for {section.name}, and all are already fixed."
                    )
                })

        with transaction.atomic():
            group = SharedClassGroup.objects.create(
                subject=subject,
                teacher=teacher,
                day=day,
                period=period,
            )
            TimetableConstraint.objects.bulk_create([
                TimetableConstraint(
                    section=section,
                    subject=subject,
                    teacher=teacher,
                    day=day,
                    period=period,
                    shared_group=group,
                )
                for section in sections
            ])

        constraints = self.get_queryset().filter(shared_group=group)
        return Response(
            TimetableConstraintSerializer(constraints, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_destroy(self, instance):
        shared_group = instance.shared_group
        instance.delete()
        if shared_group and not shared_group.constraints.exists():
            shared_group.delete()


class ScheduleEntryViewSet(viewsets.ModelViewSet):
    queryset = ScheduleEntry.objects.select_related(
        'section', 'subject', 'teacher', 'period'
    ).order_by('section__name', 'day', 'period__number')
    serializer_class = ScheduleEntrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        section_id = self.request.query_params.get('section')
        teacher_id = self.request.query_params.get('teacher')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        return queryset

    def perform_destroy(self, instance):
        if TimetableConstraint.objects.filter(
            section=instance.section,
            day=instance.day,
            period=instance.period,
        ).exists():
            raise ValidationError({'detail': 'This class is fixed by a timetable constraint and cannot be deleted.'})
        instance.delete()

    @action(detail=False, methods=['get'])
    def readiness(self, request):
        plan_adjustments = {}
        schedule, errors = build_schedule(plan_adjustments)
        return Response({
            'ready': not errors,
            'errors': errors,
            'class_count': len(schedule) if schedule else 0,
            'plan_adjustments': _plan_adjustment_details(plan_adjustments),
        })

    @action(detail=False, methods=['post'])
    def generate(self, request):
        with transaction.atomic():
            plan_adjustments = {}
            schedule, errors = build_schedule(plan_adjustments)
            if errors:
                return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

            adjustment_details = _plan_adjustment_details(plan_adjustments)
            updated_assignments = list(
                SectionSubject.objects.filter(id__in=plan_adjustments)
            )
            for assignment in updated_assignments:
                assignment.periods_per_week = plan_adjustments[assignment.id]
            if updated_assignments:
                SectionSubject.objects.bulk_update(
                    updated_assignments,
                    ['periods_per_week'],
                )

            ScheduleEntry.objects.all().delete()
            ScheduleEntry.objects.bulk_create([
                ScheduleEntry(
                    section_id=section_id,
                    subject_id=subject_id,
                    teacher_id=teacher_id,
                    day=day,
                    period_id=period_id,
                )
                for section_id, subject_id, teacher_id, day, period_id in schedule
            ])

            entries = self.get_queryset()
            return Response({
                'count': len(schedule),
                'plan_adjustments': adjustment_details,
                'schedule': ScheduleEntrySerializer(entries, many=True).data,
            })