#!/usr/bin/env bash
###############################################################################
# Paper Reader - 原生部署脚本（不使用 Docker）
# 支持 macOS (Homebrew) 和 Ubuntu/Debian Linux (apt)
#
# 用法:
#   bash scripts/deploy-native.sh          # 安装依赖 + 启动所有服务
#   bash scripts/deploy-native.sh install  # 仅安装依赖
#   bash scripts/deploy-native.sh start    # 启动所有服务
#   bash scripts/deploy-native.sh stop     # 停止所有服务
#   bash scripts/deploy-native.sh status   # 查看服务状态
#   bash scripts/deploy-native.sh restart  # 重启所有服务
#   bash scripts/deploy-native.sh logs     # 查看日志
###############################################################################

set -euo pipefail

# ─── 全局变量 ─────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
LOG_DIR="${PROJECT_ROOT}/logs"
PID_DIR="${PROJECT_ROOT}/pids"
VENV_DIR="${PROJECT_ROOT}/backend/.venv"
FRONTEND_BUILD_DIR="${PROJECT_ROOT}/frontend/build"
NGINX_CONF_DIR="${PROJECT_ROOT}/nginx"

# 默认配置（可通过 .env 覆盖）
DB_NAME="paper_reader"
DB_USER="paperuser"
DB_PASSWORD="password123"
DB_PORT="5432"
REDIS_PORT="6379"
MILVUS_PORT="19530"
BACKEND_PORT="8000"
NGINX_PORT="80"
SECRET_KEY="your_super_secret_jwt_key_change_me"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${BLUE}========== $* ==========${NC}"; }

# ─── 系统检测 ─────────────────────────────────────────────────────────────────
detect_os() {
    case "$(uname -s)" in
        Darwin*) OS="macos" ;;
        Linux*)
            if [ -f /etc/debian_version ] || command -v apt-get &>/dev/null; then
                OS="debian"
            elif [ -f /etc/redhat-release ] || command -v dnf &>/dev/null || command -v yum &>/dev/null; then
                OS="rhel"
            else
                OS="linux_unknown"
            fi
            ;;
        *) OS="unknown" ;;
    esac
    log_info "检测到操作系统: ${OS} ($(uname -s) $(uname -m))"
}

# ─── 加载 .env 配置 ───────────────────────────────────────────────────────────
load_env() {
    if [ ! -f "${PROJECT_ROOT}/.env" ]; then
        if [ -f "${PROJECT_ROOT}/.env.example" ]; then
            cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
            log_warn "已从 .env.example 创建 .env 文件，请在生产环境中修改密码和密钥"
        fi
    fi

    if [ -f "${PROJECT_ROOT}/.env" ]; then
        # 安全地加载 .env 文件
        while IFS='=' read -r key value; do
            # 跳过空行和注释
            [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            case "$key" in
                DB_PASSWORD)   DB_PASSWORD="$value" ;;
                SECRET_KEY)    SECRET_KEY="$value" ;;
                MINIO_ACCESS_KEY) ;; # Milvus Lite 不需要 MinIO
                MINIO_SECRET_KEY) ;;
            esac
        done < "${PROJECT_ROOT}/.env"
    fi
}

# ─── 创建目录结构 ─────────────────────────────────────────────────────────────
create_dirs() {
    mkdir -p "${DATA_DIR}"/{postgres,redis,milvus}
    mkdir -p "${LOG_DIR}"
    mkdir -p "${PID_DIR}"
    mkdir -p "${PROJECT_ROOT}/uploads"
    mkdir -p "${PROJECT_ROOT}/backups"
}

###############################################################################
# 安装依赖
###############################################################################

install_deps_macos() {
    log_section "安装 macOS 依赖 (Homebrew)"

    if ! command -v brew &>/dev/null; then
        log_error "未找到 Homebrew，请先安装: https://brew.sh"
        exit 1
    fi

    log_info "更新 Homebrew..."
    brew update || true

    # PostgreSQL
    if ! command -v psql &>/dev/null; then
        log_info "安装 PostgreSQL 15..."
        brew install postgresql@15
    else
        log_info "PostgreSQL 已安装: $(psql --version)"
    fi

    # Redis
    if ! command -v redis-server &>/dev/null; then
        log_info "安装 Redis..."
        brew install redis
    else
        log_info "Redis 已安装: $(redis-server --version)"
    fi

    # Node.js
    if ! command -v node &>/dev/null; then
        log_info "安装 Node.js 18..."
        brew install node@18
    else
        log_info "Node.js 已安装: $(node --version)"
    fi

    # Nginx
    if ! command -v nginx &>/dev/null; then
        log_info "安装 Nginx..."
        brew install nginx
    else
        log_info "Nginx 已安装: $(nginx -v 2>&1)"
    fi

    # Python 3.12
    if ! command -v python3.12 &>/dev/null && ! python3 --version 2>&1 | grep -q "3.12"; then
        log_info "安装 Python 3.12..."
        brew install python@3.12
    else
        log_info "Python 已安装: $(python3 --version)"
    fi
}

