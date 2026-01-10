#!/bin/bash
#
# 稳定的服务器端部署脚本
# 功能：清理端口、启动服务、验证状态
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_ROOT="/home/novelapp/novel-system"
cd "$PROJECT_ROOT"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# 检查并终止占用端口的进程
kill_port() {
    local port=$1
    print_info "检查端口 ${port}..."
    
    # 尝试多种方式查找进程
    local pids=""
    
    # 方法1: 使用lsof
    if command -v lsof >/dev/null 2>&1; then
        pids=$(lsof -ti:${port} 2>/dev/null || true)
    fi
    
    # 方法2: 使用fuser
    if [ -z "$pids" ] && command -v fuser >/dev/null 2>&1; then
        pids=$(fuser ${port}/tcp 2>/dev/null | grep -oE '[0-9]+' | tr '\n' ' ' || true)
    fi
    
    # 方法3: 使用netstat
    if [ -z "$pids" ] && command -v netstat >/dev/null 2>&1; then
        pids=$(netstat -tulpn 2>/dev/null | grep ":${port} " | grep -oE 'PID=[0-9]+' | cut -d= -f2 | tr '\n' ' ' || true)
    fi
    
    # 方法4: 使用ss
    if [ -z "$pids" ] && command -v ss >/dev/null 2>&1; then
        pids=$(ss -tulpn 2>/dev/null | grep ":${port} " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | tr '\n' ' ' || true)
    fi
    
    if [ -n "$pids" ]; then
        print_warning "找到占用端口的进程: $pids"
        for pid in $pids; do
            if [ -n "$pid" ]; then
                print_info "终止进程 $pid..."
                # 显示进程信息
                ps -fp $pid 2>/dev/null || true
                # 先尝试优雅退出
                kill -15 $pid 2>/dev/null || true
                sleep 1
                # 如果进程仍在运行，强制终止
                if ps -p $pid > /dev/null 2>&1; then
                    kill -9 $pid 2>/dev/null || true
                fi
                print_success "已终止进程 $pid"
            fi
        done
        sleep 2
    else
        print_success "端口 ${port} 未被占用"
    fi
}

# 检查gunicorn进程
kill_gunicorn() {
    print_info "检查gunicorn进程..."
    
    local pids=$(pgrep -f "gunicorn.*web.wsgi:app" || true)
    
    if [ -n "$pids" ]; then
        print_warning "找到gunicorn进程: $pids"
        for pid in $pids; do
            print_info "终止gunicorn进程 $pid..."
            kill -15 $pid 2>/dev/null || true
        done
        sleep 2
        
        # 检查是否还有残留
        pids=$(pgrep -f "gunicorn.*web.wsgi:app" || true)
        if [ -n "$pids" ]; then
            print_warning "强制终止残留进程..."
            for pid in $pids; do
                kill -9 $pid 2>/dev/null || true
            done
        fi
        print_success "所有gunicorn进程已终止"
    else
        print_success "没有运行中的gunicorn进程"
    fi
}

# 激活虚拟环境
activate_venv() {
    print_info "激活虚拟环境..."
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        print_success "虚拟环境已激活"
    else
        print_error "虚拟环境不存在: $PROJECT_ROOT/venv"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    python -c "import flask; print('Flask: OK')" 2>/dev/null || {
        print_error "Flask未安装"
        exit 1
    }
    
    python -c "import gunicorn; print('Gunicorn: OK')" 2>/dev/null || {
        print_error "Gunicorn未安装"
        exit 1
    }
    
    print_success "依赖检查通过"
}

# 启动服务
start_service() {
    print_info "启动Gunicorn服务..."
    
    # 确保日志目录存在
    mkdir -p "$PROJECT_ROOT/logs"
    
    # 启动gunicorn
    nohup gunicorn \
        -w 2 \
        -b 0.0.0.0:5000 \
        --timeout 600 \
        --access-logfile "$PROJECT_ROOT/logs/access.log" \
        --error-logfile "$PROJECT_ROOT/logs/error.log" \
        --log-level info \
        --capture-output \
        --pid "$PROJECT_ROOT/logs/gunicorn.pid" \
        web.wsgi:app > "$PROJECT_ROOT/logs/gunicorn.log" 2>&1 &
    
    local gunicorn_pid=$!
    echo $gunicorn_pid > "$PROJECT_ROOT/logs/gunicorn.pid"
    
    print_success "Gunicorn服务已启动 (PID: $gunicorn_pid)"
}

# 验证服务状态
verify_service() {
    print_info "等待服务启动..."
    sleep 5
    
    # 检查进程
    if [ -f "$PROJECT_ROOT/logs/gunicorn.pid" ]; then
        local pid=$(cat "$PROJECT_ROOT/logs/gunicorn.pid")
        if ps -p $pid > /dev/null 2>&1; then
            print_success "Gunicorn进程运行正常 (PID: $pid)"
        else
            print_error "Gunicorn进程未运行，查看日志..."
            tail -50 "$PROJECT_ROOT/logs/gunicorn.log"
            exit 1
        fi
    else
        print_error "PID文件不存在"
        exit 1
    fi
    
    # 检查端口
    if lsof -i:5000 >/dev/null 2>&1 || ss -tulpn | grep -q ":5000 "; then
        print_success "端口5000正在监听"
    else
        print_error "端口5000未监听"
        tail -50 "$PROJECT_ROOT/logs/gunicorn.log"
        exit 1
    fi
    
    # 检查HTTP响应
    sleep 3
    if command -v curl >/dev/null 2>&1; then
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 || echo "000")
        if [ "$http_code" = "200" ] || [ "$http_code" = "302" ]; then
            print_success "HTTP响应正常 (状态码: $http_code)"
        else
            print_warning "HTTP响应异常 (状态码: $http_code)"
        fi
    fi
}

# 显示状态信息
show_status() {
    print_section "部署完成"
    
    echo -e "${GREEN}✓ 服务已成功启动！${NC}"
    echo ""
    echo "访问地址: http://8.163.37.124:5000"
    echo ""
    echo "服务信息:"
    echo "  进程ID: $(cat $PROJECT_ROOT/logs/gunicorn.pid)"
    echo "  监听端口: 0.0.0.0:5000"
    echo "  工作进程数: 2"
    echo "  超时时间: 600秒"
    echo ""
    echo "日志文件:"
    echo "  Gunicorn日志: $PROJECT_ROOT/logs/gunicorn.log"
    echo "  访问日志: $PROJECT_ROOT/logs/access.log"
    echo "  错误日志: $PROJECT_ROOT/logs/error.log"
    echo ""
    echo "管理命令:"
    echo "  查看日志: tail -f $PROJECT_ROOT/logs/gunicorn.log"
    echo "  停止服务: kill \$(cat $PROJECT_ROOT/logs/gunicorn.pid)"
    echo "  重启服务: $0"
    echo ""
}

# 主函数
main() {
    print_section "小说生成系统 - 服务器部署"
    
    kill_port 5000
    kill_gunicorn
    activate_venv
    check_dependencies
    start_service
    verify_service
    show_status
}

# 执行主函数
main