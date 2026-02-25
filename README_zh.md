# Paper Reader

[English](README.md) | **中文**

一个在线学术论文阅读与管理平台，支持 AI 辅助阅读，包括基于 RAG 的智能问答、智能翻译、阅读报告生成和全文搜索等功能。

## 功能特性

- **论文管理** -- 上传、整理、标签分类和批量操作 PDF 论文。支持软删除（30 天回收站）、文件夹管理、引用导出（BibTeX、RIS、GB/T 7714）。
- **AI 智能问答** -- 针对任意论文进行提问。系统通过向量搜索（RAG）检索相关文本片段，使用可配置的大语言模型生成流式回答。
- **阅读报告** -- 使用 AI 智能体（CrewAI）为论文生成结构化 Markdown 报告。支持多种模板（通用模板、计算机科学模板）和版本历史。
- **智能翻译** -- 通过 DeepL 或用户自配置的模型实现英文到中文的行内翻译。支持 PDF 阅读器中的划词翻译。
- **全文搜索** -- 基于 PostgreSQL 的全文搜索，使用 `tsvector` + GIN 索引，支持结果高亮、搜索历史和热门搜索词。
- **用户个性化** -- 个人收藏、阅读进度追踪和笔记功能。支持深色模式和多端响应式布局。
- **灵活的模型配置** -- 用户可配置自己的 AI 模型（嵌入模型、对话模型、翻译模型），自定义 API Key 和端点。管理员可配置公共模型池供所有用户使用。
- **批量操作** -- 选择多篇论文批量向量化、删除或打标签，通过 Celery 异步任务执行，支持实时进度追踪。

## 系统架构

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
           │   (后端)      │    │  (前端)       │
           │   :8000       │    │  静态文件     │
           └──┬──┬──┬──┬──┘    └──────────────┘
              │  │  │  │
     ┌────────┘  │  │  └────────┐
     ▼           ▼  ▼           ▼
