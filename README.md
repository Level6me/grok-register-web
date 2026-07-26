# 🚀 Grok Register Web Console

> **自动化 Grok (x.ai) 批量注册机与可视化响应式 Web 控制台**  
> 支持批量代理池轮询、YYDS 验证码自动提取、全量账号去重合并保留与移动端触控适配。

---

## 🌟 核心特性

- 📱 **全响应式移动端自适应**：支持手机、平板与 PC 端流畅访问，自适应暗黑极客主题 UI。
- 🌐 **批量代理池轮询 (Round-Robin)**：支持一行一个批量输入 `IP:PORT:USER:PASS` 或 `http://...` 代理，自动格式化解析并在每次注册时自动轮询轮换。
- 📦 **全量历史账号持久化保留**：多轮注册/重启服务器绝不会擦除历史账号，自动扫描合并所有 `accounts_*.txt` 文件并去重展示。
- 📋 **单元格触控快捷复制**：表格中点击「邮箱」、「密码」或「JWT Token」单元格即可直接复制，全平台浏览器兼容（包含移动端非 HTTPS 场景）。
- ⬇️ **一键批量导出下载**：支持一键导出全量已注册账号文件（txt/json），无缝集成 CLIProxyAPI / grok2api。
- ⚡ **实时运行日志与状态预警**：实时展示轮询日志与成功率统计，内置代理失效红框警告与进程状态感知。

---

## 🛠️ 一键部署与运行

### 方式一：交互式脚本部署（推荐）

在服务器终端执行以下命令，跟随向导完成一键安装与启动：

```bash
git clone https://github.com/Level6me/grok-register-web.git
cd grok-register-web
chmod +x install.sh
./install.sh
```

运行后将弹出交互菜单：
```text
==================================================================
         Grok Register Web Console - 一键部署与管理系统          
                GitHub: Level6me/grok-register-web                
==================================================================
 1) 一键完整安装与部署
 2) 启动 Web 控制台
 3) 停止 Web 控制台与注册进程
 4) 查看运行状态与最新日志
 5) 重新运行交互式配置
 0) 退出
==================================================================
```

### 方式二：手动启动命令

如果你希望手动启动 Web 控制台：

```bash
# 启动 Web 控制台服务（默认监听端口 8318）
nohup python3 web_console.py > console.log 2>&1 &
```

访问地址：`http://你的服务器IP:8318`

---

## ⚙️ 配置文件说明 (`config.json`)

系统可以通过 Web 面板直接在线修改，也可以手动编辑 `config.json`：

```json
{
  "register_count": 100,
  "email_provider": "yyds",
  "yyds_api_key": "AC-xxxxxxxxxxxxxxxx",
  "proxy": "http://user:pass@ip:port",
  "proxy_list": [
    "http://user:pass@ip1:port1",
    "http://user:pass@ip2:port2"
  ]
}
```

---

## 🌐 批量代理格式支持

在 Web 面板的代理池框中，支持直接粘贴以下格式（每行一个）：

1. **原生四段式**：`31.59.20.176:6754:wqvufgny:iw6o3e9x3n8t`
2. **标准 URL 格式**：`http://wqvufgny:iw6o3e9x3n8t@31.59.20.176:6754`
3. **无认证 IP 格式**：`1.2.3.4:8080`

程序会自动规范化解析并在注册时循环轮换（Round-Robin）。

---

## 📄 开源协议与免责声明

本项目仅供自动化研究、测试环境验证及个人学习使用。请勿用于非法用途。使用本工具注册账号请遵守 xAI 及相关服务商的服务条款。
