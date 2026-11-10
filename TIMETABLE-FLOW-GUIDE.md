# College Timetable Planner: Workflow Guide



## 1. What the application does

The planner builds a Monday-to-Friday timetable for each section from:

- The configured school periods.
- Subjects assigned to each section and their weekly minimum periods.
- Teacher-to-subject mappings.
- Teacher availability.
- Fixed classes that must remain in a specific slot.

The generated timetable fills every configured weekday period for every section. It keeps fixed classes, meets the minimum subject requirements, avoids assigning a teacher to two sections at once, and avoids periods marked unavailable.

## 2. Important planning terms

- **Section**: A class group that gets its own timetable, such as `1A` or `Year 1 - Section A`.
- **Subject**: A class that can be assigned to a section, such as Mathematics or Biology.
- **Weekly teaching plan**: The subjects a section studies and each subject's minimum number of periods per week.
- **Teacher mapping**: The subjects a teacher is qualified/available to teach.
- **Teacher availability**: Periods when a teacher must not be assigned.
- **Fixed class**: A required section, subject, teacher, day, and period combination.
- **Period**: One school-day slot with a configured start and end time.

## 3. Recommended setup order

Complete setup in this order before generating a timetable.

### Step 1 — Configure the school week

Open **Periods** and confirm:

1. The number of teaching periods per day for the active timetable. Five periods per day gives 25 weekly class slots; seven gives 35; eight gives 40; nine gives 45.
2. The start and end time for every period.
3. That period times do not overlap.

Enter and review period times in 12-hour format with an AM/PM suffix (for example, `8:00 AM` or `1:15 PM`). The planner stores these times in standard 24-hour format internally.

The planner uses Monday through Friday. Weekly section capacity is:

`number of configured teaching periods × 5 days`

Breaks and lunch are not teaching periods and do not count toward weekly capacity. After adding periods, configure a 15-minute short break and a 45-minute lunch in **Daily break and lunch** on the same page. Period times remain manual; each configured break must exactly match the gap between adjacent periods. If no matching gap is available, adjust period times first.

When changing the number of periods, the application preserves saved subject requirements. On the **Generate timetable** page, use **Recalculate weekly plans** if existing requirements exceed the new weekly capacity. This evenly redistributes each section's subjects across its current teaching periods and respects fixed-class counts.

### Step 2 — Create sections, subjects, and teachers

Use the **Sections**, **Subjects**, and **Teachers** pages to create the records the school needs. Keep names consistent and easy to recognize in timetable and staff views.

On the **Subjects** page, mark each subject as **Basic** or **Activity**:

- Every Basic subject in a section's weekly plan is scheduled at least once each weekday. A fixed Basic class counts for its fixed day, and the subject is still scheduled on the other weekdays.
- Activity subjects are scheduled once or twice per week on different weekdays (the automatic plan targets two); fixed activity classes count toward that target and remain pinned to their fixed slots.
- The current sample catalog contains Basic: Tamil, English, Science, Social Studies, Hindi, Mathematics, and EVS; Activity: Drawing, Games, Music, Yoga, and Mantras and Shlokas.
- Seven Basic subjects plus five weekly Activity subjects require 45 weekly slots per section. Configure at least nine periods per day for this complete plan; seven periods per day cannot fit these requirements.

### Step 3 — Map teachers to subjects

Open **Teacher mapping** and add every teacher-subject pairing that may be scheduled.

- A subject needs at least one mapped teacher.
- If more than one teacher can teach a subject, map all of them. This gives the generator alternatives when teachers are busy or unavailable.
- A teacher should not be mapped to a subject they cannot teach.

### Step 4 — Create the weekly teaching plan for each section

Open **Section subjects** (the Weekly teaching plan).

For each section:

1. Choose one section from the dropdown.
2. Select all subjects that section should study.
3. Review the **Auto-calculated weekly minimums** preview.
4. Select **Save weekly plan**.

The application first gives each Basic subject at least 5 periods per week and each Activity subject at least 2 periods per week. It then distributes any remaining periods across the Basic subjects only. For example, with 35 periods, two Basic subjects, and one Activity, the preview assigns 17, 16, and 2 periods respectively.

Rules to know:

