# NarvaConnect

Student schedule & university hub for Narva Kolledž (Tartu Ülikool).

> This is a community project — not affiliated with Tartu Ülikool.

## Features

- Weekly schedule view (mobile-first, swipe navigation)
- Lesson details: subject, time, room, teacher
- Deadline tracking: exams, assignments, projects
- AI assistant: ask questions about schedule in Estonian/Russian/English
- Study hours calculator: EAP credits → remaining self-study time
- Dark/light theme, PWA-ready

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | NestJS, Prisma, PostgreSQL, PM2 (cluster) |
| AI | MLX, Llama 3.1 8B (LoRA fine-tuned on university data) |
| Data | Python, Pandas (schedule parsing), Paramiko (SSH deploy) |
| Deploy | VPS, nginx, PM2, Let's Encrypt |

## Quick Start

```bash
cp .env.example .env
./narvaconnect.sh dev        # Start backend
./narvaconnect.sh front      # Start frontend
./narvaconnect.sh open       # Open in browser
```

## Deploy

```bash
SSH_HOST=root@YOUR_IP ./narvaconnect.sh deploy
SSH_HOST=root@YOUR_IP ./narvaconnect.sh logs
```

## Live

https://narvaconnect.app

## Contributing

Contributions welcome! Fork the repo, create a feature branch, submit a PR.

## Contributors

- Kyrylo Pryiomyshev — [GitHub](https://github.com/Vilis322)

## License

All rights reserved.
