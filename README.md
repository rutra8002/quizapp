# QuizApp

An AI-powered quiz application built with Flask and Google Gemini API for intelligent quiz grading.

**Live:** http://quiz.rutra.me

## Features

- Create and manage custom quizzes
- AI-powered quiz grading using Google Gemini
- User authentication and session management
- SQLite database for persistence

## Requirements

- Docker
- Google Gemini API key

## Deployment

```bash
docker-compose up
```

Or pull from Docker Hub:
```
docker run -p 5000:5000 \
  -e GEMINI_API_KEY=your_api_key \
  -e SECRET_KEY=your_secret_key \
  ghcr.io/rutra8002/quizapp:master
```
 Configuration
Set environment variables in .env:
```
GEMINI_API_KEY=your_api_key
SECRET_KEY=your_secret_key
```
## Stack
- Backend: Flask
- Database: SQLAlchemy + SQLite
- AI: Google Gemini 2.5 Flash
- Deployment: Docker