install_deps_debian() {
    log_section "安装 Debian/Ubuntu 依赖 (apt)"

    log_info "更新软件包列表..."
    sudo apt-get update -y

    # 基础工具
    sudo apt-get install -y curl wget gnupg2 lsb-release software-properties-common \
        build-essential libpq-dev

    # PostgreSQL 15
    if ! command -v psql &>/dev/null; then
        log_info "安装 PostgreSQL 15..."
        # 添加 PostgreSQL 官方仓库
        if [ ! -f /etc/apt/sources.list.d/pgdg.list ]; then
            sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
            wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
            sudo apt-get update -y
        fi
        sudo apt-get install -y postgresql-15 postgresql-client-15
    else
        log_info "PostgreSQL 已安装: $(psql --version)"
    fi

    # Redis
    if ! command -v redis-server &>/dev/null; then
        log_info "安装 Redis..."
        sudo apt-get install -y redis-server
    else
        log_info "Redis 已安装: $(redis-server --version)"
    fi

    # Node.js 18
    if ! command -v node &>/dev/null; then
        log_info "安装 Node.js 18..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    else
        log_info "Node.js 已安装: $(node --version)"
    fi

    # Nginx
    if ! command -v nginx &>/dev/null; then
        log_info "安装 Nginx..."
        sudo apt-get install -y nginx
    else
        log_info "Nginx 已安装: $(nginx -v 2>&1)"
    fi

    # Python 3.12
    if ! command -v python3.12 &>/dev/null; then
        log_info "安装 Python 3.12..."
        sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
        sudo apt-get update -y
        sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
    else
        log_info "Python 3.12 已安装"
    fi
}

install_deps_rhel() {
    log_section "安装 RHEL/CentOS 依赖 (dnf/yum)"

    # 自动选择包管理器
    if command -v dnf &>/dev/null; then
        PKG_MGR="sudo dnf"
    else
        PKG_MGR="sudo yum"
    fi

    $PKG_MGR install -y epel-release || true
    $PKG_MGR install -y gcc gcc-c++ make libpq-devel

    # PostgreSQL 15
    if ! command -v psql &>/dev/null; then
        log_info "安装 PostgreSQL 15..."
        $PKG_MGR install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-$(rpm -E %{rhel})-x86_64/pgdg-redhat-repo-latest.noarch.rpm || true
        $PKG_MGR install -y postgresql15-server postgresql15
        sudo /usr/pgsql-15/bin/postgresql-15-setup initdb || true
        sudo systemctl enable postgresql-15
    else
        log_info "PostgreSQL 已安装: $(psql --version)"
    fi

    # Redis
    if ! command -v redis-server &>/dev/null; then
        log_info "安装 Redis..."
        $PKG_MGR install -y redis
    fi

    # Node.js 18
    if ! command -v node &>/dev/null; then
        log_info "安装 Node.js 18..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        $PKG_MGR install -y nodejs
    fi

    # Nginx
    if ! command -v nginx &>/dev/null; then
        log_info "安装 Nginx..."
        $PKG_MGR install -y nginx
    fi

    # Python 3.12
    if ! command -v python3.12 &>/dev/null; then
        log_info "安装 Python 3.12..."
        $PKG_MGR install -y python3.12 python3.12-devel || {
            log_warn "无法通过包管理器安装 Python 3.12，请手动安装"
        }
    fi
}

# ─── 获取可用的 Python 命令 ───────────────────────────────────────────────────
get_python_cmd() {
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                echo "$cmd"
                return
            fi
        fi
    done
    log_error "未找到 Python >= 3.10，请先安装"
    exit 1
}

###############################################################################
# 服务配置与初始化
###############################################################################

