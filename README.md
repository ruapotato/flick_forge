# Flick Forge - Flick Store Backend

The official app store backend for [Flick](https://github.com/ruapotato/Flick), the Qt/QML-based mobile shell for Linux.

## Overview

Flick Forge powers the Flick Store at [255.one](https://255.one), providing:

- **App Repository** - Browse and download Qt/QML apps built for Flick
- **User System** - Multi-tier accounts (anonymous, limited, promoted, admin)
- **App Requests** - Community-driven app creation with AI assistance
- **Wild West** - Testing area for AI-generated and experimental apps
- **Reviews & Ratings** - Community feedback system

## Features

### For Users
- Browse and search Flick apps by category
- Download `.flick` packages (QML apps with dependencies)
- Leave reviews and ratings
- Request new apps via AI-powered generation
- Test experimental apps in the Wild West section

### For Developers
- Submit apps for inclusion in the store
- RESTful API for integration with Flick shell
- Package format documentation at `/store/PACKAGE_FORMAT.md`

### Multi-Tier User System
| Tier | Capabilities |
|------|-------------|
| Anonymous | Browse and install apps |
| Limited | Submit app requests/prompts |
| Promoted | Approve requests, manage feedback |
| Admin | Full system access |

## Technology Stack

- **Backend**: Python/Flask with SQLAlchemy
- **Frontend**: Vanilla JavaScript with dynamic API loading
- **Database**: SQLite (development) / PostgreSQL (production)
- **UI Framework**: Qt/QML (all apps are Qt-based)

## Quick Start

### Requirements
- Python 3.10+
- pip

### Installation

```bash
cd flick_forge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure-password
```

### Database Setup

Initialize and seed the database:
```bash
python seed_data.py
```

This creates all Flick apps from the main repository.

### Running

Development:
```bash
python app.py
```

Production:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/apps` | List apps with pagination |
| `GET /api/apps/categories` | List categories with counts |
| `GET /api/apps/search?q=` | Search apps |
| `GET /api/apps/<slug>` | Get app details |
| `GET /api/apps/<slug>/download` | Download app package |
| `GET /api/apps/wild-west` | List experimental apps |
| `POST /api/requests` | Submit app request (limited+) |
| `GET /api` | API info |
| `GET /api/docs` | Full API documentation |

## Flick Package Format

Apps are distributed as `.flick` packages (ZIP archives) containing:

```
myapp.flick
├── manifest.json      # Metadata and dependencies
├── app/
│   ├── main.qml       # Entry point
│   └── *.qml          # Additional QML files
├── icon.png           # App icon (256x256)
└── screenshots/       # Store screenshots
```

See `../store/PACKAGE_FORMAT.md` for full specification.

## Deployment

Deploy to production server:
```bash
./deploy.sh
```

Or manually:
```bash
git push origin main
ssh user@255.one "cd /path/to/flick_forge && git pull && sudo systemctl restart flick-forge"
```

## Project Structure

```
flick_forge/
├── app.py              # Flask application factory
├── models.py           # SQLAlchemy models
├── config.py           # Configuration
├── seed_data.py        # Database seeding
├── routes/
│   ├── apps.py         # App endpoints
│   ├── auth.py         # Authentication
│   ├── reviews.py      # Reviews
│   ├── requests.py     # App requests
│   ├── feedback.py     # Feedback/bugs
│   └── admin.py        # Admin endpoints
├── templates/          # HTML templates
├── static/
│   ├── css/            # Stylesheets
│   └── js/             # JavaScript (API client)
└── utils/
    ├── ai_safety.py    # AI safety checks
    └── claude_code.py  # AI code generation
```

## License

AGPL-3.0 - All apps in the Flick Store must also be AGPL-3.0 licensed.

## Links

- [Flick Mobile Shell](https://github.com/ruapotato/Flick)
- [Live Store](https://255.one)
