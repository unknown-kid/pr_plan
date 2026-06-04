# Paper Reader

**English** | [中文](README_zh.md)

An online academic paper reading and management platform with AI-powered features, including RAG-based Q&A, smart translation, reading report generation, and full-text search.

## Features

- **Paper Management** -- Upload, organize, tag, and batch-operate on PDF papers. Supports soft-delete with a 30-day trash bin, folder organization, and citation export (BibTeX, RIS, GB/T 7714).
- **AI-Powered Q&A** -- Ask questions about any paper. The system retrieves relevant chunks via vector search (RAG) and generates answers using configurable LLMs with streaming responses.
- **Reading Reports** -- Generate structured Markdown reports for papers using AI agents (CrewAI). Supports multiple templates (general, CS-specific) and version history.
- **Smart Translation** -- Inline English-to-Chinese translation via DeepL or user-configured LLM models. Supports text selection translation in the PDF viewer.
- **Full-Text Search** -- PostgreSQL-based full-text search with `tsvector` + GIN indexes, result highlighting, search history, and trending queries.
- **User Personalization** -- Per-user favorites, reading progress tracking, and personal notes. Dark mode and responsive layout for desktop/mobile.
- **Flexible Model Configuration** -- Users can configure their own AI models (embedding, chat, translation) with custom API keys and endpoints. Administrators can set up a public model pool.
- **Batch Operations** -- Select multiple papers and batch vectorize, delete, or tag them via async Celery tasks with real-time progress tracking.
bDnz2Npb7qd6K4c3M4v4P4W3zUYSib3CDkk2p5fOa50K0nWF
## Architecture

```
                         ┌─────────┐
                         │  Nginx  │ :80
                         └────┬────┘
                    ┌─────────┴─────────┐
                    │                   │
              /api/*│                   │ /*
                    ▼                   ▼
           ┌──────────────┐    ┌──────────────┐
           │   FastAPI     │    │  React SPA   │
           │   (Backend)   │    │  (Frontend)  │
           │   :8000       │    │  Static Files│
           └──┬──┬──┬──┬──┘    └──────────────┘
              │  │  │  │
     ┌────────┘  │  │  └────────┐
     ▼           ▼  ▼           ▼
┌──────────┐ ┌──────┐ ┌──────────┐ ┌────────────┐
│PostgreSQL│ │Redis │ │  Milvus  │ │   Celery   │
│  (Data)  │ │(Cache│ │ (Vector  │ │  (Async    │
│          │ │+Queue│ │  Search) │ │   Tasks)   │
└──────────┘ └──────┘ └──────────┘ └────────────┘
```

| Component | Technology | Role |
|---|---|---|
| Backend API | FastAPI + Uvicorn | REST API, JWT auth, streaming responses |
| Frontend | React 18 + TypeScript + Ant Design | SPA with PDF viewer, Markdown/LaTeX rendering |
| Database | PostgreSQL 15 | Relational data, full-text search (tsvector + GIN) |
| Vector Store | Milvus / Milvus Lite | Paper chunk embeddings for RAG retrieval |
| Cache & Queue | Redis 7 | Response caching, rate limiting, Celery broker |
| Task Worker | Celery | Async vectorization, report generation, batch ops |
| Reverse Proxy | Nginx | Request routing, gzip, upload size limits, streaming |
| AI Agents | CrewAI | Multi-agent report generation |

## Project Structure