┌──────────┐ ┌──────┐ ┌──────────┐ ┌────────────┐
│PostgreSQL│ │Redis │ │  Milvus  │ │   Celery   │
│ (数据库) │ │(缓存 │ │ (向量    │ │  (异步     │
│          │ │+队列)│ │  搜索)   │ │   任务)    │
└──────────┘ └──────┘ └──────────┘ └────────────┘
```

| 组件 | 技术 | 职责 |
|---|---|---|
| 后端 API | FastAPI + Uvicorn | REST API、JWT 认证、流式响应 |
| 前端 | React 18 + TypeScript + Ant Design | 单页应用，PDF 阅读器，Markdown/LaTeX 渲染 |
| 数据库 | PostgreSQL 15 | 关系型数据、全文搜索（tsvector + GIN） |
| 向量数据库 | Milvus / Milvus Lite | 论文文本块嵌入，用于 RAG 检索 |
| 缓存与队列 | Redis 7 | 响应缓存、接口限流、Celery 消息代理 |
| 任务调度 | Celery | 异步向量化、报告生成、批量操作 |
| 反向代理 | Nginx | 请求路由、gzip 压缩、上传限制、流式传输 |
| AI 智能体 | CrewAI | 多智能体协作生成报告 |

## 项目结构

```
paper-reader/
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py                   # 应用入口
│   │   ├── config.py                 # Pydantic 配置
│   │   ├── api/                      # 路由处理器（13 个模块）
│   │   │   ├── auth.py               #   认证（注册、登录、JWT）
│   │   │   ├── papers.py             #   论文 CRUD、上传、回收站、导出
│   │   │   ├── conversations.py      #   AI 对话 + 流式响应（RAG）
│   │   │   ├── reports.py            #   阅读报告生成
│   │   │   ├── search.py             #   全文搜索
│   │   │   ├── ai_models.py          #   模型配置
│   │   │   ├── batch_operations.py   #   批量向量化/删除/打标签
│   │   │   ├── users.py              #   收藏、进度、笔记
│   │   │   ├── translate.py          #   文本翻译
│   │   │   ├── folders.py            #   文件夹管理
│   │   │   ├── admin.py              #   管理员操作
│   │   │   ├── health.py             #   健康检查端点
│   │   │   └── deps.py               #   公共依赖
│   │   ├── models/                   # SQLAlchemy ORM 模型（14 个）
│   │   ├── schemas/                  # Pydantic 请求/响应模式
│   │   ├── services/                 # 业务逻辑（13 个服务）
│   │   │   ├── rag_service.py        #   RAG 检索 + 答案生成
│   │   │   ├── milvus_service.py     #   向量存储操作
│   │   │   ├── embedding_service.py  #   文本嵌入
│   │   │   ├── model_resolver.py     #   AI 模型选择（用户 > 公共 > 默认）
│   │   │   ├── search_service.py     #   PostgreSQL 全文搜索
│   │   │   ├── cache_service.py      #   Redis 缓存
│   │   │   └── ...
│   │   ├── tasks/                    # Celery 异步任务
│   │   │   ├── celery_app.py         #   Celery 配置 + 定时任务
│   │   │   ├── vectorization_tasks.py
│   │   │   ├── paper_tasks.py
│   │   │   └── report_tasks.py
│   │   ├── core/                     # 框架级工具
│   │   │   ├── database.py           #   SQLAlchemy 引擎 + 会话
│   │   │   ├── security.py           #   JWT + 密码哈希
│   │   │   ├── exceptions.py         #   全局异常处理
│   │   │   └── knowledge_base/       #   向量存储抽象层
│   │   │       ├── base.py           #     抽象接口
│   │   │       ├── factory.py        #     工厂模式
│   │   │       └── milvus_adapter.py #     Milvus 实现
│   │   ├── agents/                   # CrewAI 智能体
│   │   │   └── paper_report_agent.py #   AI 报告生成智能体
│   │   └── utils/
│   │       └── pdf_parser.py         #   流式 PDF 文本提取
│   ├── alembic/                      # 数据库迁移
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                         # React TypeScript 前端
│   ├── src/
│   │   ├── pages/                    # 页面组件
│   │   │   ├── Home.tsx              #   论文列表主页
│   │   │   ├── PaperDetail.tsx       #   PDF 阅读 + AI 对话 + 笔记
│   │   │   ├── SearchPage.tsx        #   全文搜索
│   │   │   ├── ModelConfig.tsx       #   AI 模型配置
│   │   │   ├── UserProfile.tsx       #   用户设置 + 收藏
│   │   │   └── Login.tsx             #   登录注册
│   │   ├── components/
│   │   │   ├── chat/                 #   对话历史组件
│   │   │   ├── common/               #   Markdown 渲染器、PDF 阅读器、划词翻译
│   │   │   └── paper/                #   报告查看器
│   │   ├── services/
│   │   │   ├── api.ts                #   Axios 实例（含认证拦截器）
│   │   │   └── paperService.ts       #   论文 API 客户端
│   │   └── store/
│   │       └── userStore.ts          #   Zustand 状态管理（认证、主题）
│   ├── package.json
│   ├── nginx.conf                    # SPA 路由配置
│   └── Dockerfile
├── nginx/
│   └── nginx.conf                    # 反向代理配置
├── config/
│   └── knowledge_base.yaml           # 向量存储 + 嵌入模型配置
├── scripts/
│   ├── deploy.sh                     # Docker 部署脚本
│   ├── deploy-native.sh              # 原生部署脚本（无需 Docker）
│   └── backup.sh                     # 数据库备份脚本
├── docker-compose.yml
├── .env.example
└── .github/
    └── workflows/
        └── main.yml                  # CI/CD 流水线
