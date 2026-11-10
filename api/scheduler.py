from collections import defaultdict

from .models import (
    CombinedTeachingGroup, Period, Section, SectionSubject, Subject, TeacherAvailability,
    TeacherSubject, TimetableBreak, TimetableConstraint, TimetableSlot,
)


def _lunch_after_period(periods):
    lunch_break = TimetableBreak.objects.filter(
        kind=TimetableBreak.LUNCH,
    ).select_related('after_period').first()
    if lunch_break:
        return lunch_break.after_period

    for after_period, next_period in zip(periods, periods[1:]):
        gap_minutes = (
            next_period.start_time.hour * 60 + next_period.start_time.minute
            - after_period.end_time.hour * 60
            - after_period.end_time.minute
        )
        if gap_minutes == TimetableBreak.DURATIONS[TimetableBreak.LUNCH]:
            return after_period
    return None


def distribute_weekly_periods(subject_ids, fixed_counts, capacity, categories=None):
    categories = categories or {}
    if len(subject_ids) > capacity:
        raise ValueError('There are more selected subjects than available weekly periods.')

    allocations = {}
    basic_subject_ids = []
    for subject_id in subject_ids:
        category = categories.get(subject_id, Subject.BASIC)
        minimum = 5 if category == Subject.BASIC else 2
        allocations[subject_id] = max(fixed_counts.get(subject_id, 0), minimum)
        if category == Subject.BASIC:
            basic_subject_ids.append(subject_id)

    if sum(allocations.values()) > capacity:
        raise ValueError(
            f"Subject minimums require {sum(allocations.values())} weekly periods, "
            f"but only {capacity} are available."
        )

    while sum(allocations.values()) < capacity:
        if not basic_subject_ids:
            raise ValueError(
                'Activity subjects use their fixed weekly minimums. Add at least one '
                'Basic subject to fill the remaining weekly periods.'
            )
        next_subject_id = min(
            basic_subject_ids,
            key=lambda subject_id: (allocations[subject_id], subject_id),
        )
        allocations[next_subject_id] += 1
    return allocations


