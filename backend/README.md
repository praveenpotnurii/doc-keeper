# Doc Keeper Backend

Django REST API for the Document Keeper application.

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run development server:
```bash
python manage.py runserver
```

## Project Structure

- `apps/files/` - File management application
- `apps/authentication/` - User authentication application
- `doc_keeper/` - Main Django project configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variable template

## Development

The project is structured with separate apps for different functionality:
- File operations and revision management
- User authentication and authorization

## API Endpoints

Will be documented as development progresses.

## Testing

Run all tests:
```bash
python manage.py test
```

Run tests for specific app:
```bash
python manage.py test apps.authentication
python manage.py test apps.files
```

Run tests with coverage:
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generates htmlcov/ directory with detailed report
```

Test coverage includes:
- Authentication models, serializers, and API endpoints
- File management models, serializers, and API endpoints
- User permissions and access controls
- File upload, download, and revision management
- API error handling and validation