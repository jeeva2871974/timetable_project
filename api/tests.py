from datetime import time
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from .models import (
    CombinedTeachingGroup, Period, ScheduleEntry, Section, SectionSubject, Subject, Teacher,
    TeacherAvailability, TeacherSubject, TimetableBreak, TimetableConstraint,
    TimetableSlot, SharedClassGroup,
)
from .scheduler import build_schedule, distribute_weekly_periods
from .serializers import (
    SectionSubjectSerializer,
    TimetableConstraintSerializer,
    TeacherAvailabilitySerializer,
    TeacherSubjectSerializer,
    TimetableSlotSerializer,
)


class TimetableSlotSerializerTests(SimpleTestCase):
    @patch('api.serializers.TimetableSlot.objects.filter')
    def test_rejects_duplicate_day_and_time(self, filter_slots):
        filter_slots.return_value.exists.return_value = True
        serializer = TimetableSlotSerializer()

        with self.assertRaises(ValidationError) as error:
            serializer.validate({
                'day': 'Monday',
                'start_time': time(9),
                'end_time': time(10),
            })

        self.assertIn('already scheduled on Monday from 09:00 to 10:00', str(error.exception))
        filter_slots.assert_called_once_with(
            day='Monday',
            start_time=time(9),
            end_time=time(10),
        )

    @patch('api.serializers.TimetableSlot.objects.filter')
    def test_allows_same_time_on_a_different_day(self, filter_slots):
        filter_slots.return_value.exists.return_value = False
        serializer = TimetableSlotSerializer()
        data = {
            'day': 'Tuesday',
            'start_time': time(9),
            'end_time': time(10),
        }

        self.assertEqual(serializer.validate(data), data)