# ─── PostgreSQL ───────────────────────────────────────────────────────────────
setup_postgres() {
    log_section "配置 PostgreSQL"

    if [ "$OS" = "macos" ]; then
        # macOS: Homebrew 安装的 PostgreSQL
        # 确保 PostgreSQL 的 bin 目录在 PATH 中
        PG_BIN_CANDIDATES=(
            "/opt/homebrew/opt/postgresql@15/bin"
            "/usr/local/opt/postgresql@15/bin"
            "/opt/homebrew/opt/postgresql@16/bin"
            "/usr/local/opt/postgresql@16/bin"
            "/opt/homebrew/bin"
            "/usr/local/bin"
        )
        for p in "${PG_BIN_CANDIDATES[@]}"; do
            if [ -x "${p}/pg_isready" ]; then
                export PATH="${p}:${PATH}"
                break
            fi
        done

        # 确定数据目录
        PG_DATA_CANDIDATES=(
            "/opt/homebrew/var/postgresql@15"
            "/usr/local/var/postgresql@15"
            "/opt/homebrew/var/postgresql@16"
            "/usr/local/var/postgresql@16"
            "/opt/homebrew/var/postgres"
            "/usr/local/var/postgres"
        )
        PG_DATA=""
        for d in "${PG_DATA_CANDIDATES[@]}"; do
            if [ -d "$d" ]; then
                PG_DATA="$d"
                break
            fi
        done

        if [ -z "$PG_DATA" ]; then
            # 初始化新的数据库
            PG_DATA="/opt/homebrew/var/postgresql@15"
            if command -v initdb &>/dev/null; then
                log_info "初始化 PostgreSQL 数据目录: ${PG_DATA}"
                initdb -D "$PG_DATA" --encoding=UTF8 --locale=C 2>/dev/null || true
            fi
        fi

        # 启动 PostgreSQL
        if ! pg_isready -q 2>/dev/null; then
            log_info "启动 PostgreSQL..."
            pg_ctl -D "$PG_DATA" -l "${LOG_DIR}/postgres.log" start 2>/dev/null || \
                brew services start postgresql@15 2>/dev/null || \
                brew services start postgresql 2>/dev/null || true
            sleep 3
        fi
    else
        # Linux: systemd
        if ! pg_isready -q 2>/dev/null; then
            log_info "启动 PostgreSQL..."
            sudo systemctl start postgresql 2>/dev/null || \
                sudo systemctl start postgresql-15 2>/dev/null || \
                sudo pg_ctlcluster 15 main start 2>/dev/null || true
            sleep 2
        fi
    fi

    # 等待 PostgreSQL 就绪
    local retries=30
    while ! pg_isready -q 2>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            log_error "PostgreSQL 启动超时"
            exit 1
        fi
        sleep 1
    done
    log_info "PostgreSQL 已就绪"

    # 创建用户和数据库
    local create_user_sql="DO \$\$ BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
            CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
        END IF;
    END \$\$;"

    local create_db_sql="SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}');"

    if [ "$OS" = "macos" ]; then
        psql -U "$(whoami)" -d postgres -c "$create_user_sql" 2>/dev/null || \
            psql -U postgres -d postgres -c "$create_user_sql" 2>/dev/null || \
            createuser -s "${DB_USER}" 2>/dev/null || true

        psql -U "$(whoami)" -d postgres -tc "$create_db_sql" | psql -U "$(whoami)" -d postgres 2>/dev/null || \
            createdb -U "$(whoami)" -O "${DB_USER}" "${DB_NAME}" 2>/dev/null || true

        # 设置密码
        psql -U "$(whoami)" -d postgres -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" 2>/dev/null || true

        # 确保 pg_hba.conf 允许密码认证
        local pg_hba
        pg_hba=$(psql -U "$(whoami)" -d postgres -tAc "SHOW hba_file;" 2>/dev/null || echo "")
        if [ -n "$pg_hba" ] && [ -f "$pg_hba" ]; then
            # 如果还没有为 paperuser 配置 md5/scram 认证
            if ! grep -q "paperuser" "$pg_hba" 2>/dev/null; then
                log_info "配置 PostgreSQL 认证..."
                # 在文件开头添加规则（优先匹配）
                local tmp_hba
                tmp_hba=$(mktemp)
                echo "# Paper Reader" > "$tmp_hba"
                echo "local   ${DB_NAME}    ${DB_USER}                            md5" >> "$tmp_hba"
                echo "host    ${DB_NAME}    ${DB_USER}    127.0.0.1/32            md5" >> "$tmp_hba"
                echo "host    ${DB_NAME}    ${DB_USER}    ::1/128                 md5" >> "$tmp_hba"
                cat "$pg_hba" >> "$tmp_hba"
                cp "$tmp_hba" "$pg_hba"
                rm -f "$tmp_hba"

                # 重新加载配置
                pg_ctl -D "$PG_DATA" reload 2>/dev/null || \
                    psql -U "$(whoami)" -d postgres -c "SELECT pg_reload_conf();" 2>/dev/null || true
            fi
        fi
    else
        # Linux
        sudo -u postgres psql -c "$create_user_sql" 2>/dev/null || true
        sudo -u postgres psql -tc "$create_db_sql" 2>/dev/null | sudo -u postgres psql 2>/dev/null || \
            sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}" 2>/dev/null || true
        sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" 2>/dev/null || true

        # 确保 pg_hba.conf 允许密码认证
        local pg_hba
        pg_hba=$(sudo -u postgres psql -tAc "SHOW hba_file;" 2>/dev/null || echo "")
        if [ -n "$pg_hba" ] && [ -f "$pg_hba" ]; then
            if ! sudo grep -q "paperuser" "$pg_hba" 2>/dev/null; then
                log_info "配置 PostgreSQL 认证..."
                local tmp_hba
                tmp_hba=$(mktemp)
                echo "# Paper Reader" | sudo tee "$tmp_hba" > /dev/null
                echo "local   ${DB_NAME}    ${DB_USER}                            md5" | sudo tee -a "$tmp_hba" > /dev/null
                echo "host    ${DB_NAME}    ${DB_USER}    127.0.0.1/32            md5" | sudo tee -a "$tmp_hba" > /dev/null
                echo "host    ${DB_NAME}    ${DB_USER}    ::1/128                 md5" | sudo tee -a "$tmp_hba" > /dev/null
                sudo cat "$pg_hba" | sudo tee -a "$tmp_hba" > /dev/null
                sudo cp "$tmp_hba" "$pg_hba"
                sudo rm -f "$tmp_hba"

                sudo systemctl reload postgresql 2>/dev/null || \
                    sudo systemctl reload postgresql-15 2>/dev/null || true
            fi
        fi
    fi

    log_info "PostgreSQL 数据库 '${DB_NAME}' 和用户 '${DB_USER}' 已准备就绪"
}