```

## 环境要求

- **Python** >= 3.10（推荐 3.12）
- **Node.js** >= 18
- **PostgreSQL** >= 15
- **Redis** >= 7
- **Milvus** >= 2.3（或使用 Milvus Lite 轻量部署）

## 部署

### 方式一：Docker Compose 部署（推荐）

最简单的部署方式。所有服务（PostgreSQL、Redis、Milvus、后端、Celery、前端、Nginx）均以容器运行。

**前置条件：** 已安装 Docker 和 Docker Compose。

1. 克隆仓库：

```bash
git clone https://github.com/your-username/paper-reader.git
cd paper-reader
```

2. 配置环境变量：

```bash
cp .env.example .env
# 编辑 .env 文件，设置密码和密钥：
#   DB_PASSWORD     - PostgreSQL 密码
#   SECRET_KEY      - JWT 签名密钥（生产环境务必修改！）
```

3. 一键部署：

```bash
bash scripts/deploy.sh
```

脚本将自动完成：
- 构建并启动全部 9 个容器（postgres、redis、etcd、minio、milvus、backend、celery、frontend、nginx）
- 等待数据库就绪
- 执行 Alembic 数据库迁移
- 输出服务状态报告

4. 访问 **http://localhost** 即可使用

**手动控制：**

```bash
# 启动
docker-compose up -d --build

# 停止
docker-compose down

# 查看日志
docker-compose logs -f backend

# 手动执行迁移
docker-compose exec -T backend alembic upgrade head

# 重启单个服务
docker-compose restart backend
```

### 方式二：原生部署（无需 Docker）

适用于无法使用 Docker 的环境或偏好原生运行服务的场景。支持 **macOS**（Homebrew）和 **Linux**（apt/dnf）。

使用 **Milvus Lite**（纯 Python 嵌入式 Milvus 引擎）替代完整的 Milvus 服务栈，完全无需 Docker。

1. 克隆仓库：

```bash
git clone https://github.com/your-username/paper-reader.git
cd paper-reader
```

2. 配置环境变量：

```bash
cp .env.example .env
# 按需编辑
```

3. 一键完整部署：

```bash
bash scripts/deploy-native.sh
```

脚本将自动完成：
- 检测操作系统（macOS / Debian / RHEL）
- 通过系统包管理器安装 PostgreSQL 15、Redis、Node.js 18、Nginx、Python 3.12
- 创建 Python 虚拟环境并安装全部后端依赖
- 安装 Milvus Lite（`pip install milvus-lite`）作为向量数据库
- 构建 React 前端（`npm run build`）
- 配置并启动 Nginx 反向代理
- 创建数据库、执行迁移
- 启动全部服务（PostgreSQL、Redis、Milvus Lite、后端、Celery、Nginx）

4. 访问 **http://localhost** 即可使用

**服务管理命令：**

```bash
# 启动所有服务
bash scripts/deploy-native.sh start

# 停止所有服务
bash scripts/deploy-native.sh stop

# 查看服务状态
bash scripts/deploy-native.sh status

# 重启所有服务
bash scripts/deploy-native.sh restart

# 查看日志
bash scripts/deploy-native.sh logs

