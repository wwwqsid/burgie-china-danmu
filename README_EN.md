English | [简体中文](README.md)

> ⚠️ **This document is written by WorkBuddy AI.** Code modifications, feature extensions, packaging configuration, and this document were all completed with the assistance of WorkBuddy AI.

# Burgie China Danmu Assistant

> This project is derived from the original author **HeyNau Games**' [BLR (Burgie's Livestream Reader) 1.02](https://steamcommunity.com/app/3314340/discussions/0/561408449130437193/) plugin, reverse-engineered and rewritten with extended support for five major Chinese livestream platforms.

A livestream chat/danmaku reader for Chinese streaming platforms, built for [Burgie's Cozy Kitchen](https://heynaugames.com/burgie-commands) gameplay interaction.

Reverse-engineered and rewritten from BLR 1.02, supporting 5 major Chinese live streaming platforms.

## ✨ Supported Platforms

| Platform | Connection Method | Login Required |
|----------|------------------|----------------|
| Douyin (TikTok China) | WebSocket interception | No |
| Bilibili | WebSocket interception | No |
| Xiaohongshu (RED) | WebSocket interception | No |
| Kuaishou | WebSocket interception + Protobuf parsing | No |
| WeChat Channels (视频号) | HTTP response interception + WebSocket | Yes (WeChat QR scan, streamer account) |

## 🎮 How It Works

The tool reads live chat messages from Chinese streaming platforms and forwards them to the game **Burgie's Cozy Kitchen** via a local IRC server. Viewers can order burgers, ring bells, change skins, and file complaints — all through chat commands.

## 🚀 Getting Started

### Option 1: Run from Source

1. Install Python 3.10+
2. Install dependencies: `pip install playwright`
3. Install Chromium: `playwright install chromium`
4. Run `启动弹幕助手.bat`

### Option 2: Build as Executable

```bash
pip install pyinstaller
pyinstaller "Burgie弹幕助手.spec" --noconfirm
```

The built executable will be in `dist/Burgie弹幕助手/`.

## 📋 Chat Commands

| Command | Description |
|---------|-------------|
| `!Burgie [ingredients]` | Order a burger |
| `!Bell` | Ring the bell |
| `!Skin {gender} {animal}` | Change skin (Subscribers/VIP only) |
| `!Leave` | Leave the counter |
| `!Dirty` | Complain: food touched the floor |
| `!Fire` | Complain: pan is on fire |
| `!Noise` | Complain: too much bell ringing |

Full command list: [Official Site](https://heynaugames.com/burgie-commands)

## 🔧 Tech Stack

- **Python** + **Tkinter** — GUI
- **Playwright** — Browser automation / WebSocket interception
- **Protobuf** — Manual parsing (no third-party protobuf library)
- **IRC Server** — Local TCP relay to forward danmaku to the game

## 📄 License

This project is based on HeyNau Games' BLR 1.02 reverse engineering rewrite, for educational and learning purposes only.

## 🤖 About This Project

Code modifications, feature extensions, bug fixes, packaging configuration, and this README file were all completed with the assistance of **WorkBuddy AI**.

- Code refactoring & 5-platform adaptation: WorkBuddy AI
- PyInstaller packaging config & exe generation: WorkBuddy AI
- WeChat Channels danmaku parsing & debugging: WorkBuddy AI
- This README.md was written by: WorkBuddy AI

To learn more about WorkBuddy, visit [codebuddy.cn](https://www.codebuddy.cn)