- The allocations always add up to the section's capacity.
- Basic subjects receive at least one period each weekday (five per week); Activity subjects receive two periods per week by default.
- A fixed Basic class counts toward coverage on its pinned day, and the generator schedules that Basic subject on the remaining weekdays too. A fixed Activity class counts toward the two-day activity target and remains only in its pinned slot(s).
- If all selected subjects are Activities, the plan cannot fill the remaining timetable periods; add at least one Basic subject.
- If category minimums exceed the section's weekly capacity, the preview reports that the plan cannot fit instead of assigning misleading period counts.
- Subjects with fixed classes are preselected while editing the plan. They cannot be removed until those fixed classes are deleted.
- Saving a plan replaces that section's selected subject list and allocations as one operation.
- Every subject in the plan must have at least one teacher mapping before generation.

### Step 5 — Enter teacher availability

Open **Staff schedule** and select a teacher.

- The grid shows weekdays and periods.
- Green **Available** cells are available by default. Click a cell to mark it unavailable.
- Red **Unavailable** cells are excluded by the generator. Click them to mark them available again.
- Indigo cells display generated teaching assignments.
- Do not mark a fixed-class period unavailable. The application rejects this conflict.

Only periods explicitly marked unavailable are restricted; unmarked periods are treated as available.

### Step 6 — Add fixed timetable classes (optional)

Open **Fixed classes**.

1. Select one section for an ordinary fixed class, or select multiple sections to create one combined lesson shared by those sections.
2. Select a subject assigned to every selected section in the weekly teaching plans.
3. Select a teacher mapped to that subject.
4. Select a day and period.
5. Save the fixed class. For multiple sections, the same teacher teaches the shared lesson to all selected sections in that one slot.

The form shows how many weekly periods for that subject are already fixed. A fixed class:

- Must use a subject assigned to the selected section.
- Must use a teacher mapped to the subject.
- Must not overlap another fixed class for the section. A teacher cannot be fixed to another lesson at the same time; the only allowed simultaneous section entries are the participants in that same combined class.
- A combined class occupies one slot in each selected section, but the shared teacher is considered to be teaching one lesson in one slot—not several simultaneous classes.
- A subject used in a combined fixed class is pinned only in that combined slot for each participating section.
- Must not be at a time when the teacher is unavailable.
- For an Activity, locks that occurrence to its explicitly fixed slot(s); the generator does not move it. For a Basic subject, the fixed lesson counts toward its daily coverage on that day and the generator schedules it on the other weekdays as well.
- Fixed slots still count toward the section's weekly capacity.

Remove or update a fixed class before removing its subject from the weekly plan, changing its teacher mapping, or making its teacher unavailable at that time.

### Step 7 — Review readiness and generate

Open **Generate** and review **Before generating**. Resolve any incomplete items, especially:

- Every section has a weekly plan.
- Each section's minimums fit within its available weekly slots.
- Every assigned subject has at least one mapped teacher.
- Periods are configured.

Wait for the full readiness check. Generation is enabled only when the current period count, weekly plans, teacher mappings, availability, and fixed classes can produce a complete schedule. If the generator finds an impossible requirement, it returns an error list and does not replace the previously saved schedule.

### Step 9 — Review and share the timetable

Open **Timetable**:

- Filter by section, teacher, or both.
- Review the weekly matrix with weekdays as rows and teaching periods as columns. Each class shows its subject and teacher.
- Review 15-minute break and 45-minute lunch columns between teaching periods. Explicitly configured breaks appear in the view; exact 15- or 45-minute gaps are also recognized as breaks/lunch automatically.
- Download the displayed timetable as a PDF for sharing or printing.
- Use the timetable editor to add or edit an individual class when a manual adjustment is needed.
- A class pinned by a fixed-class rule cannot be deleted or moved away from its fixed slot.

## 4. How automatic generation works

At a high level, the planner:

1. Loads weekly plans, teacher mappings, availability, and fixed classes.
2. Checks for missing plans, unmapped subjects, invalid fixed classes, weekly capacity issues, and teacher workload/capacity conflicts.
3. Reserves all fixed classes.
4. Schedules each **Basic** subject at least once on every weekday. Basic subject assignments are raised to at least five weekly periods; higher counts may be reduced to fit weekly capacity.
5. Schedules each **Activity** subject twice per week on different weekdays. Fixed activity slots count toward those two periods, and remaining occurrences are placed on other weekdays. More than two fixed occurrences are retained and reported in the weekly-plan count.
6. Keeps Basic subjects in their fixed slots and schedules them on the other weekdays to preserve daily coverage.
7. Shows proposed weekly-plan count changes in readiness and saves those changes only after timetable generation succeeds.
8. Fills remaining section periods from Basic subjects.
9. Places Activity requirements within each day's remaining capacity after fixed classes and Basic-subject coverage, and balances additional Basic lessons across the week.
10. Assigns an available mapped teacher to each lesson while preventing the same teacher from teaching two separate classes in the same period.
11. Replaces the saved schedule only after a complete schedule has been built successfully.

