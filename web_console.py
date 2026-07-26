#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grok Register Web Console v3.3
Bug 修复说明：
- 修复运行日志遇到 Cloudflare / HTML 调试文本（如 <!DOCTYPE html> <!--[if ...）导致浏览器 innerHTML 解析错乱、终端日志加载空白的漏洞。
- 新增 JS 端的 escapeHtml 安全转义处理，保障日志 100% 稳定安全地实时渲染输出。
监听端口 8318
"""

import json
import os
import glob
import subprocess
import time
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

CONFIG_FILE = "/home/ubuntu/grok-register/config.json"
PROXIES_FILE = "/home/ubuntu/grok-register/proxies.txt"
LOG_FILE = "/home/ubuntu/grok-register/run.log"
CPA_DIR = "/home/ubuntu/.cli-proxy-api"
REGISTER_DIR = "/home/ubuntu/grok-register"
PORT = 8318

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Grok Register Web Console</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-card: #151d30;
            --bg-card-hover: #1e2942;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-yellow: #eab308;
            --border-color: #24314d;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            min-height: 100vh;
            padding: 16px;
            -webkit-tap-highlight-color: transparent;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 12px;
        }
        .logo-group { display: flex; align-items: center; gap: 10px; }
        .logo-icon {
            width: 36px; height: 36px;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 18px; color: #fff;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
        }
        h1 { font-size: 18px; font-weight: 700; }
        .subtitle { font-size: 12px; color: var(--text-muted); }

        .status-badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 5px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
            background: rgba(255,255,255,0.05); border: 1px solid var(--border-color);
        }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
        .status-badge.running .status-dot {
            background: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
            animation: pulse 2s infinite;
        }
        .status-badge.stopped .status-dot { background: var(--accent-red); }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

        .alert-banner {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid var(--accent-red);
            color: #fca5a5;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            display: none;
            align-items: center;
            gap: 8px;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }
        @media (max-width: 768px) {
            .stat-grid { grid-template-columns: repeat(2, 1fr); }
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px; padding: 14px;
        }
        .stat-title { font-size: 12px; color: var(--text-muted); font-weight: 500; }
        .stat-value { font-size: 24px; font-weight: 700; margin-top: 4px; font-family: 'Fira Code', monospace; }
        .stat-unit { font-size: 12px; color: var(--text-muted); font-weight: normal; }

        .panel {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px; padding: 16px;
            display: flex; flex-direction: column; gap: 14px;
        }
        .panel-header {
            display: flex; justify-content: space-between; align-items: center;
            flex-wrap: wrap; gap: 10px;
        }
        .panel-title { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 6px; }

        .btn-group { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn {
            display: inline-flex; align-items: center; justify-content: center; gap: 6px;
            padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 600;
            cursor: pointer; border: none; transition: all 0.2s; touch-action: manipulation;
        }
        .btn-success { background: var(--accent-green); color: #000; }
        .btn-success:hover { background: #16a34a; }
        .btn-danger { background: var(--accent-red); color: #fff; }
        .btn-danger:hover { background: #dc2626; }
        .btn-secondary { background: #24314d; color: var(--text-main); }
        .btn-secondary:hover { background: #334155; }
        .btn-outline { background: transparent; border: 1px solid var(--border-color); color: var(--text-main); }
        .btn-outline:hover { background: rgba(255,255,255,0.05); }

        .terminal {
            background: #060911; border: 1px solid #1a2336; border-radius: 8px;
            padding: 12px; font-family: 'Fira Code', monospace; font-size: 11px;
            line-height: 1.5; height: 300px; overflow-y: auto; color: #cbd5e1;
            white-space: pre-wrap; word-break: break-all;
        }
        .log-tag-success { color: #22c55e; }
        .log-tag-error { color: #ef4444; font-weight: bold; }
        .log-tag-debug { color: #64748b; }
        .log-tag-info { color: #38bdf8; }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
        }
        .form-group { display: flex; flex-direction: column; gap: 4px; }
        label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
        input[type="text"], input[type="number"], select, textarea {
            background: #0b0f19; border: 1px solid var(--border-color);
            border-radius: 6px; padding: 8px 10px; color: var(--text-main);
            font-size: 13px; outline: none; width: 100%; font-family: 'Fira Code', monospace;
        }
        input:focus, select:focus, textarea:focus { border-color: var(--accent-blue); }

        .table-wrapper {
            overflow-x: auto; border: 1px solid var(--border-color);
            border-radius: 8px; background: #060911;
        }
        table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
        th, td { padding: 10px 12px; border-bottom: 1px solid #1a2336; white-space: nowrap; }
        th { background: #111827; color: var(--text-muted); font-weight: 600; }
        tr:hover td { background: rgba(255,255,255,0.03); }
        .cell-mono { font-family: 'Fira Code', monospace; cursor: pointer; transition: background 0.15s; }
        .cell-mono:hover { background: rgba(56, 189, 248, 0.15); }
        .cell-token { max-width: 180px; overflow: hidden; text-overflow: ellipsis; }

        .pagination {
            display: flex; justify-content: space-between; align-items: center;
            flex-wrap: wrap; gap: 10px; padding-top: 10px;
            font-size: 12px; color: var(--text-muted);
        }
        .pagination-controls { display: flex; align-items: center; gap: 8px; }

        .toast {
            position: fixed; bottom: 20px; right: 20px;
            background: var(--accent-green); color: #000;
            padding: 10px 18px; border-radius: 8px; font-weight: 600;
            font-size: 13px; display: none; box-shadow: 0 4px 14px rgba(0,0,0,0.6); z-index: 1000;
        }
    </style>
</head>
<body>

<div class="container">
    <!-- Header -->
    <header>
        <div class="logo-group">
            <div class="logo-icon">G</div>
            <div>
                <h1>Grok Register 控制台</h1>
                <div class="subtitle">批量代理池与响应式注册控制面板 v3.3</div>
            </div>
        </div>
        <div id="statusBadge" class="status-badge stopped">
            <span class="status-dot"></span>
            <span id="statusText">检测中...</span>
        </div>
    </header>

    <!-- Alert Banner -->
    <div id="alertBanner" class="alert-banner">
        <span>⚠️ 提示信息：</span>
        <span id="alertMsg">检测到系统有提示</span>
    </div>

    <!-- Top Stats -->
    <div class="stat-grid">
        <div class="stat-card">
            <div class="stat-title">已成功注册账号 (全量保留)</div>
            <div class="stat-value" id="statSuccess" style="color: var(--accent-green)">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">代理池 IP 数量</div>
            <div class="stat-value" id="statProxyCount" style="color: var(--accent-blue)">0 <span class="stat-unit">个</span></div>
        </div>
        <div class="stat-card">
            <div class="stat-title">配置目标注册量</div>
            <div class="stat-value" id="statTarget" style="color: var(--accent-yellow)">100</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">账号导出文件列表</div>
            <div class="stat-value" id="statAccounts" style="color: #a7f3d0">0 <span class="stat-unit">个</span></div>
        </div>
    </div>

    <!-- Main Actions & Terminal Panel -->
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">⚡ 流程控制与运行日志</div>
            <div class="btn-group">
                <button id="btnStart" class="btn btn-success" onclick="startRegister()">▶ 启动注册</button>
                <button id="btnStop" class="btn btn-danger" onclick="stopRegister()">⏹ 停止注册</button>
            </div>
        </div>
        <div class="terminal" id="terminalLog">正在加载日志...</div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-muted);">
            <label style="display: flex; align-items: center; gap: 4px; cursor: pointer;">
                <input type="checkbox" id="autoScroll" checked> 自动滚动底部
            </label>
            <span>自动刷新间隔: 3 秒</span>
        </div>
    </div>

    <!-- Proxy Pool & Config Panel -->
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">🌐 批量代理池导入与系统参数配置</div>
            <span id="dirtyIndicator" style="display: none; font-size: 12px; color: var(--accent-yellow);">● 有未保存修改</span>
        </div>
        <form id="configForm" onsubmit="saveConfig(event)">
            <div class="form-group" style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <label>批量代理池列表 (支持 <code>IP:PORT:USER:PASS</code> 或 <code>http://user:pass@ip:port</code> 每行一个)</label>
                    <button type="button" class="btn btn-outline" style="padding: 2px 8px; font-size: 11px; color: var(--accent-red); border-color: rgba(239, 68, 68, 0.4);" onclick="clearProxyList()">🗑️ 清空代理列表</button>
                </div>
                <textarea id="cfgProxyList" rows="6" placeholder="31.59.20.176:6754:wqvufgny:iw6o3e9x3n8t&#10;31.56.127.193:7684:wqvufgny:iw6o3e9x3n8t" oninput="markConfigDirty()"></textarea>
            </div>

            <div class="form-grid">
                <div class="form-group">
                    <label>注册目标数量 (register_count)</label>
                    <input type="number" id="cfgRegisterCount" min="1" max="1000" value="100" oninput="markConfigDirty()">
                </div>
                <div class="form-group">
                    <label>邮箱服务商 (email_provider)</label>
                    <select id="cfgEmailProvider" onchange="markConfigDirty()">
                        <option value="yyds">YYDS (推荐，自动提取验证码)</option>
                        <option value="cloudflare">Cloudflare 临时邮箱</option>
                        <option value="duckmail">DuckMail</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>YYDS API Key</label>
                    <input type="text" id="cfgYydsApiKey" placeholder="AC-xxxxxxxx" oninput="markConfigDirty()">
                </div>
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 10px;">
                <button type="submit" class="btn btn-secondary">💾 保存代理池与配置参数</button>
            </div>
        </form>
    </div>

    <!-- Accounts Manager Panel with Pagination -->
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">📦 已注册历史账号管理 (点击对应文本格直接复制)</div>
            <div class="btn-group">
                <a class="btn btn-secondary" href="/api/download_accounts" download style="text-decoration: none;">⬇️ 下载导出全量 TXT</a>
            </div>
        </div>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th style="width: 40px;">#</th>
                        <th>邮箱账号 (点击直接复制)</th>
                        <th>密码 (点击直接复制)</th>
                        <th>JWT / SSO Token (点击直接复制)</th>
                    </tr>
                </thead>
                <tbody id="accountsTableBody">
                    <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">暂无已保存账号数据</td></tr>
                </tbody>
            </table>
        </div>

        <div class="pagination">
            <div id="pageSummary">显示第 0 到 0 条，共 0 条账号</div>
            <div class="pagination-controls">
                <button id="btnPrevPage" class="btn btn-outline" style="padding: 4px 10px; font-size: 12px;" onclick="changePage(-1)">◀ 上一页</button>
                <span id="pageIndicator" style="font-weight: 600;">第 1 / 1 页</span>
                <button id="btnNextPage" class="btn btn-outline" style="padding: 4px 10px; font-size: 12px;" onclick="changePage(1)">下一页 ▶</button>
            </div>
        </div>
    </div>
</div>

<div id="toast" class="toast">操作成功</div>

<script>
    let isAutoScroll = true;
    let isConfigDirty = false;
    let currentRunningState = false;

    let currentPage = 1;
    const pageSize = 20;
    let allAccountItems = [];

    document.getElementById('autoScroll').addEventListener('change', (e) => {
        isAutoScroll = e.target.checked;
    });

    function showToast(msg, bg) {
        const toast = document.getElementById('toast');
        toast.innerText = msg;
        toast.style.background = bg || 'var(--accent-green)';
        toast.style.color = bg ? '#fff' : '#000';
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 2500);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function copyText(str, label) {
        if (!str || str === '-') return showToast('内容为空');
        try {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(str).then(() => {
                    showToast('已复制 ' + (label || '') + ': ' + str.substring(0, 18) + '...');
                }).catch(() => fallbackCopy(str, label));
            } else {
                fallbackCopy(str, label);
            }
        } catch (e) {
            fallbackCopy(str, label);
        }
    }

    function fallbackCopy(str, label) {
        const el = document.createElement('textarea');
        el.value = str;
        el.setAttribute('readonly', '');
        el.style.position = 'absolute';
        el.style.left = '-9999px';
        document.body.appendChild(el);
        el.select();
        try {
            document.execCommand('copy');
            showToast('已复制 ' + (label || '') + ': ' + str.substring(0, 18) + '...');
        } catch (err) {
            showToast('复制失败，请重试');
        }
        document.body.removeChild(el);
    }

    function markConfigDirty() {
        isConfigDirty = true;
        document.getElementById('dirtyIndicator').style.display = 'inline';
    }

    function clearProxyList() {
        document.getElementById('cfgProxyList').value = '';
        markConfigDirty();
        showToast('已清空文本框，请点击【保存代理池与配置参数】');
    }

    async function fetchStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            const badge = document.getElementById('statusBadge');
            const statusText = document.getElementById('statusText');

            currentRunningState = data.running;

            if (data.running) {
                badge.className = 'status-badge running';
                statusText.innerText = '正在自动化注册中...';
                document.getElementById('btnStart').style.opacity = '0.6';
            } else {
                badge.className = 'status-badge stopped';
                statusText.innerText = '已暂停';
                document.getElementById('btnStart').style.opacity = '1';
            }

            const alertBanner = document.getElementById('alertBanner');
            const alertMsg = document.getElementById('alertMsg');
            if (data.proxy_error) {
                alertBanner.style.display = 'flex';
                alertMsg.innerText = '代理异常提示: ' + data.proxy_error;
            } else {
                alertBanner.style.display = 'none';
            }

            document.getElementById('statSuccess').innerText = data.stats.success || 0;
            document.getElementById('statTarget').innerText = data.config.register_count || 100;
            document.getElementById('statAccounts').innerText = data.accounts_count || 0;
            document.getElementById('statProxyCount').innerText = data.proxy_count || 0;

            if (!isConfigDirty) {
                document.getElementById('cfgRegisterCount').value = data.config.register_count || 100;
                document.getElementById('cfgEmailProvider').value = data.config.email_provider || 'yyds';
                document.getElementById('cfgYydsApiKey').value = data.config.yyds_api_key || '';
                document.getElementById('cfgProxyList').value = data.proxy_text || '';
            }
        } catch (e) {}
    }

    async function fetchLogs() {
        try {
            const res = await fetch('/api/logs');
            const text = await res.text();
            const logEl = document.getElementById('terminalLog');

            const formatted = text.split('\\n').map(line => {
                const escaped = escapeHtml(line);
                if (line.includes('[+]') || line.includes('成功')) return `<span class="log-tag-success">${escaped}</span>`;
                if (line.includes('[-]')) return `<span class="log-tag-error">${escaped}</span>`;
                if (line.includes('[Debug]')) return `<span class="log-tag-debug">${escaped}</span>`;
                if (line.includes('[*]')) return `<span class="log-tag-info">${escaped}</span>`;
                return escaped;
            }).join('\\n');

            logEl.innerHTML = formatted || '暂无日志输出...';
            if (isAutoScroll) logEl.scrollTop = logEl.scrollHeight;
        } catch (e) {}
    }

    async function fetchAccountsTable() {
        try {
            const res = await fetch('/api/accounts_json');
            const data = await res.json();
            allAccountItems = data.items || [];
            renderAccountsPage();
        } catch (e) {}
    }

    function renderAccountsPage() {
        const total = allAccountItems.length;
        const totalPages = Math.max(1, Math.ceil(total / pageSize));

        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        const startIdx = (currentPage - 1) * pageSize;
        const endIdx = Math.min(startIdx + pageSize, total);
        const pageItems = allAccountItems.slice(startIdx, endIdx);

        const tbody = document.getElementById('accountsTableBody');
        if (total === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">暂无已保存账号数据</td></tr>';
            document.getElementById('pageSummary').innerText = '显示 0 条，共 0 条';
            document.getElementById('pageIndicator').innerText = '第 1 / 1 页';
            document.getElementById('btnPrevPage').disabled = true;
            document.getElementById('btnNextPage').disabled = true;
            return;
        }

        tbody.innerHTML = pageItems.map((item, idx) => {
            const globalIdx = startIdx + idx + 1;
            const escEmail = escapeHtml(item.email);
            const escPass = escapeHtml(item.password);
            const escToken = escapeHtml(item.token);
            return `
                <tr>
                    <td>${globalIdx}</td>
                    <td class="cell-mono" style="color: var(--accent-blue);" onclick="copyText('${item.email}', '邮箱')" title="点击复制邮箱">${escEmail}</td>
                    <td class="cell-mono" style="color: var(--accent-green);" onclick="copyText('${item.password}', '密码')" title="点击复制密码">${escPass}</td>
                    <td class="cell-mono cell-token" style="color: var(--text-muted);" onclick="copyText('${item.token}', 'Token')" title="点击复制 Token">${escToken || '-'}</td>
                </tr>
            `;
        }).join('');

        document.getElementById('pageSummary').innerText = `显示第 ${startIdx + 1} 到 ${endIdx} 条，共 ${total} 条账号`;
        document.getElementById('pageIndicator').innerText = `第 ${currentPage} / ${totalPages} 页`;

        document.getElementById('btnPrevPage').disabled = (currentPage <= 1);
        document.getElementById('btnNextPage').disabled = (currentPage >= totalPages);
    }

    function changePage(delta) {
        currentPage += delta;
        renderAccountsPage();
    }

    async function startRegister() {
        if (currentRunningState) {
            showToast('⚠️ 注册流程已经在后台运行中，无需重复启动！', 'var(--accent-yellow)');
            return;
        }
        if (!confirm('确定启动批量注册流程？')) return;
        const res = await fetch('/api/start', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            showToast('🚀 注册指令已发送，后台启动成功！');
            fetchStatus();
        } else {
            showToast('启动失败: ' + (data.msg || ''), 'var(--accent-red)');
        }
    }

    async function stopRegister() {
        if (!confirm('确定要停止当前注册进程？')) return;
        await fetch('/api/stop', { method: 'POST' });
        showToast('🛑 停止指令已发送，进程已终止！', 'var(--accent-red)');
        fetchStatus();
    }

    async function saveConfig(e) {
        e.preventDefault();
        const payload = {
            register_count: parseInt(document.getElementById('cfgRegisterCount').value) || 100,
            email_provider: document.getElementById('cfgEmailProvider').value,
            yyds_api_key: document.getElementById('cfgYydsApiKey').value.trim(),
            proxy_list_text: document.getElementById('cfgProxyList').value
        };

        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            isConfigDirty = false;
            document.getElementById('dirtyIndicator').style.display = 'none';
            showToast('代理池与参数修改保存成功！');
            fetchStatus();
        } else {
            showToast('保存配置失败', 'var(--accent-red)');
        }
    }

    setInterval(fetchStatus, 3000);
    setInterval(fetchLogs, 3000);
    setInterval(fetchAccountsTable, 5000);

    fetchStatus();
    fetchLogs();
    fetchAccountsTable();
</script>

</body>
</html>
"""

def is_register_running():
    try:
        res = subprocess.run(["pgrep", "-f", "grok_register_ttk"], stdout=subprocess.PIPE, text=True)
        return bool(res.stdout.strip())
    except Exception:
        return False

def get_log_stats():
    success = 0
    failed = 0
    proxy_error = ""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                for line in reversed(lines[-200:]):
                    if not proxy_error and any(k in line for k in ["代理", "Proxy", "402", "403", "ConnectionError"]) and any(k in line for k in ["失败", "错误", "Error", "Refused"]):
                        proxy_error = line.strip()
                    if "当前统计:" in line and success == 0:
                        m = re.search(r"成功\s*(\d+)\s*\|\s*失败\s*(\d+)", line)
                        if m:
                            success = int(m.group(1))
                            failed = int(m.group(2))
        except Exception:
            pass
    return {"success": success, "failed": failed, "proxy_error": proxy_error}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def normalize_proxy(raw):
    s = str(raw or "").strip()
    if not s:
        return ""
    if "://" in s:
        return s
    parts = s.split(":")
    if len(parts) == 4:
        ip, port, user, pwd = parts
        return f"http://{user}:{pwd}@{ip}:{port}"
    if "@" in s:
        return "http://" + s
    return "http://" + s

def load_proxies_file():
    if os.path.exists(PROXIES_FILE):
        try:
            with open(PROXIES_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception:
            pass
    return []

def save_proxies_file(proxy_lines):
    clean_lines = []
    for line in proxy_lines:
        line = line.strip()
        if line:
            clean_lines.append(line)
    with open(PROXIES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(clean_lines) + ("\n" if clean_lines else ""))

    cfg = load_config()
    if clean_lines:
        cfg["proxy"] = normalize_proxy(clean_lines[0])
        cfg["proxy_list"] = [normalize_proxy(p) for p in clean_lines]
    else:
        cfg["proxy"] = ""
        cfg["proxy_list"] = []
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_accounts_parsed():
    account_files = glob.glob(os.path.join(REGISTER_DIR, "accounts_*.txt"))
    account_files.sort(key=os.path.getmtime)
    seen_emails = set()
    items = []
    raw_lines = []

    for fpath in account_files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("----")
                    email = parts[0].strip() if len(parts) > 0 else ""
                    if email and email not in seen_emails:
                        seen_emails.add(email)
                        pwd = parts[1].strip() if len(parts) > 1 else ""
                        token = parts[2].strip() if len(parts) > 2 else ""
                        items.append({"email": email, "password": pwd, "token": token})
                        raw_lines.append(f"{email}----{pwd}----{token}")
        except Exception:
            pass

    return {"items": items, "raw_text": "\n".join(raw_lines), "count": len(items)}

class WebConsoleHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status, text, filename=None):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            body = HTML_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/status":
            running = is_register_running()
            stats = get_log_stats()
            cfg = load_config()
            acc_data = get_accounts_parsed()
            proxies_list = load_proxies_file()
            self.send_json(200, {
                "running": running,
                "stats": stats,
                "accounts_count": acc_data["count"],
                "proxy_count": len(proxies_list),
                "proxy_text": "\n".join(proxies_list),
                "proxy_error": stats.get("proxy_error", ""),
                "config": {
                    "register_count": cfg.get("register_count", 100),
                    "email_provider": cfg.get("email_provider", "yyds"),
                    "yyds_api_key": cfg.get("yyds_api_key", ""),
                    "proxy": cfg.get("proxy", "")
                }
            })
            return

        if path == "/api/logs":
            if os.path.exists(LOG_FILE):
                try:
                    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        tail_lines = lines[-200:]
                        self.send_text(200, "".join(tail_lines))
                        return
                except Exception as exc:
                    self.send_text(500, f"读取日志错误: {exc}")
                    return
            self.send_text(200, "暂无日志文件")
            return

        if path == "/api/accounts_json":
            acc_data = get_accounts_parsed()
            self.send_json(200, acc_data)
            return

        if path == "/api/download_accounts":
            acc_data = get_accounts_parsed()
            filename = f"grok_accounts_all_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            self.send_text(200, acc_data["raw_text"], filename=filename)
            return

        self.send_text(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b""

        if path == "/api/start":
            if not is_register_running():
                cmd = f"nohup bash -c 'cd {REGISTER_DIR} && printf \"start\\n\" | xvfb-run -a ./venv/bin/python grok_register_ttk.py cli' >> {LOG_FILE} 2>&1 &"
                subprocess.Popen(cmd, shell=True)
                self.send_json(200, {"ok": True, "msg": "注册进程已成功启动！"})
            else:
                self.send_json(200, {"ok": False, "msg": "注册流程已在后台运行中，无需重复启动"})
            return

        if path == "/api/stop":
            subprocess.run("pkill -9 -f grok_register_ttk 2>/dev/null || true", shell=True)
            subprocess.run("pkill -9 Xvfb 2>/dev/null || true", shell=True)
            self.send_json(200, {"ok": True, "msg": "注册进程已停止"})
            return

        if path == "/api/config":
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                proxy_text = data.get("proxy_list_text", "")
                lines = [l.strip() for l in proxy_text.splitlines() if l.strip()]
                save_proxies_file(lines)

                cfg_update = {
                    "register_count": data.get("register_count", 100),
                    "email_provider": data.get("email_provider", "yyds"),
                    "yyds_api_key": data.get("yyds_api_key", "").strip()
                }
                cfg = load_config()
                cfg.update(cfg_update)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)

                self.send_json(200, {"ok": True})
            except Exception as exc:
                self.send_json(400, {"error": str(exc)})
            return

        self.send_text(404, "Not Found")

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), WebConsoleHandler)
    print(f"[+] Grok Register Web Console v3.3 运行在 http://0.0.0.0:{PORT}")
    server.serve_forever()
