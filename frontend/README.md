# School Timetable Planner

The React/Vite frontend uses the Django REST API and the configured MySQL database.

## Run locally

From `D:\timetable\timetable_project`, apply database migrations and start Django:

```powershell
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
```

In another terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

The API defaults to `http://127.0.0.1:8000/api/`. Set `VITE_API_BASE_URL` when the API runs at a different address.

The initial migration creates eight 45-minute periods, Monday through Friday. Update period start/end times or add/remove periods from the **Periods** page.

## Scheduling workflow

1. Add sections, subjects, and teachers.
2. Map each teacher to the subjects they can teach.
3. Assign subjects and minimum weekly period requirements to each section. The generator fills remaining periods using those assigned subjects.
4. Configure teacher availability and any fixed classes.
5. Generate a timetable, or add/edit classes manually from the timetable page.

The generator fills every configured period for every section, meeting each subject's minimum weekly requirement first and using the section's assigned subjects for any additional periods. It prevents section/teacher collisions, respects teacher availability and fixed classes, and keeps the existing schedule when it cannot produce a complete replacement.

The **Timetable** view shows a print-friendly weekly matrix for each section: weekdays are rows, class periods are columns, and 15-minute breaks/45-minute lunch gaps appear as separate columns. Use the optional section and teacher filters. **Download PDF** exports the same layout in landscape, with a separate page for each section.

The school planner uses its own section, subject, teacher, and period tables. The migration is additive and does not delete the previous college timetable tables.

For a complete step-by-step user guide, generation rules, troubleshooting, and current feature limitations, see [TIMETABLE-FLOW-GUIDE.md](../TIMETABLE-FLOW-GUIDE.md).