Daily coverage requires at least one available period per weekday for every Basic subject, in addition to the two weekly periods for each Activity subject. If the configured period count or fixed classes make those requirements impossible, readiness reports the section and the capacity needed. With seven Basic subjects and at least one weekly Activity, a seven-period day is not enough on an Activity day; configure an additional period or reduce the daily Basic subjects.

The placement strategy is a heuristic. It tries to produce a complete, conflict-free timetable; it is not a proof that no possible timetable exists when the configured constraints prevent a solution. If generation reports a conflict, review teacher mappings, availability, weekly minimums, and fixed classes.

## 5. Common generation errors and what to do

| Error or symptom | What it means | Recommended action |
|---|---|---|
| A section requires more weekly subject periods than available | The sum of that section's minimums exceeds its weekly capacity | Edit the section's plan and reduce the subject load or configure the correct school periods |
| A teacher is required for more periods than available | The teacher is the only mapped option for too many lessons, or has too many unavailable periods | Map another qualified teacher, reduce the subject load, or review availability |
| No teacher is mapped to a subject | A planned subject has no eligible teacher | Add a teacher-subject mapping |
| No available mapped teacher for a class | All mapped teachers are unavailable or assigned elsewhere at that slot | Add another eligible teacher or change availability/fixed classes |
| A fixed class is not in the weekly plan | A fixed class references a subject the section is not assigned | Add the subject to the section's weekly plan or remove the fixed class |
| Fixed class count exceeds a subject's weekly minimum | More classes are pinned than the plan permits | Increase that subject's minimum in the weekly plan |
| One teacher is fixed to multiple sections at the same time | Fixed classes require a teacher to be in two places simultaneously | Change one of the fixed teachers or periods |

## 6. Manager summary

> The system creates a complete weekly timetable for every section using the school's periods, each section's subject plan, qualified teacher mappings, staff availability, and required fixed classes. It checks for capacity and assignment conflicts before saving. Managers can review the result by section or teacher and export a PDF. If setup rules cannot be satisfied, generation reports the issue and preserves the previous timetable.

## 7. Current scope and limitations

The automatic planner currently schedules sections, subjects, teachers, weekdays, periods, availability, and fixed classes. The separate legacy **Courses**, **Rooms**, **Instructors**, and **Timetable** API records are not inputs to automatic timetable generation.

The planner does not currently model:

- Room assignment, room capacity, or room/equipment suitability.
- Course credits, semesters, academic terms, or multiple campuses.
- Student-level elective groups or students enrolled across sections.
- School holidays or different bell schedules for different weekdays.
- Teacher daily maximums, consecutive-period limits, preferred times, or workload targets.
- Subject-specific daily maximums or guaranteed maximum gaps between a student's classes.
- An optimization guarantee or alternative-schedule comparison.

These are possible future enhancements, but should not be presented as current functionality.

## 8. API reference

The API base path is `/api/`.

| Endpoint | Purpose |
|---|---|
| `GET/POST /api/sections/` | List or create sections |
| `GET/POST /api/subjects/` | List or create subjects |
| `GET/POST /api/teachers/` | List or create teachers |
| `GET/POST /api/periods/` | List or create school periods |
| `GET/POST /api/timetable-breaks/` | Configure non-teaching break/lunch placements in exact period gaps |
| `GET/POST /api/teacher-subjects/` | Manage teacher-subject mappings |
| `GET/POST /api/teacher-availability/` | Manage teacher availability |
| `GET/POST /api/section-subjects/` | List or manage weekly subject requirements |
| `POST /api/section-subjects/configure-section/` | Save a section's multi-subject plan and auto-distribute periods |
| `POST /api/section-subjects/recalculate-all/` | Recalculate all section plans for the active period capacity |
| `GET/POST /api/constraints/` | List or add fixed timetable classes |
| `GET /api/schedule/` | List saved classes; accepts optional `section` and `teacher` filters |
| `GET /api/schedule/readiness/` | Check whether the active setup can generate a complete schedule |
| `POST /api/schedule/generate/` | Generate and save a complete timetable |

## 9. Running and verifying locally

From `D:\timetable\timetable_project`:

```powershell
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
```

In another terminal:

```powershell
cd frontend
npm run dev
```

To run the backend test suite:

```powershell
..\venv\Scripts\python.exe manage.py test api
```

The frontend can be checked with:

```powershell
cd frontend
npm run build
npm run lint
```

Do not clear or reseed a shared/production database to test generation. Use a dedicated test database or the automated test suite.
