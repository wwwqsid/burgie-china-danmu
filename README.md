[English](README_EN.md) | 简体中文

> ⚠️ **本文件由 WorkBuddy AI 撰写。**

# Burgie 直播弹幕助手

> 本项目源自原作者 **HeyNau Games** 的 [BLR (Burgie's Livestream Reader) 1.02](https://steamcommunity.com/app/3314340/discussions/0/561408449130437193/) 插件。

> 📌 **仓库地址**：[GitHub](https://github.com/wwwqsid/burgie-china-danmu) | [Gitee](https://gitee.com/wwwqsid/burgie-china-danmu)

原插件已支持抖音、B站、小红书三大平台。本项目在原插件基础上做了以下 **4 项修改**（由 WorkBuddy AI 协助完成）：

1. **新增快手平台** — WebSocket 拦截 + Protobuf 解析
2. **新增微信视频号平台** — HTTP 响应拦截 + WebSocket 双通道
3. **界面改为中文** — 适配中国用户使用习惯
4. **新增浏览器显示** — 可直观查看拦截过程

## ✨ 支持平台

| 平台 | 来源 | 连接方式 | 需要登录 |
|------|------|---------|---------|
| 抖音 Douyin | 原作者 | WebSocket 拦截 | 否 |
| B站 哔哩哔哩 | 原作者 | WebSocket 拦截 | 否 |
| 小红书 XHS | 原作者 | WebSocket 拦截 | 否 |
| 快手 Kuaishou | ✨ 新增 | WebSocket 拦截 + Protobuf 解析 | 否 |
| 视频号 WeChat | ✨ 新增 | HTTP 响应拦截 + WebSocket | 需微信扫码（主播账号） |

## 🎮 配合游戏

[Burgie's Cozy Kitchen](https://heynaugames.com/burgie-commands) 直播做饭游戏，弹幕指令包括点餐、投诉、换皮肤等。

## 🚀 使用方法

### 方式零：直接下载 exe（推荐 ⭐）

前往 [Releases 页面](https://github.com/wwwqsid/burgie-china-danmu/releases/tag/v1.02) 下载 `Burgie弹幕助手-v1.02.zip`，解压后双击 `Burgie弹幕助手.exe` 即可运行，无需安装 Python。

### 方式一：从源码运行

1. 安装 Python 3.10+
2. 安装依赖：`pip install playwright`
3. 安装 Chromium：`playwright install chromium`
4. 双击 `启动弹幕助手.bat`

### 方式二：自行打包为 exe

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

本项目基于 HeyNau Games 的 BLR 1.02 修改，仅供学习交流使用。

## 🤖 关于本项目

本项目仅在原作者 BLR 1.02 基础上做了 4 项修改（新增快手平台、新增视频号平台、界面中文化、新增浏览器显示），以及 PyInstaller 打包配置和本文档，均由 **WorkBuddy AI** 协助完成。

- 快手平台弹幕解析：WorkBuddy AI
- 视频号平台弹幕解析：WorkBuddy AI
- 界面中文化：WorkBuddy AI
- 浏览器显示功能：WorkBuddy AI
- PyInstaller 打包配置与 exe 生成：WorkBuddy AI
- 本 README.md 文件撰写：WorkBuddy AI

如需了解 WorkBuddy，请访问 [codebuddy.cn](https://www.codebuddy.cn)

## 📬 联系方式

- Email: wwwqsid@outlook.com
