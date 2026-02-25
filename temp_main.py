from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import (
    auth,
    papers,
    ai_models,
    conversations,
    reports,
    batch_operations,
    search,
    health,
    admin,
    users,
    translate,
)
from app.core.exceptions import setup_exception_handlers

app = FastAPI(
    title="在线论文阅读器 API",
    description="支持AI辅助阅读、批量管理、智能翻译、全文搜索的论文阅读平台",
    version="2.2.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置全局异常处理器
setup_exception_handlers(app)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(papers.router, prefix="/api/papers", tags=["论文管理"])
app.include_router(ai_models.router, prefix="/api/models", tags=["AI模型"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["AI对话"])
app.include_router(reports.router, prefix="/api/reports", tags=["阅读报告"])
app.include_router(batch_operations.router, prefix="/api/batch", tags=["批量操作"])
app.include_router(search.router, prefix="/api/search", tags=["全文搜索"])
app.include_router(health.router, prefix="/api/health", tags=["健康检查"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理员接口"])
app.include_router(users.router, prefix="/api/users", tags=["用户个性化"])
app.include_router(translate.router, prefix="/api/translate", tags=["智能翻译"])


@app.get("/")
async def root():
    return {"message": "Welcome to Online Paper Reader API", "version": "2.2.0"}
