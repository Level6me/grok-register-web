#!/usr/bin/env bash
# ==============================================================================
# Grok Register Web Console - 交互式一键部署、后台运行与开机自启脚本
# GitHub: https://github.com/Level6me/grok-register
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_FILE="run.log"
CONSOLE_LOG="console.log"
PORT=8318

print_banner() {
    echo -e "${CYAN}"
    echo "=================================================================="
    echo "       Grok Register - 交互式一键部署、后台运行与开机自启系统      "
    echo "               Fork 源: Level6me/grok-register                    "
    echo "=================================================================="
    echo -e "${NC}"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${YELLOW}[!] 提示: 配置开机自启服务 (Systemd) 需要 sudo 权限。${NC}"
    fi
}

install_dependencies() {
    echo -e "${BLUE}[*] 正在安装与检查系统基础环境 (Python3, Xvfb, Chromium, Net-tools)...${NC}"
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -y
        sudo apt-get install -y python3 python3-pip python3-venv xvfb chromium-browser curl net-tools sshpass systemd
    elif command -v yum &>/dev/null; then
        sudo yum install -y python3 python3-pip xvfb chromium curl net-tools systemd
    fi
    echo -e "${GREEN}[+] 系统依赖与无头浏览器环境检查完成！${NC}"
}

setup_venv() {
    echo -e "${BLUE}[*] 正在配置 Python 运行环境与依赖包...${NC}"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip -q
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -q
    else
        pip install requests curl_cffi DrissionPage -q
    fi
    echo -e "${GREEN}[+] Python 依赖库安装成功！${NC}"
}

interactive_config() {
    echo -e "${PURPLE}------------------ 交互式配置向导 ------------------${NC}"

    if [ -f "config.json" ]; then
        read -p "检测到已存在 config.json，是否重新配置？(y/N): " choice
        if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
            echo -e "${GREEN}[*] 跳过配置向导，保留现有 config.json。${NC}"
            return
        fi
    fi

    read -p "1. 请输入 YYDS 验证码 API Key (可选, 直接回车跳过): " YYDS_KEY
    read -p "2. 请输入默认目标注册账号数 [默认: 100]: " REG_COUNT
    REG_COUNT=${REG_COUNT:-100}

    read -p "3. 请输入 Web 控制台监听端口 [默认: 8318]: " IN_PORT
    PORT=${IN_PORT:-8318}

    cat <<EOF > config.json
{
  "register_count": ${REG_COUNT},
  "email_provider": "yyds",
  "yyds_api_key": "${YYDS_KEY}",
  "proxy": "",
  "proxy_list": []
}
EOF
    echo -e "${GREEN}[+] 配置文件 config.json 已成功保存！${NC}"
}

setup_systemd_autostart() {
    echo -e "${BLUE}[*] 正在生成 Systemd 开机自启服务 (grok-console.service)...${NC}"
    SERVICE_FILE="/etc/systemd/system/grok-console.service"
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)

    sudo bash -c "cat <<EOF > ${SERVICE_FILE}
[Unit]
Description=Grok Register Web Console & Daemon Service
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${CURRENT_DIR}
ExecStart=/usr/bin/python3 ${CURRENT_DIR}/web_console.py
Restart=always
RestartSec=5
StandardOutput=append:${CURRENT_DIR}/console.log
StandardError=append:${CURRENT_DIR}/console.log

[Install]
WantedBy=multi-user.target
EOF"

    sudo systemctl daemon-reload
    sudo systemctl enable grok-console
    sudo systemctl restart grok-console
    echo -e "${GREEN}[+] 开机自启服务 (grok-console.service) 已成功启用并启动！${NC}"
}

disable_systemd_autostart() {
    echo -e "${YELLOW}[*] 正在禁用 Systemd 开机自启服务...${NC}"
    sudo systemctl disable grok-console 2>/dev/null || true
    sudo systemctl stop grok-console 2>/dev/null || true
    echo -e "${GREEN}[+] 开机自启服务已关闭。${NC}"
}

