# Doc Keeper

A web application for secure file storage and retrieval with user authentication and revision management.

## Screenshots

### Authentication
| Login Screen | Registration Screen |
|:---:|:---:|
| ![Login](<Screenshot 2025-09-17 at 7.57.09 PM.png>) | ![Register](<Screenshot 2025-09-17 at 7.57.18 PM.png>) |

### Dashboard Views
| Light Theme - Empty State | Light Theme - With Files |
|:---:|:---:|
| ![Dashboard Empty](<Screenshot 2025-09-17 at 7.58.29 PM.png>) | ![Dashboard With Files](<Screenshot 2025-09-17 at 7.59.21 PM.png>) |

### File Management
| File Upload | Revision History |
|:---:|:---:|
| ![File Upload](<Screenshot 2025-09-17 at 7.59.07 PM.png>) | ![Revision History](<Screenshot 2025-09-17 at 8.00.02 PM.png>) |

### Dark Theme
![Dark Theme Dashboard](<Screenshot 2025-09-17 at 8.00.31 PM.png>)

## Features

- **User Authentication**: JWT-based authentication with registration and login
- **File Management**: Upload, download, and manage files with version control
- **File Revisions**: Track and access different versions of files
- **User Isolation**: Each user can only access their own files
- **Secure Storage**: Files are stored securely with proper access controls
- **Modern UI**: Clean, responsive interface built with React and Tailwind CSS

## Technology Stack

### Backend
- **Django 5.2+**: Web framework
- **Django REST Framework**: API development
- **JWT Authentication**: Simple JWT for token-based auth
- **SQLite**: Database (development)
- **Python 3.x**: Programming language

### Frontend  
- **React 19+**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Axios**: HTTP client
- **React Router**: Navigation

## Project Structure

```
doc-keeper/
├── backend/                 # Django REST API
│   ├── apps/
│   │   ├── authentication/ # User auth and JWT
│   │   └── files/          # File management
│   ├── doc_keeper/         # Django settings
│   ├── media/              # File storage
│   └── manage.py
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── contexts/       # React contexts
│   │   ├── lib/           # Utilities
│   │   └── services/      # API services
│   └── public/
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser (optional):
```bash
python manage.py createsuperuser
```

6. Start development server:
```bash
python manage.py runserver
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/profile/` - Get user profile

### Files
- `GET /api/files/` - List user's files
- `POST /api/files/upload/` - Upload new file
- `GET /api/files/{path}/` - Download file
- `POST /api/files/{path}/upload/` - Upload new version
- `GET /api/files/{path}/revisions/` - Get file revisions
- `GET /api/files/{path}/?revision={n}` - Download specific revision

## Testing

### Backend Tests
Run comprehensive backend tests:
```bash
cd backend
python manage.py test
```

Coverage includes:
- Authentication models, serializers, and API endpoints
- File management models, serializers, and API endpoints  
- JWT token handling and permissions
- File upload, download, and revision management

### Frontend Tests
Run frontend tests:
```bash
cd frontend
npm test
```

Tests include:
- Component import verification
- Utility function testing
- Basic JavaScript functionality

## Environment Variables

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

## File Storage

Files are stored in `backend/media/uploads/` organized by:
- User ID subdirectories
- File ID subdirectories  
- Revision numbering system

Example: `media/uploads/user_1/file_5/0_document.pdf`

## Security Features

- JWT-based authentication
- User isolation (users can only access their own files)
- Secure file storage with access controls
- Input validation and sanitization
- CORS configuration for frontend integration

## Development

### Code Style
- Backend: Follow Django best practices
- Frontend: TypeScript with React best practices
- Testing: Comprehensive unit test coverage

### Adding New Features
1. Create backend API endpoints in Django
2. Add corresponding frontend services and components
3. Write unit tests for both backend and frontend
4. Update documentation

## License

This project is for educational/development purposes.