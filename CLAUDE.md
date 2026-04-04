# NarvaConnect — Student Schedule & University Hub

## Overview

Mobile-first web app for Narva Kolledž (Tartu Ülikool) students. Schedule, lessons, deadlines, grades — all in one place. Domain: `narvaconnect.app`.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | NestJS, Prisma, PostgreSQL |
| Data Processing | Python, Pandas (schedule parsing, data import) |
| Deploy | VPS, nginx, Let's Encrypt, PM2 |
| Mobile | Responsive web (mobile-first), PWA (future) |

## Architecture

```
React (:5173)  ->  NestJS (:3000)  ->  PostgreSQL
                        |
                   Pandas scripts (data import)
```

- **React** — mobile-first SPA: schedule view, lesson details, deadlines
- **NestJS** — API: auth, schedule CRUD, notifications
- **Pandas** — offline data processing: parse university schedule (Excel/CSV/HTML) → structured JSON → DB import

## Project Structure

```
narvaconnect/
|-- backend/                NestJS API (TypeScript)
|   |-- src/modules/
|   |   |-- auth/           JWT, student login
|   |   |-- schedule/       timetable, lessons, rooms
|   |   |-- subjects/       courses, teachers
|   |   +-- deadlines/      assignments, exams, dates
|   +-- prisma/             schema, migrations, seeds
|
|-- frontend/               React 18 SPA (TypeScript)
|   +-- src/
|       |-- features/
|       |   |-- auth/       login page
|       |   |-- schedule/   week/day view, lesson cards
|       |   |-- subjects/   course list, details
|       |   +-- deadlines/  upcoming deadlines
|       |-- shared/         components, hooks, layouts
|       +-- i18n/           et/ru/en
|
|-- data/                   Pandas data processing
|   |-- scripts/
|   |   |-- parse_schedule.py   parse university schedule source
|   |   |-- import_db.py        write parsed data to PostgreSQL
|   |   +-- validate.py         data validation
|   |-- raw/                raw schedule files (xlsx, csv, html)
|   +-- processed/          cleaned JSON for import
|
+-- docker-compose.yml      PostgreSQL (dev)
```

## Database Schema (Prisma)

```
subjects         -- id, name, code, credits, teacher, semester
lessons          -- id, subject_id, type (lecture/practice/lab), day_of_week,
                    start_time, end_time, room, teacher, week_type (every/odd/even)
deadlines        -- id, subject_id, title, description, due_date, type (exam/assignment/project)
semesters        -- id, name (e.g. "2026 Spring"), start_date, end_date, is_active
users            -- id, name, email, student_code, language (et/ru/en)
```

## Data Pipeline (Pandas)

```
1. Get schedule source (Narva Kolledž website / ÕIS / manual Excel)
2. parse_schedule.py: read → clean → normalize → structured DataFrame
3. validate.py: check times, rooms, teacher names, conflicts
4. import_db.py: DataFrame → PostgreSQL via SQLAlchemy / Prisma seed
5. NestJS serves via API → React renders
```

Key Pandas operations:
- `pd.read_excel()` / `pd.read_html()` for source parsing
- `pd.to_datetime()` for time normalization
- `groupby(['day_of_week', 'start_time'])` for conflict detection
- `to_json()` for export to DB seed format

## Mobile-First Design

- **Primary view:** Weekly schedule (swipe left/right for weeks)
- **Lesson card:** subject, time, room, teacher — tap for details
- **Bottom nav:** Schedule | Subjects | Deadlines | Profile
- Tailwind breakpoints: `sm:` (mobile default), `md:` (tablet), `lg:` (desktop)
- Touch-friendly: min 44px tap targets, swipe gestures
- Dark/light theme (system preference + toggle)

## i18n

- Estonian (et) — default
- Russian (ru) — for Russian-speaking students
- English (en) — fallback

## Auth

- Simple JWT: student code + password
- Demo mode: pre-filled credentials (like FinCRM pattern)
- No registration — admin seeds users from student list

## Dev Commands

```bash
# Infrastructure
docker compose up -d postgres

# Backend
cd backend && npm run start:dev     # :3000

# Frontend
cd frontend && npm run dev          # :5173

# Data import
cd data && python scripts/parse_schedule.py --input raw/schedule.xlsx --output processed/schedule.json
cd data && python scripts/import_db.py --input processed/schedule.json
```

## CRITICAL: University Rules

- **No AI co-author in commits** — if this is submitted as coursework
- **Student data** — only use own schedule or anonymized data for demo
- **NarvaConnect is a personal project** — not affiliated with Tartu Ülikool

## AI Assistant

- Model: MLX + Llama 3.1 8B, LoRA fine-tuned on university data
- **System prompt includes current date** (`datetime.now()`) — model always knows "today"
- Calculates remaining study hours: `(EAP × 26) - completed_hours`
- Knows weekly schedule → "You have Data Science today at 10:00, room 215"
- Reads deadline proximity → "SE exam is in 5 days"
- Trained on: ÕIS descriptions, Moodle assignments, lecture materials, past notebooks

### Data sources for training
```
university/year3/semester2/{subject}/
├── ois2/          ← course description from ÕIS + weekly schedule
├── moodle/        ← assignments, materials from Moodle
├── code/          ← notebooks, solutions
├── lectures/      ← lecture materials
└── materials/     ← textbooks
```

Feedback/ folders ignored — not useful for training.

## Domain

- **narvaconnect.app** — purchased on Dynadot, will be moved to personal Cloudflare when deploying
- **nginx:** `nginx/narvaconnect.app.conf.example`
- **AI endpoint:** `/ai/` proxied to MLX FastAPI (commented until deployed)

## Deploy

- **Backend:** PM2 cluster mode (1 instance for now)
- **Frontend:** static build served by nginx
- **AI:** MLX on Mac (dev) / proxied endpoint (prod)
- **Port:** 3001
- **DB port:** 5434

## Future

- PWA (offline schedule, push notifications for deadlines)
- ÕIS integration (auto-import grades, if API available)
- Telegram bot (@narvaconnect_bot — schedule for today/tomorrow)
- Calendar export (iCal/Google Calendar)
