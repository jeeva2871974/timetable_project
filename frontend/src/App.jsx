import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  AlertTriangle, BookOpen, CalendarDays, Check, Clock3, Download, GraduationCap,
  LayoutDashboard, Link2, Pencil, Plus, RefreshCw, Settings2,
  Trash2, Users, WandSparkles, X,
} from 'lucide-react';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api/',
});
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const PERIOD_COLORS = [
  { header: 'bg-sky-100 text-sky-900', cell: 'bg-sky-50', card: 'border-sky-500 bg-sky-100/80', teacher: 'text-sky-800', empty: 'text-sky-300', pdf: [224, 242, 254], pdfHeader: [125, 211, 252] },
  { header: 'bg-emerald-100 text-emerald-900', cell: 'bg-emerald-50', card: 'border-emerald-500 bg-emerald-100/80', teacher: 'text-emerald-800', empty: 'text-emerald-300', pdf: [209, 250, 229], pdfHeader: [110, 231, 183] },
  { header: 'bg-amber-100 text-amber-900', cell: 'bg-amber-50', card: 'border-amber-500 bg-amber-100/80', teacher: 'text-amber-800', empty: 'text-amber-300', pdf: [254, 243, 199], pdfHeader: [252, 211, 77] },
  { header: 'bg-rose-100 text-rose-900', cell: 'bg-rose-50', card: 'border-rose-500 bg-rose-100/80', teacher: 'text-rose-800', empty: 'text-rose-300', pdf: [255, 228, 230], pdfHeader: [253, 164, 175] },
  { header: 'bg-violet-100 text-violet-900', cell: 'bg-violet-50', card: 'border-violet-500 bg-violet-100/80', teacher: 'text-violet-800', empty: 'text-violet-300', pdf: [237, 233, 254], pdfHeader: [196, 181, 253] },
  { header: 'bg-cyan-100 text-cyan-900', cell: 'bg-cyan-50', card: 'border-cyan-500 bg-cyan-100/80', teacher: 'text-cyan-800', empty: 'text-cyan-300', pdf: [207, 250, 254], pdfHeader: [103, 232, 249] },
  { header: 'bg-lime-100 text-lime-900', cell: 'bg-lime-50', card: 'border-lime-500 bg-lime-100/80', teacher: 'text-lime-800', empty: 'text-lime-300', pdf: [236, 252, 203], pdfHeader: [190, 242, 100] },
  { header: 'bg-orange-100 text-orange-900', cell: 'bg-orange-50', card: 'border-orange-500 bg-orange-100/80', teacher: 'text-orange-800', empty: 'text-orange-300', pdf: [255, 237, 213], pdfHeader: [253, 186, 116] },
];
const SUBJECT_COLORS = [
  { card: 'border-indigo-500 bg-indigo-100', name: 'text-indigo-950', teacher: 'text-indigo-800', marker: 'bg-indigo-500', pdf: [224, 231, 255] },
  { card: 'border-teal-500 bg-teal-100', name: 'text-teal-950', teacher: 'text-teal-800', marker: 'bg-teal-500', pdf: [204, 251, 241] },
  { card: 'border-orange-500 bg-orange-100', name: 'text-orange-950', teacher: 'text-orange-800', marker: 'bg-orange-500', pdf: [255, 237, 213] },
  { card: 'border-fuchsia-500 bg-fuchsia-100', name: 'text-fuchsia-950', teacher: 'text-fuchsia-800', marker: 'bg-fuchsia-500', pdf: [250, 232, 255] },
  { card: 'border-lime-500 bg-lime-100', name: 'text-lime-950', teacher: 'text-lime-800', marker: 'bg-lime-500', pdf: [236, 252, 203] },
  { card: 'border-sky-500 bg-sky-100', name: 'text-sky-950', teacher: 'text-sky-800', marker: 'bg-sky-500', pdf: [224, 242, 254] },
  { card: 'border-rose-500 bg-rose-100', name: 'text-rose-950', teacher: 'text-rose-800', marker: 'bg-rose-500', pdf: [255, 228, 230] },
  { card: 'border-yellow-500 bg-yellow-100', name: 'text-yellow-950', teacher: 'text-yellow-800', marker: 'bg-yellow-500', pdf: [254, 249, 195] },
];
const ROUTES = [
  { id: 'timetable', label: 'Timetable', icon: CalendarDays },
  { id: 'teacher-timetable', label: 'Teacher timetable', icon: Users },
  { id: 'sections', label: 'Sections', icon: GraduationCap },
  { id: 'subjects', label: 'Subjects', icon: BookOpen },
  { id: 'teachers', label: 'Teachers', icon: Users },
  { id: 'mappings', label: 'Teacher mapping', icon: Link2 },
  { id: 'assignments', label: 'Section subjects', icon: LayoutDashboard },
  { id: 'periods', label: 'Periods', icon: Clock3 },
  { id: 'availability', label: 'Staff schedule', icon: Check },
  { id: 'constraints', label: 'Fixed classes', icon: Settings2 },
  { id: 'generate', label: 'Generate', icon: WandSparkles },
];
const EMPTY_DATA = {
  sections: [], subjects: [], teachers: [], periods: [], assignments: [],
  mappings: [], combinedGroups: [], availability: [], constraints: [], breaks: [], schedule: [],
};
const inputClass = 'mt-1 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100';
const buttonClass = 'inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50';
const secondaryButtonClass = 'inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700';

function getErrorMessage(error) {
  const response = error.response?.data;
  if (Array.isArray(response?.errors)) return response.errors.join(' ');
  if (typeof response === 'string') return response;
  if (response && typeof response === 'object') {
    const messages = [];
    const collectMessages = (value) => {
      if (typeof value === 'string') messages.push(value);
      else if (Array.isArray(value)) value.forEach(collectMessages);
      else if (value && typeof value === 'object') Object.values(value).forEach(collectMessages);
    };
    collectMessages(response);
    if (messages.length) return [...new Set(messages)].join(' ');
  }
  return error.message || 'Something went wrong. Please try again.';
}

function formatTime12Hour(time) {
  const match = /^(\d{1,2}):(\d{2})/.exec(time);
  if (!match) return time;

  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour > 23 || minute > 59) return time;
  const suffix = hour < 12 ? 'AM' : 'PM';
  return `${hour % 12 || 12}:${String(minute).padStart(2, '0')} ${suffix}`;
}

function formatTimeRange(startTime, endTime) {
  const start = formatTime12Hour(startTime);
  const end = formatTime12Hour(endTime);
  const startSuffix = start.slice(-2);
  const endSuffix = end.slice(-2);
  return startSuffix === endSuffix
    ? `${start.slice(0, -3)}–${end}`
    : `${start}–${end}`;
}

function addMinutesToTime(time, minutes) {
  const [hours, mins] = time.split(':').map(Number);
  const totalMinutes = hours * 60 + mins + minutes;
  if (totalMinutes < 0 || totalMinutes >= 24 * 60) return null;
  return `${String(Math.floor(totalMinutes / 60)).padStart(2, '0')}:${String(totalMinutes % 60).padStart(2, '0')}`;
}

function getTimeDifferenceMinutes(startTime, endTime) {
  const [startHour, startMinute] = startTime.split(':').map(Number);
  const [endHour, endMinute] = endTime.split(':').map(Number);
  return endHour * 60 + endMinute - (startHour * 60 + startMinute);
}

function getBreakPlacementOptions(periods, durationMinutes) {
  const orderedPeriods = [...periods].sort((left, right) => left.number - right.number);
  return orderedPeriods.slice(0, -1).flatMap((period, index) => {
    const nextPeriod = orderedPeriods[index + 1];
    if (getTimeDifferenceMinutes(period.end_time, nextPeriod.start_time) !== durationMinutes) {
      return [];
    }
    return [{
      value: period.id,
      label: `After Period ${period.number} · ${formatTime12Hour(period.end_time)}–${formatTime12Hour(nextPeriod.start_time)}`,
    }];
  });
}

function toRomanNumeral(number) {
  const numerals = [
    [10, 'X'],
    [9, 'IX'],
    [5, 'V'],
    [4, 'IV'],
    [1, 'I'],
  ];
  let remaining = number;
  let result = '';
  numerals.forEach(([value, numeral]) => {
    while (remaining >= value) {
      result += numeral;
      remaining -= value;
    }
  });
  return result || String(number);
}

function getTimetableColumns(periods, breaks) {
  const orderedPeriods = [...periods].sort((left, right) => left.number - right.number);
  return orderedPeriods.flatMap((period, index) => {
    const savedBreak = breaks.find(
      (item) => String(item.after_period) === String(period.id),
    );
    const nextPeriod = orderedPeriods[index + 1];
    const gapMinutes = nextPeriod
      ? getTimeDifferenceMinutes(period.end_time, nextPeriod.start_time)
      : 0;
    const inferredBreak = !savedBreak && (gapMinutes === 15 || gapMinutes === 45)
      ? {
        id: `gap-${period.id}`,
        kind: gapMinutes === 45 ? 'lunch' : 'break',
        after_period: period.id,
        duration_minutes: gapMinutes,
        start_time: period.end_time,
        end_time: nextPeriod.start_time,
      }
      : null;
    const timetableBreak = savedBreak || inferredBreak;
    return [
      { type: 'period', period },
      ...(timetableBreak ? [{ type: 'break', timetableBreak }] : []),
    ];
  });
}

function suggestPeriodTimes(periods, periodNumber) {
  const orderedPeriods = [...periods].sort((left, right) => left.number - right.number);
  const previous = orderedPeriods.find((period) => period.number === periodNumber - 1);
  const next = orderedPeriods.find((period) => period.number === periodNumber + 1);

  if (previous && next && previous.end_time < next.start_time) {
    return {
      start_time: previous.end_time.slice(0, 5),
      end_time: next.start_time.slice(0, 5),
    };
  }
  if (previous) {
    const start_time = previous.end_time.slice(0, 5);
    const end_time = addMinutesToTime(start_time, 45);
    if (end_time && (!next || end_time <= next.start_time.slice(0, 5))) {
      return { start_time, end_time };
    }
  }
  if (next) {
    const end_time = next.start_time.slice(0, 5);
    const start_time = addMinutesToTime(end_time, -45);
    if (start_time && (!previous || start_time >= previous.end_time.slice(0, 5))) {
      return { start_time, end_time };
    }
  }
  return { start_time: '08:00', end_time: '08:45' };
}

function getNextPeriodNumber(periods) {
  const existingNumbers = new Set(periods.map((period) => period.number));
  let number = 1;
  while (existingNumbers.has(number)) number += 1;
  return number;
}

function getTimeParts(time) {
  const [hours, minutes] = time.split(':').map(Number);
  const hour24 = Number.isFinite(hours) ? hours : 8;
  return {
    hour: String(hour24 % 12 || 12),
    minute: String(Number.isFinite(minutes) ? minutes : 0).padStart(2, '0'),
    period: hour24 < 12 ? 'AM' : 'PM',
  };
}

