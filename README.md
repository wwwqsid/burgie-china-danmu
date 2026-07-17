# Burgie 直播弹幕助手

基于 BLR 1.02 逆向重写，支持五大直播平台的弹幕读取与游戏互动。

## ✨ 支持平台

| 平台 | 连接方式 | 需要登录 |
|------|---------|---------|
| 抖音 Douyin | WebSocket 拦截 | 否 |
| B站 哔哩哔哩 | WebSocket 拦截 | 否 |
| 小红书 XHS | WebSocket 拦截 | 否 |
| 快手 Kuaishou | WebSocket 拦截 + Protobuf 解析 | 否 |
| 视频号 WeChat | HTTP 响应拦截 + WebSocket | 需微信扫码（主播账号） |

## 🎮 配合游戏

[Burgie's Cozy Kitchen](https://heynaugames.com/burgie-commands) 直播做饭游戏，弹幕指令包括点餐、投诉、换皮肤等。

## 🚀 使用方法

### 方式一：直接运行 Python 脚本

1. 安装 Python 3.10+
2. 安装依赖：`pip install playwright`
3. 安装 Chromium：`playwright install chromium`
4. 双击 `启动弹幕助手.bat`

### 方式二：打包为 exe

```bash
pip install pyinstaller
pyinstaller "Burgie弹幕助手.spec" --noconfirm
```

打包结果在 `dist/Burgie弹幕助手/` 目录下。

## 📋 弹幕指令

| 指令 | 用途 |
|------|------|
| `!Burgie [食材]` | 点一个汉堡 |
| `!Bell` | 按铃铛 |
| `!Skin {性别} {动物}` | 更换皮肤（订阅者/VIP） |
| `!Leave` | 离开柜台 |
| `!Dirty` | 投诉食物碰地 |
| `!Fire` | 投诉起火 |
| `!Noise` | 投诉按铃铛 |

完整指令列表见 [官网](https://heynaugames.com/burgie-commands)。

## 🔧 技术栈

- **Python** + **Tkinter**（GUI）
- **Playwright**（浏览器自动化 / WebSocket 拦截）
- **Protobuf** 手动解析（无第三方 protobuf 库依赖）
- **IRC Server**（本地 TCP 转发弹幕到游戏）

## 📄 许可

本项目基于 HeyNau Games 的 BLR 1.02 逆向重写，仅供学习交流使用。

## 🤖 关于本项目

本项目的代码修改、功能扩展、Bug 修复、打包配置以及本 README 文件均由 **WorkBuddy AI** 协助完成。

- 代码重构与五平台适配：WorkBuddy AI
- PyInstaller 打包配置与 exe 生成：WorkBuddy AI
- 视频号弹幕解析调试：WorkBuddy AI
- 本 README.md 文件撰写：WorkBuddy AI

如需了解 WorkBuddy，请访问 [codebuddy.cn](https://www.codebuddy.cn)