```
paper-reader/
├── backend/                          # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                   # Application entry point
│   │   ├── config.py                 # Pydantic settings
│   │   ├── api/                      # Route handlers (13 modules)
│   │   │   ├── auth.py               #   Authentication (register, login, JWT)
│   │   │   ├── papers.py             #   Paper CRUD, upload, trash, export
│   │   │   ├── conversations.py      #   AI chat with streaming (RAG)
│   │   │   ├── reports.py            #   Reading report generation
│   │   │   ├── search.py             #   Full-text search
│   │   │   ├── ai_models.py          #   Model configuration
│   │   │   ├── batch_operations.py   #   Batch vectorize/delete/tag
│   │   │   ├── users.py              #   Favorites, progress, notes
│   │   │   ├── translate.py          #   Text translation
│   │   │   ├── folders.py            #   Folder organization
│   │   │   ├── admin.py              #   Admin operations
│   │   │   ├── health.py             #   Health check endpoints
│   │   │   └── deps.py               #   Shared dependencies
│   │   ├── models/                   # SQLAlchemy ORM models (14 models)
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── services/                 # Business logic (13 services)
│   │   │   ├── rag_service.py        #   RAG retrieval + answer generation
│   │   │   ├── milvus_service.py     #   Vector store operations
│   │   │   ├── embedding_service.py  #   Text embedding
│   │   │   ├── model_resolver.py     #   AI model selection (user > public > default)
│   │   │   ├── search_service.py     #   PostgreSQL full-text search
│   │   │   ├── cache_service.py      #   Redis caching
│   │   │   └── ...
│   │   ├── tasks/                    # Celery async tasks
│   │   │   ├── celery_app.py         #   Celery config + scheduled tasks
│   │   │   ├── vectorization_tasks.py
│   │   │   ├── paper_tasks.py
│   │   │   └── report_tasks.py
│   │   ├── core/                     # Framework-level utilities
│   │   │   ├── database.py           #   SQLAlchemy engine + session
│   │   │   ├── security.py           #   JWT + password hashing
│   │   │   ├── exceptions.py         #   Global exception handlers
│   │   │   └── knowledge_base/       #   Vector store abstraction layer
│   │   │       ├── base.py           #     Abstract interfaces
│   │   │       ├── factory.py        #     Factory pattern
│   │   │       └── milvus_adapter.py #     Milvus implementation
│   │   ├── agents/                   # CrewAI agents
│   │   │   └── paper_report_agent.py #   AI report generation agent
│   │   └── utils/
│   │       └── pdf_parser.py         #   Streaming PDF text extraction
│   ├── alembic/                      # Database migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                         # React TypeScript frontend
│   ├── src/
│   │   ├── pages/                    # Page components
│   │   │   ├── Home.tsx              #   Paper list dashboard
│   │   │   ├── PaperDetail.tsx       #   PDF viewer + AI chat + notes
│   │   │   ├── SearchPage.tsx        #   Full-text search
│   │   │   ├── ModelConfig.tsx       #   AI model configuration
│   │   │   ├── UserProfile.tsx       #   User settings + favorites
│   │   │   └── Login.tsx             #   Authentication
│   │   ├── components/
│   │   │   ├── chat/                 #   Chat history component
│   │   │   ├── common/               #   MarkdownRenderer, PDFViewer, SelectionTranslator
│   │   │   └── paper/                #   ReportViewer
│   │   ├── services/
│   │   │   ├── api.ts                #   Axios instance with auth interceptor
│   │   │   └── paperService.ts       #   Paper API client
│   │   └── store/
│   │       └── userStore.ts          #   Zustand state (auth, theme)
│   ├── package.json
│   ├── nginx.conf                    # SPA routing config
│   └── Dockerfile
├── nginx/
│   └── nginx.conf                    # Reverse proxy configuration
├── config/
│   └── knowledge_base.yaml           # Vector store + embedding config
├── scripts/
│   ├── deploy.sh                     # Docker deployment script
│   ├── deploy-native.sh              # Native deployment script (no Docker)
│   └── backup.sh                     # Database backup script
├── docker-compose.yml
├── .env.example
└── .github/
    └── workflows/
        └── main.yml                  # CI/CD pipeline
```

## Prerequisites

- **Python** >= 3.10 (3.12 recommended)
- **Node.js** >= 18
- **PostgreSQL** >= 15
- **Redis** >= 7
- **Milvus** >= 2.3 (or Milvus Lite for lightweight deployment)

## Deployment

### Option 1: Docker Compose (Recommended)

This is the simplest way to deploy. All services (PostgreSQL, Redis, Milvus, Backend, Celery, Frontend, Nginx) run as containers.

**Prerequisites:** Docker and Docker Compose installed.

1. Clone the repository:

```bash
git clone https://github.com/unknown-kid/paper-reader.git
cd paper-reader
```

2. Configure environment variables:

```bash
cp .env.example .env
# Edit .env to set your passwords and secrets:
#   DB_PASSWORD     - PostgreSQL password
#   SECRET_KEY      - JWT signing key (change in production!)
```

3. Deploy with one command:

```bash
bash scripts/deploy.sh
```

This will:
- Build and start all 9 containers (postgres, redis, etcd, minio, milvus, backend, celery, frontend, nginx)
- Wait for the database to be healthy
- Run Alembic migrations
- Report service status

4. Access the application at **http://localhost**

**Manual control:**

```bash
# Start
docker-compose up -d --build

# Stop
docker-compose down

# View logs
docker-compose logs -f backend

# Run migrations manually
docker-compose exec -T backend alembic upgrade head

# Restart a single service
docker-compose restart backend
```

### Option 2: Native Deployment (No Docker)

For environments where Docker is unavailable or you prefer running services natively. Supports **macOS** (Homebrew) and **Linux** (apt/dnf).

Uses **Milvus Lite** (a pure-Python embedded Milvus engine) instead of the full Milvus stack, so no Docker is needed at all.

1. Clone the repository:

```bash
git clone https://github.com/unknown-kid/paper-reader.git
cd paper-reader
```

2. Configure environment variables:

```bash
cp .env.example .env
# Edit .env as needed
```

3. Full one-click deployment:

```bash
bash scripts/deploy-native.sh
```