function TimeInput12Hour({ value, onChange, label }) {
  const { hour, minute, period } = getTimeParts(value);
  const selectClass = 'min-h-10 w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200';
  const updateTime = (nextHour, nextMinute, nextPeriod) => {
    const hour24 = (Number(nextHour) % 12) + (nextPeriod === 'PM' ? 12 : 0);
    onChange(`${String(hour24).padStart(2, '0')}:${nextMinute}`);
  };

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-center gap-2">
      <select className={`${selectClass} min-w-0 flex-1`} aria-label={`${label} hour`} value={hour} onChange={(event) => updateTime(event.target.value, minute, period)}>
        {Array.from({ length: 12 }, (_, index) => String(index + 1)).map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
      <span className="sr-only">Minute</span>
      <select className={`${selectClass} min-w-0 flex-1`} aria-label={`${label} minute`} value={minute} onChange={(event) => updateTime(hour, event.target.value, period)}>
        {Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0')).map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
      <select className={`${selectClass} w-16`} aria-label={`${label} AM or PM`} value={period} onChange={(event) => updateTime(hour, minute, event.target.value)}>
        <option value="AM">AM</option>
        <option value="PM">PM</option>
      </select>
    </div>
  );
}

function calculateWeeklyDistribution(subjectIds, fixedCounts, capacity, subjectsById) {
  if (!subjectIds.length || subjectIds.length > capacity) return null;

  const allocations = {};
  const basicSubjectIds = [];
  for (const subjectId of subjectIds) {
    const category = subjectsById[String(subjectId)]?.category || 'basic';
    const minimum = category === 'activity' ? 2 : 5;
    allocations[String(subjectId)] = Math.max(
      fixedCounts[String(subjectId)] || 0,
      minimum,
    );
    if (category === 'basic') basicSubjectIds.push(String(subjectId));
  }
  const fixedTotal = Object.values(allocations).reduce((sum, count) => sum + count, 0);
  if (fixedTotal > capacity) return null;

  while (Object.values(allocations).reduce((sum, count) => sum + count, 0) < capacity) {
    if (basicSubjectIds.length === 0) return null;
    const nextSubjectId = basicSubjectIds.sort(
      (left, right) => allocations[left] - allocations[right] || Number(left) - Number(right),
    )[0];
    allocations[nextSubjectId] += 1;
  }
  return allocations;
}

function Field({ label, children, className = '' }) {
  return (
    <label className={`block text-sm font-medium text-slate-700 ${className}`}>
      {label}
      {children}
    </label>
  );
}

function Select({ value, onChange, options, placeholder, required = true }) {
  return (
    <select className={inputClass} value={value} onChange={onChange} required={required}>
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  );
}

function MultiSelectDropdown({ label, options, values, onChange, placeholder, disabled = false }) {
  const selectedLabels = options
    .filter((option) => values.includes(String(option.value)))
    .map((option) => option.label);

  return (
    <details
      className="group relative mt-1"
      onClick={(event) => {
        if (disabled) event.preventDefault();
      }}
    >
      <summary className={`${inputClass} flex list-none items-center justify-between ${disabled ? 'cursor-not-allowed bg-slate-50' : 'cursor-pointer'}`} aria-disabled={disabled}>
        <span className={selectedLabels.length ? 'text-slate-800' : 'text-slate-400'}>
          {selectedLabels.length
            ? `${selectedLabels.length} ${label.toLowerCase()} selected`
            : placeholder}
        </span>
        <span aria-hidden="true" className="text-slate-400">▾</span>
      </summary>
      <div className="absolute z-20 mt-2 max-h-60 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
        {options.length === 0 ? (
          <p className="px-3 py-2 text-sm text-slate-500">No {label} available.</p>
        ) : options.map((option) => {
          const value = String(option.value);
          const checked = values.includes(value);
          return (
            <label key={option.value} className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-indigo-50">
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={() => onChange(
                  checked ? values.filter((item) => item !== value) : [...values, value],
                )}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              {option.label}
            </label>
          );
        })}
      </div>
    </details>
  );
}

function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">{eyebrow}</p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}

function EmptyState({ children }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-10 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}

function getExportDate() {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function App() {
  const [page, setPage] = useState('timetable');
  const [data, setData] = useState(EMPTY_DATA);
  const [sectionFilter, setSectionFilter] = useState('');
  const [teacherFilter, setTeacherFilter] = useState('');
  const [teacherTimetableFilter, setTeacherTimetableFilter] = useState('');
  const [availabilityTeacher, setAvailabilityTeacher] = useState('');
  const [appliedFilters, setAppliedFilters] = useState({ section: '', teacher: '' });
  const [pageError, setPageError] = useState('');
  const [toast, setToast] = useState('');
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({});
  const [periodTimeDrafts, setPeriodTimeDrafts] = useState({});
  const [savingPeriodId, setSavingPeriodId] = useState(null);
  const [breakDrafts, setBreakDrafts] = useState({});
  const [savingBreakKind, setSavingBreakKind] = useState('');
  const [generationReadiness, setGenerationReadiness] = useState(null);
  const [recalculatingPlans, setRecalculatingPlans] = useState(false);
  const [editingMappingId, setEditingMappingId] = useState(null);
  const [editingSubjectId, setEditingSubjectId] = useState(null);
  const [editingConstraintId, setEditingConstraintId] = useState(null);
  const [editingEntry, setEditingEntry] = useState(null);
  const [entryModalOpen, setEntryModalOpen] = useState(false);
  const [entryForm, setEntryForm] = useState({});
  const [generationErrors, setGenerationErrors] = useState([]);
  const readinessKey = JSON.stringify({
    sections: data.sections.map((item) => item.id),
    subjects: data.subjects.map((item) => [item.id, item.category]),
    periods: data.periods.map((item) => [item.id, item.number, item.start_time, item.end_time]),
    assignments: data.assignments.map((item) => [item.id, item.section, item.subject, item.periods_per_week]),
    mappings: data.mappings.map((item) => [item.id, item.teacher, item.subject, item.section]),
    combinedGroups: data.combinedGroups.map((item) => [
      item.id,
      item.teacher,
      item.subject,
      item.sections,
      item.periods_per_week,
    ]),
    availability: data.availability.map((item) => [item.id, item.teacher, item.day, item.period, item.is_available]),
    constraints: data.constraints.map((item) => [item.id, item.section, item.subject, item.teacher, item.day, item.period]),
  });

  async function fetchDataSnapshot() {
    const endpoints = [
      ['sections', 'sections/'],
      ['subjects', 'subjects/'],
      ['teachers', 'teachers/'],
      ['periods', 'periods/'],
      ['assignments', 'section-subjects/'],
      ['mappings', 'teacher-subjects/'],
      ['combinedGroups', 'combined-teaching-groups/'],
      ['availability', 'teacher-availability/'],
      ['constraints', 'constraints/'],
      ['breaks', 'timetable-breaks/'],
      ['schedule', 'schedule/'],
    ];
    const responses = await Promise.all(endpoints.map(([, endpoint]) => API.get(endpoint)));
    return Object.fromEntries(
      endpoints.map(([key], index) => [key, responses[index].data]),
    );
  }

  async function refreshData() {
    try {
      setData(await fetchDataSnapshot());
      setPageError('');
    } catch (error) {
      console.error('Unable to load timetable data', error);
      setPageError(getErrorMessage(error));
    }
  }

  useEffect(() => {
    let ignore = false;
    async function loadInitialData() {
      try {
        const initialData = await fetchDataSnapshot();
        if (!ignore) setData(initialData);
      } catch (error) {
        console.error('Unable to load timetable data', error);
        if (!ignore) setPageError(getErrorMessage(error));
      }
    }
    loadInitialData();
    return () => { ignore = true; };
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(''), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (page !== 'generate') return undefined;

    let ignore = false;
    API.get('schedule/readiness/').then((response) => {
      if (!ignore) setGenerationReadiness({ ...response.data, key: readinessKey });
    }).catch((error) => {
      if (!ignore) {
        setGenerationReadiness({
          ready: false,
          errors: [getErrorMessage(error)],
          key: readinessKey,
        });
      }
    });

    return () => { ignore = true; };
  }, [page, readinessKey]);

  const setField = (name, value) => setForm((current) => ({ ...current, [name]: value }));
  const setEntryField = (name, value) => setEntryForm((current) => ({ ...current, [name]: value }));

  async function createRecord(endpoint, payload, successMessage) {
    setBusy(true);
    setPageError('');
    try {
      await API.post(endpoint, payload);
      setForm({});
      await refreshData();
      setToast(successMessage);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function removeRecord(endpoint, id) {
    if (!window.confirm('Delete this item? Any related timetable records may also be removed.')) return;
    setPageError('');
    try {
      await API.delete(`${endpoint}${id}/`);
      await refreshData();
      setToast('Deleted successfully.');
    } catch (error) {
      setPageError(getErrorMessage(error));
    }
  }

  async function toggleTeacherAvailability(teacherId, day, periodId, currentlyAvailable) {
    const existing = data.availability.find((item) => (
      String(item.teacher) === String(teacherId)
      && item.day === day
      && String(item.period) === String(periodId)
    ));
    const payload = {
      teacher: Number(teacherId),
      day,
      period: Number(periodId),
      is_available: !currentlyAvailable,
    };

    setBusy(true);
    setPageError('');
    try {
      if (existing) await API.patch(`teacher-availability/${existing.id}/`, payload);
      else await API.post('teacher-availability/', payload);
      await refreshData();
      setToast(payload.is_available ? 'Teacher marked available.' : 'Teacher marked unavailable.');
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveMapping(event) {
    event.preventDefault();
    const subjects = editingMappingId ? [form.subject] : (form.subjects || []);
    const sections = editingMappingId ? [form.section] : (form.sections || []);
    if (subjects.length === 0) {
      setPageError('Select at least one subject to map.');
      return;
    }
    if (sections.length === 0) {
      setPageError('Select at least one class to map.');
      return;
    }
    const payload = editingMappingId
      ? {
        teacher: Number(form.teacher),
        subject: Number(subjects[0]),
        section: Number(form.section),
      }
      : {
        teacher: Number(form.teacher),
        sections: sections.map(Number),
        subjects: subjects.map(Number),
        combine_classes: Boolean(form.combineClasses),
        combined_periods_per_week: Number(form.combinedPeriodsPerWeek || 5),
      };
    setBusy(true);
    setPageError('');
    try {
      if (editingMappingId) await API.patch(`teacher-subjects/${editingMappingId}/`, payload);
      const response = editingMappingId
        ? null
        : await API.post('teacher-subjects/bulk-create/', payload);
      setEditingMappingId(null);
      setForm({});
      await refreshData();
      if (editingMappingId) {
        setToast('Teacher mapping updated.');
      } else {
        const { created_count: createdCount, existing_count: existingCount } = response.data;
        const messages = [];
        if (createdCount) messages.push(`${createdCount} mapping${createdCount === 1 ? '' : 's'} added`);
        if (existingCount) messages.push(`${existingCount} already existed`);
        if (response.data.combined_groups?.length) {
          messages.push(`${response.data.combined_groups.length} combined subject group${response.data.combined_groups.length === 1 ? '' : 's'} saved`);
        }
        setToast(`${messages.join('; ')}.`);
      }
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveSubject(event) {
    event.preventDefault();
    const payload = {
      name: form.name?.trim(),
      category: form.category || 'basic',
    };
    setBusy(true);
    setPageError('');
    try {
      if (editingSubjectId) {
        await API.patch(`subjects/${editingSubjectId}/`, payload);
      } else {
        await API.post('subjects/', payload);
      }
      setEditingSubjectId(null);
      setForm({});
      await refreshData();
      setToast(editingSubjectId ? 'Subject updated.' : 'Subject added.');
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveConstraint(event) {
    event.preventDefault();
    const sectionIds = (form.sections || (form.section ? [form.section] : [])).map(Number);
    const payload = {
      subject: Number(form.subject),
      teacher: Number(form.teacher),
      day: form.day || 'Monday',
      period: Number(form.period),
    };
    setBusy(true);
    setPageError('');
    try {
      if (editingConstraintId) {
        await API.patch(`constraints/${editingConstraintId}/`, {
          ...payload,
          section: sectionIds[0],
        });
      }
      else if (sectionIds.length > 1) {
        await API.post('constraints/create-shared/', { ...payload, sections: sectionIds });
      } else {
        await API.post('constraints/', { ...payload, section: sectionIds[0] });
      }
      setEditingConstraintId(null);
      setForm({});
      await refreshData();
      setToast(editingConstraintId ? 'Fixed class updated.' : sectionIds.length > 1 ? 'Combined fixed class added.' : 'Fixed class added.');
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveAssignment(event) {
    event.preventDefault();
    const subjectIds = (form.subjects || []).map(Number);
    if (!form.section || subjectIds.length === 0) {
      setPageError('Select one section and at least one subject for the weekly plan.');
      return;
    }

    setBusy(true);
    setPageError('');
    try {
      await API.post('section-subjects/configure-section/', {
        section: Number(form.section),
        subject_ids: subjectIds,
      });
      setForm({});
      await refreshData();
      setToast('Weekly plan saved with evenly distributed periods.');
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function generateTimetable() {
    setBusy(true);
    setGenerationErrors([]);
    setPageError('');
    try {
      const response = await API.post('schedule/generate/');
      const adjustmentCount = response.data.plan_adjustments?.length || 0;
      setToast(
        `Generated ${response.data.count} timetable classes.`
        + (adjustmentCount ? ` Updated ${adjustmentCount} weekly-plan counts for weekday coverage.` : ''),
      );
      await refreshData();
    } catch (error) {
      const errors = error.response?.data?.errors;
      if (Array.isArray(errors)) setGenerationErrors(errors);
      else setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveBreak(kind) {
    const existing = data.breaks.find((item) => item.kind === kind);
    const afterPeriod = breakDrafts[kind] ?? existing?.after_period;
    if (!afterPeriod) {
      setPageError(`Choose an exact ${kind === 'break' ? '15-minute break' : '45-minute lunch'} gap between periods.`);
      return;
    }

    setSavingBreakKind(kind);
    setPageError('');
    try {
      const payload = { kind, after_period: Number(afterPeriod) };
      if (existing) await API.patch(`timetable-breaks/${existing.id}/`, payload);
      else await API.post('timetable-breaks/', payload);
      setBreakDrafts((current) => {
        const next = { ...current };
        delete next[kind];
        return next;
      });
      await refreshData();
      setToast(`${kind === 'break' ? '15-minute break' : '45-minute lunch'} saved.`);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setSavingBreakKind('');
    }
  }

  async function removeBreak(kind) {
    const existing = data.breaks.find((item) => item.kind === kind);
    if (!existing) return;
    setSavingBreakKind(kind);
    setPageError('');
    try {
      await API.delete(`timetable-breaks/${existing.id}/`);
      setBreakDrafts((current) => {
        const next = { ...current };
        delete next[kind];
        return next;
      });
      await refreshData();
      setToast(`${kind === 'break' ? 'Break' : 'Lunch'} removed.`);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setSavingBreakKind('');
    }
  }

  async function recalculateWeeklyPlans() {
    setRecalculatingPlans(true);
    setPageError('');
    try {
      const response = await API.post('section-subjects/recalculate-all/');
      setData((current) => ({ ...current, assignments: response.data }));
      setToast('Weekly plans recalculated for the current number of periods.');
      setGenerationErrors([]);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setRecalculatingPlans(false);
    }
  }

  function openEntryEditor(entry = null) {
    setEditingEntry(entry);
    setEntryModalOpen(true);
    setEntryForm(entry ? {
      section: String(entry.section),
      subject: String(entry.subject),
      teacher: String(entry.teacher),
      day: entry.day,
      period: String(entry.period),
    } : {
      section: sectionFilter || (data.sections[0] ? String(data.sections[0].id) : ''),
      subject: '',
      teacher: '',
      day: 'Monday',
      period: data.periods[0] ? String(data.periods[0].id) : '',
    });
    setPageError('');
  }

  async function saveEntry(event) {
    event.preventDefault();
    const payload = {
      section: Number(entryForm.section),
      subject: Number(entryForm.subject),
      teacher: Number(entryForm.teacher),
      day: entryForm.day,
      period: Number(entryForm.period),
    };
    setBusy(true);
    setPageError('');
    try {
      if (editingEntry) await API.patch(`schedule/${editingEntry.id}/`, payload);
      else await API.post('schedule/', payload);
      setEntryModalOpen(false);
      await refreshData();
      setToast(editingEntry ? 'Class updated.' : 'Class added.');
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  const sectionOptions = data.sections.map((item) => ({ value: item.id, label: item.name }));
  const subjectOptions = data.subjects.map((item) => ({ value: item.id, label: item.name }));
  const teacherOptions = data.teachers.map((item) => ({ value: item.id, label: item.name }));
  const periodOptions = data.periods.map((item) => ({
    value: item.id,
    label: `P${item.number} · ${item.start_time.slice(0, 5)}–${item.end_time.slice(0, 5)}`,
  }));
  const displayedSchedule = data.schedule.filter((entry) => (
    (!appliedFilters.section || String(entry.section) === appliedFilters.section)
    && (!appliedFilters.teacher || String(entry.teacher) === appliedFilters.teacher)
  ));
  const displayedSections = data.sections.filter((section) => (
    (!appliedFilters.section || String(section.id) === appliedFilters.section)
    && (!appliedFilters.teacher || displayedSchedule.some(
      (entry) => String(entry.section) === String(section.id),
    ))
  ));
  const subjectColorById = new Map(
    [...data.subjects]
      .sort((left, right) => Number(left.id) - Number(right.id))
      .map((subject, index) => [String(subject.id), SUBJECT_COLORS[index % SUBJECT_COLORS.length]]),
  );
  const displayedSubjects = [...new Map(
    displayedSchedule.map((entry) => [String(entry.subject), entry.subject_name]),
  )].sort((left, right) => left[1].localeCompare(right[1]));
  const getSubjectColor = (subjectId) => (
    subjectColorById.get(String(subjectId)) || SUBJECT_COLORS[0]
  );
  const getCombinedGroup = (entry) => data.combinedGroups.find((group) => (
    String(group.teacher) === String(entry.teacher)
    && String(group.subject) === String(entry.subject)
    && group.sections.some((sectionId) => String(sectionId) === String(entry.section))
  ));
  const getCombinedClassLabel = (entry) => {
    const group = getCombinedGroup(entry);
    return group ? `Combined classes: ${group.section_names.join(' + ')}` : '';
  };

  async function downloadTimetablePdf(sectionId) {
    const sectionsToExport = displayedSections.filter(
      (section) => sectionId === undefined || String(section.id) === String(sectionId),
    );
    const entriesToExport = displayedSchedule.filter(
      (entry) => sectionId === undefined || String(entry.section) === String(sectionId),
    );
    if (entriesToExport.length === 0) {
      setPageError('There are no timetable entries to download. Generate a timetable first.');
      return;
    }

    try {
      const [{ jsPDF }, { default: autoTable }] = await Promise.all([
        import('jspdf'),
        import('jspdf-autotable'),
      ]);
      const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const teacherName = data.teachers.find(
        (teacher) => String(teacher.id) === appliedFilters.teacher,
      )?.name;
      const timetableColumns = getTimetableColumns(data.periods, data.breaks);

      sectionsToExport.forEach((section, index) => {
        if (index > 0) pdf.addPage();

        pdf.setFontSize(18);
        pdf.setTextColor(30, 41, 59);
        pdf.text('WEEKLY CLASS TIME TABLE', 148, 14, { align: 'center' });
        pdf.setFontSize(11);
        pdf.text(`SECTION: ${section.name}`, 148, 21, { align: 'center' });
        if (teacherName) pdf.text(`TEACHER: ${teacherName}`, 148, 27, { align: 'center' });

        const rows = DAYS.map((day) => [
          day,
          ...timetableColumns.map((column) => {
            if (column.type === 'break') {
              return `${column.timetableBreak.kind === 'lunch' ? 'LUNCH' : 'BREAK'}\nNo class`;
            }
            const { period } = column;
            const entry = entriesToExport.find((item) => (
              String(item.section) === String(section.id)
              && item.day === day
              && String(item.period) === String(period.id)
            ));
            const fixed = data.constraints.some((constraint) => (
              String(constraint.section) === String(section.id)
              && constraint.day === day
              && String(constraint.period) === String(period.id)
            ));
            const combinedLabel = entry && getCombinedClassLabel(entry);
            return entry
              ? `${entry.subject_name}\n${entry.teacher_name}${combinedLabel ? `\n${combinedLabel}` : ''}${fixed ? '\n[FIXED]' : ''}`
              : '';
          }),
        ]);
        const headers = [
          'DAYS',
          ...timetableColumns.map((column) => (
            column.type === 'break'
              ? `${column.timetableBreak.kind === 'lunch' ? 'LUNCH' : 'BREAK'}\n${formatTimeRange(column.timetableBreak.start_time, column.timetableBreak.end_time)}`
              : `${toRomanNumeral(column.period.number)}\n${formatTimeRange(column.period.start_time, column.period.end_time)}`
          )),
        ];

        autoTable(pdf, {
          startY: 32,
          head: [headers],
          body: rows,
          theme: 'grid',
          margin: { left: 8, right: 8 },
          styles: {
            font: 'helvetica',
            fontSize: 6.5,
            cellPadding: 2,
            minCellHeight: 21,
            valign: 'middle',
            lineColor: [203, 213, 225],
            lineWidth: 0.2,
          },
          headStyles: {
            fillColor: [30, 41, 59],
            textColor: [255, 255, 255],
            fontStyle: 'bold',
            halign: 'center',
          },
          didParseCell: (hookData) => {
            if (hookData.column.index === 0) return;
            const column = timetableColumns[hookData.column.index - 1];
            if (column.type === 'break') {
              hookData.cell.styles.fillColor = hookData.section === 'head'
                ? [251, 191, 36]
                : [254, 243, 199];
              hookData.cell.styles.textColor = [120, 53, 15];
              hookData.cell.styles.halign = 'center';
              return;
            }
            const periodIndex = data.periods.findIndex(
              (period) => period.id === column.period.id,
            );
            const periodColor = PERIOD_COLORS[periodIndex % PERIOD_COLORS.length];
            if (hookData.section === 'head') {
              hookData.cell.styles.fillColor = periodColor.pdfHeader;
              hookData.cell.styles.textColor = [30, 41, 59];
              return;
            }

            const day = DAYS[hookData.row.index];
            const { period } = column;
            const entry = entriesToExport.find((item) => (
              String(item.section) === String(section.id)
              && item.day === day
              && String(item.period) === String(period?.id)
            ));
            hookData.cell.styles.fillColor = entry
              ? getSubjectColor(entry.subject).pdf
              : periodColor.pdf;
          },
          columnStyles: { 0: { cellWidth: 25, fontStyle: 'bold' } },
        });
      });

      const filenameParts = [
        'school-timetable',
        ...sectionsToExport.map((section) => section.name),
        teacherName,
      ].filter(Boolean).map((part) => part.trim().replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase());
      pdf.save(`${filenameParts.join('-')}-${getExportDate()}.pdf`);
      setPageError('');
    } catch (error) {
      console.error('Unable to create timetable PDF', error);
      setPageError('Unable to create the timetable PDF. Please try again.');
    }
  }

  async function downloadTeacherTimetablePdf(teacherId) {
    const teacher = data.teachers.find(
      (item) => String(item.id) === String(teacherId),
    );
    const entriesToExport = data.schedule.filter(
      (entry) => String(entry.teacher) === String(teacherId),
    );
    if (!teacher || entriesToExport.length === 0) {
      setPageError('There are no saved timetable entries for this teacher to download.');
      return;
    }

    try {
      const [{ jsPDF }, { default: autoTable }] = await Promise.all([
        import('jspdf'),
        import('jspdf-autotable'),
      ]);
      const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const timetableColumns = getTimetableColumns(data.periods, data.breaks);
      const entriesBySlot = new Map();
      for (const entry of entriesToExport) {
        const key = `${entry.day}-${entry.period}`;
        entriesBySlot.set(key, [...(entriesBySlot.get(key) || []), entry]);
      }

      pdf.setFontSize(18);
      pdf.setTextColor(30, 41, 59);
      pdf.text('WEEKLY TEACHER TIME TABLE', 148, 14, { align: 'center' });
      pdf.setFontSize(12);
      pdf.text(`TEACHER: ${teacher.name}`, 148, 22, { align: 'center' });

      const headers = [
        'DAYS',
        ...timetableColumns.map((column) => (
          column.type === 'break'
            ? `${column.timetableBreak.kind === 'lunch' ? 'LUNCH' : 'BREAK'}\n${formatTimeRange(column.timetableBreak.start_time, column.timetableBreak.end_time)}`
            : `${toRomanNumeral(column.period.number)}\n${formatTimeRange(column.period.start_time, column.period.end_time)}`
        )),
      ];
      const rows = DAYS.map((day) => [
        day,
        ...timetableColumns.map((column) => {
          if (column.type === 'break') {
            return `${column.timetableBreak.kind === 'lunch' ? 'LUNCH' : 'BREAK'}\nNo class`;
          }
          const entries = entriesBySlot.get(`${day}-${column.period.id}`) || [];
          if (!entries.length) return 'Free';
          const sections = [...new Set(entries.map((entry) => entry.section_name))];
          const fixed = entries.some((entry) => data.constraints.some((constraint) => (
            String(constraint.section) === String(entry.section)
            && constraint.day === day
            && String(constraint.period) === String(column.period.id)
          )));
          const combinedGroup = getCombinedGroup(entries[0]);
          const sectionLabel = combinedGroup
            ? `Combined classes: ${combinedGroup.section_names.join(' + ')}`
            : sections.map((name) => `Section ${name}`).join(', ');
          return `${entries[0].subject_name}\n${sectionLabel}${fixed ? '\n[FIXED]' : ''}`;
        }),
      ]);

      autoTable(pdf, {
        startY: 28,
        head: [headers],
        body: rows,
        theme: 'grid',
        margin: { left: 8, right: 8 },
        styles: {
          font: 'helvetica',
          fontSize: 6.5,
          cellPadding: 2,
          minCellHeight: 21,
          valign: 'middle',
          lineColor: [203, 213, 225],
          lineWidth: 0.2,
        },
        headStyles: {
          fillColor: [30, 41, 59],
          textColor: [255, 255, 255],
          fontStyle: 'bold',
          halign: 'center',
        },
        didParseCell: (hookData) => {
          if (hookData.column.index === 0) return;
          const column = timetableColumns[hookData.column.index - 1];
          if (column.type === 'break') {
            hookData.cell.styles.fillColor = hookData.section === 'head'
              ? [251, 191, 36]
              : [254, 243, 199];
            hookData.cell.styles.textColor = [120, 53, 15];
            hookData.cell.styles.halign = 'center';
            return;
          }
          const periodIndex = data.periods.findIndex(
            (period) => period.id === column.period.id,
          );
          const periodColor = PERIOD_COLORS[periodIndex % PERIOD_COLORS.length];
          if (hookData.section === 'head') {
            hookData.cell.styles.fillColor = periodColor.pdfHeader;
            hookData.cell.styles.textColor = [30, 41, 59];
            return;
          }
          const day = DAYS[hookData.row.index];
          const entries = entriesBySlot.get(`${day}-${column.period.id}`) || [];
          hookData.cell.styles.fillColor = entries.length
            ? getSubjectColor(entries[0].subject).pdf
            : periodColor.pdf;
        },
        columnStyles: { 0: { cellWidth: 25, fontStyle: 'bold' } },
      });

      const safeTeacherName = teacher.name
        .trim()
        .replace(/[^a-z0-9]+/gi, '-')
        .replace(/^-|-$/g, '')
        .toLowerCase();
      pdf.save(`teacher-timetable-${safeTeacherName}-${getExportDate()}.pdf`);
      setPageError('');
    } catch (error) {
      console.error('Unable to create teacher timetable PDF', error);
      setPageError('Unable to create the teacher timetable PDF. Please try again.');
    }
  }

  function renderTimetable() {
    const timetableColumns = getTimetableColumns(data.periods, data.breaks);
    return (
      <>
        <PageHeading
          eyebrow="School planner · View"
          title="C.E.R.D NURSERY AND PRIMARY SCHOOL TIMETABLE"
          description="Browse the weekly timetable by section or teacher, with every school day and period in one clear view."
          action={(
            <div className="flex flex-wrap gap-2 print:hidden">
              <button
                className={secondaryButtonClass}
                onClick={downloadTimetablePdf}
                disabled={displayedSchedule.length === 0}
                title={displayedSchedule.length === 0 ? 'Generate a timetable before downloading.' : undefined}
              >
                <Download className="h-4 w-4" /> Download PDF
              </button>
            </div>
          )}
        />
        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm print:hidden">
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto_auto] sm:items-end">
            <Field label="Section">
              <Select
                required={false}
                value={sectionFilter}
                onChange={(event) => setSectionFilter(event.target.value)}
                options={sectionOptions}
                placeholder="All sections"
              />
            </Field>
            <Field label="Teacher">
              <Select
                required={false}
                value={teacherFilter}
                onChange={(event) => setTeacherFilter(event.target.value)}
                options={teacherOptions}
                placeholder="All teachers"
              />
            </Field>
            <button className={buttonClass} onClick={() => setAppliedFilters({ section: sectionFilter, teacher: teacherFilter })}>
              Filter timetable
            </button>
            <button
              className={secondaryButtonClass}
              onClick={() => {
                setSectionFilter('');
                setTeacherFilter('');
                setAppliedFilters({ section: '', teacher: '' });
              }}
            >
              Clear
            </button>
          </div>
        </div>

        {data.periods.length === 0 && (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 print:hidden">
            Add periods before creating or generating a school timetable.
          </div>
        )}

        {displayedSubjects.length > 0 && (
          <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-slate-200 bg-white px-4 py-3 print:hidden" aria-label="Subject color legend">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">Subjects</span>
            {displayedSubjects.map(([subjectId, subjectName]) => {
              const color = getSubjectColor(subjectId);
              return (
                <span key={subjectId} className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
                  <span className={`h-3 w-3 rounded-sm ${color.marker}`} aria-hidden="true" />
                  {subjectName}
                </span>
              );
            })}
          </div>
        )}

        {displayedSections.length > 0 && displayedSections.map((section) => (
          <section key={section.id} className="timetable-print-section mb-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="relative border-b-2 border-slate-800 bg-white px-4 py-5 text-center sm:px-6">
              <p className="text-xs font-bold uppercase tracking-[0.22em] text-slate-500">School planner</p>
              <h2 className="mt-1 text-xl font-extrabold uppercase tracking-wide text-slate-900 sm:text-2xl">Weekly Class Time Table</h2>
              <p className="mt-1 text-sm font-bold uppercase text-slate-700">Class: {section.name}</p>
              {appliedFilters.teacher && (
                <p className="text-sm text-slate-500">
                  Teacher: {data.teachers.find((teacher) => String(teacher.id) === appliedFilters.teacher)?.name}
                </p>
              )}
              <button
                className={`${secondaryButtonClass} print:hidden`}
                onClick={() => downloadTimetablePdf(section.id)}
                disabled={!displayedSchedule.some((entry) => String(entry.section) === String(section.id))}
                aria-label={`Download ${section.name} timetable as PDF`}
              >
                <Download className="h-4 w-4" /> Download PDF
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1200px] border-collapse text-left">
                <thead>
                  <tr>
                    <th scope="col" className="sticky left-0 z-10 min-w-28 border border-slate-700 bg-slate-800 px-3 py-3 text-center text-sm font-extrabold uppercase text-white">Days</th>
                    {timetableColumns.map((column, columnIndex) => {
                      if (column.type === 'break') {
                        const label = column.timetableBreak.kind === 'lunch' ? 'Lunch break' : 'Break';
                        return (
                          <th key={`break-${column.timetableBreak.id}`} scope="col" className="min-w-32 border border-amber-300 bg-amber-300 px-2 py-2 text-center text-amber-950">
                            <span className="block text-xs font-extrabold uppercase tracking-wide">{label}</span>
                            <span className="mt-1 block text-[11px] font-semibold">
                              {formatTimeRange(column.timetableBreak.start_time, column.timetableBreak.end_time)}
                            </span>
                          </th>
                        );
                      }
                      const color = PERIOD_COLORS[columnIndex % PERIOD_COLORS.length];
                      return (
                        <th key={column.period.id} scope="col" className={`min-w-32 border border-slate-200 px-2 py-2 text-center ${color.header}`}>
                          <span className="block text-sm font-extrabold">{toRomanNumeral(column.period.number)}</span>
                          <span className="mt-1 block text-[11px] font-semibold">
                            {formatTimeRange(column.period.start_time, column.period.end_time)}
                          </span>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {DAYS.map((day, dayIndex) => (
                    <tr key={day} className={dayIndex % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                      <th scope="row" className="sticky left-0 z-10 border border-slate-300 bg-slate-100 px-3 py-3 text-center text-xs font-extrabold uppercase tracking-wide text-slate-800">
                        {day}
                      </th>
                      {timetableColumns.map((column, columnIndex) => {
                        if (column.type === 'break') {
                          const label = column.timetableBreak.kind === 'lunch' ? 'Lunch' : 'Break';
                          return (
                            <td key={`break-${column.timetableBreak.id}`} className="border border-amber-200 bg-amber-50 px-2 py-3 text-center text-xs font-bold uppercase text-amber-800">
                              {label}
                            </td>
                          );
                        }
                        const { period } = column;
                        const color = PERIOD_COLORS[columnIndex % PERIOD_COLORS.length];
                        const entry = displayedSchedule.find((item) => (
                          String(item.section) === String(section.id)
                          && item.day === day
                          && String(item.period) === String(period.id)
                        ));
                        const fixed = data.constraints.some((constraint) => (
                          String(constraint.section) === String(section.id)
                          && constraint.day === day
                          && String(constraint.period) === String(period.id)
                        ));
                        const subjectColor = entry ? getSubjectColor(entry.subject) : null;
                        return (
                          <td key={period.id} className={`border border-slate-200 p-1.5 align-top ${color.cell}`}>
                            {entry ? (
                              <div className={`min-h-[72px] rounded-md border-l-4 px-2 py-2 ${subjectColor.card}`}>
                                {fixed && (
                                  <span className="mb-1 inline-flex rounded bg-indigo-700 px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-wide text-white">
                                    Fixed
                                  </span>
                                )}
                                <p className={`text-xs font-bold leading-snug sm:text-sm ${subjectColor.name}`}>{entry.subject_name}</p>
                                <p className={`mt-1 text-[11px] font-medium ${subjectColor.teacher}`}>{entry.teacher_name}</p>
                                {getCombinedGroup(entry) ? (
                                  <p className="mt-1 text-[10px] font-semibold text-indigo-700">
                                    {getCombinedClassLabel(entry)}
                                  </p>
                                ) : !appliedFilters.section && (
                                  <p className="mt-1 text-[10px] text-slate-500">{entry.section_name}</p>
                                )}
                                <div className="mt-1 flex gap-1 print:hidden">
                                  <button className="rounded-md p-1 text-slate-500 hover:bg-white hover:text-indigo-700" onClick={() => openEntryEditor(entry)} aria-label={`Edit ${entry.subject_name} on ${day}`}>
                                    <Pencil className="h-3.5 w-3.5" />
                                  </button>
                                  <button className="rounded-md p-1 text-slate-500 hover:bg-white hover:text-rose-600" onClick={() => removeRecord('schedule/', entry.id)} aria-label={`Delete ${entry.subject_name} on ${day}`}>
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </button>
                                </div>
                              </div>
                            ) : <div className={`flex min-h-[72px] items-center justify-center text-sm ${color.empty}`}>—</div>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))}
        {displayedSections.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-12 text-center">
            <CalendarDays className="mx-auto mb-3 h-8 w-8 text-slate-300" />
            <h2 className="font-semibold text-slate-700">No timetable to display</h2>
            <p className="mt-1 text-sm text-slate-500">
              {data.sections.length === 0
                ? 'Add sections to create a timetable view.'
                : 'No sections match these filters. Try another teacher or section.'}
            </p>
            {data.sections.length === 0 && (
              <button className={`${buttonClass} mt-4`} onClick={() => setPage('sections')}>
                <GraduationCap className="h-4 w-4" /> Add a section
              </button>
            )}
          </div>
        )}
      </>
    );
  }

  function renderSimpleManager(title, description, entity, endpoint, label, icon) {
    const Icon = icon;
    const rows = data[entity];
    return (
      <>
        <PageHeading eyebrow="School setup" title={title} description={description} />
        <div className="grid gap-5 lg:grid-cols-[minmax(260px,0.8fr)_minmax(0,1.4fr)]">
          <form
            className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            onSubmit={(event) => {
              if (entity === 'subjects') {
                saveSubject(event);
                return;
              }
              event.preventDefault();
              createRecord(endpoint, { name: form.name?.trim() }, `${label} added.`);
            }}
          >
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"><Icon className="h-5 w-5" /></div>
            <h2 className="font-bold text-slate-900">Add {label.toLowerCase()}</h2>
            <Field label={`${label} name`} className="mt-4">
              <input className={inputClass} value={form.name || ''} onChange={(event) => setField('name', event.target.value)} placeholder={`Enter ${label.toLowerCase()} name`} required maxLength={100} />
            </Field>
            {entity === 'subjects' && (
              <Field label="Subject type" className="mt-3">
                <Select
                  value={form.category || 'basic'}
                  onChange={(event) => setField('category', event.target.value)}
                  options={[
                    { value: 'basic', label: 'Basic · scheduled every weekday' },
                    { value: 'activity', label: 'Activity · 2 periods per week' },
                  ]}
                />
              </Field>
            )}
            <button className={`${buttonClass} mt-4 w-full`} disabled={busy}><Plus className="h-4 w-4" /> {editingSubjectId ? 'Save subject' : `Add ${label}`}</button>
            {editingSubjectId && (
              <button
                type="button"
                className={`${secondaryButtonClass} mt-2 w-full`}
                onClick={() => { setEditingSubjectId(null); setForm({}); }}
              >
                Cancel edit
              </button>
            )}
          </form>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-bold text-slate-900">All {title.toLowerCase()}</h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{rows.length}</span>
            </div>
            {rows.length === 0 ? <EmptyState>No {title.toLowerCase()} added yet.</EmptyState> : (
              <div className="space-y-2">
                {rows.map((row) => (
                  <div key={row.id} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3 transition hover:border-indigo-100 hover:bg-indigo-50/40">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-800">{row.name}</p>
                      {entity === 'subjects' && (
                        <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          row.category === 'activity'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-indigo-100 text-indigo-800'
                        }`}>
                          {row.category === 'activity' ? 'Activity · 2/week' : 'Basic · every weekday'}
                        </span>
                      )}
                    </div>
                    <div className="ml-2 flex gap-1">
                      {entity === 'subjects' && (
                        <button
                          className="rounded-lg p-2 text-slate-400 transition hover:bg-indigo-50 hover:text-indigo-600"
                          aria-label={`Edit ${row.name}`}
                          onClick={() => {
                            setEditingSubjectId(row.id);
                            setForm({ name: row.name, category: row.category });
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      )}
                      <button className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600" aria-label={`Delete ${row.name}`} onClick={() => removeRecord(endpoint, row.id)}><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </>
    );
  }

  function renderMappings() {
    return (
      <>
        <PageHeading eyebrow="Teaching team" title="Teacher–subject mapping" description="Map a teacher to subjects and classes. You can also combine selected classes so one teacher teaches them together in the same periods." />
        <div className="grid gap-5 lg:grid-cols-[minmax(260px,0.8fr)_minmax(0,1.4fr)]">
          <form className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={saveMapping}>
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-violet-50 text-violet-600"><Link2 className="h-5 w-5" /></div>
            <h2 className="font-bold text-slate-900">{editingMappingId ? 'Edit teacher mapping' : 'Map a teacher'}</h2>
            <Field label="Class" className="mt-4">
              {editingMappingId
                ? <Select value={form.section || ''} onChange={(event) => setField('section', event.target.value)} options={sectionOptions} placeholder="Select class" />
                : <MultiSelectDropdown label="classes" values={form.sections || []} onChange={(values) => setField('sections', values)} options={sectionOptions} placeholder="Select one or more classes" />}
            </Field>
            <Field label="Teacher" className="mt-3"><Select value={form.teacher || ''} onChange={(event) => setField('teacher', event.target.value)} options={teacherOptions} placeholder="Select teacher" /></Field>
            <Field label="Subject" className="mt-3">
              {editingMappingId
                ? <Select value={form.subject || ''} onChange={(event) => setField('subject', event.target.value)} options={subjectOptions} placeholder="Select subject" />
                : <MultiSelectDropdown label="subjects" values={form.subjects || []} onChange={(values) => setField('subjects', values)} options={subjectOptions} placeholder="Select one or more subjects" />}
            </Field>
            {!editingMappingId && (
              <>
                <label className="mt-4 flex items-start gap-3 rounded-xl border border-slate-200 p-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={Boolean(form.combineClasses)}
                    onChange={(event) => setField('combineClasses', event.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span><span className="font-semibold">Combine selected classes</span><span className="mt-1 block text-xs text-slate-500">The selected classes will have these subjects together with this teacher in the same periods.</span></span>
                </label>
                {form.combineClasses && (
                  <Field label="Shared periods per week" className="mt-3">
                    <input
                      type="number"
                      min="1"
                      max={data.periods.length * DAYS.length}
                      required
                      className={inputClass}
                      value={form.combinedPeriodsPerWeek || 5}
                      onChange={(event) => setField('combinedPeriodsPerWeek', event.target.value)}
                    />
                  </Field>
                )}
              </>
            )}
            <button className={`${buttonClass} mt-4 w-full`} disabled={busy}><Plus className="h-4 w-4" /> Save mapping</button>
            {editingMappingId && <button type="button" className={`${secondaryButtonClass} mt-2 w-full`} onClick={() => { setEditingMappingId(null); setForm({}); }}>Cancel edit</button>}
          </form>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-bold text-slate-900">Mapped subjects</h2>
            {data.mappings.length === 0 ? <EmptyState>No teacher mappings yet.</EmptyState> : (
              <div className="grid gap-2 sm:grid-cols-2">
                {data.mappings.map((mapping) => (
                  <div key={mapping.id} className="flex items-center justify-between rounded-xl border border-slate-100 p-3">
                    <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{mapping.teacher_name}</p><p className="mt-1 text-xs text-slate-500">{mapping.subject_name} · {mapping.section_name || 'All classes (legacy mapping)'}</p></div>
                    <div className="ml-2 flex gap-1">
                      <button className="rounded-lg p-2 text-slate-400 hover:bg-indigo-50 hover:text-indigo-600" onClick={() => { setEditingMappingId(mapping.id); setForm({ teacher: String(mapping.teacher), subject: String(mapping.subject), section: mapping.section ? String(mapping.section) : '' }); }} aria-label="Edit mapping"><Pencil className="h-4 w-4" /></button>
                      <button className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => removeRecord('teacher-subjects/', mapping.id)} aria-label="Remove mapping"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-bold text-slate-900">Combined classes</h2>
          {data.combinedGroups.length === 0 ? <EmptyState>No combined classes configured.</EmptyState> : (
            <div className="grid gap-2 sm:grid-cols-2">
              {data.combinedGroups.map((group) => (
                <div key={group.id} className="flex items-center justify-between rounded-xl border border-slate-100 p-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800">{group.subject_name} · {group.section_names.join(' + ')}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {group.teacher_name} · {group.periods_per_week} shared period{group.periods_per_week === 1 ? '' : 's'} per week
                    </p>
                  </div>
                  <button className="ml-2 rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => removeRecord('combined-teaching-groups/', group.id)} aria-label="Remove combined class"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      </>
    );
  }

  function renderAssignments() {
    const weeklyCapacity = data.periods.length * DAYS.length;
    const selectedSection = data.sections.find(
      (section) => String(section.id) === String(form.section || ''),
    );
    const fixedCounts = {};
    for (const constraint of data.constraints) {
      if (String(constraint.section) !== String(form.section || '')) continue;
      const subjectId = String(constraint.subject);
      fixedCounts[subjectId] = (fixedCounts[subjectId] || 0) + 1;
    }
    const selectedSubjectIds = [...new Set(form.subjects || [])].sort(
      (left, right) => Number(left) - Number(right),
    );
    const subjectsById = Object.fromEntries(
      data.subjects.map((subject) => [String(subject.id), subject]),
    );
    const allocations = calculateWeeklyDistribution(
      selectedSubjectIds,
      fixedCounts,
      weeklyCapacity,
      subjectsById,
    );
    const activityCount = selectedSubjectIds.filter(
      (subjectId) => subjectsById[String(subjectId)]?.category === 'activity',
    ).length;
    const basicCount = selectedSubjectIds.length - activityCount;
    const sectionPlans = data.sections.map((section) => {
      const assignments = data.assignments.filter(
        (item) => String(item.section) === String(section.id),
      );
      return {
        section,
        assignments,
        total: assignments.reduce((sum, item) => sum + item.periods_per_week, 0),
      };
    }).filter((plan) => plan.assignments.length > 0);

    return (
      <>
        <PageHeading eyebrow="Weekly teaching plan" title="Assign subjects to sections" description={`Choose one section and its subjects. Basic subjects receive at least 5 periods/week, Activities receive at least 2, and remaining periods are shared across Basic subjects. Fixed classes count toward each subject’s minimum.`} />
        <div className="grid gap-5 lg:grid-cols-[minmax(280px,0.85fr)_minmax(0,1.4fr)]">
          <form className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={saveAssignment}>
            <h2 className="font-bold text-slate-900">
              {selectedSection && data.assignments.some(
                (item) => String(item.section) === String(selectedSection.id),
              ) ? 'Edit weekly plan' : 'Create weekly plan'}
            </h2>
            <Field label="Section" className="mt-4">
              <Select
                value={form.section || ''}
                onChange={(event) => {
                  const sectionId = event.target.value;
                  const existingSubjectIds = data.assignments
                    .filter((item) => String(item.section) === sectionId)
                    .map((item) => String(item.subject));
                  const fixedSubjectIds = data.constraints
                    .filter((item) => String(item.section) === sectionId)
                    .map((item) => String(item.subject));
                  setForm({
                    section: sectionId,
                    subjects: [...new Set([...existingSubjectIds, ...fixedSubjectIds])],
                  });
                }}
                options={sectionOptions}
                placeholder="Select one section"
              />
            </Field>
            <div className="mt-3 text-sm font-medium text-slate-700">
              <span>Subjects for this section</span>
              <MultiSelectDropdown
                label="subjects"
                values={form.subjects || []}
                onChange={(values) => {
                  const fixedSubjectIds = data.constraints
                    .filter((item) => String(item.section) === String(form.section || ''))
                    .map((item) => String(item.subject));
                  setField('subjects', [...new Set([...values, ...fixedSubjectIds])]);
                }}
                options={subjectOptions}
                placeholder={form.section ? 'Select one or more subjects' : 'Select a section first'}
                disabled={!form.section}
              />
            </div>
            {selectedSubjectIds.length > 0 && allocations && (
              <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/60 p-3" aria-live="polite">
                <p className="text-xs font-bold uppercase tracking-wide text-indigo-800">
                  Auto-calculated weekly plan
                </p>
                <p className="mt-1 text-xs text-indigo-700">
                  {basicCount} Basic subject(s) · minimum 5 each; {activityCount} Activity subject(s) · minimum 2 each.
                  {activityCount > 0 && ' Activity periods are scheduled on separate weekdays.'}
                </p>
                <div className="mt-2 space-y-1.5">
                  {selectedSubjectIds.map((subjectId) => {
                    const subject = data.subjects.find(
                      (item) => String(item.id) === subjectId,
                    );
                    const fixedCount = fixedCounts[subjectId] || 0;
                    return (
                      <div key={subjectId} className="flex items-center justify-between gap-3 text-sm text-slate-700">
                        <span>{subject?.name || 'Subject'}{fixedCount ? ` · ${fixedCount} fixed` : ''}</span>
                        <span className="font-bold">
                          {allocations[subjectId]} / week
                          {subject?.category === 'activity' ? ' · Activity' : ' · Basic'}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <p className="mt-2 border-t border-indigo-100 pt-2 text-xs text-indigo-700">
                  Total: {Object.values(allocations).reduce((sum, count) => sum + count, 0)} / {weeklyCapacity} periods
                </p>
              </div>
            )}
            {selectedSubjectIds.length > 0 && !allocations && (
              <p role="alert" className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">
                Subject minimums do not fit the weekly capacity, or Activities have remaining periods but no Basic subject can fill the rest.
              </p>
            )}
            <button
              className={`${buttonClass} mt-4 w-full`}
              disabled={busy || !form.section || selectedSubjectIds.length === 0 || !allocations}
            >
              <Plus className="h-4 w-4" /> Save weekly plan
            </button>
            {selectedSection && (
              <button
                type="button"
                className={`${secondaryButtonClass} mt-2 w-full`}
                onClick={() => setForm({})}
              >
                Clear selection
              </button>
            )}
          </form>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-bold text-slate-900">Weekly plans by section</h2>
            {sectionPlans.length === 0 ? <EmptyState>No weekly plans configured.</EmptyState> : (
              <div className="space-y-3">
                {sectionPlans.map(({ section, assignments, total }) => (
                  <div key={section.id} className="rounded-xl border border-slate-100 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-slate-900">{section.name}</h3>
                        <p className="text-xs text-slate-500">{total} of {weeklyCapacity} weekly periods assigned</p>
                      </div>
                      <button
                        type="button"
                        className={secondaryButtonClass}
                        onClick={() => setForm({
                          section: String(section.id),
                          subjects: assignments.map((item) => String(item.subject)),
                        })}
                      >
                        <Pencil className="h-4 w-4" /> Edit plan
                      </button>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {assignments.map((item) => (
                        <span key={item.id} className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">
                          {item.subject_name} · {item.periods_per_week} periods/week · {subjectsById[String(item.subject)]?.category === 'activity' ? 'Activity' : 'Basic'}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </>
    );
  }

  function renderPeriods() {
    const suggestedPeriodNumber = getNextPeriodNumber(data.periods);
    const addPeriodNumber = Number(form.number || suggestedPeriodNumber);
    const suggestedTimes = suggestPeriodTimes(data.periods, addPeriodNumber);
    const shortBreakOptions = getBreakPlacementOptions(data.periods, 15);
    const lunchOptions = getBreakPlacementOptions(data.periods, 45);
    const savedBreak = (kind) => data.breaks.find((item) => item.kind === kind);
    const renderBreakConfig = (kind, title, durationMinutes, options) => {
      const current = savedBreak(kind);
      const other = savedBreak(kind === 'break' ? 'lunch' : 'break');
      const availableOptions = options.filter((option) => (
        String(option.value) !== String(other?.after_period)
        || String(option.value) === String(current?.after_period)
      ));
      const selectedValue = breakDrafts[kind] ?? current?.after_period ?? '';
      return (
        <div key={kind} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 text-xs text-slate-500">{durationMinutes} minutes · visible in the weekly timetable, not a teaching period</p>
            </div>
            {current && <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">Configured</span>}
          </div>
          <Field label="Place after" className="mt-3">
            <Select
              value={String(selectedValue)}
              onChange={(event) => setBreakDrafts((drafts) => ({ ...drafts, [kind]: event.target.value }))}
              options={availableOptions}
              placeholder={availableOptions.length ? 'Select an exact break gap' : 'No matching time gap'}
              required={false}
            />
          </Field>
          {availableOptions.length === 0 ? (
            <p className="mt-2 text-xs text-amber-700">
              Set a gap of exactly {durationMinutes} minutes between two periods in the Bell schedule first.
            </p>
          ) : (
            <p className="mt-2 text-xs text-slate-500">
              Period times stay manual; only gaps exactly {durationMinutes} minutes long can be selected.
            </p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              className={`${buttonClass} flex-1`}
              disabled={!selectedValue || savingBreakKind === kind}
              onClick={() => saveBreak(kind)}
            >
              {savingBreakKind === kind ? 'Saving…' : current ? 'Save placement' : 'Add to timetable'}
            </button>
            {current && (
              <button
                type="button"
                className={secondaryButtonClass}
                disabled={savingBreakKind === kind}
                onClick={() => removeBreak(kind)}
              >
                Remove
              </button>
            )}
          </div>
        </div>
      );
    };
    return (
      <>
        <PageHeading eyebrow="Bell schedule" title="Periods and times" description="Configure the periods used by the timetable. The default setup includes eight 45-minute periods; add, edit, or remove periods to match your school day." />
        <div className="grid gap-5 lg:grid-cols-[minmax(260px,0.75fr)_minmax(0,1.5fr)]">
          <form className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={(event) => {
            event.preventDefault();
            createRecord('periods/', {
              number: addPeriodNumber,
              start_time: form.start_time || suggestedTimes.start_time,
              end_time: form.end_time || suggestedTimes.end_time,
            }, 'Period added.');
          }}>
            <h2 className="font-bold text-slate-900">Add a period</h2>
            <Field label="Period number" className="mt-4"><input className={inputClass} type="number" min="1" value={form.number || suggestedPeriodNumber} onChange={(event) => {
              const number = Number(event.target.value);
              if (!Number.isInteger(number) || number < 1) {
                setForm((current) => ({ ...current, number: event.target.value }));
                return;
              }
              const suggestedTimes = suggestPeriodTimes(data.periods, number);
              setForm((current) => ({ ...current, number: event.target.value, ...suggestedTimes }));
            }} placeholder={`Next available: ${suggestedPeriodNumber}`} required /></Field>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Field label="Starts"><TimeInput12Hour label="Period start time" value={form.start_time || suggestedTimes.start_time} onChange={(value) => setField('start_time', value)} /></Field>
              <Field label="Ends"><TimeInput12Hour label="Period end time" value={form.end_time || suggestedTimes.end_time} onChange={(value) => setField('end_time', value)} /></Field>
            </div>
            <p className="mt-2 text-xs font-medium text-indigo-700">Suggested: {formatTime12Hour(form.start_time || suggestedTimes.start_time)} – {formatTime12Hour(form.end_time || suggestedTimes.end_time)}</p>
            <p className="mt-2 text-xs text-slate-500">Choosing a period number suggests a free slot between neighboring periods. Adjust the suggested times if needed.</p>
            <button className={`${buttonClass} mt-4 w-full`} disabled={busy}><Plus className="h-4 w-4" /> Add period</button>
          </form>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-bold text-slate-900">Current school day</h2>
            {data.periods.length === 0 ? <EmptyState>No periods configured.</EmptyState> : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {data.periods.map((period) => (
                  <div key={period.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <div className="flex items-center justify-between"><span className="rounded-lg bg-white px-2.5 py-1 text-xs font-bold text-indigo-700 shadow-sm">PERIOD {period.number}</span><button className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => removeRecord('periods/', period.id)} aria-label={`Delete period ${period.number}`}><Trash2 className="h-4 w-4" /></button></div>
                    <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-700"><Clock3 className="h-4 w-4 text-indigo-500" />{formatTime12Hour(period.start_time)} – {formatTime12Hour(period.end_time)}</div>
                   
                  
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
            <h2 className="font-bold text-slate-900">Daily break and lunch</h2>
            <p className="mt-1 text-sm text-slate-500">
              Configure the same non-teaching breaks for Monday–Friday. Period times remain manual; the break must match the gap between periods.
            </p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {renderBreakConfig('break', 'Short break', 15, shortBreakOptions)}
              {renderBreakConfig('lunch', 'Lunch', 45, lunchOptions)}
            </div>
          </div>
        </div>
      </>
    );
  }

  function renderAvailability() {
    const selectedTeacherId = availabilityTeacher || String(data.teachers[0]?.id || '');
    const selectedTeacher = data.teachers.find(
      (teacher) => String(teacher.id) === selectedTeacherId,
    );
    const teacherClasses = data.schedule.filter(
      (entry) => String(entry.teacher) === selectedTeacherId,
    );
    const teachingPeriodCount = new Set(
      teacherClasses.map((entry) => `${entry.day}-${entry.period}`),
    ).size;
    const unavailableCount = data.availability.filter(
      (item) => String(item.teacher) === selectedTeacherId && !item.is_available,
    ).length;
    return (
      <>
        <PageHeading eyebrow="Staff schedule" title="Teacher availability" description="View each teacher’s weekly teaching schedule and mark open periods as available or unavailable. Unmarked periods are available by default." />
        <div className="mb-5 grid gap-4 sm:grid-cols-[minmax(220px,360px)_1fr] sm:items-end">
          <Field label="Staff member">
            <Select
              value={selectedTeacherId}
              onChange={(event) => setAvailabilityTeacher(event.target.value)}
              options={teacherOptions}
              placeholder="Select staff member"
            />
          </Field>
          <div className="flex flex-wrap gap-2 text-xs font-medium">
            <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-emerald-800">Available</span>
            <span className="rounded-full bg-rose-100 px-3 py-1.5 text-rose-800">Unavailable</span>
            <span className="rounded-full bg-indigo-100 px-3 py-1.5 text-indigo-800">Teaching</span>
            <span className="self-center text-slate-500">Select an open period to change availability.</span>
          </div>
        </div>
        {!selectedTeacher ? (
          <EmptyState>Add a teacher to view the staff schedule.</EmptyState>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="font-bold text-slate-900">{selectedTeacher.name} · Weekly schedule</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {teachingPeriodCount} teaching periods · {unavailableCount} unavailable periods
                </p>
              </div>
              {data.schedule.length === 0 && (
                <button className={secondaryButtonClass} onClick={() => setPage('generate')}>
                  <WandSparkles className="h-4 w-4" /> Generate timetable
                </button>
              )}
            </div>
            {data.periods.length === 0 ? (
              <div className="p-5"><EmptyState>Configure periods before setting staff availability.</EmptyState></div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse text-left">
                  <thead>
                    <tr className="bg-slate-50">
                      <th className="sticky left-0 z-10 border-b border-r border-slate-200 bg-slate-50 px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Day</th>
                      {data.periods.map((period) => (
                        <th key={period.id} className="border-b border-slate-200 px-3 py-3 text-center text-xs font-bold text-slate-600">
                          <span className="block">P{period.number}</span>
                          <span className="mt-1 block font-normal text-slate-400">{period.start_time.slice(0, 5)}</span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {DAYS.map((day) => (
                      <tr key={day}>
                        <th className="sticky left-0 z-10 whitespace-nowrap border-b border-r border-slate-100 bg-white px-4 py-3 text-sm font-semibold text-slate-700">{day}</th>
                        {data.periods.map((period) => {
                          const scheduledClass = teacherClasses.find((entry) => (
                            entry.day === day && String(entry.period) === String(period.id)
                          ));
                          const availability = data.availability.find((item) => (
                            String(item.teacher) === selectedTeacherId
                            && item.day === day
                            && String(item.period) === String(period.id)
                          ));
                          const isAvailable = availability?.is_available !== false;
                          return (
                            <td key={period.id} className="border-b border-slate-100 p-1.5 text-center">
                              {scheduledClass ? (
                                <div className="min-h-16 rounded-lg border border-indigo-200 bg-indigo-50 px-2 py-2 text-xs">
                                  <p className="font-bold text-indigo-900">{scheduledClass.subject_name}</p>
                                  <p className="mt-1 text-indigo-700">
                                    {getCombinedClassLabel(scheduledClass)
                                      || `Section ${scheduledClass.section_name}`}
                                  </p>
                                </div>
                              ) : (
                                <button
                                  type="button"
                                  className={`min-h-16 w-full rounded-lg border px-2 py-2 text-xs font-semibold transition disabled:cursor-wait disabled:opacity-60 ${isAvailable ? 'border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100' : 'border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100'}`}
                                  onClick={() => toggleTeacherAvailability(
                                    selectedTeacher.id,
                                    day,
                                    period.id,
                                    isAvailable,
                                  )}
                                  disabled={busy}
                                  aria-label={`${selectedTeacher.name}, ${day}, period ${period.number}: ${isAvailable ? 'available, mark unavailable' : 'unavailable, mark available'}`}
                                >
                                  {isAvailable ? 'Available' : 'Unavailable'}
                                </button>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </>
    );
  }

  function renderConstraints() {
    const selectedSectionIds = form.sections || (form.section ? [String(form.section)] : []);
    const firstSectionAssignments = data.assignments.filter(
      (item) => String(item.section) === String(selectedSectionIds[0] || ''),
    );
    const constraintSubjectOptions = firstSectionAssignments
      .filter((assignment) => selectedSectionIds.every((sectionId) => (
        data.assignments.some((other) => (
          String(other.section) === String(sectionId)
          && String(other.subject) === String(assignment.subject)
        ))
      )))
      .map((assignment) => ({
        value: assignment.subject,
        label: `${assignment.subject_name} · assigned to all selected sections`,
      }));
    const constraintTeacherOptions = data.mappings
      .filter((mapping) => String(mapping.subject) === String(form.subject || ''))
      .map((mapping) => ({ value: mapping.teacher, label: mapping.teacher_name }));
    const selectedAssignments = selectedSectionIds.map((sectionId) => (
      data.assignments.find((assignment) => (
        String(assignment.section) === String(sectionId)
        && String(assignment.subject) === String(form.subject || '')
      ))
    )).filter(Boolean);
    const selectedAssignment = selectedAssignments[0];
    const fixedCountsBySection = selectedAssignments.map((assignment) => ({
      sectionName: data.sections.find((section) => String(section.id) === String(assignment.section))?.name,
      count: data.constraints.filter((item) => (
        String(item.section) === String(assignment.section)
        && String(item.subject) === String(form.subject)
        && item.id !== editingConstraintId
      )).length,
      required: assignment.periods_per_week,
    }));
    const fixedCapacityReached = Boolean(
      fixedCountsBySection.some((item) => item.count >= item.required),
    );

    return (
      <>
        <PageHeading eyebrow="Generation rules" title="Fixed timetable classes" description="Pin a class from the weekly teaching plan to a day and period. Subjects and teachers are limited to the selected section’s assignments and mapped staff." />
        <div className="grid gap-5 lg:grid-cols-[minmax(280px,0.9fr)_minmax(0,1.4fr)]">
          <form className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={saveConstraint}>
            <h2 className="font-bold text-slate-900">{editingConstraintId ? 'Edit fixed class' : 'Add a fixed class'}</h2>
            <Field label="Sections (select one or more)" className="mt-4">
              <div className="mt-1 max-h-40 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-2">
                {data.sections.map((section) => {
                  const checked = selectedSectionIds.some((id) => String(id) === String(section.id));
                  return (
                    <label key={section.id} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={Boolean(editingConstraintId)}
                        onChange={(event) => setForm((current) => ({
                          ...current,
                          sections: event.target.checked
                            ? [...selectedSectionIds, String(section.id)]
                            : selectedSectionIds.filter((id) => String(id) !== String(section.id)),
                          section: '',
                          subject: '',
                          teacher: '',
                        }))}
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span>{section.name}</span>
                    </label>
                  );
                })}
              </div>
              <p className="mt-1 text-xs text-slate-500">Selecting multiple sections creates one shared lesson for all of them at the same time.</p>
            </Field>
            <Field label="Weekly-plan subject" className="mt-3">
              <Select
                value={form.subject || ''}
                onChange={(event) => setForm((current) => ({
                  ...current,
                  subject: event.target.value,
                  teacher: '',
                }))}
                options={constraintSubjectOptions}
                placeholder={selectedSectionIds.length ? 'Select subject assigned to all sections' : 'Select section(s) first'}
                required={selectedSectionIds.length > 0}
              />
            </Field>
            {selectedAssignment && (
              <div className={`mt-2 rounded-lg px-3 py-2 text-xs ${fixedCapacityReached ? 'bg-rose-50 text-rose-700' : 'bg-indigo-50 text-indigo-700'}`}>
                <p>
                  Fixed classes by section: {fixedCountsBySection.map((item) => `${item.sectionName}: ${item.count}/${item.required}`).join(' · ')}
                  {fixedCapacityReached ? ' · weekly requirement is fully fixed' : ''}
                </p>
                <p className="mt-1">
                  This lesson stays in its pinned slot. Basic subjects still appear on other weekdays; Activities count their fixed slots toward the weekly target.
                </p>
              </div>
            )}
            <Field label="Mapped teacher" className="mt-3">
              <Select
                value={form.teacher || ''}
                onChange={(event) => setField('teacher', event.target.value)}
                options={constraintTeacherOptions}
                placeholder={form.subject ? 'Select mapped teacher' : 'Select a subject first'}
                required={Boolean(form.subject)}
              />
            </Field>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Field label="Day"><Select value={form.day || 'Monday'} onChange={(event) => setField('day', event.target.value)} options={DAYS.map((day) => ({ value: day, label: day }))} /></Field>
              <Field label="Period"><Select value={form.period || ''} onChange={(event) => setField('period', event.target.value)} options={periodOptions} placeholder="Select period" /></Field>
            </div>
            {constraintSubjectOptions.length === 0 && selectedSectionIds.length > 0 && (
              <p className="mt-3 text-xs text-amber-700">For a combined class, assign the same subject to every selected section in the Weekly teaching plan first.</p>
            )}
            {constraintTeacherOptions.length === 0 && form.subject && (
              <p className="mt-3 text-xs text-amber-700">Map at least one teacher to this subject before fixing a class.</p>
            )}
            <button className={`${buttonClass} mt-4 w-full`} disabled={busy || !selectedSectionIds.length || selectedSectionIds.length !== selectedAssignments.length || !selectedAssignment || !form.teacher || !form.period || fixedCapacityReached}><Plus className="h-4 w-4" /> {selectedSectionIds.length > 1 ? 'Save combined fixed class' : 'Save fixed class'}</button>
            {editingConstraintId && <button type="button" className={`${secondaryButtonClass} mt-2 w-full`} onClick={() => { setEditingConstraintId(null); setForm({}); }}>Cancel edit</button>}
          </form>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-bold text-slate-900">Current fixed classes</h2>
            {data.constraints.length === 0 ? <EmptyState>No fixed classes. The generator will place lessons automatically.</EmptyState> : (
              <div className="space-y-2">
                {data.constraints.map((item) => (
                  <div key={item.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 p-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-800">{item.section_name} · {item.subject_name}{item.shared_group ? ' · Shared class' : ''}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.teacher_name} · {item.day} · Period {item.period_number}</p>
                      {item.shared_group && (
                        <p className="mt-1 text-xs text-indigo-700">
                          Combined with {data.constraints.filter((other) => (
                            other.shared_group === item.shared_group && other.id !== item.id
                          )).map((other) => other.section_name).join(', ')}
                        </p>
                      )}
                      <span className="mt-1 inline-flex rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-indigo-800">Pinned to this slot</span>
                    </div>
                    <div className="flex gap-1">
                      {!item.shared_group && <button className="rounded-lg p-2 text-slate-400 hover:bg-indigo-50 hover:text-indigo-600" onClick={() => { setEditingConstraintId(item.id); setForm({ sections: [String(item.section)], subject: String(item.subject), teacher: String(item.teacher), day: item.day, period: String(item.period) }); }} aria-label="Edit fixed class"><Pencil className="h-4 w-4" /></button>}
                      <button className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => removeRecord('constraints/', item.id)} aria-label="Delete fixed class"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </>
    );
  }

  function renderTeacherTimetable() {
    const selectedTeacherId = data.teachers.some(
      (teacher) => String(teacher.id) === teacherTimetableFilter,
    )
      ? teacherTimetableFilter
      : String(data.teachers[0]?.id || '');
    const selectedTeacher = data.teachers.find(
      (teacher) => String(teacher.id) === selectedTeacherId,
    );
    const teacherEntries = data.schedule.filter(
      (entry) => String(entry.teacher) === selectedTeacherId,
    );
    const timetableColumns = getTimetableColumns(data.periods, data.breaks);
    const entriesBySlot = new Map();
    for (const entry of teacherEntries) {
      const key = `${entry.day}-${entry.period}`;
      entriesBySlot.set(key, [...(entriesBySlot.get(key) || []), entry]);
    }
    const taughtSections = new Set(teacherEntries.map((entry) => entry.section));
    const taughtSubjects = new Set(teacherEntries.map((entry) => entry.subject));
    const teachingPeriodCount = new Set(
      teacherEntries.map((entry) => `${entry.day}-${entry.period}`),
    ).size;

    return (
      <>
        <PageHeading
          eyebrow="Saved school timetable · Teacher view"
          title="Teacher timetable"
          description="View each teacher’s classes by weekday and period. This page reads the saved School Timetable produced by Automatic planning."
          action={(
            <div className="flex flex-wrap gap-2">
              <button
                className={secondaryButtonClass}
                onClick={() => downloadTeacherTimetablePdf(selectedTeacherId)}
                disabled={!selectedTeacher || teacherEntries.length === 0}
                title={teacherEntries.length === 0 ? 'Select a teacher with saved timetable classes to download.' : undefined}
              >
                <Download className="h-4 w-4" /> Download PDF
              </button>
              <button className={buttonClass} onClick={() => setPage('generate')}>
                <WandSparkles className="h-4 w-4" /> Automatic planning
              </button>
            </div>
          )}
        />
        <div className="mb-5 grid gap-4 sm:grid-cols-[minmax(240px,1fr)_repeat(3,minmax(120px,0.5fr))]">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <Field label="Select teacher">
              <Select
                required={false}
                value={selectedTeacherId}
                onChange={(event) => setTeacherTimetableFilter(event.target.value)}
                options={teacherOptions}
                placeholder="Select a teacher"
              />
            </Field>
          </div>
          {[
            ['Teaching periods', teachingPeriodCount],
            ['Sections', taughtSections.size],
            ['Subjects', taughtSubjects.size],
          ].map(([label, count]) => (
            <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{count}</p>
            </div>
          ))}
        </div>

        {!selectedTeacher ? (
          <EmptyState>Add a teacher to view their timetable.</EmptyState>
        ) : data.schedule.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-10 text-center">
            <p className="font-semibold text-slate-800">No saved school timetable yet.</p>
            <p className="mt-2 text-sm text-slate-500">Use Automatic planning to generate the school timetable first.</p>
            <button className={`${buttonClass} mt-4`} onClick={() => setPage('generate')}>
              <WandSparkles className="h-4 w-4" /> Generate timetable
            </button>
          </div>
        ) : teacherEntries.length === 0 ? (
          <EmptyState>{selectedTeacher.name} has no classes in the saved school timetable.</EmptyState>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
              <span>
                Showing the saved timetable for <strong>{selectedTeacher.name}</strong>.
                Generate again in Automatic planning to refresh it from the current weekly plans and fixed classes.
              </span>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-indigo-700">
                {teachingPeriodCount} teaching periods this week
              </span>
            </div>
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1000px] border-collapse text-left">
                  <thead>
                    <tr>
                      <th scope="col" className="sticky left-0 z-10 min-w-28 border border-slate-700 bg-slate-800 px-3 py-3 text-center text-sm font-extrabold uppercase text-white">Day</th>
                      {timetableColumns.map((column, columnIndex) => {
                        if (column.type === 'break') {
                          const label = column.timetableBreak.kind === 'lunch' ? 'Lunch break' : 'Break';
                          return (
                            <th key={`break-${column.timetableBreak.id}`} scope="col" className="min-w-28 border border-amber-300 bg-amber-300 px-2 py-2 text-center text-amber-950">
                              <span className="block text-xs font-extrabold uppercase">{label}</span>
                              <span className="mt-1 block text-[11px] font-semibold">
                                {formatTimeRange(column.timetableBreak.start_time, column.timetableBreak.end_time)}
                              </span>
                            </th>
                          );
                        }
                        const color = PERIOD_COLORS[columnIndex % PERIOD_COLORS.length];
                        return (
                          <th key={column.period.id} scope="col" className={`min-w-32 border border-slate-200 px-2 py-2 text-center ${color.header}`}>
                            <span className="block text-sm font-extrabold">Period {column.period.number}</span>
                            <span className="mt-1 block text-[11px] font-semibold">
                              {formatTimeRange(column.period.start_time, column.period.end_time)}
                            </span>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {DAYS.map((day, dayIndex) => (
                      <tr key={day} className={dayIndex % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                        <th scope="row" className="sticky left-0 z-10 border border-slate-300 bg-slate-100 px-3 py-3 text-center text-xs font-extrabold uppercase tracking-wide text-slate-800">
                          {day}
                        </th>
                        {timetableColumns.map((column, columnIndex) => {
                          if (column.type === 'break') {
                            return (
                              <td key={`break-${column.timetableBreak.id}`} className="border border-amber-200 bg-amber-50 px-2 py-3 text-center text-xs font-bold uppercase text-amber-800">
                                {column.timetableBreak.kind === 'lunch' ? 'Lunch' : 'Break'}
                              </td>
                            );
                          }
                          const { period } = column;
                          const entries = entriesBySlot.get(`${day}-${period.id}`) || [];
                          const entry = entries[0];
                          const fixed = entries.some((item) => data.constraints.some((constraint) => (
                            String(constraint.section) === String(item.section)
                            && constraint.day === day
                            && String(constraint.period) === String(period.id)
                          )));
                          const color = PERIOD_COLORS[columnIndex % PERIOD_COLORS.length];
                          const subjectColor = entry ? getSubjectColor(entry.subject) : null;
                          const sections = [...new Set(entries.map((item) => item.section_name))];
                          return (
                            <td key={period.id} className={`border border-slate-200 p-1.5 align-top ${color.cell}`}>
                              {entry ? (
                                <div className={`min-h-[72px] rounded-md border-l-4 px-2 py-2 ${subjectColor.card}`}>
                                  {fixed && <span className="mb-1 inline-flex rounded bg-indigo-700 px-1.5 py-0.5 text-[9px] font-extrabold uppercase text-white">Fixed</span>}
                                  <p className={`text-xs font-bold leading-snug sm:text-sm ${subjectColor.name}`}>{entry.subject_name}</p>
                                  <p className={`mt-1 text-[11px] font-medium ${subjectColor.teacher}`}>
                                    {getCombinedGroup(entry)
                                      ? getCombinedClassLabel(entry)
                                      : sections.length > 1 ? `Sections ${sections.join(', ')}` : `Section ${sections[0]}`}
                                  </p>
                                </div>
                              ) : (
                                <div className="flex min-h-[72px] items-center justify-center rounded-md border border-dashed border-slate-200 bg-white/70">
                                  <span className="text-xs text-slate-400">Free</span>
                                </div>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </>
    );
  }

  function renderGeneration() {
    const readiness = generationReadiness?.key === readinessKey ? generationReadiness : null;
    const totalRequired = data.assignments.reduce((sum, item) => sum + item.periods_per_week, 0);
    const weeklyCapacity = data.periods.length * DAYS.length;
    const sectionsWithoutAssignments = data.sections.filter(
      (section) => !data.assignments.some((item) => String(item.section) === String(section.id)),
    );
    const overCapacitySections = data.sections.filter((section) => (
      data.assignments
        .filter((item) => String(item.section) === String(section.id))
        .reduce((sum, item) => sum + item.periods_per_week, 0) > weeklyCapacity
    ));
    const unmappedSubjects = [...new Set(
      data.assignments
        .filter((assignment) => !data.mappings.some(
          (mapping) => String(mapping.subject) === String(assignment.subject),
        ))
        .map((assignment) => assignment.subject_name),
    )];
    const setupReady = (
      data.sections.length > 0
      && data.periods.length > 0
      && data.assignments.length > 0
      && sectionsWithoutAssignments.length === 0
      && overCapacitySections.length === 0
      && unmappedSubjects.length === 0
      && readiness?.ready
    );
    return (
      <>
        <PageHeading eyebrow="Automatic planning" title="Generate timetable" description="Build a complete weekly schedule from your section requirements, teacher mappings, availability, and fixed classes." />
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.65fr)]">
          <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-700 via-indigo-600 to-violet-700 p-6 text-white shadow-lg sm:p-8">
            <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15"><WandSparkles className="h-6 w-6" /></div>
            <h2 className="text-xl font-bold">Ready to plan the school week?</h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-indigo-100">The generator schedules each subject's minimum weekly requirement, then fills every remaining section period with an assigned subject and an available mapped teacher. It avoids teacher conflicts and keeps fixed classes in place.</p>
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ['Sections', data.sections.length],
                ['Requirements', data.assignments.length],
                ['Teachers', data.teachers.length],
                ['Periods to place', totalRequired],
              ].map(([label, count]) => <div key={label} className="rounded-xl bg-white/10 p-3"><p className="text-2xl font-bold">{count}</p><p className="mt-1 text-xs text-indigo-100">{label}</p></div>)}
            </div>
            <p className="mt-5 text-sm text-indigo-100">
              {readiness === null
                ? 'Checking current periods, weekly plans, and teacher availability…'
                : readiness.ready
                  ? `Ready to fill ${readiness.class_count} class slots using ${data.periods.length} configured periods per day.`
                  : 'Resolve the readiness issues shown on the right before generating.'}
            </p>
            <button className="mt-4 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-indigo-700 transition hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-50" onClick={generateTimetable} disabled={busy || !setupReady || readiness === null}>
              {busy ? <RefreshCw className="h-5 w-5 animate-spin" /> : <WandSparkles className="h-5 w-5" />}
              {busy ? 'Building timetable…' : 'Generate timetable'}
            </button>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-bold text-slate-900">Before generating</h2>
            <ul className="mt-4 space-y-3 text-sm text-slate-600">
              {[
                [data.sections.length > 0, 'Create at least one section'],
                [data.subjects.length > 0, 'Add the subjects taught'],
                [data.teachers.length > 0 && data.mappings.length > 0, 'Map teachers to subjects'],
                [data.assignments.length > 0 && sectionsWithoutAssignments.length === 0, 'Set weekly periods for every section'],
                [overCapacitySections.length === 0, `Keep each section within ${weeklyCapacity} weekly periods`],
                [unmappedSubjects.length === 0, 'Map teachers to every assigned subject'],
                [data.periods.length > 0, 'Configure the school periods'],
                [readiness?.ready === true, 'Pass the full timetable generation check'],
              ].map(([complete, label]) => <li key={label} className="flex items-center gap-2"><span className={`flex h-5 w-5 items-center justify-center rounded-full ${complete ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>{complete ? <Check className="h-3.5 w-3.5" /> : <span className="text-xs">·</span>}</span>{label}</li>)}
            </ul>
            <p className="mt-4 rounded-xl bg-indigo-50 p-3 text-xs leading-5 text-indigo-800">
              Every Basic subject is scheduled at least once each weekday, including subjects with a fixed class. Activities are scheduled twice per week on different days; fixed activity slots count toward those two periods.
            </p>
            {readiness?.plan_adjustments?.length > 0 && (
              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <p className="font-semibold">Weekly-plan counts will be adjusted when generation succeeds:</p>
                <ul className="mt-2 list-inside list-disc space-y-1">
                  {readiness.plan_adjustments.map((item) => (
                    <li key={`${item.section}-${item.subject}`}>
                      {item.section} · {item.subject}: {item.from_periods_per_week} → {item.to_periods_per_week} periods/week
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {overCapacitySections.length > 0 && (
              <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-900">
                  Weekly plans exceed the current {weeklyCapacity}-period capacity:
                  {' '}
                  {overCapacitySections.map((section) => section.name).join(', ')}.
                </p>
                <p className="mt-1 text-xs leading-5 text-amber-800">
                  Existing subject requirements are preserved when periods change. Recalculate to evenly redistribute each section across the current week, respecting fixed classes.
                </p>
                <button
                  className={`${buttonClass} mt-3 w-full`}
                  disabled={recalculatingPlans || busy}
                  onClick={recalculateWeeklyPlans}
                >
                  {recalculatingPlans ? 'Recalculating…' : 'Recalculate weekly plans'}
                </button>
              </div>
            )}
            {readiness?.errors?.length > 0 && (
              <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                <p className="font-semibold">Generation check found:</p>
                <ul className="mt-2 list-inside list-disc space-y-1">
                  {readiness.errors.map((error) => <li key={error}>{error}</li>)}
                </ul>
              </div>
            )}
          </div>
        </div>
        {generationErrors.length > 0 && (
          <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
            <div className="mb-2 flex items-center gap-2 font-bold"><AlertTriangle className="h-5 w-5" /> Could not generate a complete schedule</div>
            <ul className="list-inside list-disc space-y-1 text-sm">{generationErrors.map((error) => <li key={error}>{error}</li>)}</ul>
          </div>
        )}
      </>
    );
  }

  function renderContent() {
    switch (page) {
      case 'teacher-timetable': return renderTeacherTimetable();
      case 'sections': return renderSimpleManager('Sections', 'Create the class groups that need their own weekly timetable.', 'sections', 'sections/', 'Section', GraduationCap);
      case 'subjects': return renderSimpleManager('Subjects', 'Maintain the subjects that can be assigned to sections and teachers.', 'subjects', 'subjects/', 'Subject', BookOpen);
      case 'teachers': return renderSimpleManager('Teachers', 'Maintain the teachers who can be mapped to subjects and scheduled.', 'teachers', 'teachers/', 'Teacher', Users);
      case 'mappings': return renderMappings();
      case 'assignments': return renderAssignments();
      case 'periods': return renderPeriods();
      case 'availability': return renderAvailability();
      case 'constraints': return renderConstraints();
      case 'generate': return renderGeneration();
      default: return renderTimetable();
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f7fc] text-slate-800">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/95 shadow-sm backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-200"><CalendarDays className="h-5 w-5" /></div>
              <div><p className="font-bold leading-tight text-slate-900">C.E.R.D NURSERY AND PRIMARY SCHOOL TIMETABLE</p><p className="text-xs text-slate-500">Planning workspace</p></div>
            </div>
            <div className="hidden items-center gap-2 text-xs font-medium text-slate-500 sm:flex"><span className="h-2 w-2 rounded-full bg-indigo-400" /> Monday–Friday <span className="text-slate-300">•</span> 8 periods to start</div>
          </div>
          <nav className="-mx-1 flex gap-1 overflow-x-auto pb-1" aria-label="Timetable sections">
            {ROUTES.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => { setPage(id); setForm({}); setEditingMappingId(null); setEditingConstraintId(null); setPageError(''); setEntryModalOpen(false); }}
                className={`flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold transition sm:text-sm ${page === id ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-indigo-50 hover:text-indigo-700'}`}
              >
                <Icon className="h-4 w-4" />{label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        {pageError && <div role="alert" className="mb-5 flex items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{pageError}</span><button onClick={() => setPageError('')} aria-label="Dismiss error"><X className="h-4 w-4" /></button></div>}
        {renderContent()}
      </main>

      {toast && <div role="status" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-xl"><Check className="h-4 w-4 text-emerald-400" />{toast}</div>}

      {entryModalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/40 p-4" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setEntryModalOpen(false); }}>
          <form className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl sm:p-6" onSubmit={saveEntry}>
            <div className="mb-5 flex items-start justify-between">
              <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">Schedule editor</p><h2 className="mt-1 text-xl font-bold text-slate-900">{editingEntry ? 'Edit class' : 'Add a class'}</h2></div>
              <button type="button" className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" onClick={() => setEntryModalOpen(false)} aria-label="Close editor"><X className="h-5 w-5" /></button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Section"><Select value={entryForm.section || ''} onChange={(event) => setEntryField('section', event.target.value)} options={sectionOptions} placeholder="Select section" /></Field>
              <Field label="Subject"><Select value={entryForm.subject || ''} onChange={(event) => setEntryField('subject', event.target.value)} options={subjectOptions} placeholder="Select subject" /></Field>
              <Field label="Teacher"><Select value={entryForm.teacher || ''} onChange={(event) => setEntryField('teacher', event.target.value)} options={teacherOptions} placeholder="Select teacher" /></Field>
              <Field label="Day"><Select value={entryForm.day || ''} onChange={(event) => setEntryField('day', event.target.value)} options={DAYS.map((day) => ({ value: day, label: day }))} /></Field>
              <Field label="Period" className="sm:col-span-2"><Select value={entryForm.period || ''} onChange={(event) => setEntryField('period', event.target.value)} options={periodOptions} placeholder="Select period" /></Field>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" className={secondaryButtonClass} onClick={() => setEntryModalOpen(false)}>Cancel</button>
              <button className={buttonClass} disabled={busy}><Check className="h-4 w-4" />{editingEntry ? 'Save changes' : 'Add class'}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