class PeriodUpdateAPITests(TestCase):
    def setUp(self):
        Period.objects.filter(number=3).delete()
        self.period = Period.objects.get(number=1)
        self.section = Section.objects.create(name='Test Section')
        self.subject = Subject.objects.create(name='Test Subject')
        self.teacher = Teacher.objects.create(name='Test Teacher')
        self.assignment = SectionSubject.objects.create(
            section=self.section,
            subject=self.subject,
            periods_per_week=2,
        )
        TeacherSubject.objects.create(
            teacher=self.teacher,
            subject=self.subject,
        )

    def test_patch_updates_period_times_in_database(self):
        response = APIClient().patch(
            f'/api/periods/{self.period.id}/',
            {'start_time': '07:30', 'end_time': '08:15'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.period.refresh_from_db()
        self.assertEqual(self.period.start_time, time(7, 30))
        self.assertEqual(self.period.end_time, time(8, 15))

    def test_patch_rejects_time_overlapping_another_period(self):
        response = APIClient().patch(
            f'/api/periods/{self.period.id}/',
            {'start_time': '08:30', 'end_time': '09:00'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.period.refresh_from_db()
        self.assertEqual(self.period.start_time, time(8))
        self.assertEqual(self.period.end_time, time(8, 45))

    def test_can_recreate_deleted_period_in_gap_between_neighbors(self):
        response = APIClient().post(
            '/api/periods/',
            {'number': 3, 'start_time': '09:30', 'end_time': '10:15'},
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        period = Period.objects.get(number=3)
        self.assertEqual(period.start_time, time(9, 30))
        self.assertEqual(period.end_time, time(10, 15))

    def test_recreated_period_cannot_overlap_next_period(self):
        response = APIClient().post(
            '/api/periods/',
            {'number': 3, 'start_time': '09:45', 'end_time': '10:30'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Period.objects.filter(number=3).exists())

    def test_saves_lunch_in_exact_45_minute_gap(self):
        response = APIClient().post(
            '/api/timetable-breaks/',
            {'kind': TimetableBreak.LUNCH, 'after_period': self._period_id(2)},
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['duration_minutes'], 45)
        self.assertEqual(response.data['start_time'], '09:30:00')
        self.assertEqual(response.data['end_time'], '10:15:00')

    def test_rejects_break_when_gap_duration_does_not_match(self):
        response = APIClient().post(
            '/api/timetable-breaks/',
            {'kind': TimetableBreak.BREAK, 'after_period': self._period_id(2)},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('exactly 15 minutes', str(response.data))
        self.assertFalse(TimetableBreak.objects.exists())

    def test_period_edit_cannot_break_configured_gap(self):
        TimetableBreak.objects.create(
            kind=TimetableBreak.LUNCH,
            after_period=Period.objects.get(number=2),
        )

        response = APIClient().patch(
            f'/api/periods/{self._period_id(2)}/',
            {'number': 2, 'start_time': '08:45', 'end_time': '10:00'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('exactly 45 minutes', str(response.data))

    def test_recalculates_weekly_plan_for_current_period_capacity(self):
        response = APIClient().post('/api/section-subjects/recalculate-all/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assignment.refresh_from_db()
        self.assertEqual(
            self.assignment.periods_per_week,
            Period.objects.count() * len(TimetableSlot.DAYS_OF_WEEK),
        )

    def test_readiness_uses_current_configured_period_count(self):
        self.assignment.periods_per_week = 40
        self.assignment.save(update_fields=['periods_per_week'])

        response = APIClient().get('/api/schedule/readiness/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['ready'])
        self.assertTrue(any('35 available weekly slots' in error for error in response.data['errors']))

    @staticmethod
    def _period_id(number):
        return Period.objects.get(number=number).id


class ScheduleGenerationTests(TestCase):
    def setUp(self):
        self.section = Section.objects.create(name='1A')
        self.subject = Subject.objects.create(name='Math')
        self.teacher = Teacher.objects.create(name='Alex')
        self.assignment = SectionSubject.objects.create(
            section=self.section,
            subject=self.subject,
            periods_per_week=2,
        )
        TeacherSubject.objects.create(teacher=self.teacher, subject=self.subject)
        self.periods = list(Period.objects.filter(number__in=[1, 2]))

    def test_weekly_distribution_evenly_fills_capacity_and_respects_fixed_counts(self):
        allocations = distribute_weekly_periods(
            [1, 2, 3],
            {1: 5},
            40,
        )

        self.assertEqual(allocations, {1: 14, 2: 13, 3: 13})
        self.assertEqual(sum(allocations.values()), 40)
        self.assertGreaterEqual(allocations[1], 5)

    def test_weekly_distribution_rejects_impossible_fixed_counts(self):
        with self.assertRaises(ValueError):
            distribute_weekly_periods([1, 2], {1: 5, 2: 6}, 10)

    def test_weekly_distribution_keeps_activities_at_two_and_shares_remaining_with_basics(self):
        allocations = distribute_weekly_periods(
            [1, 2, 3],
            {},
            35,
            {
                1: Subject.BASIC,
                2: Subject.BASIC,
                3: Subject.ACTIVITY,
            },
        )

        self.assertEqual(allocations, {1: 17, 2: 16, 3: 2})
        self.assertEqual(sum(allocations.values()), 35)

    def test_fixed_activity_counts_toward_two_period_weekly_minimum(self):
        allocations = distribute_weekly_periods(
            [1, 2],
            {2: 1},
            35,
            {1: Subject.BASIC, 2: Subject.ACTIVITY},
        )

        self.assertEqual(allocations[2], 2)
        self.assertEqual(allocations[1], 33)

    def test_activity_only_plan_cannot_fill_remaining_periods(self):
        with self.assertRaisesMessage(ValueError, 'Add at least one Basic subject'):
            distribute_weekly_periods(
                [1],
                {},
                35,
                {1: Subject.ACTIVITY},
            )

    def test_many_basic_subjects_leave_daily_capacity_for_activities(self):
        Period.objects.filter(number__gt=8).delete()
        for number in range(1, 9):
            Period.objects.get_or_create(
                number=number,
                defaults={
                    'start_time': time(8),
                    'end_time': time(8, 45),
                },
            )

        self.assignment.periods_per_week = 5
        self.assignment.save(update_fields=['periods_per_week'])
        for number in range(2, 7):
            subject = Subject.objects.create(name=f'Basic {number}')
            teacher = Teacher.objects.create(name=f'Teacher {number}')
            SectionSubject.objects.create(
                section=self.section,
                subject=subject,
                periods_per_week=5,
            )
            TeacherSubject.objects.create(
                teacher=teacher,
                subject=subject,
                section=self.section,
            )
        for number in range(1, 5):
            subject = Subject.objects.create(
                name=f'Activity {number}',
                category=Subject.ACTIVITY,
            )
            teacher = Teacher.objects.create(name=f'Activity Teacher {number}')
            SectionSubject.objects.create(
                section=self.section,
                subject=subject,
                periods_per_week=2,
            )
            TeacherSubject.objects.create(
                teacher=teacher,
                subject=subject,
                section=self.section,
            )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        self.assertEqual(len(schedule), 40)
        self.assertEqual(
            len({(entry[3], entry[4]) for entry in schedule}),
            40,
        )

    def test_subject_minimums_must_fit_weekly_capacity(self):
        with self.assertRaisesMessage(ValueError, 'require 7 weekly periods'):
            distribute_weekly_periods(
                [1, 2],
                {},
                6,
                {1: Subject.BASIC, 2: Subject.ACTIVITY},
            )

    def test_configure_section_plan_distributes_periods_and_preserves_fixed_classes(self):
        second_subject = Subject.objects.create(name='Science')
        third_subject = Subject.objects.create(name='English')
        fixed_period = self.periods[0]
        constraint = TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=fixed_period,
        )

        response = APIClient().post(
            '/api/section-subjects/configure-section/',
            {
                'section': self.section.id,
                'subject_ids': [self.subject.id, second_subject.id, third_subject.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        assignments = {
            item.subject_id: item.periods_per_week
            for item in SectionSubject.objects.filter(section=self.section)
        }
        self.assertEqual(assignments, {
            self.subject.id: 14,
            second_subject.id: 13,
            third_subject.id: 13,
        })
        self.assertEqual(sum(assignments.values()), 40)
        self.assertTrue(TimetableConstraint.objects.filter(pk=constraint.pk).exists())

    def test_configure_section_plan_replaces_unselected_unfixed_subjects(self):
        replacement = Subject.objects.create(name='Science')
        response = APIClient().post(
            '/api/section-subjects/configure-section/',
            {'section': self.section.id, 'subject_ids': [replacement.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        assignments = list(SectionSubject.objects.filter(section=self.section))
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].subject_id, replacement.id)
        self.assertEqual(assignments[0].periods_per_week, 40)

    def test_configure_section_plan_assigns_two_weekly_periods_to_activity(self):
        activity = Subject.objects.create(
            name='Games',
            category=Subject.ACTIVITY,
        )
        response = APIClient().post(
            '/api/section-subjects/configure-section/',
            {'section': self.section.id, 'subject_ids': [self.subject.id, activity.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        assignments = {
            item.subject_id: item.periods_per_week
            for item in SectionSubject.objects.filter(section=self.section)
        }
        self.assertEqual(assignments[activity.id], 2)
        self.assertEqual(
            assignments[self.subject.id],
            Period.objects.count() * len(TimetableSlot.DAYS_OF_WEEK) - 2,
        )

    def test_configure_section_plan_fixed_activity_still_gets_two_periods(self):
        activity = Subject.objects.create(
            name='Games',
            category=Subject.ACTIVITY,
        )
        TimetableConstraint.objects.create(
            section=self.section,
            subject=activity,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )
        response = APIClient().post(
            '/api/section-subjects/configure-section/',
            {'section': self.section.id, 'subject_ids': [self.subject.id, activity.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        activity_assignment = SectionSubject.objects.get(
            section=self.section,
            subject=activity,
        )
        self.assertEqual(activity_assignment.periods_per_week, 2)

    def test_configure_section_plan_keeps_fixed_subject_selected(self):
        second_subject = Subject.objects.create(name='Science')
        constraint = TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )

        response = APIClient().post(
            '/api/section-subjects/configure-section/',
            {'section': self.section.id, 'subject_ids': [second_subject.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('fixed classes', str(response.data).lower())
        self.assertTrue(TimetableConstraint.objects.filter(pk=constraint.pk).exists())
        self.assertTrue(SectionSubject.objects.filter(pk=self.assignment.pk).exists())

    def test_even_multi_subject_plan_generates_when_another_section_has_one_subject(self):
        second_section = Section.objects.create(name='1B')
        third_section = Section.objects.create(name='1C')
        subjects = [self.subject]
        for name in (
            'English', 'Science', 'Computer', 'Music',
            'Art', 'Social Studies', 'Physical Education',
        ):
            subjects.append(Subject.objects.create(name=name))

        for subject in subjects:
            teacher, _ = Teacher.objects.get_or_create(
                name=f'{subject.name} Teacher',
            )
            TeacherSubject.objects.get_or_create(teacher=teacher, subject=subject)
            for section in (self.section, second_section):
                SectionSubject.objects.update_or_create(
                    section=section,
                    subject=subject,
                    defaults={'periods_per_week': 5},
                )
        additional_math_teacher = Teacher.objects.create(name='Additional Math Teacher')
        TeacherSubject.objects.create(
            teacher=additional_math_teacher,
            subject=self.subject,
        )
        SectionSubject.objects.update_or_create(
            section=third_section,
            subject=subjects[0],
            defaults={'periods_per_week': 5},
        )

        response = APIClient().post(
            '/api/section-subjects/configure-section/',
            {
                'section': third_section.id,
                'subject_ids': [subject.id for subject in subjects],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        self.assertEqual(
            len(schedule),
            3 * len(TimetableSlot.DAYS_OF_WEEK) * Period.objects.count(),
        )
        teacher_slots = [(entry[2], entry[3], entry[4]) for entry in schedule]
        self.assertEqual(len(teacher_slots), len(set(teacher_slots)))

    def test_builds_the_requested_weekly_period_count(self):
        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        self.assertEqual(len(schedule), len(TimetableSlot.DAYS_OF_WEEK) * Period.objects.count())
        self.assertTrue(all(entry[0] == self.section.id for entry in schedule))
        self.assertEqual(
            len({(entry[3], entry[4]) for entry in schedule}),
            len(TimetableSlot.DAYS_OF_WEEK) * Period.objects.count(),
        )
        self.assertGreater(len(schedule), self.assignment.periods_per_week)

    def test_create_shared_fixed_class_for_multiple_sections_and_generate(self):
        second_section = Section.objects.create(name='1B')
        SectionSubject.objects.create(
            section=second_section,
            subject=self.subject,
            periods_per_week=1,
        )
        for section, subject_name in (
            (self.section, 'English'),
            (second_section, 'Science'),
        ):
            filler_subject = Subject.objects.create(name=subject_name)
            filler_teacher = Teacher.objects.create(name=f'{subject_name} Teacher')
            TeacherSubject.objects.create(teacher=filler_teacher, subject=filler_subject)
            SectionSubject.objects.create(
                section=section,
                subject=filler_subject,
                periods_per_week=1,
            )
        backup_math_teacher = Teacher.objects.create(name='Backup Math Teacher')
        TeacherSubject.objects.create(
            teacher=backup_math_teacher,
            subject=self.subject,
        )
        fixed_period = Period.objects.get(number=7)
        response = APIClient().post(
            '/api/constraints/create-shared/',
            {
                'sections': [self.section.id, second_section.id],
                'subject': self.subject.id,
                'teacher': self.teacher.id,
                'day': 'Monday',
                'period': fixed_period.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        constraints = list(TimetableConstraint.objects.filter(
            shared_group__isnull=False,
        ).order_by('section_id'))
        self.assertEqual(len(constraints), 2)
        self.assertEqual(constraints[0].shared_group_id, constraints[1].shared_group_id)
        self.assertEqual(
            {constraint.section_id for constraint in constraints},
            {self.section.id, second_section.id},
        )
        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        self.assertIn(
            (self.section.id, self.subject.id, self.teacher.id, 'Monday', fixed_period.id),
            schedule,
        )
        self.assertIn(
            (second_section.id, self.subject.id, self.teacher.id, 'Monday', fixed_period.id),
            schedule,
        )
        response = APIClient().post('/api/schedule/generate/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            ScheduleEntry.objects.filter(
                teacher=self.teacher,
                day='Monday',
                period=fixed_period,
            ).count(),
            2,
        )

    def test_shared_fixed_class_requires_subject_assigned_to_every_section(self):
        second_section = Section.objects.create(name='1B')
        response = APIClient().post(
            '/api/constraints/create-shared/',
            {
                'sections': [self.section.id, second_section.id],
                'subject': self.subject.id,
                'teacher': self.teacher.id,
                'day': 'Monday',
                'period': self.periods[0].id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Assign Math to every selected section', str(response.data))
        self.assertFalse(TimetableConstraint.objects.exists())
        self.assertFalse(SharedClassGroup.objects.exists())

    def test_section_subject_serializer_rejects_weekly_over_capacity(self):
        another_subject = Subject.objects.create(name='Science')
        serializer = SectionSubjectSerializer(data={
            'section': self.section.id,
            'subject': another_subject.id,
            'periods_per_week': 39,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('exceeding the 40 available periods', str(serializer.errors))

    def test_section_subject_update_counts_other_requirements(self):
        self.assignment.periods_per_week = 39
        self.assignment.save()
        another_subject = Subject.objects.create(name='Science')
        SectionSubject.objects.create(
            section=self.section,
            subject=another_subject,
            periods_per_week=1,
        )
        serializer = SectionSubjectSerializer(
            self.assignment,
            data={
                'section': self.section.id,
                'subject': self.subject.id,
                'periods_per_week': 40,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('exceeding the 40 available periods', str(serializer.errors))

    def test_fixed_constraint_is_included_in_weekly_count(self):
        constraint_period = self.periods[0]
        filler_subject = Subject.objects.create(name='Science')
        filler_teacher = Teacher.objects.create(name='Science Teacher')
        TeacherSubject.objects.create(teacher=filler_teacher, subject=filler_subject)
        SectionSubject.objects.create(
            section=self.section,
            subject=filler_subject,
            periods_per_week=1,
        )
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=constraint_period,
        )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        self.assertEqual(len(schedule), len(TimetableSlot.DAYS_OF_WEEK) * Period.objects.count())
        self.assertIn(
            (self.section.id, self.subject.id, self.teacher.id, 'Monday', constraint_period.id),
            schedule,
        )

    def test_fixed_activity_stays_pinned_and_counts_toward_two_weekly_days(self):
        self.subject.name = 'Yoga'
        self.subject.category = Subject.ACTIVITY
        self.subject.save(update_fields=['name', 'category'])
        TimetableBreak.objects.create(
            kind=TimetableBreak.LUNCH,
            after_period=Period.objects.get(number=4),
        )
        self.assignment.periods_per_week = 3
        self.assignment.save(update_fields=['periods_per_week'])

        other_subject = Subject.objects.create(name='Science')
        other_teacher = Teacher.objects.create(name='Science Teacher')
        TeacherSubject.objects.create(teacher=other_teacher, subject=other_subject)
        SectionSubject.objects.create(
            section=self.section,
            subject=other_subject,
            periods_per_week=8,
        )
        fixed_period = self.periods[0]
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=fixed_period,
        )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        yoga_entries = [entry for entry in schedule if entry[1] == self.subject.id]
        self.assertEqual(len(yoga_entries), 2)
        self.assertIn(
            (self.section.id, self.subject.id, self.teacher.id, 'Monday', fixed_period.id),
            yoga_entries,
        )
        self.assertEqual(len({entry[3] for entry in yoga_entries}), 2)
        self.assertEqual(
            len(schedule),
            len(TimetableSlot.DAYS_OF_WEEK) * Period.objects.count(),
        )

    def test_non_fixed_subjects_are_scheduled_each_weekday_and_plan_is_adjusted(self):
        second_subject = Subject.objects.create(name='Science')
        second_teacher = Teacher.objects.create(name='Morgan')
        TeacherSubject.objects.create(teacher=second_teacher, subject=second_subject)
        second_assignment = SectionSubject.objects.create(
            section=self.section,
            subject=second_subject,
            periods_per_week=38,
        )
        self.assignment.periods_per_week = 2
        self.assignment.save(update_fields=['periods_per_week'])

        plan_adjustments = {}
        schedule, errors = build_schedule(plan_adjustments)

        self.assertEqual(errors, [])
        self.assertEqual(
            plan_adjustments,
            {self.assignment.id: 5, second_assignment.id: 35},
        )
        self.assignment.refresh_from_db()
        second_assignment.refresh_from_db()
        self.assertEqual(self.assignment.periods_per_week, 2)
        self.assertEqual(second_assignment.periods_per_week, 38)

        for day, _ in TimetableSlot.DAYS_OF_WEEK:
            subjects_scheduled = {
                entry[1] for entry in schedule if entry[0] == self.section.id and entry[3] == day
            }
            self.assertIn(self.subject.id, subjects_scheduled)
            self.assertIn(second_subject.id, subjects_scheduled)

        client = APIClient()
        readiness = client.get('/api/schedule/readiness/')
        self.assertEqual(readiness.status_code, 200)
        self.assertTrue(readiness.data['ready'], readiness.data['errors'])
        self.assertEqual(
            readiness.data['plan_adjustments'],
            [
                {
                    'section': self.section.name,
                    'subject': self.subject.name,
                    'from_periods_per_week': 2,
                    'to_periods_per_week': 5,
                },
                {
                    'section': self.section.name,
                    'subject': second_subject.name,
                    'from_periods_per_week': 38,
                    'to_periods_per_week': 35,
                },
            ],
        )

        response = client.post('/api/schedule/generate/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data['plan_adjustments'],
            [
                {
                    'section': self.section.name,
                    'subject': self.subject.name,
                    'from_periods_per_week': 2,
                    'to_periods_per_week': 5,
                },
                {
                    'section': self.section.name,
                    'subject': second_subject.name,
                    'from_periods_per_week': 38,
                    'to_periods_per_week': 35,
                },
            ],
        )
        self.assignment.refresh_from_db()
        second_assignment.refresh_from_db()
        self.assertEqual(self.assignment.periods_per_week, 5)
        self.assertEqual(second_assignment.periods_per_week, 35)

    def test_fixed_activity_counts_toward_its_weekly_target(self):
        self.subject.name = 'Yoga'
        self.subject.category = Subject.ACTIVITY
        self.subject.save(update_fields=['name', 'category'])
        TimetableBreak.objects.create(
            kind=TimetableBreak.LUNCH,
            after_period=Period.objects.get(number=4),
        )
        self.assignment.periods_per_week = 3
        self.assignment.save(update_fields=['periods_per_week'])
        second_subject = Subject.objects.create(name='Science')
        second_teacher = Teacher.objects.create(name='Science Teacher')
        TeacherSubject.objects.create(teacher=second_teacher, subject=second_subject)
        SectionSubject.objects.create(
            section=self.section,
            subject=second_subject,
            periods_per_week=37,
        )
        fixed_period = self.periods[0]
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=fixed_period,
        )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        yoga_entries = [entry for entry in schedule if entry[1] == self.subject.id]
        self.assertEqual(len(yoga_entries), 2)
        self.assertIn(
            (self.section.id, self.subject.id, self.teacher.id, 'Monday', fixed_period.id),
            yoga_entries,
        )
        self.assertEqual(len({entry[3] for entry in yoga_entries}), 2)
        for day, _ in TimetableSlot.DAYS_OF_WEEK:
            self.assertTrue(any(
                entry[0] == self.section.id
                and entry[1] == second_subject.id
                and entry[3] == day
                for entry in schedule
            ))

    def test_fixed_basic_subject_is_scheduled_every_weekday(self):
        second_subject = Subject.objects.create(name='Science', category=Subject.BASIC)
        second_teacher = Teacher.objects.create(name='Science Teacher')
        TeacherSubject.objects.create(teacher=second_teacher, subject=second_subject)
        SectionSubject.objects.create(
            section=self.section,
            subject=second_subject,
            periods_per_week=33,
        )
        self.assignment.periods_per_week = 2
        self.assignment.save(update_fields=['periods_per_week'])
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=Period.objects.first(),
        )

        plan_adjustments = {}
        schedule, errors = build_schedule(plan_adjustments)

        self.assertEqual(errors, [], errors)
        self.assertGreaterEqual(plan_adjustments[self.assignment.id], 5)
        for day, _ in TimetableSlot.DAYS_OF_WEEK:
            self.assertTrue(
                any(
                    entry[0] == self.section.id
                    and entry[1] == self.subject.id
                    and entry[3] == day
                    for entry in schedule
                ),
                f'{self.subject.name} is missing on {day}',
            )

    def test_fixed_basic_class_keeps_daily_activity_load_within_period_capacity(self):
        Period.objects.filter(number__gt=7).delete()
        basic_subjects = [self.subject]
        for name in ('English', 'EVS', 'Hindi', 'Tamil'):
            subject = Subject.objects.create(name=name, category=Subject.BASIC)
            teacher = Teacher.objects.create(name=f'{name} Teacher')
            TeacherSubject.objects.create(teacher=teacher, subject=subject)
            SectionSubject.objects.create(
                section=self.section,
                subject=subject,
                periods_per_week=5,
            )
            basic_subjects.append(subject)

        activities = []
        for name in ('Drawing', 'Games', 'GK', 'Tamil Reading'):
            subject = Subject.objects.create(name=name, category=Subject.ACTIVITY)
            teacher = Teacher.objects.create(name=f'{name} Teacher')
            TeacherSubject.objects.create(teacher=teacher, subject=subject)
            SectionSubject.objects.create(
                section=self.section,
                subject=subject,
                periods_per_week=2,
            )
            activities.append(subject)

        fixed_class = TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Tuesday',
            period=Period.objects.first(),
        )
        response = APIClient().patch(
            f'/api/constraints/{fixed_class.id}/',
            {'day': 'Monday'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        for day, _ in TimetableSlot.DAYS_OF_WEEK:
            subjects_scheduled = {
                entry[1]
                for entry in schedule
                if entry[0] == self.section.id and entry[3] == day
            }
            self.assertTrue(
                {subject.id for subject in basic_subjects}.issubset(subjects_scheduled),
                f'A Basic subject is missing on {day}',
            )
        for activity in activities:
            activity_days = {
                entry[3]
                for entry in schedule
                if entry[0] == self.section.id and entry[1] == activity.id
            }
            self.assertEqual(len(activity_days), 2, activity.name)

    def test_multiple_math_teachers_allow_daily_math_across_sections_without_same_period_collision(self):
        Period.objects.filter(number__gt=7).delete()
        sections = [self.section] + [
            Section.objects.create(name=str(number))
            for number in range(2, 6)
        ]
        mathematics_backup = Teacher.objects.create(name='Mathematics Backup')
        TeacherSubject.objects.create(
            teacher=mathematics_backup,
            subject=self.subject,
        )
        subjects_by_name = {
            'Mathematics': self.subject,
        }
        teacher_by_subject = {
            'Mathematics': self.teacher,
        }
        categories_by_section = {
            '1A': {
                'Mathematics': 9, 'English': 9, 'EVS': 6, 'Tamil': 5,
                'Drawing': 2, 'Games': 2, 'Tamil Reading': 2,
            },
            '2': {
                'Mathematics': 5, 'English': 6, 'EVS': 5, 'Hindi': 5, 'Tamil': 6,
                'Drawing': 2, 'Games': 2, 'GK': 2, 'Tamil Reading': 2,
            },
            '3': {
                'English': 5, 'Games': 2, 'GK': 2, 'Hindi': 5, 'Mathematics': 5,
                'Science': 5, 'Social Studies': 5, 'Tamil': 6,
            },
            '4': {
                'Drawing': 2, 'English': 5, 'Games': 2, 'Hindi': 5,
                'Mathematics': 5, 'Science': 5, 'Social Studies': 5, 'Tamil': 6,
            },
            '5': {
                'Drawing': 2, 'English': 6, 'Games': 2, 'GK': 2, 'Mathematics': 5,
                'Science': 6, 'Social Studies': 6, 'Tamil': 6,
            },
        }
        activity_names = {'Drawing', 'Games', 'GK', 'Tamil Reading'}
        for section in sections:
            for name, periods_per_week in categories_by_section[section.name].items():
                subject = subjects_by_name.get(name)
                if subject is None:
                    subject = Subject.objects.create(
                        name=name,
                        category=(
                            Subject.ACTIVITY if name in activity_names else Subject.BASIC
                        ),
                    )
                    subjects_by_name[name] = subject
                    teacher = Teacher.objects.create(name=f'{name} Teacher')
                    TeacherSubject.objects.create(teacher=teacher, subject=subject)
                    teacher_by_subject[name] = teacher
                SectionSubject.objects.update_or_create(
                    section=section,
                    subject=subject,
                    defaults={'periods_per_week': periods_per_week},
                )

        period_by_number = {
            period.number: period for period in Period.objects.all()
        }
        for day in dict(TimetableSlot.DAYS_OF_WEEK):
            TimetableConstraint.objects.create(
                section=sections[4],
                subject=self.subject,
                teacher=mathematics_backup,
                day=day,
                period=period_by_number[3],
            )
        for subject_name, day, period_number, section_index in (
            ('Games', 'Monday', 7, 0),
            ('Games', 'Wednesday', 6, 0),
            ('Drawing', 'Tuesday', 7, 0),
            ('Drawing', 'Thursday', 7, 0),
            ('GK', 'Monday', 7, 2),
        ):
            subject = subjects_by_name[subject_name]
            TimetableConstraint.objects.create(
                section=sections[section_index],
                subject=subject,
                teacher=teacher_by_subject[subject_name],
                day=day,
                period=period_by_number[period_number],
            )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        self.assertEqual(len(schedule), len(sections) * 5 * len(period_by_number))
        teacher_slots = [(entry[2], entry[3], entry[4]) for entry in schedule]
        self.assertEqual(len(teacher_slots), len(set(teacher_slots)))
        for section in sections:
            for assignment in SectionSubject.objects.filter(
                section=section,
                subject__category=Subject.BASIC,
            ):
                for day, _ in TimetableSlot.DAYS_OF_WEEK:
                    self.assertTrue(
                        any(
                            entry[0] == section.id
                            and entry[1] == assignment.subject_id
                            and entry[3] == day
                            for entry in schedule
                        ),
                        f'{assignment.subject.name} is missing for {section.name} on {day}',
                    )

    def test_basic_subjects_are_daily_and_activity_is_twice_on_separate_days(self):
        basic_subjects = [self.subject]
        for name in ('Tamil', 'English', 'Science', 'Social Studies', 'Hindi', 'EVS'):
            subject = Subject.objects.create(name=name, category=Subject.BASIC)
            teacher = Teacher.objects.create(name=f'{name} Teacher')
            TeacherSubject.objects.create(teacher=teacher, subject=subject)
            SectionSubject.objects.create(
                section=self.section,
                subject=subject,
                periods_per_week=5,
            )
            basic_subjects.append(subject)

        activity = Subject.objects.create(name='Drawing', category=Subject.ACTIVITY)
        activity_teacher = Teacher.objects.create(name='Drawing Teacher')
        TeacherSubject.objects.create(teacher=activity_teacher, subject=activity)
        activity_assignment = SectionSubject.objects.create(
            section=self.section,
            subject=activity,
            periods_per_week=3,
        )
        fixed_period = Period.objects.get(number=7)
        TimetableConstraint.objects.create(
            section=self.section,
            subject=activity,
            teacher=activity_teacher,
            day='Monday',
            period=fixed_period,
        )

        plan_adjustments = {}
        schedule, errors = build_schedule(plan_adjustments)

        self.assertEqual(errors, [], errors)
        for day, _ in TimetableSlot.DAYS_OF_WEEK:
            subjects_scheduled = {
                entry[1] for entry in schedule
                if entry[0] == self.section.id and entry[3] == day
            }
            self.assertTrue(
                {subject.id for subject in basic_subjects}.issubset(subjects_scheduled),
            )

        activity_entries = [
            entry for entry in schedule
            if entry[0] == self.section.id and entry[1] == activity.id
        ]
        self.assertEqual(len(activity_entries), 2)
        self.assertEqual(len({entry[3] for entry in activity_entries}), 2)
        self.assertIn(activity_assignment.id, plan_adjustments)
        self.assertEqual(plan_adjustments[activity_assignment.id], 2)

    def test_activities_except_yoga_are_scheduled_in_the_last_two_periods(self):
        self.assignment.periods_per_week = 5
        self.assignment.save(update_fields=['periods_per_week'])
        activities = []
        for name in ('Games', 'GK', 'Drawing', 'Tamil Reading'):
            activity = Subject.objects.create(name=name, category=Subject.ACTIVITY)
            activity_teacher = Teacher.objects.create(name=f'{name} Teacher')
            TeacherSubject.objects.create(teacher=activity_teacher, subject=activity)
            SectionSubject.objects.create(
                section=self.section,
                subject=activity,
                periods_per_week=2,
            )
            activities.append(activity)

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        last_period_numbers = {
            period.number
            for period in Period.objects.order_by('-number')[:2]
        }
        for activity in activities:
            activity_entries = [
                entry for entry in schedule
                if entry[0] == self.section.id and entry[1] == activity.id
            ]
            self.assertEqual(len(activity_entries), 2)
            self.assertTrue(
                all(
                    Period.objects.get(pk=entry[4]).number in last_period_numbers
                    for entry in activity_entries
                ),
                (activity.name, activity_entries),
            )

    def test_yoga_is_scheduled_before_lunch(self):
        self.assignment.periods_per_week = 5
        self.assignment.save(update_fields=['periods_per_week'])
        TimetableBreak.objects.create(
            kind=TimetableBreak.LUNCH,
            after_period=Period.objects.get(number=4),
        )
        yoga = Subject.objects.create(name='Yoga', category=Subject.ACTIVITY)
        yoga_teacher = Teacher.objects.create(name='Yoga Teacher')
        TeacherSubject.objects.create(teacher=yoga_teacher, subject=yoga)
        SectionSubject.objects.create(
            section=self.section,
            subject=yoga,
            periods_per_week=2,
        )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        yoga_entries = [
            entry for entry in schedule
            if entry[0] == self.section.id and entry[1] == yoga.id
        ]
        self.assertEqual(len(yoga_entries), 2)
        self.assertTrue(all(
            Period.objects.get(pk=entry[4]).number <= 4
            for entry in yoga_entries
        ))

    def test_yoga_uses_timetable_lunch_gap_when_break_is_not_configured(self):
        self.assignment.periods_per_week = 5
        self.assignment.save(update_fields=['periods_per_week'])
        lunch_gap_start = Period.objects.get(number=5)
        lunch_gap_start.start_time = time(11, 45)
        lunch_gap_start.end_time = time(12, 30)
        lunch_gap_start.save(update_fields=['start_time', 'end_time'])
        yoga = Subject.objects.create(name='Yoga', category=Subject.ACTIVITY)
        yoga_teacher = Teacher.objects.create(name='Yoga Teacher')
        TeacherSubject.objects.create(teacher=yoga_teacher, subject=yoga)
        SectionSubject.objects.create(
            section=self.section,
            subject=yoga,
            periods_per_week=2,
        )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        yoga_entries = [
            entry for entry in schedule
            if entry[0] == self.section.id and entry[1] == yoga.id
        ]
        self.assertEqual(len(yoga_entries), 2)
        self.assertTrue(all(
            Period.objects.get(pk=entry[4]).number <= 4
            for entry in yoga_entries
        ))

    def test_subject_category_is_editable_through_the_api(self):
        response = APIClient().patch(
            f'/api/subjects/{self.subject.id}/',
            {'category': Subject.ACTIVITY},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.category, Subject.ACTIVITY)

    def test_fixed_constraint_requires_a_weekly_plan_assignment(self):
        other_subject = Subject.objects.create(name='Science')
        serializer = TimetableConstraintSerializer(data={
            'section': self.section.id,
            'subject': other_subject.id,
            'teacher': self.teacher.id,
            'day': 'Monday',
            'period': self.periods[0].id,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('weekly teaching plan', str(serializer.errors))

    def test_fixed_constraint_rejects_unavailable_teacher(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
            is_available=False,
        )
        serializer = TimetableConstraintSerializer(data={
            'section': self.section.id,
            'subject': self.subject.id,
            'teacher': self.teacher.id,
            'day': 'Monday',
            'period': self.periods[0].id,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('marked unavailable', str(serializer.errors))

    def test_fixed_constraint_cannot_exceed_weekly_assignment(self):
        self.assignment.periods_per_week = 1
        self.assignment.save()
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )
        serializer = TimetableConstraintSerializer(data={
            'section': self.section.id,
            'subject': self.subject.id,
            'teacher': self.teacher.id,
            'day': 'Tuesday',
            'period': self.periods[1].id,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('all are already fixed', str(serializer.errors))

    def test_teacher_cannot_be_marked_unavailable_for_fixed_class(self):
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )
        serializer = TeacherAvailabilitySerializer(data={
            'teacher': self.teacher.id,
            'day': 'Monday',
            'period': self.periods[0].id,
            'is_available': False,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('Remove the fixed class', str(serializer.errors))

    def test_teacher_mapping_cannot_change_while_used_by_fixed_class(self):
        mapping = TeacherSubject.objects.get(teacher=self.teacher, subject=self.subject)
        another_teacher = Teacher.objects.create(name='Morgan')
        serializer = TeacherSubjectSerializer(
            mapping,
            data={
                'teacher': another_teacher.id,
                'subject': self.subject.id,
                'section': self.section.id,
            },
        )
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('Remove fixed classes', str(serializer.errors))

    def test_teacher_mapping_is_limited_to_selected_class(self):
        second_section = Section.objects.create(name='2')
        SectionSubject.objects.create(
            section=second_section,
            subject=self.subject,
            periods_per_week=5,
        )
        self.assignment.periods_per_week = 5
        self.assignment.save(update_fields=['periods_per_week'])
        self.teacher.name = 'Sumitra'
        self.teacher.save(update_fields=['name'])
        mapping = TeacherSubject.objects.get(teacher=self.teacher, subject=self.subject)
        mapping.section = second_section
        mapping.save(update_fields=['section'])
        general_teacher = Teacher.objects.create(name='Other Maths Teacher')
        TeacherSubject.objects.create(
            teacher=general_teacher,
            subject=self.subject,
        )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        self.assertTrue(any(
            entry[0] == second_section.id and entry[2] == self.teacher.id
            for entry in schedule
        ))
        self.assertFalse(any(
            entry[0] == self.section.id and entry[2] == self.teacher.id
            for entry in schedule
        ))

    def test_class_specific_teacher_mapping_is_scheduled_at_least_once(self):
        self.teacher.name = 'Sumitra'
        self.teacher.save(update_fields=['name'])
        mapping = TeacherSubject.objects.get(teacher=self.teacher, subject=self.subject)
        mapping.section = self.section
        mapping.save(update_fields=['section'])
        general_teacher = Teacher.objects.create(name='Other Maths Teacher')
        TeacherSubject.objects.create(
            teacher=general_teacher,
            subject=self.subject,
        )

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        self.assertTrue(any(
            entry[0] == self.section.id
            and entry[1] == self.subject.id
            and entry[2] == self.teacher.id
            for entry in schedule
        ))

    def test_teacher_mapping_api_requires_a_class(self):
        serializer = TeacherSubjectSerializer(data={
            'teacher': self.teacher.id,
            'subject': self.subject.id,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('section', serializer.errors)

    def test_bulk_teacher_mapping_creates_all_selected_subjects(self):
        second_subject = Subject.objects.create(name='English')
        third_subject = Subject.objects.create(name='Science')
        response = APIClient().post(
            '/api/teacher-subjects/bulk-create/',
            {
                'teacher': self.teacher.id,
                'sections': [self.section.id],
                'subjects': [second_subject.id, third_subject.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 2)
        self.assertEqual(response.data['existing_count'], 0)
        self.assertEqual(len(response.data['mappings']), 2)
        self.assertEqual(
            set(TeacherSubject.objects.filter(
                teacher=self.teacher,
                section=self.section,
            ).values_list('subject_id', flat=True)),
            {second_subject.id, third_subject.id},
        )

    def test_bulk_teacher_mapping_rejects_duplicate_subjects_and_skips_existing_mappings(self):
        second_subject = Subject.objects.create(name='English')
        client = APIClient()
        duplicate_response = client.post(
            '/api/teacher-subjects/bulk-create/',
            {
                'teacher': self.teacher.id,
                'sections': [self.section.id],
                'subjects': [second_subject.id, second_subject.id],
            },
            format='json',
        )
        TeacherSubject.objects.create(
            teacher=self.teacher,
            subject=second_subject,
            section=self.section,
        )
        existing_response = client.post(
            '/api/teacher-subjects/bulk-create/',
            {
                'teacher': self.teacher.id,
                'sections': [self.section.id],
                'subjects': [second_subject.id, self.subject.id],
            },
            format='json',
        )

        self.assertEqual(duplicate_response.status_code, 400)
        self.assertEqual(existing_response.status_code, 201, existing_response.data)
        self.assertEqual(existing_response.data['created_count'], 1)
        self.assertEqual(existing_response.data['existing_count'], 1)
        self.assertEqual(len(existing_response.data['mappings']), 2)
        self.assertTrue(TeacherSubject.objects.filter(
            teacher=self.teacher,
            subject=self.subject,
            section=self.section,
        ).exists())

    def test_bulk_teacher_mapping_applies_subjects_to_each_selected_class(self):
        second_section = Section.objects.create(name='2')
        second_subject = Subject.objects.create(name='English')
        response = APIClient().post(
            '/api/teacher-subjects/bulk-create/',
            {
                'teacher': self.teacher.id,
                'sections': [self.section.id, second_section.id],
                'subjects': [self.subject.id, second_subject.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 4)
        self.assertEqual(
            {
                (mapping.section_id, mapping.subject_id)
                for mapping in TeacherSubject.objects.filter(
                    teacher=self.teacher,
                    section__in=[self.section, second_section],
                    subject__in=[self.subject, second_subject],
                )
            },
            {
                (section_id, subject_id)
                for section_id in (self.section.id, second_section.id)
                for subject_id in (self.subject.id, second_subject.id)
            },
        )

    def test_bulk_teacher_mapping_requires_class_selection(self):
        response = APIClient().post(
            '/api/teacher-subjects/bulk-create/',
            {
                'teacher': self.teacher.id,
                'subjects': [self.subject.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('sections', response.data)

    def test_combined_teacher_mapping_schedules_subjects_in_the_same_periods(self):
        second_section = Section.objects.create(name='2')
        for section, subject_name in (
            (self.section, 'English'),
            (second_section, 'Science'),
        ):
            filler_subject = Subject.objects.create(name=subject_name)
            filler_teacher = Teacher.objects.create(name=f'{subject_name} Teacher')
            TeacherSubject.objects.create(
                teacher=filler_teacher,
                subject=filler_subject,
                section=section,
            )
            SectionSubject.objects.create(
                section=section,
                subject=filler_subject,
                periods_per_week=30,
            )
        response = APIClient().post(
            '/api/teacher-subjects/bulk-create/',
            {
                'teacher': self.teacher.id,
                'sections': [self.section.id, second_section.id],
                'subjects': [self.subject.id],
                'combine_classes': True,
                'combined_periods_per_week': 5,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data['combined_groups']), 1)
        self.assertEqual(response.data['combined_groups'][0]['periods_per_week'], 5)
        self.assertTrue(SectionSubject.objects.filter(
            section=second_section,
            subject=self.subject,
        ).exists())

        schedule, errors = build_schedule()

        self.assertEqual(errors, [], errors)
        first_slots = {
            (entry[3], entry[4])
            for entry in schedule
            if entry[0] == self.section.id and entry[1] == self.subject.id
        }
        second_slots = {
            (entry[3], entry[4])
            for entry in schedule
            if entry[0] == second_section.id and entry[1] == self.subject.id
        }
        self.assertEqual(len(first_slots.intersection(second_slots)), 5)

    def test_combined_yoga_schedule_uses_one_shared_monday_period(self):
        self.subject.name = 'Yoga'
        self.subject.category = Subject.ACTIVITY
        self.subject.save(update_fields=['name', 'category'])
        TimetableBreak.objects.create(
            kind=TimetableBreak.LUNCH,
            after_period=Period.objects.get(number=4),
        )
        sections = [self.section] + [
            Section.objects.create(name=str(number))
            for number in range(2, 6)
        ]
        self.assignment.periods_per_week = 2
        self.assignment.save(update_fields=['periods_per_week'])
        for section in sections[1:]:
            SectionSubject.objects.create(
                section=section,
                subject=self.subject,
                periods_per_week=2,
            )
        group = CombinedTeachingGroup.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            periods_per_week=1,
        )
        group.sections.set(sections)

        for section in sections:
            filler_subject = Subject.objects.create(name=f'Math {section.name}')
            filler_teacher = Teacher.objects.create(name=f'Math Teacher {section.name}')
            TeacherSubject.objects.create(
                teacher=filler_teacher,
                subject=filler_subject,
                section=section,
            )
            SectionSubject.objects.create(
                section=section,
                subject=filler_subject,
                periods_per_week=5,
            )

        plan_adjustments = {}
        schedule, errors = build_schedule(plan_adjustments)

        self.assertEqual(errors, [], errors)
        yoga_entries = [entry for entry in schedule if entry[1] == self.subject.id]
        self.assertEqual(len(yoga_entries), len(sections))
        self.assertEqual({entry[3] for entry in yoga_entries}, {'Monday'})
        period_four_id = Period.objects.get(number=4).id
        self.assertEqual({entry[4] for entry in yoga_entries}, {period_four_id})
        self.assertEqual(
            {entry[0] for entry in yoga_entries},
            {section.id for section in sections},
        )
        self.assertEqual(
            {
                assignment.id: plan_adjustments[assignment.id]
                for assignment in SectionSubject.objects.filter(subject=self.subject)
            },
            {
                assignment.id: 1
                for assignment in SectionSubject.objects.filter(subject=self.subject)
            },
        )

    def test_combining_yoga_reduces_class_plans_to_shared_count(self):
        yoga = Subject.objects.create(name='Yoga', category=Subject.ACTIVITY)
        sections = [self.section] + [
            Section.objects.create(name=str(number))
            for number in range(2, 6)
        ]
        assignments = [
            SectionSubject.objects.create(
                section=section,
                subject=yoga,
                periods_per_week=2,
            )
            for section in sections
        ]

        response = APIClient().post(
            '/api/teacher-subjects/bulk-create/',
            {
                'teacher': self.teacher.id,
                'sections': [section.id for section in sections],
                'subjects': [yoga.id],
                'combine_classes': True,
                'combined_periods_per_week': 1,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        for assignment in assignments:
            assignment.refresh_from_db()
        self.assertEqual(
            [assignment.periods_per_week for assignment in assignments],
            [1] * len(sections),
        )
        self.assertEqual(response.data['combined_groups'][0]['periods_per_week'], 1)

    def test_fixed_class_dependencies_cannot_be_deleted(self):
        TimetableConstraint.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )
        client = APIClient()

        assignment_response = client.delete(
            f'/api/section-subjects/{self.assignment.id}/',
        )
        mapping = TeacherSubject.objects.get(teacher=self.teacher, subject=self.subject)
        mapping_response = client.delete(f'/api/teacher-subjects/{mapping.id}/')

        self.assertEqual(assignment_response.status_code, 400)
        self.assertEqual(mapping_response.status_code, 400)
        self.assertTrue(SectionSubject.objects.filter(pk=self.assignment.pk).exists())
        self.assertTrue(TeacherSubject.objects.filter(pk=mapping.pk).exists())

    def test_weekly_assignment_cannot_be_reduced_below_fixed_classes(self):
        self.assignment.periods_per_week = 2
        self.assignment.save()
        for day, period in zip(('Monday', 'Tuesday'), self.periods):
            TimetableConstraint.objects.create(
                section=self.section,
                subject=self.subject,
                teacher=self.teacher,
                day=day,
                period=period,
            )
        serializer = SectionSubjectSerializer(
            self.assignment,
            data={
                'section': self.section.id,
                'subject': self.subject.id,
                'periods_per_week': 1,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('cannot be reduced below 2', str(serializer.errors))

    def test_teacher_is_never_scheduled_for_two_sections_at_once(self):
        second_section = Section.objects.create(name='1B')
        SectionSubject.objects.create(
            section=second_section,
            subject=self.subject,
            periods_per_week=8,
        )
        second_teacher = Teacher.objects.create(name='Morgan')
        TeacherSubject.objects.create(teacher=second_teacher, subject=self.subject)
        self.assignment.periods_per_week = 8
        self.assignment.save()

        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        teacher_slots = [(entry[2], entry[3], entry[4]) for entry in schedule]
        self.assertEqual(len(teacher_slots), len(set(teacher_slots)))

    def test_reports_missing_teacher_subject_mapping(self):
        TeacherSubject.objects.all().delete()

        schedule, errors = build_schedule()

        self.assertIsNone(schedule)
        self.assertTrue(any(
            'Map at least one teacher' in error
            and f'class {self.section.name}' in error
            and 'remove it from the weekly plan' in error
            for error in errors
        ))

    def test_reports_when_one_teacher_is_forced_beyond_weekly_capacity(self):
        computer = Subject.objects.create(name='Computer')
        english = Subject.objects.create(name='English')
        gk = Subject.objects.create(name='GK')
        section_b = Section.objects.create(name='1B')
        section_c = Section.objects.create(name='1C')
        computer_teacher = Teacher.objects.create(name='Computer Teacher')
        english_teacher = Teacher.objects.create(name='English Teacher')
        gk_teacher = Teacher.objects.create(name='GK Teacher')
        TeacherSubject.objects.create(teacher=computer_teacher, subject=computer)
        TeacherSubject.objects.create(teacher=english_teacher, subject=english)
        TeacherSubject.objects.create(teacher=gk_teacher, subject=gk)

        SectionSubject.objects.create(section=self.section, subject=computer, periods_per_week=5)
        SectionSubject.objects.create(section=self.section, subject=gk, periods_per_week=5)
        SectionSubject.objects.create(section=section_b, subject=computer, periods_per_week=5)
        SectionSubject.objects.create(section=section_b, subject=english, periods_per_week=3)
        SectionSubject.objects.create(section=section_c, subject=computer, periods_per_week=3)
        SectionSubject.objects.create(section=section_c, subject=english, periods_per_week=3)

        schedule, errors = build_schedule()

        self.assertIsNone(schedule)
        self.assertTrue(any(
            'Computer Teacher is required to teach Computer for at least' in error
            and 'only 40 periods are available' in error
            for error in errors
        ), errors)

        backup_teacher = Teacher.objects.create(name='Backup Computer Teacher')
        TeacherSubject.objects.create(teacher=backup_teacher, subject=computer)

        schedule, errors = build_schedule()

        self.assertEqual(errors, [])
        self.assertEqual(
            len(schedule),
            Section.objects.count() * len(TimetableSlot.DAYS_OF_WEEK) * Period.objects.count(),
        )

    def test_generate_endpoint_persists_a_complete_schedule(self):
        response = APIClient().post('/api/schedule/generate/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['count'],
            Section.objects.count() * len(TimetableSlot.DAYS_OF_WEEK) * Period.objects.count(),
        )
        self.assertEqual(ScheduleEntry.objects.count(), response.data['count'])

    def test_schedule_endpoint_filters_by_section_and_teacher(self):
        second_section = Section.objects.create(name='1B')
        entry = ScheduleEntry.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )
        ScheduleEntry.objects.create(
            section=second_section,
            subject=self.subject,
            teacher=self.teacher,
            day='Tuesday',
            period=self.periods[0],
        )

        response = APIClient().get(
            f'/api/schedule/?section={self.section.id}&teacher={self.teacher.id}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [entry.id])

    def test_failed_generation_does_not_replace_existing_schedule(self):
        existing = ScheduleEntry.objects.create(
            section=self.section,
            subject=self.subject,
            teacher=self.teacher,
            day='Monday',
            period=self.periods[0],
        )
        TeacherAvailability.objects.bulk_create([
            TeacherAvailability(
                teacher=self.teacher,
                day=day,
                period=period,
                is_available=False,
            )
            for day, _ in TimetableSlot.DAYS_OF_WEEK
            for period in Period.objects.all()
        ])

        response = APIClient().post('/api/schedule/generate/')

        self.assertEqual(response.status_code, 400)
        self.assertTrue(ScheduleEntry.objects.filter(pk=existing.pk).exists())


class CerdScheduleGenerationTests(TestCase):
    def test_generates_five_classes_with_balanced_mapped_teachers(self):
        Period.objects.filter(number__gt=7).delete()
        sections = {'1': Section.objects.create(name='1')}
        sections.update({
            str(number): Section.objects.create(name=str(number))
            for number in range(2, 6)
        })
        subjects = {
            'Mathematics': Subject.objects.create(name='Mathematics'),
        }
        for name in (
            'Tamil', 'English', 'Science', 'Social Studies', 'Hindi', 'EVS',
            'Drawing', 'Games', 'Tamil Reading', 'GK',
        ):
            subjects[name] = Subject.objects.create(
                name=name,
                category=(
                    Subject.ACTIVITY
                    if name in {'Drawing', 'Games', 'Tamil Reading', 'GK'}
                    else Subject.BASIC
                ),
            )

        teachers = {
            name: Teacher.objects.create(name=name)
            for name in (
                'Tamil/Maths', 'English/Hindi', 'EVS/Maths',
                'Social/GK/Drawing', 'Games', 'Hindi',
                'Maths backup 1', 'Maths backup 2', 'Maths backup 3',
            )
        }
        teacher_mappings = {
            'Mathematics': [
                'Tamil/Maths', 'EVS/Maths', 'Maths backup 1',
                'Maths backup 2', 'Maths backup 3',
            ],
            'Tamil': ['Tamil/Maths', 'Social/GK/Drawing'],
            'English': ['English/Hindi'],
            'Science': ['EVS/Maths'],
            'Social Studies': ['Social/GK/Drawing'],
            'Hindi': ['English/Hindi', 'Hindi'],
            'EVS': ['EVS/Maths'],
            'Drawing': ['Social/GK/Drawing'],
            'Games': ['Games'],
            'Tamil Reading': ['Tamil/Maths'],
            'GK': ['Hindi'],
        }
        for subject_name, teacher_names in teacher_mappings.items():
            TeacherSubject.objects.bulk_create([
                TeacherSubject(
                    teacher=teachers[teacher_name],
                    subject=subjects[subject_name],
                )
                for teacher_name in teacher_names
            ])

        weekly_plans = {
            '1': {
                'Tamil': 5, 'English': 9, 'Mathematics': 9, 'EVS': 6,
                'Drawing': 2, 'Games': 2, 'Tamil Reading': 2,
            },
            '2': {
                'Tamil': 6, 'English': 6, 'Hindi': 5, 'Mathematics': 5,
                'EVS': 5, 'Drawing': 2, 'Games': 2, 'Tamil Reading': 2, 'GK': 2,
            },
            '3': {
                'Tamil': 6, 'English': 5, 'Science': 5, 'Social Studies': 5,
                'Hindi': 5, 'Mathematics': 5, 'Games': 2, 'GK': 2,
            },
            '4': {
                'Tamil': 6, 'English': 5, 'Science': 5, 'Social Studies': 5,
                'Hindi': 5, 'Mathematics': 5, 'Drawing': 2, 'Games': 2,
            },
            '5': {
                'Tamil': 6, 'English': 6, 'Science': 6, 'Social Studies': 6,
                'Mathematics': 5, 'Drawing': 2, 'Games': 2, 'GK': 2,
            },
        }
        for section_name, weekly_plan in weekly_plans.items():
            for subject_name, periods_per_week in weekly_plan.items():
                SectionSubject.objects.create(
                    section=sections[section_name],
                    subject=subjects[subject_name],
                    periods_per_week=periods_per_week,
                )

        period_three = Period.objects.get(number=3)
        TimetableConstraint.objects.bulk_create([
            TimetableConstraint(
                section=sections['5'],
                subject=subjects['Mathematics'],
                teacher=teachers['Maths backup 1'],
                day=day,
                period=period_three,
            )
            for day, _ in TimetableSlot.DAYS_OF_WEEK
        ])

        plan_adjustments = {}
        schedule, errors = build_schedule(plan_adjustments)

        self.assertEqual(errors, [], errors)
        self.assertEqual(len(schedule), 5 * 5 * 7)
        self.assertEqual(
            len({(teacher_id, day, period_id) for _, _, teacher_id, day, period_id in schedule}),
            len(schedule),
        )
        for section_name, section in sections.items():
            for assignment in SectionSubject.objects.filter(
                section=section,
                subject__category=Subject.BASIC,
            ):
                for day, _ in TimetableSlot.DAYS_OF_WEEK:
                    self.assertTrue(any(
                        entry[0] == section.id
                        and entry[1] == assignment.subject_id
                        and entry[3] == day
                        for entry in schedule
                    ), f'{section_name}: {assignment.subject.name} is missing on {day}')
