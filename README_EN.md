English | [简体中文](README.md)

> ⚠️ **This document is written by WorkBuddy AI.**

# Burgie China Danmu Assistant

> This project is derived from the original author **HeyNau Games**' [BLR (Burgie's Livestream Reader) 1.02](https://steamcommunity.com/app/3314340/discussions/0/561408449130437193/) plugin.

The original plugin already supported three platforms: Douyin, Bilibili, and Xiaohongshu. This project makes the following **4 modifications** to the original plugin (assisted by WorkBuddy AI):

1. **Added Kuaishou platform** — WebSocket interception + Protobuf parsing
2. **Added WeChat Channels platform** — HTTP response interception + WebSocket dual-channel
3. **Chinese localization** — UI adapted for Chinese users
4. **Added browser display** — Visual inspection of the interception process

## ✨ Supported Platforms

| Platform | Source | Connection Method | Login Required |
|----------|--------|------------------|----------------|
| Douyin (TikTok China) | Original Author | WebSocket interception | No |
| Bilibili | Original Author | WebSocket interception | No |
| Xiaohongshu (RED) | Original Author | WebSocket interception | No |
| Kuaishou | ✨ New | WebSocket interception + Protobuf parsing | No |
| WeChat Channels (视频号) | ✨ New | HTTP response interception + WebSocket | Yes (WeChat QR scan, streamer account) |

## 🎮 How It Works

The tool reads live chat messages from Chinese streaming platforms and forwards them to the game **Burgie's Cozy Kitchen** via a local IRC server. Viewers can order burgers, ring bells, change skins, and file complaints — all through chat commands.

## 🚀 Getting Started

### Option 0: Download Executable (Recommended ⭐)

Go to the [Releases page](https://github.com/wwwqsid/burgie-china-danmu/releases/tag/v1.02) and download `Burgie弹幕助手-v1.02.zip`. Extract and run `Burgie弹幕助手.exe` — no Python installation required.

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

This project is a modification of HeyNau Games' BLR 1.02, for educational and learning purposes only.

## 🤖 About This Project

This project only makes 4 modifications to the original BLR 1.02 plugin (adding Kuaishou platform, adding WeChat Channels platform, Chinese localization, and browser display), plus PyInstaller packaging configuration and this document, all completed with the assistance of **WorkBuddy AI**.

- Kuaishou platform danmaku parsing: WorkBuddy AI
- WeChat Channels platform danmaku parsing: WorkBuddy AI
- Chinese localization: WorkBuddy AI
- Browser display feature: WorkBuddy AI
- PyInstaller packaging config & exe generation: WorkBuddy AI
- This README.md was written by: WorkBuddy AI

To learn more about WorkBuddy, visit [codebuddy.cn](https://www.codebuddy.cn)

## 📬 Contact

- Email: wwwqsid@outlook.com