# ─── Redis ────────────────────────────────────────────────────────────────────
setup_redis() {
    log_section "配置 Redis"

    if ! redis-cli ping &>/dev/null; then
        log_info "启动 Redis..."
        if [ "$OS" = "macos" ]; then
            brew services start redis 2>/dev/null || \
                redis-server --daemonize yes --port ${REDIS_PORT} \
                    --logfile "${LOG_DIR}/redis.log" \
                    --pidfile "${PID_DIR}/redis.pid" 2>/dev/null
        else
            sudo systemctl start redis-server 2>/dev/null || \
                sudo systemctl start redis 2>/dev/null || \
                redis-server --daemonize yes --port ${REDIS_PORT} \
                    --logfile "${LOG_DIR}/redis.log" \
                    --pidfile "${PID_DIR}/redis.pid" 2>/dev/null
        fi
        sleep 2
    fi

    local retries=15
    while ! redis-cli ping &>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            log_error "Redis 启动超时"
            exit 1
        fi
        sleep 1
    done
    log_info "Redis 已就绪 (PONG)"
}

# ─── Python 虚拟环境 + 后端依赖 ──────────────────────────────────────────────
setup_backend() {
    log_section "配置 Python 后端"

    local PYTHON_CMD
    PYTHON_CMD=$(get_python_cmd)
    log_info "使用 Python: ${PYTHON_CMD} ($($PYTHON_CMD --version))"

    # 创建虚拟环境
    if [ ! -d "${VENV_DIR}" ]; then
        log_info "创建 Python 虚拟环境..."
        $PYTHON_CMD -m venv "${VENV_DIR}"
    fi

    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"

    log_info "升级 pip 和 setuptools..."
    pip install --upgrade pip "setuptools<81" 2>/dev/null

    log_info "安装后端依赖 (这可能需要几分钟)..."
    pip install -r "${PROJECT_ROOT}/backend/requirements.txt"

    # 安装 Milvus Lite（替代 Milvus 独立服务）
    log_info "安装 Milvus Lite..."
    pip install -U milvus-lite

    deactivate
    log_info "后端依赖安装完成"
}

# ─── 前端构建 ─────────────────────────────────────────────────────────────────
setup_frontend() {
    log_section "构建前端"

    cd "${PROJECT_ROOT}/frontend"

    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install --legacy-peer-deps
    fi

    if [ ! -d "build" ] || [ "$1" = "force" ] 2>/dev/null; then
        log_info "构建前端 (npm run build)..."
        npm run build
    else
        log_info "前端已构建，跳过 (使用 'deploy-native.sh install' 强制重建)"
    fi

    cd "${PROJECT_ROOT}"
    log_info "前端构建完成"
}