This will:
- Detect your OS (macOS / Debian / RHEL)
- Install PostgreSQL 15, Redis, Node.js 18, Nginx, and Python 3.12 via the system package manager
- Create a Python virtual environment and install all backend dependencies
- Install Milvus Lite (`pip install milvus-lite`) as the vector database
- Build the React frontend (`npm run build`)
- Configure and start Nginx as a reverse proxy
- Create the database, run migrations
- Start all services (PostgreSQL, Redis, Milvus Lite, Backend, Celery, Nginx)

4. Access the application at **http://localhost**

**Service management:**

```bash
# Start all services
bash scripts/deploy-native.sh start

# Stop all services
bash scripts/deploy-native.sh stop

# Check status
bash scripts/deploy-native.sh status

# Restart
bash scripts/deploy-native.sh restart

# View logs
bash scripts/deploy-native.sh logs

# Install dependencies only (no start)
bash scripts/deploy-native.sh install
```

**Logs and data directories:**

| Directory | Purpose |
|---|---|
| `logs/` | All service logs (backend, celery, milvus, nginx) |
| `pids/` | PID files for process management |
| `data/` | Milvus Lite database files |
| `uploads/` | Uploaded PDF files |
| `backups/` | Database backup files |

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DB_PASSWORD` | PostgreSQL password | `password123` |
| `SECRET_KEY` | JWT signing secret | `your_super_secret_jwt_key_change_me` |
| `MINIO_ACCESS_KEY` | MinIO access key (Docker only) | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key (Docker only) | `minioadmin` |
| `HTTP_PROXY` | HTTP proxy for external API calls | _(none)_ |
| `HTTPS_PROXY` | HTTPS proxy for external API calls | _(none)_ |

### AI Model Configuration

After deployment, log in and navigate to the **Model Config** page to configure:

- **Embedding Model** -- For vectorizing paper text (e.g., OpenAI `text-embedding-ada-002`)
- **Chat Model** -- For AI Q&A conversations (e.g., GPT-4, Claude)
- **Translation Model** -- For text translation (or use DeepL API)

Each user can configure their own models with personal API keys. Administrators can also set up **public models** available to all users.

**Model resolution priority:** User-specified model > User's default model > Public model > System default.

## API Overview

The backend exposes a RESTful API at `/api/`. Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc` when the backend is running.

| Endpoint Group | Prefix | Description |
|---|---|---|
| Auth | `/api/auth` | Register, login, profile |
| Papers | `/api/papers` | CRUD, upload, trash, export citations |
| Conversations | `/api/conversations` | AI chat sessions (streaming) |
| Reports | `/api/reports` | Reading report generation |
| Search | `/api/search` | Full-text search, history, trending |
| Models | `/api/models` | AI model configuration |
| Batch | `/api/batch` | Batch operations |
| Users | `/api/users` | Favorites, progress, notes |
| Translate | `/api/translate` | Text translation |
| Folders | `/api/folders` | Folder management |
| Admin | `/api/admin` | Admin operations (public models, tags) |
| Health | `/api/health` | Service health checks |

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| FastAPI | Web framework |
| SQLAlchemy 2.0 | ORM |
| Alembic | Database migrations |
| PostgreSQL 15 | Primary database + full-text search |
| Redis 7 | Caching + Celery broker |
| Celery | Async task queue |
| Milvus / Milvus Lite | Vector database |
| pymilvus | Milvus Python client |
| OpenAI SDK | LLM + embedding API |
| CrewAI | AI agent framework (report generation) |
| PyPDF2 + pdfplumber | PDF text extraction |
| Pydantic v2 | Data validation |
| python-jose | JWT authentication |

### Frontend

| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| TypeScript | Type safety |
| Ant Design | UI component library |
| Zustand | State management |
| React Router v6 | Client-side routing |
| react-pdf | PDF viewer |
| react-markdown + remark-gfm | Markdown rendering |
| remark-math + rehype-katex | LaTeX formula rendering |
| Mermaid | Diagram rendering |
| react-window | Virtual list (performance) |
| Axios | HTTP client |

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://paperuser:password123@localhost:5432/paper_reader"
export REDIS_URL="redis://localhost:6379/0"
export MILVUS_HOST="localhost"
export MILVUS_PORT="19530"

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm start
# Dev server runs at http://localhost:3000, proxying /api to :8000
```

### Running Tests

```bash
cd backend
pytest
```

## Database Backup

A backup script is included for PostgreSQL data:

```bash
bash scripts/backup.sh
# Backups are saved to the backups/ directory
```

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) -- High-performance Python web framework
- [Milvus](https://milvus.io/) -- Open-source vector database
- [CrewAI](https://www.crewai.com/) -- Multi-agent AI framework
- [Ant Design](https://ant.design/) -- React UI component library
- [react-pdf](https://github.com/wojtekmaj/react-pdf) -- PDF rendering for React