# 仅安装依赖（不启动）
bash scripts/deploy-native.sh install
```

**目录说明：**

| 目录 | 用途 |
|---|---|
| `logs/` | 所有服务日志（后端、Celery、Milvus、Nginx） |
| `pids/` | PID 文件，用于进程管理 |
| `data/` | Milvus Lite 数据文件 |
| `uploads/` | 上传的 PDF 文件 |
| `backups/` | 数据库备份文件 |

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|---|---|---|
| `DB_PASSWORD` | PostgreSQL 密码 | `password123` |
| `SECRET_KEY` | JWT 签名密钥 | `your_super_secret_jwt_key_change_me` |
| `MINIO_ACCESS_KEY` | MinIO 访问密钥（仅 Docker 部署） | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO 秘密密钥（仅 Docker 部署） | `minioadmin` |
| `HTTP_PROXY` | 访问外部 API 的 HTTP 代理 | _(无)_ |
| `HTTPS_PROXY` | 访问外部 API 的 HTTPS 代理 | _(无)_ |

### AI 模型配置

部署完成后，登录系统并进入**模型配置**页面进行设置：

- **嵌入模型** -- 用于论文文本向量化（如 OpenAI `text-embedding-ada-002`）
- **对话模型** -- 用于 AI 问答（如 GPT-4、Claude）
- **翻译模型** -- 用于文本翻译（或使用 DeepL API）

每个用户可以使用自己的 API Key 配置私有模型。管理员还可以设置**公共模型池**供所有用户使用。

**模型选择优先级：** 用户指定模型 > 用户默认模型 > 公共模型 > 系统默认模型。

## API 概览

后端在 `/api/` 路径下提供 RESTful API。服务运行时可通过 `/docs`（Swagger UI）和 `/redoc` 查看完整的交互式 API 文档。

| 接口分组 | 路径前缀 | 说明 |
|---|---|---|
| 认证 | `/api/auth` | 注册、登录、个人信息 |
| 论文 | `/api/papers` | CRUD、上传、回收站、引用导出 |
| 对话 | `/api/conversations` | AI 对话会话（流式响应） |
| 报告 | `/api/reports` | 阅读报告生成 |
| 搜索 | `/api/search` | 全文搜索、搜索历史、热门搜索 |
| 模型 | `/api/models` | AI 模型配置 |
| 批量操作 | `/api/batch` | 批量操作 |
| 用户 | `/api/users` | 收藏、阅读进度、笔记 |
| 翻译 | `/api/translate` | 文本翻译 |
| 文件夹 | `/api/folders` | 文件夹管理 |
| 管理 | `/api/admin` | 管理员操作（公共模型、标签） |
| 健康检查 | `/api/health` | 服务健康状态 |

## 技术栈

### 后端

| 技术 | 用途 |
|---|---|
| FastAPI | Web 框架 |
| SQLAlchemy 2.0 | ORM |
| Alembic | 数据库迁移 |
| PostgreSQL 15 | 主数据库 + 全文搜索 |
| Redis 7 | 缓存 + Celery 消息代理 |
| Celery | 异步任务队列 |
| Milvus / Milvus Lite | 向量数据库 |
| pymilvus | Milvus Python 客户端 |
| OpenAI SDK | LLM + 嵌入 API |
| CrewAI | AI 智能体框架（报告生成） |
| PyPDF2 + pdfplumber | PDF 文本提取 |
| Pydantic v2 | 数据校验 |
| python-jose | JWT 认证 |

### 前端

| 技术 | 用途 |
|---|---|
| React 18 | UI 框架 |
| TypeScript | 类型安全 |
| Ant Design | UI 组件库 |
| Zustand | 状态管理 |
| React Router v6 | 客户端路由 |
| react-pdf | PDF 阅读器 |
| react-markdown + remark-gfm | Markdown 渲染 |
| remark-math + rehype-katex | LaTeX 公式渲染 |
| Mermaid | 图表渲染 |
| react-window | 虚拟列表（性能优化） |
| Axios | HTTP 客户端 |

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 设置环境变量
export DATABASE_URL="postgresql://paperuser:password123@localhost:5432/paper_reader"
export REDIS_URL="redis://localhost:6379/0"
export MILVUS_HOST="localhost"
export MILVUS_PORT="19530"

# 执行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install --legacy-peer-deps
npm start
# 开发服务器运行在 http://localhost:3000，/api 请求代理到 :8000
```

### 运行测试

```bash
cd backend
pytest
```

## 数据库备份

项目包含 PostgreSQL 数据备份脚本：

```bash
bash scripts/backup.sh
# 备份文件保存在 backups/ 目录
```

## 参与贡献

欢迎贡献代码。请按以下步骤操作：

1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/your-feature`）
3. 提交修改（`git commit -m 'Add some feature'`）
4. 推送分支（`git push origin feature/your-feature`）
5. 发起 Pull Request

## 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE) 文件。

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) -- 高性能 Python Web 框架
- [Milvus](https://milvus.io/) -- 开源向量数据库
- [CrewAI](https://www.crewai.com/) -- 多智能体 AI 框架
- [Ant Design](https://ant.design/) -- React UI 组件库
- [react-pdf](https://github.com/wojtekmaj/react-pdf) -- React PDF 渲染组件