# ─── Nginx 配置 ───────────────────────────────────────────────────────────────
setup_nginx() {
    log_section "配置 Nginx 反向代理"

    # 生成适用于原生部署的 nginx 配置
    local NGINX_NATIVE_CONF="${NGINX_CONF_DIR}/nginx-native.conf"

    # 获取 mime.types 位置
    local MIME_TYPES="/etc/nginx/mime.types"
    if [ "$OS" = "macos" ]; then
        local brew_prefix
        brew_prefix=$(brew --prefix 2>/dev/null || echo "/opt/homebrew")
        MIME_TYPES="${brew_prefix}/etc/nginx/mime.types"
        if [ ! -f "$MIME_TYPES" ]; then
            MIME_TYPES="/opt/homebrew/etc/nginx/mime.types"
        fi
        if [ ! -f "$MIME_TYPES" ]; then
            MIME_TYPES="/usr/local/etc/nginx/mime.types"
        fi
    fi

    cat > "${NGINX_NATIVE_CONF}" << NGINX_EOF
# Paper Reader - 原生部署 Nginx 配置
# 自动生成，请勿手动修改

worker_processes auto;
pid ${PID_DIR}/nginx.pid;
error_log ${LOG_DIR}/nginx-error.log;

events {
    worker_connections 1024;
}

http {
    include       ${MIME_TYPES};
    default_type  application/octet-stream;

    access_log ${LOG_DIR}/nginx-access.log;

    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    # gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    server {
        listen ${NGINX_PORT};
        server_name localhost;

        # 流式响应 (AI 对话)
        location /api/conversations/ {
            proxy_pass http://127.0.0.1:${BACKEND_PORT};
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;

            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 300s;
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
            chunked_transfer_encoding on;
        }

        # 后端 API
        location /api/ {
            proxy_pass http://127.0.0.1:${BACKEND_PORT};
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        }

        # 前端静态文件
        location / {
            root ${FRONTEND_BUILD_DIR};
            index index.html;
            try_files \$uri \$uri/ /index.html;
        }
    }
}
NGINX_EOF

    log_info "Nginx 配置已生成: ${NGINX_NATIVE_CONF}"
}

###############################################################################
# 数据库迁移
###############################################################################

run_migrations() {
    log_section "运行数据库迁移"

    source "${VENV_DIR}/bin/activate"
    cd "${PROJECT_ROOT}/backend"

    # 设置环境变量
    export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}"
    export SECRET_KEY="${SECRET_KEY}"
    export REDIS_URL="redis://localhost:${REDIS_PORT}/0"
    export MILVUS_HOST="localhost"
    export MILVUS_PORT="${MILVUS_PORT}"

    log_info "执行 Alembic 迁移..."
    if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions 2>/dev/null)" ]; then
        python -m alembic upgrade head
        log_info "数据库迁移完成"
    else
        log_info "没有找到迁移文件，尝试自动生成..."
        python -m alembic revision --autogenerate -m "Initial migration" 2>/dev/null || true
        python -m alembic upgrade head
        log_info "初始迁移已创建并执行"
    fi

    cd "${PROJECT_ROOT}"
    deactivate
}

###############################################################################
# 启动服务
###############################################################################

