# Doc Keeper - Build and Run Documentation

This document provides comprehensive instructions for building and running the Doc Keeper application, which consists of a Django REST API backend and a React TypeScript frontend.

## Project Structure

```
doc-keeper/
├── backend/          # Django REST API
├── frontend/         # React TypeScript application
├── docker-compose.yml # Docker orchestration
└── Document.md       # This documentation
```

## Prerequisites

### For Local Development
- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **Git**

### For Docker Deployment
- **Docker** and **Docker Compose**

## Backend (Django REST API)

### Local Development Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Collect static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

7. **Start development server:**
   ```bash
   python manage.py runserver
   ```

The backend will be available at: `http://localhost:8000`

### Backend Testing

Run tests with:
```bash
python manage.py test
```

## Frontend (React TypeScript)

### Local Development Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm start
   ```

The frontend will be available at: `http://localhost:3000`

### Frontend Build for Production

1. **Create production build:**
   ```bash
   npm run build
   ```

2. **Run tests:**
   ```bash
   npm test
   ```

The production build will be created in the `build/` directory.

## Docker Deployment

### Quick Start with Docker Compose

1. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

2. **Run in detached mode:**
   ```bash
   docker-compose up -d --build
   ```

3. **Stop services:**
   ```bash
   docker-compose down
   ```

### Service Access
- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`

### Docker Individual Services

#### Backend Only
```bash
cd backend
docker build -t doc-keeper-backend .
docker run -p 8000:8000 doc-keeper-backend
```

#### Frontend Only
```bash
cd frontend
docker build -t doc-keeper-frontend .
docker run -p 3000:80 doc-keeper-frontend
```

## Environment Configuration

### Backend Environment Variables
- `DEBUG`: Set to `1` for development, `0` for production
- `DJANGO_SETTINGS_MODULE`: `doc_keeper.settings`
- Database settings (when using PostgreSQL in production)

### Frontend Environment Variables
- `REACT_APP_API_URL`: Backend API URL (for production builds)

## Development Workflow

### Starting Development Environment
1. **Start backend:**
   ```bash
   cd backend
   source venv/bin/activate
   python manage.py runserver
   ```

2. **Start frontend (in new terminal):**
   ```bash
   cd frontend
   npm start
   ```

### Production Deployment
Use Docker Compose for production deployment:
```bash
docker-compose -f docker-compose.yml up -d --build
```

## Key Dependencies

### Backend
- Django 5.2.0+
- Django REST Framework 3.16.0+
- Django CORS Headers 4.8.0+
- Django REST Framework SimpleJWT 5.5.0+
- Pillow 9.5.0+ (for file handling)

### Frontend
- React 19.1.1
- TypeScript 4.9.5
- React Router DOM 6.30.1
- Axios 1.12.2 (for API calls)
- Tailwind CSS 3.4.16 (for styling)
- Radix UI components

## Ports

- **Backend:** `8000`
- **Frontend Development:** `3000`
- **Frontend Production (Docker):** `80` (mapped to `3000`)

## File Storage

The application stores uploaded files in the `backend/media/uploads/` directory, organized by user and file ID.

## Troubleshooting

### Common Issues

1. **Port conflicts:** Ensure ports 3000 and 8000 are available
2. **Virtual environment:** Always activate the Python virtual environment before running backend commands
3. **Dependencies:** Run `pip install -r requirements.txt` and `npm install` if you encounter missing dependency errors
4. **Database:** Run `python manage.py migrate` if you encounter database-related errors

### Docker Issues

1. **Build failures:** Run `docker-compose down` and `docker-compose up --build` to rebuild
2. **Volume issues:** Use `docker-compose down -v` to remove volumes if needed
3. **Network issues:** Ensure Docker daemon is running and ports are not in use

## Additional Commands

### Backend Management Commands
- `python manage.py makemigrations` - Create new migrations
- `python manage.py migrate` - Apply migrations
- `python manage.py collectstatic` - Collect static files
- `python manage.py createsuperuser` - Create admin user

### Frontend Scripts
- `npm start` - Start development server
- `npm run build` - Create production build
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App (not recommended)