def _solve_with_milp(
    candidates,
    sections,
    assignments,
    periods,
    days,
    targets,
    fixed,
    mappings,
    combined_groups,
):
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    candidate_index = {candidate: index for index, candidate in enumerate(candidates)}
    teacher_slot_terms = defaultdict(list)
    section_slots = defaultdict(list)
    section_subjects = defaultdict(list)
    section_subject_days = defaultdict(list)
    combined_sections = {}
    combined_group_slots = {}
    for group in combined_groups:
        section_ids = sorted(group.sections.values_list('id', flat=True))
        combined_sections[group.id] = section_ids
        for day in days:
            for period in periods:
                combined_group_slots[(group.id, day, period.id)] = (
                    len(candidates) + len(combined_group_slots)
                )

    for candidate, index in candidate_index.items():
        section_id, day, period_id, subject_id, teacher_id = candidate
        teacher_slot_terms[(teacher_id, day, period_id)].append(index)
        section_slots[(section_id, day, period_id)].append(index)
        section_subjects[(section_id, subject_id)].append(index)
        section_subject_days[(section_id, subject_id, day)].append(index)

    fixed_teacher_slot_counts = defaultdict(int)
    for (section_id, day, period_id), constraint in fixed.items():
        fixed_teacher_slot_counts[
            (constraint.teacher_id, day, period_id)
        ] += 1

    rows = []
    lower_bounds = []
    upper_bounds = []

    def add_constraint(terms, lower, upper):
        row = defaultdict(float)
        for index, coefficient in terms:
            row[index] += coefficient
        rows.append(row)
        lower_bounds.append(lower)
        upper_bounds.append(upper)

    for section in sections:
        for day in days:
            for period in periods:
                slot = (section.id, day, period.id)
                add_constraint(
                    [(index, 1) for index in section_slots[slot]],
                    1,
                    1,
                )

    for teacher_slot, indices in teacher_slot_terms.items():
        terms = [(index, 1) for index in indices]
        for group in combined_groups:
            group_teacher_slot = (
                group.teacher_id,
                teacher_slot[1],
                teacher_slot[2],
            )
            if group_teacher_slot != teacher_slot:
                continue
            group_size = len(combined_sections[group.id])
            terms.append((
                combined_group_slots[(group.id, teacher_slot[1], teacher_slot[2])],
                -(group_size - 1),
            ))
        add_constraint(
            terms,
            0,
            max(1, fixed_teacher_slot_counts.get(teacher_slot, 0)),
        )

    assignment_by_key = {
        (assignment.section_id, assignment.subject_id): assignment
        for assignment in assignments
    }
    for mapping in mappings:
        key = (mapping.section_id, mapping.subject_id)
        if mapping.section_id is None or key not in assignment_by_key:
            continue
        mapped_teacher_indices = [
            index
            for candidate, index in candidate_index.items()
            if candidate[0] == mapping.section_id
            and candidate[3] == mapping.subject_id
            and candidate[4] == mapping.teacher_id
        ]
        add_constraint(
            [(index, 1) for index in mapped_teacher_indices],
            1,
            float('inf'),
        )

    for group in combined_groups:
        section_ids = combined_sections[group.id]
        is_yoga = (
            group.subject.category == Subject.ACTIVITY
            and group.subject.name.strip().casefold() == 'yoga'
        )
        shared_candidates = {
            section_id: {
                (day, period.id): candidate_index.get((
                    section_id,
                    day,
                    period.id,
                    group.subject_id,
                    group.teacher_id,
                ))
                for day in days
                for period in periods
            }
            for section_id in section_ids
        }
        for day in days:
            for period in periods:
                indicator = combined_group_slots[(group.id, day, period.id)]
                if is_yoga and (day != 'Monday' or period.number != 4):
                    add_constraint([(indicator, 1)], 0, 0)
                section_indices = [
                    shared_candidates[section_id][(day, period.id)]
                    for section_id in section_ids
                ]
                available_indices = [
                    index for index in section_indices if index is not None
                ]
                for index in available_indices:
                    add_constraint([(indicator, 1), (index, -1)], -float('inf'), 0)
                if len(available_indices) != len(section_ids):
                    add_constraint([(indicator, 1)], 0, 0)
                else:
                    add_constraint(
                        [(index, 1) for index in available_indices] + [(indicator, -1)],
                        -float('inf'),
                        len(section_ids) - 1,
                    )

        add_constraint(
            [
                (combined_group_slots[(group.id, day, period.id)], 1)
                for day in days
                for period in periods
            ],
            group.periods_per_week,
            group.periods_per_week,
        )

    for key, target in targets.items():
        assignment = assignment_by_key[key]
        add_constraint(
            [(index, 1) for index in section_subjects[key]],
            target,
            target,
        )
        for day in days:
            day_indices = section_subject_days[(key[0], key[1], day)]
            if assignment.subject.category == Subject.BASIC:
                fixed_count = sum(
                    constraint.section_id == key[0]
                    and constraint.subject_id == key[1]
                    and constraint.day == day
                    for constraint in fixed.values()
                )
                add_constraint(
                    [(index, 1) for index in day_indices],
                    max(fixed_count, target // len(days)),
                    max(
                        fixed_count,
                        (target + len(days) - 1) // len(days),
                    ),
                )
            else:
                add_constraint([(index, 1) for index in day_indices], 0, 1)

    max_teacher_load_index = len(candidates)
    max_teacher_load_index += len(combined_group_slots)
    teachers = sorted({candidate[4] for candidate in candidates})
    for teacher_id in teachers:
        terms = []
        for (slot_teacher_id, day, period_id), indices in teacher_slot_terms.items():
            if slot_teacher_id != teacher_id:
                continue
            fixed_count = fixed_teacher_slot_counts.get(
                (teacher_id, day, period_id),
                0,
            )
            terms.extend(
                (index, 1)
                for index in indices[:1 if fixed_count > 1 else len(indices)]
            )
            for group in combined_groups:
                if (
                    group.teacher_id == teacher_id
                    and (group.teacher_id, day, period_id) in teacher_slot_terms
                ):
                    terms.append((
                        combined_group_slots[(group.id, day, period_id)],
                        -(len(combined_sections[group.id]) - 1),
                    ))
        terms.append((max_teacher_load_index, -1))
        add_constraint(terms, -float('inf'), 0)

    row_indices = []
    column_indices = []
    values = []
    for row_index, row in enumerate(rows):
        for column_index, value in row.items():
            row_indices.append(row_index)
            column_indices.append(column_index)
            values.append(value)

    matrix = coo_matrix(
        (values, (row_indices, column_indices)),
        shape=(len(rows), max_teacher_load_index + 1),
    ).tocsr()
    objective = np.zeros(max_teacher_load_index + 1)
    objective[max_teacher_load_index] = (
        len(sections) * len(days) * len(periods) + 1
    )
    integrality = np.zeros(max_teacher_load_index + 1)
    integrality[:max_teacher_load_index] = 1
    bounds = Bounds(
        np.zeros(max_teacher_load_index + 1),
        np.append(
            np.append(
                np.ones(len(candidates)),
                np.ones(len(combined_group_slots)),
            ),
            len(days) * len(periods),
        ),
    )
    result = milp(
        c=objective,
        integrality=integrality,
        bounds=bounds,
        constraints=LinearConstraint(
            matrix,
            np.asarray(lower_bounds),
            np.asarray(upper_bounds),
        ),
        options={'time_limit': 30},
    )
    if result.x is None:
        if result.status == 2:
            return None, [
                'The current teacher mappings and fixed classes do not allow a conflict-free timetable. '
                'Check class-specific teacher requirements and combined-class availability. '
                f'Optimizer: {result.message}'
            ]
        return None, [f'Timetable optimization did not complete: {result.message}']

    return [
        candidate
        for index, candidate in enumerate(candidates)
        if result.x[index] > 0.5
    ], []


def build_schedule(plan_adjustments=None):
    days = [day for day, _ in TimetableSlot.DAYS_OF_WEEK]
    periods = list(Period.objects.order_by('number'))
    lunch_after_period = _lunch_after_period(periods)
    last_period_ids = {period.id for period in periods[-2:]}
    sections = list(Section.objects.order_by('name'))
    assignments = list(
        SectionSubject.objects.select_related('section', 'subject').order_by(
            'section__name',
            'subject__name',
        )
    )
    mappings = list(TeacherSubject.objects.select_related('teacher', 'subject'))
    constraints = list(
        TimetableConstraint.objects.select_related('section', 'subject', 'teacher', 'period')
    )
    combined_groups = list(
        CombinedTeachingGroup.objects.select_related('teacher', 'subject').prefetch_related(
            'sections',
        )
    )
    unavailable = set(
        TeacherAvailability.objects.filter(is_available=False).values_list(
            'teacher_id',
            'day',
            'period_id',
        )
    )

    errors = []
    if not sections:
        errors.append('Add at least one section before generating a timetable.')
    if not periods:
        errors.append('Configure periods before generating a timetable.')
    if not assignments:
        errors.append('Assign weekly subjects and period counts to at least one section.')
    if (
        lunch_after_period is None
        and any(
            assignment.subject.category == Subject.ACTIVITY
            and assignment.subject.name.strip().casefold() == 'yoga'
            for assignment in assignments
        )
    ):
        errors.append(
            'Configure a lunch break or a 45-minute lunch gap before scheduling Yoga.'
        )
    if errors:
        return None, errors

    assignment_by_key = {
        (assignment.section_id, assignment.subject_id): assignment
        for assignment in assignments
    }
    global_teachers_for_subject = defaultdict(set)
    teachers_for_assignment = defaultdict(set)
    for mapping in mappings:
        if mapping.section_id is None:
            global_teachers_for_subject[mapping.subject_id].add(mapping.teacher_id)
        else:
            teachers_for_assignment[
                (mapping.section_id, mapping.subject_id)
            ].add(mapping.teacher_id)
    for assignment in assignments:
        key = (assignment.section_id, assignment.subject_id)
        teachers_for_assignment[key].update(
            global_teachers_for_subject[assignment.subject_id]
        )

    fixed = {}
    fixed_teacher_shared_groups = {}
    fixed_counts = defaultdict(int)
    fixed_days = defaultdict(set)
    for constraint in constraints:
        key = (constraint.section_id, constraint.day, constraint.period_id)
        assignment_key = (constraint.section_id, constraint.subject_id)
        if assignment_key not in assignment_by_key:
            errors.append(
                f"{constraint.section.name}: assign {constraint.subject.name} before fixing a period."
            )
            continue
        if constraint.teacher_id not in teachers_for_assignment[assignment_key]:
            errors.append(f"{constraint.teacher.name} is not mapped to {constraint.subject.name}.")
            continue
        if constraint.subject.category == Subject.ACTIVITY:
            if constraint.subject.name.strip().casefold() == 'yoga':
                if (
                    lunch_after_period is not None
                    and constraint.period.number > lunch_after_period.number
                ):
                    errors.append(
                        f"{constraint.section.name}'s fixed Yoga class must be before lunch."
                    )
                    continue
            elif constraint.period.id not in last_period_ids:
                errors.append(
                    f"{constraint.section.name}'s fixed {constraint.subject.name} class "
                    'must be in one of the last two periods.'
                )
                continue
        if (constraint.teacher_id, constraint.day, constraint.period_id) in unavailable:
            errors.append(
                f"{constraint.teacher.name} is marked unavailable on {constraint.day}, "
                f"period {constraint.period.number}."
            )
            continue
        if key in fixed:
            errors.append(
                f"{constraint.section.name} has more than one fixed class on "
                f"{constraint.day}, period {constraint.period.number}."
            )
            continue

        teacher_slot = (constraint.teacher_id, constraint.day, constraint.period_id)
        if teacher_slot in fixed_teacher_shared_groups:
            if (
                constraint.shared_group_id is None
                or fixed_teacher_shared_groups[teacher_slot] != constraint.shared_group_id
            ):
                errors.append(
                    f"{constraint.teacher.name} is fixed to more than one section on "
                    f"{constraint.day}, period {constraint.period.number}."
                )
                continue
        else:
            fixed_teacher_shared_groups[teacher_slot] = constraint.shared_group_id

        fixed[key] = constraint
        fixed_counts[assignment_key] += 1
        fixed_days[assignment_key].add(constraint.day)

    combined_assignment_keys = set()
    combined_section_subjects = set()
    combined_yoga_periods = {}
    period_four_exists = any(period.number == 4 for period in periods)
    for group in combined_groups:
        group_section_ids = set(group.sections.values_list('id', flat=True))
        is_yoga = (
            group.subject.category == Subject.ACTIVITY
            and group.subject.name.strip().casefold() == 'yoga'
        )
        if is_yoga:
            if not period_four_exists:
                errors.append('Configure period 4 before scheduling shared Yoga.')
            elif lunch_after_period and lunch_after_period.number < 4:
                errors.append(
                    'Configure period 4 before lunch to schedule shared Yoga on Monday.'
                )
            if group.periods_per_week != 1:
                errors.append('Shared Yoga must be configured for 1 period per week.')
        if len(group_section_ids) < 2:
            errors.append(
                f'{group.subject.name} combined group needs at least two classes.'
            )
            continue
        if not 0 < group.periods_per_week <= len(days) * len(periods):
            errors.append(
                f'{group.subject.name} combined group has an invalid weekly period count.'
            )
        for section_id in group_section_ids:
            assignment_key = (section_id, group.subject_id)
            if assignment_key in combined_section_subjects:
                errors.append(
                    f'{group.subject.name} combined class groups cannot overlap.'
                )
            combined_section_subjects.add(assignment_key)
            if assignment_key not in assignment_by_key:
                errors.append(
                    f'{group.subject.name} must be in every class weekly plan before '
                    'classes can be combined.'
                )
                continue
            combined_assignment_keys.add(assignment_key)
            if (
                group.subject.category == Subject.ACTIVITY
                and group.subject.name.strip().casefold() == 'yoga'
            ):
                combined_yoga_periods[assignment_key] = group.periods_per_week
            if group.teacher_id not in teachers_for_assignment[assignment_key]:
                errors.append(
                    f'{group.teacher.name} must be mapped to {group.subject.name} in '
                    f'{assignment_by_key[assignment_key].section.name}.'
                )
            if any(
                constraint.section_id == section_id
                and constraint.subject_id == group.subject_id
                for constraint in constraints
            ):
                errors.append(
                    f'Remove fixed {group.subject.name} classes from the combined '
                    'classes before generating.'
                )

    for assignment in assignments:
        if not teachers_for_assignment[
            (assignment.section_id, assignment.subject_id)
        ] and not fixed_counts[
            (assignment.section_id, assignment.subject_id)
        ]:
            errors.append(
                f"Map at least one teacher to {assignment.subject.name} for "
                f"class {assignment.section.name}, or remove it from the weekly "
                "plan if it is not taught in this class."
            )
    if errors:
        return None, errors

    capacity = len(days) * len(periods)
    for assignment in assignments:
        if assignment.periods_per_week > capacity:
            errors.append(
                f"{assignment.section.name} requires more periods of "
                f"{assignment.subject.name} than the {capacity} available weekly slots."
            )
    if errors:
        return None, errors

    targets = {}
    plan_changes = {}
    for section in sections:
        section_assignments = [
            assignment for assignment in assignments
            if assignment.section_id == section.id
        ]
        counts = {}
        for assignment in section_assignments:
            key = (section.id, assignment.subject_id)
            fixed_count = fixed_counts[key]
            if assignment.subject.category == Subject.BASIC:
                count = max(
                    assignment.periods_per_week,
                    len(days) + fixed_count - len(fixed_days[key]),
                    fixed_count,
                )
            elif key in combined_yoga_periods:
                count = max(combined_yoga_periods[key], fixed_count)
            else:
                count = max(2, fixed_count)
                if fixed_count > len(fixed_days[key]):
                    errors.append(
                        f"{section.name} has multiple fixed {assignment.subject.name} "
                        "classes on the same weekday."
                    )
                if len(fixed_days[key]) > count:
                    errors.append(
                        f"{section.name} has more fixed {assignment.subject.name} days "
                        "than its weekly activity requirement."
                    )
            counts[key] = count

        excess = sum(counts.values()) - capacity
        for assignment in sorted(
            (
                item for item in section_assignments
                if item.subject.category == Subject.BASIC
            ),
            key=lambda item: (-counts[(section.id, item.subject_id)], item.subject.name),
        ):
            if excess <= 0:
                break
            key = (section.id, assignment.subject_id)
            reducible = counts[key] - max(
                len(days),
                fixed_counts[key],
            )
            reduction = min(reducible, excess)
            counts[key] -= reduction
            excess -= reduction
        if excess > 0:
            errors.append(
                f"{section.name} needs more than {capacity} weekly periods for its "
                "basic-subject and activity requirements."
            )
            continue

        remaining = capacity - sum(counts.values())
        basic_assignments = [
            assignment for assignment in section_assignments
            if assignment.subject.category == Subject.BASIC
        ]
        if remaining and not basic_assignments:
            errors.append(f"{section.name} has periods left but no Basic subject to fill them.")
            continue
        for _ in range(remaining):
            assignment = min(
                basic_assignments,
                key=lambda item: (
                    counts[(section.id, item.subject_id)],
                    item.subject.name,
                ),
            )
            counts[(section.id, assignment.subject_id)] += 1

        for assignment in section_assignments:
            key = (section.id, assignment.subject_id)
            targets[key] = counts[key]
            if counts[key] != assignment.periods_per_week:
                plan_changes[assignment.id] = counts[key]

    if errors:
        return None, errors

    teacher_required_load = defaultdict(int)
    teacher_required_subjects = defaultdict(set)
    for teacher_id, _, _ in {
        (constraint.teacher_id, constraint.day, constraint.period_id)
        for constraint in constraints
    }:
        teacher_required_load[teacher_id] += 1
    for assignment in assignments:
        subject_teachers = teachers_for_assignment[
            (assignment.section_id, assignment.subject_id)
        ]
        if (assignment.section_id, assignment.subject_id) in combined_assignment_keys:
            continue
        if len(subject_teachers) != 1:
            continue
        teacher_id = next(iter(subject_teachers))
        key = (assignment.section_id, assignment.subject_id)
        remaining_count = targets[key] - fixed_counts[key]
        teacher_required_load[teacher_id] += remaining_count
        if remaining_count:
            teacher_required_subjects[teacher_id].add(assignment.subject.name)
    for group in combined_groups:
        teacher_required_load[group.teacher_id] += group.periods_per_week
        teacher_required_subjects[group.teacher_id].add(group.subject.name)
    for teacher_id, required_load in teacher_required_load.items():
        teacher_capacity = capacity - sum(
            unavailable_teacher_id == teacher_id
            for unavailable_teacher_id, _, _ in unavailable
        )
        if required_load <= teacher_capacity:
            continue
        teacher = next(
            mapping.teacher
            for mapping in mappings
            if mapping.teacher_id == teacher_id
        )
        subject_names = sorted(teacher_required_subjects[teacher_id])
        if not subject_names:
            subject_names = sorted({
                constraint.subject.name
                for constraint in constraints
                if constraint.teacher_id == teacher_id
            })
        errors.append(
            f"{teacher.name} is required to teach {', '.join(subject_names)} for at least "
            f"{required_load} periods, but only {teacher_capacity} periods are available. "
            f"Map another teacher to {', '.join(subject_names)}, or adjust the subject assignments."
        )
    if errors:
        return None, errors

    for group in combined_groups:
        for section_id in group.sections.values_list('id', flat=True):
            assignment_key = (section_id, group.subject_id)
            if targets[assignment_key] < group.periods_per_week:
                errors.append(
                    f'{assignment_by_key[assignment_key].section.name} needs at least '
                    f'{group.periods_per_week} weekly periods of {group.subject.name} '
                    'for the combined class.'
                )
    if errors:
        return None, errors

    reserved_teachers = {
        (constraint.day, constraint.period_id, constraint.teacher_id)
        for constraint in constraints
    }
    candidates = []
    for section in sections:
        for day in days:
            for period in periods:
                fixed_class = fixed.get((section.id, day, period.id))
                for assignment in assignments:
                    if assignment.section_id != section.id:
                        continue
                    if assignment.subject.category == Subject.ACTIVITY:
                        if assignment.subject.name.strip().casefold() == 'yoga':
                            if (
                                lunch_after_period is None
                                or period.number > lunch_after_period.number
                            ):
                                continue
                        elif period.id not in last_period_ids:
                            continue
                    if fixed_class and assignment.subject_id != fixed_class.subject_id:
                        continue
                    teacher_ids = (
                        {fixed_class.teacher_id}
                        if fixed_class
                        else teachers_for_assignment[
                            (assignment.section_id, assignment.subject_id)
                        ]
                    )
                    for teacher_id in teacher_ids:
                        if (teacher_id, day, period.id) in unavailable:
                            continue
                        if not fixed_class and (
                            day,
                            period.id,
                            teacher_id,
                        ) in reserved_teachers:
                            continue
                        candidates.append((
                            section.id,
                            day,
                            period.id,
                            assignment.subject_id,
                            teacher_id,
                        ))

    if plan_adjustments is not None:
        plan_adjustments.update(plan_changes)
    schedule, solver_errors = _solve_with_milp(
        candidates,
        sections,
        assignments,
        periods,
        days,
        targets,
        fixed,
        mappings,
        combined_groups,
    )
    if solver_errors:
        if plan_adjustments is not None:
            plan_adjustments.clear()
        return None, solver_errors

    return [
        (
            section_id,
            subject_id,
            teacher_id,
            day,
            period_id,
        )
        for section_id, day, period_id, subject_id, teacher_id in schedule
    ], []