start_milvus_lite() {
    log_section "启动 Milvus Lite"

    if [ -f "${PID_DIR}/milvus.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/milvus.pid")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Milvus Lite 已在运行 (PID: ${pid})"
            return
        fi
    fi

    source "${VENV_DIR}/bin/activate"

    # 使用 Milvus Lite 的 Server 类启动一个 gRPC 服务
    # 这样现有的 pymilvus 连接代码无需修改
    mkdir -p "${DATA_DIR}/milvus"

    cat > "${PROJECT_ROOT}/scripts/_milvus_server.py" << 'PYEOF'
#!/usr/bin/env python3
"""Milvus Lite gRPC Server Launcher"""
import os
import sys
import signal
import time

def main():
    db_file = sys.argv[1] if len(sys.argv) > 1 else "./data/milvus/paper_reader.db"
    address = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1:19530"

    # 确保目录存在
    os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)

    try:
        from milvus_lite.server import Server
        server = Server(db_file=db_file, address=address)
        if not server.init():
            print("[Milvus Lite] Init failed", file=sys.stderr)
            sys.exit(1)
        if not server.start():
            print("[Milvus Lite] Start failed", file=sys.stderr)
            sys.exit(1)

        print(f"[Milvus Lite] Server started at {address}, data: {db_file}")

        # 写入子进程 PID（milvus binary 进程）
        if server._p:
            pid_file = os.environ.get("MILVUS_PID_FILE", "")
            if pid_file:
                with open(pid_file, "w") as f:
                    f.write(str(server._p.pid))

        # 等待信号
        def handle_signal(signum, frame):
            print("[Milvus Lite] Shutting down...")
            server.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        # 保持运行
        while True:
            if server._p and server._p.poll() is not None:
                print("[Milvus Lite] Process exited unexpectedly", file=sys.stderr)
                sys.exit(1)
            time.sleep(5)

    except ImportError:
        print("[Milvus Lite] milvus-lite not installed, trying alternative...", file=sys.stderr)
        # 如果 milvus_lite.server 不可用，尝试使用 pymilvus MilvusServer
        try:
            from pymilvus import MilvusServer
            server = MilvusServer()
            server.set_base_dir(os.path.dirname(os.path.abspath(db_file)))
            server.listen_port = int(address.split(":")[-1])
            server.start()
            print(f"[Milvus] Server started at port {server.listen_port}")

            def handle_signal(signum, frame):
                server.stop()
                sys.exit(0)
            signal.signal(signal.SIGTERM, handle_signal)
            signal.signal(signal.SIGINT, handle_signal)

            while True:
                time.sleep(5)
        except ImportError:
            print("[ERROR] Neither milvus_lite.server nor pymilvus.MilvusServer available", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
PYEOF

    MILVUS_PID_FILE="${PID_DIR}/milvus_inner.pid" \
    nohup "${VENV_DIR}/bin/python" "${PROJECT_ROOT}/scripts/_milvus_server.py" \
        "${DATA_DIR}/milvus/paper_reader.db" \
        "127.0.0.1:${MILVUS_PORT}" \
        > "${LOG_DIR}/milvus.log" 2>&1 &

    echo $! > "${PID_DIR}/milvus.pid"

    deactivate

    # 等待 Milvus 就绪
    log_info "等待 Milvus Lite 启动..."
    local retries=30
    while ! "${VENV_DIR}/bin/python" -c "
from pymilvus import connections
try:
    connections.connect(host='127.0.0.1', port=${MILVUS_PORT}, timeout=3)
    connections.disconnect('default')
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            log_warn "Milvus Lite 启动超时，请查看日志: ${LOG_DIR}/milvus.log"
            log_warn "向量搜索功能可能暂时不可用，但其他功能正常"
            return
        fi
        sleep 2
    done
    log_info "Milvus Lite 已就绪 (端口: ${MILVUS_PORT})"
}

start_backend() {
    log_section "启动后端 API 服务"

    if [ -f "${PID_DIR}/backend.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/backend.pid")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "后端已在运行 (PID: ${pid})"
            return
        fi
    fi

    # 设置环境变量
    export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}"
    export SECRET_KEY="${SECRET_KEY}"
    export REDIS_URL="redis://localhost:${REDIS_PORT}/0"
    export MILVUS_HOST="localhost"
    export MILVUS_PORT="${MILVUS_PORT}"
    export UPLOAD_DIR="${PROJECT_ROOT}/uploads"

    cd "${PROJECT_ROOT}/backend"

    nohup "${VENV_DIR}/bin/uvicorn" app.main:app \
        --host 0.0.0.0 \
        --port "${BACKEND_PORT}" \
        --workers 1 \
        --loop asyncio \
        > "${LOG_DIR}/backend.log" 2>&1 &

    echo $! > "${PID_DIR}/backend.pid"
    cd "${PROJECT_ROOT}"

    # 等待后端就绪
    local retries=20
    while ! curl -s "http://127.0.0.1:${BACKEND_PORT}/api/health" &>/dev/null && \
          ! curl -s "http://127.0.0.1:${BACKEND_PORT}/" &>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            log_warn "后端启动超时，请查看日志: ${LOG_DIR}/backend.log"
            return
        fi
        sleep 2
    done
    log_info "后端 API 已就绪 (端口: ${BACKEND_PORT})"
}

start_celery() {
    log_section "启动 Celery Worker"

    if [ -f "${PID_DIR}/celery.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/celery.pid")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Celery 已在运行 (PID: ${pid})"
            return
        fi
    fi

    export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}"
    export SECRET_KEY="${SECRET_KEY}"
    export REDIS_URL="redis://localhost:${REDIS_PORT}/0"
    export MILVUS_HOST="localhost"
    export MILVUS_PORT="${MILVUS_PORT}"
    export UPLOAD_DIR="${PROJECT_ROOT}/uploads"

    cd "${PROJECT_ROOT}/backend"

    nohup "${VENV_DIR}/bin/celery" -A app.tasks.celery_app worker \
        --loglevel=info \
        --concurrency=2 \
        > "${LOG_DIR}/celery.log" 2>&1 &

    echo $! > "${PID_DIR}/celery.pid"
    cd "${PROJECT_ROOT}"

    log_info "Celery Worker 已启动"
}