start_background_nohup() {
    echo -e "${BLUE}[*] 正在后台启动 Grok Register 控制台 (Port: ${PORT})...${NC}"
    fuser -k ${PORT}/tcp 2>/dev/null || pkill -9 -f web_console.py 2>/dev/null || true
    sleep 1

    nohup python3 web_console.py </dev/null > "${CONSOLE_LOG}" 2>&1 &
    sleep 2

    if pgrep -f web_console.py &>/dev/null; then
        SERVER_IP=$(curl -s https://api.ipify.org || hostname -I | awk '{print $1}')
        echo -e "${GREEN}==================================================================${NC}"
        echo -e "${GREEN}[+] 后台进程启动成功！${NC}"
        echo -e "${GREEN}[+] Web 控制台访问地址: http://${SERVER_IP}:${PORT}${NC}"
        echo -e "${GREEN}==================================================================${NC}"
    else
        echo -e "${RED}[!] 启动失败，请查看 ${CONSOLE_LOG} 日志文件！${NC}"
    fi
}

stop_all() {
    echo -e "${YELLOW}[*] 正在停止后台所有控制台与注册进程...${NC}"
    sudo systemctl stop grok-console 2>/dev/null || true
    pkill -9 -f web_console.py 2>/dev/null || true
    pkill -9 -f grok_register_ttk 2>/dev/null || true
    pkill -9 Xvfb 2>/dev/null || true
    echo -e "${GREEN}[+] 后台进程已全部终止！${NC}"
}

show_status() {
    echo -e "${PURPLE}------------------ 运行状态与服务查询 ------------------${NC}"
    if systemctl is-enabled grok-console &>/dev/null; then
        echo -e "开机自启服务 (Systemd): ${GREEN}已启用 (Enabled)${NC}"
    else
        echo -e "开机自启服务 (Systemd): ${YELLOW}未启用 (Disabled)${NC}"
    fi

    if pgrep -f web_console.py &>/dev/null; then
        echo -e "Web 控制台进程: ${GREEN}运行中 (Running)${NC}"
    else
        echo -e "Web 控制台进程: ${RED}已停止 (Stopped)${NC}"
    fi

    if pgrep -f grok_register_ttk &>/dev/null; then
        echo -e "自动化注册主程序: ${GREEN}运行中 (Running)${NC}"
    else
        echo -e "自动化注册主程序: ${YELLOW}未启动 (Idle)${NC}"
    fi

    if [ -f "run.log" ]; then
        echo -e "${BLUE}--- 最新运行日志摘要 ---${NC}"
        tail -n 10 run.log
    fi
}

show_menu() {
    print_banner
    echo " 1) 🚀 一键完整部署 (安装依赖 + 交互配置 + 后台运行 + 配置开机自启)"
    echo " 2) ▶ 仅后台启动 (Nohup 模式)"
    echo " 3) ⏹ 停止后台所有服务"
    echo " 4) ⚙️ 开启 Systemd 开机自启服务"
    echo " 5) 🚫 关闭 Systemd 开机自启服务"
    echo " 6) 📊 查看服务运行状态与日志"
    echo " 7) 📝 重新进行交互式参数配置"
    echo " 0) 退出"
    echo "=================================================================="
    read -p "请输入对应功能序号 [0-7]: " num
    case "$num" in
        1)
            check_root
            install_dependencies
            setup_venv
            interactive_config
            setup_systemd_autostart
            show_status
            ;;
        2)
            start_background_nohup
            ;;
        3)
            stop_all
            ;;
        4)
            check_root
            setup_systemd_autostart
            ;;
        5)
            check_root
            disable_systemd_autostart
            ;;
        6)
            show_status
            ;;
        7)
            interactive_config
            ;;
        0)
            exit 0
            ;;
        *)
            echo -e "${RED}[!] 无效选择${NC}"
            ;;
    esac
}

# 命令行直导快捷传参
if [ "$1" == "install" ]; then
    check_root
    install_dependencies
    setup_venv
    interactive_config
    setup_systemd_autostart
elif [ "$1" == "start" ]; then
    start_background_nohup
elif [ "$1" == "stop" ]; then
    stop_all
elif [ "$1" == "autostart" ]; then
    check_root
    setup_systemd_autostart
elif [ "$1" == "status" ]; then
    show_status
else
    show_menu
fi