start_nginx() {
    log_section "启动 Nginx"

    local NGINX_CONF="${NGINX_CONF_DIR}/nginx-native.conf"

    if [ ! -f "$NGINX_CONF" ]; then
        setup_nginx
    fi

    # 检查 Nginx 是否已在运行
    if [ -f "${PID_DIR}/nginx.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/nginx.pid")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Nginx 已在运行 (PID: ${pid})，重新加载配置..."
            nginx -s reload -c "${NGINX_CONF}" 2>/dev/null || true
            return
        fi
    fi

    # 端口 80 需要特权
    local use_sudo=""
    if [ "${NGINX_PORT}" -lt 1024 ] && [ "$(id -u)" -ne 0 ]; then
        use_sudo="sudo"
        log_warn "端口 ${NGINX_PORT} 需要管理员权限"
    fi

    # 测试配置
    if ! ${use_sudo} nginx -t -c "${NGINX_CONF}" 2>/dev/null; then
        log_error "Nginx 配置测试失败，尝试使用端口 8080..."
        NGINX_PORT=8080
        setup_nginx  # 重新生成配置
    fi

    ${use_sudo} nginx -c "${NGINX_CONF}" 2>/dev/null || {
        # 如果端口冲突，停掉旧的再启动
        log_warn "Nginx 启动失败，尝试先停止现有实例..."
        ${use_sudo} nginx -s stop 2>/dev/null || true
        sleep 1
        ${use_sudo} nginx -c "${NGINX_CONF}"
    }

    log_info "Nginx 已启动 (端口: ${NGINX_PORT})"
}

###############################################################################
# 停止服务
###############################################################################

stop_service() {
    local name=$1
    local pid_file="${PID_DIR}/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "停止 ${name} (PID: ${pid})..."
            kill "$pid" 2>/dev/null || true
            # 等待进程退出
            local retries=10
            while kill -0 "$pid" 2>/dev/null; do
                retries=$((retries - 1))
                if [ $retries -le 0 ]; then
                    log_warn "强制终止 ${name}..."
                    kill -9 "$pid" 2>/dev/null || true
                    break
                fi
                sleep 1
            done
        fi
        rm -f "$pid_file"
    fi
}

stop_all() {
    log_section "停止所有服务"

    # 停止 Nginx
    if [ -f "${PID_DIR}/nginx.pid" ]; then
        local use_sudo=""
        if [ "${NGINX_PORT}" -lt 1024 ] && [ "$(id -u)" -ne 0 ]; then
            use_sudo="sudo"
        fi
        ${use_sudo} nginx -s stop -c "${NGINX_CONF_DIR}/nginx-native.conf" 2>/dev/null || true
        rm -f "${PID_DIR}/nginx.pid"
        log_info "Nginx 已停止"
    fi

    # 停止应用服务
    stop_service "celery"
    stop_service "backend"
    stop_service "milvus"

    # 停止 Redis（如果是我们自己启动的守护进程）
    if [ -f "${PID_DIR}/redis.pid" ]; then
        stop_service "redis"
    fi

    log_info "所有服务已停止"
    log_warn "注意: PostgreSQL 和 Redis 系统服务未被停止（可能其他应用也在使用）"
    log_warn "如需停止它们，请手动执行:"
    if [ "$OS" = "macos" ]; then
        log_warn "  brew services stop postgresql@15"
        log_warn "  brew services stop redis"
    else
        log_warn "  sudo systemctl stop postgresql"
        log_warn "  sudo systemctl stop redis-server"
    fi
}

###############################################################################
# 服务状态
###############################################################################

check_status() {
    log_section "服务状态"

    local all_ok=true

    # PostgreSQL
    if pg_isready -q 2>/dev/null; then
        echo -e "  ${GREEN}[运行中]${NC} PostgreSQL (端口 ${DB_PORT})"
    else
        echo -e "  ${RED}[已停止]${NC} PostgreSQL"
        all_ok=false
    fi

    # Redis
    if redis-cli ping &>/dev/null; then
        echo -e "  ${GREEN}[运行中]${NC} Redis (端口 ${REDIS_PORT})"
    else
        echo -e "  ${RED}[已停止]${NC} Redis"
        all_ok=false
    fi

    # Milvus Lite
    if [ -f "${PID_DIR}/milvus.pid" ] && kill -0 "$(cat "${PID_DIR}/milvus.pid")" 2>/dev/null; then
        echo -e "  ${GREEN}[运行中]${NC} Milvus Lite (端口 ${MILVUS_PORT}, PID: $(cat "${PID_DIR}/milvus.pid"))"
    else
        echo -e "  ${RED}[已停止]${NC} Milvus Lite"
        all_ok=false
    fi

    # Backend
    if [ -f "${PID_DIR}/backend.pid" ] && kill -0 "$(cat "${PID_DIR}/backend.pid")" 2>/dev/null; then
        echo -e "  ${GREEN}[运行中]${NC} Backend API (端口 ${BACKEND_PORT}, PID: $(cat "${PID_DIR}/backend.pid"))"
    else
        echo -e "  ${RED}[已停止]${NC} Backend API"
        all_ok=false
    fi

    # Celery
    if [ -f "${PID_DIR}/celery.pid" ] && kill -0 "$(cat "${PID_DIR}/celery.pid")" 2>/dev/null; then
        echo -e "  ${GREEN}[运行中]${NC} Celery Worker (PID: $(cat "${PID_DIR}/celery.pid"))"
    else
        echo -e "  ${RED}[已停止]${NC} Celery Worker"
        all_ok=false
    fi

    # Nginx
    if [ -f "${PID_DIR}/nginx.pid" ] && kill -0 "$(cat "${PID_DIR}/nginx.pid")" 2>/dev/null; then
        echo -e "  ${GREEN}[运行中]${NC} Nginx (端口 ${NGINX_PORT}, PID: $(cat "${PID_DIR}/nginx.pid"))"
    else
        echo -e "  ${RED}[已停止]${NC} Nginx"
        all_ok=false
    fi

    echo ""
    if [ "$all_ok" = true ]; then
        echo -e "  ${GREEN}所有服务正常运行${NC}"
        echo -e "  访问地址: http://localhost:${NGINX_PORT}"
    else
        echo -e "  ${YELLOW}部分服务未运行，请查看日志: ${LOG_DIR}/${NC}"
    fi
}

###############################################################################
# 查看日志
###############################################################################

show_logs() {
    log_section "最近日志"

    for logfile in "${LOG_DIR}"/*.log; do
        if [ -f "$logfile" ]; then
            echo -e "\n${BLUE}--- $(basename "$logfile") (最后 10 行) ---${NC}"
            tail -n 10 "$logfile" 2>/dev/null || true
        fi
    done
}

###############################################################################
# 主入口
###############################################################################

cmd_install() {
    detect_os
    load_env
    create_dirs

    case "$OS" in
        macos)  install_deps_macos ;;
        debian) install_deps_debian ;;
        rhel)   install_deps_rhel ;;
        *)
            log_error "不支持的操作系统: ${OS}"
            log_error "请手动安装: PostgreSQL 15, Redis, Node.js 18, Nginx, Python 3.12"
            exit 1
            ;;
    esac

    setup_backend
    setup_frontend "force"
    setup_nginx
    setup_postgres
}

cmd_start() {
    detect_os
    load_env
    create_dirs

    setup_postgres
    setup_redis
    start_milvus_lite
    run_migrations
    start_backend
    start_celery
    setup_nginx
    start_nginx

    echo ""
    log_section "部署完成"
    check_status
}

cmd_stop() {
    detect_os
    load_env
    stop_all
}

cmd_status() {
    detect_os
    load_env
    check_status
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_logs() {
    show_logs
}

cmd_full_deploy() {
    log_section "Paper Reader 一键部署 (原生模式)"
    echo ""
    echo "  本脚本将在当前系统上安装和配置以下服务:"
    echo "    - PostgreSQL 15    (关系型数据库)"
    echo "    - Redis 7          (缓存 + 消息队列)"
    echo "    - Milvus Lite      (向量数据库 - 纯 Python 原生运行)"
    echo "    - FastAPI + Uvicorn (后端 API)"
    echo "    - Celery Worker    (异步任务处理)"
    echo "    - React (构建)      (前端静态文件)"
    echo "    - Nginx            (反向代理)"
    echo ""

    cmd_install
    echo ""
    cmd_start
}

# 解析命令
case "${1:-}" in
    install)  cmd_install ;;
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    status)   cmd_status ;;
    restart)  cmd_restart ;;
    logs)     cmd_logs ;;
    help|-h|--help)
        echo "Paper Reader 原生部署脚本 (不使用 Docker)"
        echo ""
        echo "用法: bash scripts/deploy-native.sh [命令]"
        echo ""
        echo "命令:"
        echo "  (无参数)  完整部署: 安装依赖 + 启动所有服务"
        echo "  install   仅安装和配置依赖"
        echo "  start     启动所有服务"
        echo "  stop      停止所有服务"
        echo "  status    查看服务状态"
        echo "  restart   重启所有服务"
        echo "  logs      查看最近日志"
        echo "  help      显示帮助信息"
        echo ""
        echo "日志目录: ${LOG_DIR}"
        echo "PID 目录: ${PID_DIR}"
        echo "数据目录: ${DATA_DIR}"
        ;;
    *)  cmd_full_deploy ;;
esac
