#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Burgie 直播弹幕助手 (含快手支持)
基于 BLR 1.02 逆向重写 + 快手平台扩展
原始作者: HeyNau / BLR 插件作者
快手支持: 通过 WebSocket 拦截 + Protobuf 解析
"""

import sys, os, re, gzip, json, zlib, struct, asyncio, socket, threading, base64
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

# ─── Chromium 路径设置 ───
def find_chromium_exe():
    """查找 bundled chromium 可执行文件，绕过 Playwright 版本检查"""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        # PyInstaller onedir 模式: 数据在 _internal 下; onefile 或旧版: 在 exe 同级
        candidates = [
            os.path.join(exe_dir, 'chromium_data'),
            os.path.join(exe_dir, '_internal', 'chromium_data'),
        ]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = [os.path.join(base, 'chromium_data')]
    for cdata in candidates:
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = cdata
        if os.path.isdir(cdata):
            for d in os.listdir(cdata):
                if d.startswith('chromium-') and not d.startswith('chromium_headless'):
                    exe = os.path.join(cdata, d, 'chrome-win64', 'chrome.exe')
                    if os.path.isfile(exe):
                        return exe
    return None

CHROMIUM_EXE = find_chromium_exe()

# ─── Protobuf 解析工具 ───
def read_varint(data, pos):
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, pos

def proto_fields(data):
    """解析 raw protobuf bytes → dict, 所有值都是 list"""
    fields = {}
    pos = 0
    try:
        while pos < len(data):
            tag, pos = read_varint(data, pos)
            field = tag >> 3
            wt = tag & 7
            if wt == 0:  # varint
                v, pos = read_varint(data, pos)
                fields.setdefault(field, []).append(v)
            elif wt == 2:  # length-delimited
                l, pos = read_varint(data, pos)
                fields.setdefault(field, []).append(data[pos:pos+l])
                pos += l
            elif wt == 1:  # 64-bit
                pos += 8
            elif wt == 5:  # 32-bit
                pos += 4
            else:
                break
    except:
        pass
    return fields

def pS(f, n):
    v = f.get(n, [None])[0]
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8')
        except:
            return ''
    return ''

def pB(f, n):
    v = f.get(n, [b''])[0]
    if isinstance(v, bytes):
        return v
    return b''

def pI(f, n):
    v = f.get(n, [0])[0]
    if isinstance(v, int):
        return v
    return 0

def pL(f, n):
    """取重复字段的完整列表"""
    return f.get(n, [])

def gunzip(d):
    try:
        return gzip.decompress(d)
    except:
        return d

# ─── IRC 配置 ───
IRC_PORT = 6667
IRC_CHANNEL = '#live'

# ─── IRC 服务器 ───
class IRCServer:
    def __init__(self, log_fn=None):
        self.clients = []
        self.lock = threading.Lock()
        self.log = log_fn or print
        self._server = None
        self._running = False

    def start(self):
        self._running = True
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(('0.0.0.0', IRC_PORT))
        self._server.listen(5)
        self.log(f'[IRC] 服务器已启动 localhost:{IRC_PORT}')
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self._running = False
        if self._server:
            self._server.close()

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server.accept()
                self.log(f'[IRC] 客户端来自 {addr[0]}')
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except:
                break

    def _handle(self, conn):
        conn.settimeout(5)
        nick = 'unity'
        try:
            buf = ''
            while self._running:
                try:
                    chunk = conn.recv(4096).decode('utf-8', 'ignore')
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                lines = buf.split('\n')
                buf = lines[-1]
                for line in lines[:-1]:
                    line = line.strip()
                    if line.startswith('NICK '):
                        nick = line[5:]
                    elif line.startswith('USER '):
                        conn.sendall(f':BLRMod 001 {nick} :Welcome\r\n'.encode())
                        conn.sendall(f':BLRMod 376 {nick} :End of MOTD\r\n'.encode())
                        conn.sendall(f':{nick}!{nick}@BLRMod JOIN {IRC_CHANNEL}\r\n'.encode())
                        with self.lock:
                            self.clients.append(conn)
                        self.log(f'[IRC] {nick} 已加入')
        except Exception as e:
            self.log(f'[IRC] 错误: {e}')
        finally:
            conn.close()

    def _keepalive(self, conn, nick):
        while self._running:
            try:
                data = conn.recv(4096).decode('utf-8', 'ignore').strip()
                if data.startswith('PING'):
                    conn.sendall(f'PONG :BLRMod\r\n'.encode())
                elif not data:
                    break
            except:
                break
        with self.lock:
            if conn in self.clients:
                self.clients.remove(conn)
        self.log(f'[IRC] {nick} 已断开')
        conn.close()

    def broadcast(self, event_type, user, text, extra=''):
        line = f'{event_type}|{user}|{text}|{extra}'
        raw = f':{user.replace(" ", "_").replace("\r", "").replace("\n", "")}!live@BLRMod PRIVMSG {IRC_CHANNEL} :{line}\r\n'
        data = raw.encode('utf-8')
        dead = []
        with self.lock:
            for c in self.clients:
                try:
                    c.sendall(data)
                except:
                    dead.append(c)
            for c in dead:
                if c in self.clients:
                    self.clients.remove(c)

# ─── 抖音弹幕处理 ───
def process_douyin_frame(raw, irc, log_fn):
    frame = proto_fields(raw)
    pt = pI(frame, 1)
    pay = pB(frame, 3)
    if pt == 0xa and pay:
        pay = gunzip(pay)
    elif pay:
        pass
    mb = proto_fields(pay) if pay else {}
    handle_douyin_msg(mb, irc, log_fn)

def handle_douyin_msg(data, irc, log_fn):
    f = data
    method = pS(f, 2)
    if method == 'WebcastChatMessage':
        pay = pB(f, 5)
        if pay:
            mf = proto_fields(pay)
            uf = proto_fields(pB(mf, 2))
            nick = pS(uf, 1) or '?'
            text = pS(mf, 1)
            irc.broadcast('CHAT', nick, text)
    elif method == 'WebcastGiftMessage':
        pay = pB(f, 5)
        if pay:
            mf = proto_fields(pay)
            uf = proto_fields(pB(mf, 7))
            nick = pS(uf, 1) or '?'
            gf = proto_fields(pB(mf, 1))
            gift = pS(gf, 1) or 'gift'
            cnt = pI(mf, 3) or 1
            irc.broadcast('GIFT', nick, gift, str(cnt))
    elif method == 'WebcastLikeMessage':
        pay = pB(f, 5)
        if pay:
            mf = proto_fields(pay)
            uf = proto_fields(pB(mf, 5))
            nick = pS(uf, 1) or '?'
            irc.broadcast('LIKE', nick, '')
    elif method == 'WebcastMemberMessage':
        pay = pB(f, 5)
        if pay:
            mf = proto_fields(pay)
            uf = proto_fields(pB(mf, 3))
            nick = pS(uf, 1) or '?'
            irc.broadcast('JOIN', nick, '')

async def run_douyin(room_id, irc, log_fn, stop_event):
    from playwright.async_api import async_playwright
    log_fn(f'[抖音] 正在连接房间 {room_id}...')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=CHROMIUM_EXE, args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
        ])
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
            locale='zh-CN',
        )
        page = await ctx.new_page()

        async def on_ws(ws):
            url = ws.url
            if 'webcast' not in url:
                return
            log_fn('[抖音] ✓ 已连接 — 正在接收弹幕')
            async def on_frame(payload):
                raw = payload if isinstance(payload, bytes) else payload.encode('utf-8') if isinstance(payload, str) else b''
                if raw:
                    process_douyin_frame(raw, irc, log_fn)
            ws.on('framereceived', on_frame)
            ws.on('close', lambda: log_fn('[抖音] WebSocket 已断开'))

        page.on('websocket', on_ws)
        await page.goto(f'https://live.douyin.com/{room_id}', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        log_fn('[抖音] 页面已加载 ✓')
        while not stop_event.is_set():
            await page.wait_for_timeout(500)
        await ctx.close()
        await browser.close()

# ─── 小红书弹幕处理 ───
def handle_xhs_msg(cd, irc, log_fn):
    msg_type = cd.get('type', '')
    if msg_type == 'text':
        profile = cd.get('profile', {})
        nick = profile.get('nickname', '?')
        content = cd.get('content', {})
        text = content.get('message', content.get('desc', ''))
        irc.broadcast('CHAT', nick, text)
    elif msg_type == 'gift_comment':
        user = cd.get('send_user_info', {})
        nick = user.get('nick_name', '?')
        gift = cd.get('gift_info', {})
        name = gift.get('name', 'gift')
        cnt = gift.get('count', 1)
        irc.broadcast('GIFT', nick, name, str(cnt))
    elif msg_type == 'gift_dock_and_effect':
        pass
    elif msg_type == 'audience_join_v2':
        profile = cd.get('profile', {})
        nick = profile.get('nickname', '?')
        irc.broadcast('JOIN', nick, '')
    elif msg_type == 'praise':
        profile = cd.get('profile', {})
        nick = profile.get('nickname', '?')
        irc.broadcast('LIKE', nick, '')
    elif msg_type == 'follow_emcee':
        profile = cd.get('profile', {})
        nick = profile.get('nickname', '?')
        irc.broadcast('follow', nick, '')

async def run_xhs(room_id, irc, log_fn, stop_event):
    from playwright.async_api import async_playwright
    log_fn(f'[小红书] 正在打开房间 {room_id}...')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=CHROMIUM_EXE, args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
        ])
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
        )
        page = await ctx.new_page()

        async def on_ws(ws):
            url = ws.url
            if 'xiaohongshu' not in url:
                return
            log_fn('[小红书] ✓ 已连接 — 正在接收弹幕')
            async def on_frame(payload):
                if isinstance(payload, str):
                    try:
                        data = json.loads(payload)
                        items = data.get('data', {}).get('items', [])
                        for item in items:
                            raw = item.get('b', '')
                            if raw:
                                pad = 4 - len(raw) % 4
                                decoded = base64.b64decode(raw + '=' * pad)
                                inner = json.loads(decoded.decode('utf-8', 'ignore'))
                                cd = inner.get('customData', inner)
                                if isinstance(cd, str):
                                    cd = json.loads(cd)
                                handle_xhs_msg(cd, irc, log_fn)
                    except Exception as e:
                        pass
            ws.on('framereceived', on_frame)
            ws.on('close', lambda: log_fn('[小红书] WebSocket 已断开'))

        page.on('websocket', on_ws)
        await page.goto(f'https://www.xiaohongshu.com/livestream/{room_id}', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        log_fn('[小红书] 页面已加载 ✓')
        while not stop_event.is_set():
            await page.wait_for_timeout(500)
        await ctx.close()
        await browser.close()

# ─── B站弹幕处理 ───
BILI_WS = 'wss://broadcastlv.chat.bilibili.com/sub'

def bili_pack(data, op=2, ver=1):
    if isinstance(data, str):
        data = data.encode('utf-8')
    total = 16 + len(data)
    header = struct.pack('>IHHII', total, 16, ver, op, 1)
    return header + data

def bili_unpack(data):
    packets = []
    pos = 0
    while pos < len(data):
        if pos + 16 > len(data):
            break
        total, hlen, ver, op, seq = struct.unpack('>IHHII', data[pos:pos+16])
        body = data[pos+16:pos+total]
        packets.append((ver, op, body))
        pos += total
    return packets

def bili_get_room_info(room_id):
    url = f'https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={room_id}'
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    r = urlopen(req, timeout=10)
    data = json.loads(r.read())
    token = data['data']['token']
    host = data['data']['host_list'][0]['host']
    port = data['data']['host_list'][0]['wss_port']
    return f'wss://{host}:{port}/sub', token

def handle_bili_cmd(body, irc, log_fn):
    c = json.loads(body)
    cmd = c.get('cmd', '')
    if cmd == 'DANMU_MSG':
        info = c.get('info', [])
        text = info[1] if len(info) > 1 else '?'
        nick = info[2][1] if len(info) > 2 and len(info[2]) > 1 else '?'
        irc.broadcast('CHAT', nick, text)
    elif cmd == 'SEND_GIFT':
        d = c.get('data', {})
        nick = d.get('uname', '?')
        gift = d.get('giftName', 'gift')
        cnt = d.get('num', 1)
        irc.broadcast('GIFT', nick, gift, str(cnt))
    elif cmd == 'SUPER_CHAT_MESSAGE':
        d = c.get('data', {})
        info = d.get('user_info', {})
        nick = info.get('uname', '?')
        text = d.get('message', '')
        price = d.get('price', 0)
        irc.broadcast('SC', nick, f'[{price}元] {text}')
    elif cmd == 'INTERACT_WORD':
        d = c.get('data', {})
        if d.get('msg_type') == 1:
            nick = d.get('uname', '?')
            irc.broadcast('JOIN', nick, '')
    elif cmd == 'GUARD_BUY':
        d = c.get('data', {})
        nick = d.get('username', '?')
        irc.broadcast('guard', nick, '')

async def run_bilibili(room_id, irc, log_fn, stop_event):
    from playwright.async_api import async_playwright
    log_fn(f'[B站] 正在打开房间 {room_id}...')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=CHROMIUM_EXE, args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
        ])
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
        )
        page = await ctx.new_page()

        async def on_ws(ws):
            url = ws.url
            if 'broadcastlv.chat.bilibili' not in url:
                return
            log_fn('[B站] ✓ WebSocket 已连接 — 正在接收弹幕')
            async def on_frame(payload):
                raw = payload if isinstance(payload, bytes) else payload.encode('utf-8') if isinstance(payload, str) else b''
                if not raw:
                    return
                for ver, op, body in bili_unpack(raw):
                    if op == 5:
                        if ver == 0:
                            pass
                        elif ver == 2:
                            try:
                                body = zlib.decompress(body)
                            except:
                                try:
                                    import brotlicffi
                                    body = brotlicffi.decompress(body)
                                except:
                                    continue
                        try:
                            handle_bili_cmd(body, irc, log_fn)
                        except Exception as e:
                            pass
            ws.on('framereceived', on_frame)
            ws.on('close', lambda: log_fn('[B站] WebSocket 已断开'))

        page.on('websocket', on_ws)
        await page.goto(f'https://live.bilibili.com/{room_id}', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        log_fn('[B站] 页面已加载 ✓')
        while not stop_event.is_set():
            await page.wait_for_timeout(500)
        await ctx.close()
        await browser.close()

# ─── 快手弹幕处理 (新增) ───
def process_kuaishou_frame(raw, irc, log_fn):
    """解析快手 SocketMessage protobuf"""
    try:
        sm = proto_fields(raw)
        payload_type = pI(sm, 1)
        compression_type = pI(sm, 2)
        payload = pB(sm, 3)

        if not payload:
            log_fn(f'[快手] [调试] payloadType={payload_type} compression={compression_type} payload 为空')
            return

        # 解压
        if compression_type == 2:  # GZIP
            payload = gunzip(payload)

        log_fn(f'[快手] [调试] payloadType={payload_type} compression={compression_type} payload_len={len(payload)}')

        if payload_type == 310:  # SC_FEED_PUSH — 弹幕/礼物/点赞聚合推送
            handle_kuaishou_feed(payload, irc, log_fn)
        elif payload_type == 300:  # SC_ENTER_ROOM_ACK
            log_fn('[快手] ✓ 已进入直播间')
        elif payload_type == 1:  # heartbeat ack
            pass  # 心跳回复，不打日志
    except Exception as e:
        log_fn(f'[快手] [调试] 解析异常: {e}')

def handle_kuaishou_feed(data, irc, log_fn):
    """解析 SCWebFeedPush — 提取弹幕、礼物、点赞"""
    try:
        fp = proto_fields(data)
    except:
        return

    # 弹幕消息 (field 5 = commentFeeds, repeated WebCommentFeed)
    for comment_bytes in pL(fp, 5):
        if not isinstance(comment_bytes, bytes):
            continue
        try:
            cf = proto_fields(comment_bytes)
            user_bytes = pB(cf, 2)  # SimpleUserInfo
            content = pS(cf, 3)    # 弹幕内容
            if user_bytes:
                uf = proto_fields(user_bytes)
                nick = pS(uf, 2) or '?'  # userName
            else:
                nick = '?'
            if content:
                irc.broadcast('CHAT', nick, content)
        except:
            pass

    # 礼物消息 (field 9 = giftFeeds, repeated WebGiftFeed)
    for gift_bytes in pL(fp, 9):
        if not isinstance(gift_bytes, bytes):
            continue
        try:
            gf = proto_fields(gift_bytes)
            user_bytes = pB(gf, 2)  # SimpleUserInfo
            gift_id = pI(gf, 4)     # giftId
            batch_size = pI(gf, 7)  # batchSize
            combo_count = pI(gf, 8) # comboCount
            if user_bytes:
                uf = proto_fields(user_bytes)
                nick = pS(uf, 2) or '?'
            else:
                nick = '?'
            count = max(batch_size, combo_count, 1)
            gift_name = f'gift_{gift_id}'
            irc.broadcast('GIFT', nick, gift_name, str(count))
        except:
            pass

    # 点赞消息 (field 8 = likeFeeds, repeated WebLikeFeed)
    for like_bytes in pL(fp, 8):
        if not isinstance(like_bytes, bytes):
            continue
        try:
            lf = proto_fields(like_bytes)
            user_bytes = pB(lf, 2)  # SimpleUserInfo
            if user_bytes:
                uf = proto_fields(user_bytes)
                nick = pS(uf, 2) or '?'
            else:
                nick = '?'
            irc.broadcast('LIKE', nick, '')
        except:
            pass

    # 分享消息 (field 12 = shareFeeds)
    for share_bytes in pL(fp, 12):
        if not isinstance(share_bytes, bytes):
            continue
        try:
            sf = proto_fields(share_bytes)
            user_bytes = pB(sf, 2)
            if user_bytes:
                uf = proto_fields(user_bytes)
                nick = pS(uf, 2) or '?'
            else:
                nick = '?'
            irc.broadcast('SHARE', nick, '')
        except:
            pass

async def run_kuaishou(room_id, irc, log_fn, stop_event):
    """快手直播弹幕读取 — 通过 Playwright 拦截 WebSocket"""
    from playwright.async_api import async_playwright
    log_fn(f'[快手] 正在连接房间 {room_id}...')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=CHROMIUM_EXE, args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--mute-audio',
        ])
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
            locale='zh-CN',
        )
        page = await ctx.new_page()

        async def on_ws(ws):
            url = ws.url
            log_fn(f'[快手] [调试] 检测到 WebSocket: {url}')
            if 'kuaishou' not in url and 'live-ws' not in url:
                log_fn(f'[快手] [调试] URL 不匹配，跳过')
                return
            log_fn(f'[快手] ✓ WebSocket 已连接 — {url}')
            log_fn('[快手] ✓ 正在接收弹幕')
            frame_count = 0
            async def on_frame(payload):
                nonlocal frame_count
                frame_count += 1
                raw = payload if isinstance(payload, bytes) else b''
                if raw:
                    if frame_count <= 5:
                        log_fn(f'[快手] [调试] 收到第 {frame_count} 帧，长度 {len(raw)} 字节')
                    process_kuaishou_frame(raw, irc, log_fn)
                else:
                    log_fn(f'[快手] [调试] 第 {frame_count} 帧为空，类型={type(payload).__name__}')
            ws.on('framereceived', on_frame)
            ws.on('close', lambda: log_fn('[快手] WebSocket 已断开'))

        page.on('websocket', on_ws)

        # 监听页面 console 消息
        def on_console(msg):
            log_fn(f'[快手] [Console] {msg.text}')
        page.on('console', on_console)

        # 监听页面导航
        def on_nav(frame):
            log_fn(f'[快手] [导航] {frame.url}')
        page.on('framenavigated', on_nav)

        # 快手直播间 URL
        if room_id.isdigit():
            url = f'https://live.kuaishou.com/u/{room_id}'
        else:
            url = f'https://live.kuaishou.com/u/{room_id}'

        log_fn(f'[快手] [调试] 正在打开: {url}')
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)

        # 检查当前 URL（可能被重定向到登录页）
        current_url = page.url
        log_fn(f'[快手] [调试] 当前页面 URL: {current_url}')

        # 检查页面标题
        title = await page.title()
        log_fn(f'[快手] [调试] 页面标题: {title}')

        log_fn('[快手] 页面已加载 ✓')
        while not stop_event.is_set():
            await page.wait_for_timeout(500)
        await ctx.close()
        await browser.close()

# ─── 微信视频号弹幕处理 (新增) ───
def process_wechat_frame(raw, irc, log_fn):
    """解析微信视频号 WebSocket 消息帧。
    尝试 protobuf 和 JSON 两种格式。
    """
    if not raw or not isinstance(raw, (bytes, bytearray)):
        return

    # 方案1: 尝试 JSON 解析
    try:
        text = raw.decode('utf-8', errors='ignore')
        if text.startswith('{') or text.startswith('['):
            data = json.loads(text)
            _handle_wechat_json(data, irc, log_fn)
            return
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    # 方案2: 尝试 Protobuf 解析
    try:
        sm = proto_fields(raw)
        payload_type = pI(sm, 1)
        payload = pB(sm, 3)

        if payload:
            log_fn(f'[视频号] [调试] protobuf: type={payload_type} payload_len={len(payload)}')

            # 尝试解压
            comp = pI(sm, 2)
            if comp == 2 and payload:  # GZIP
                payload = gunzip(payload)

            # 尝试 JSON payload
            try:
                text = payload.decode('utf-8', errors='ignore')
                if text.startswith('{') or text.startswith('['):
                    data = json.loads(text)
                    _handle_wechat_json(data, irc, log_fn)
                    return
            except:
                pass

            # 尝试嵌套 protobuf
            _handle_wechat_proto(payload, irc, log_fn)
        else:
            # 没有 payload，可能是心跳/ACK
            pass
    except Exception as e:
        # 都失败了，记录前几帧供调试
        log_fn(f'[视频号] [调试] 无法解析帧: len={len(raw)} hex={raw[:32].hex()}')


def _handle_wechat_json(data, irc, log_fn, source='', raw_text=None):
    """处理 JSON 格式的微信视频号消息"""
    try:
        if isinstance(data, dict):
            # 处理 {errCode, errMsg, data} 包装结构
            if 'data' in data and len(data) <= 5 and any(k in data for k in ['errCode', 'errMsg', 'ret', 'code']):
                # 递归处理 data 字段
                _handle_wechat_json(data['data'], irc, log_fn, source, raw_text)
                return

            # 先尝试从字典中直接提取弹幕/礼物/点赞
            if _try_extract_wechat_dict(data, irc, log_fn):
                return

            # 递归查找可能的评论/消息列表
            found_any = False
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    # 只检查可能是消息列表的 key
                    list_keys = ['comment', 'comments', 'message', 'messages', 'msg', 'msgs',
                                 'list', 'data', 'items', 'record', 'records', 'feed', 'feeds',
                                 'chat', 'chats', 'text', 'contentlist']
                    if any(k in key.lower() for k in list_keys):
                        for item in value:
                            if _try_extract_wechat_dict(item, irc, log_fn):
                                found_any = True
            if found_any:
                return

            # 未知类型，记录调试（包含原始内容前300字符）
            if source:
                type_str = data.get('type', data.get('cmd', data.get('msgType', '(none)')))
                preview = raw_text[:300] if raw_text else str(data)[:300]
                log_fn(f'[视频号] [调试] [{source}] 未识别JSON: type={type_str} keys={list(data.keys())[:10]}')
                log_fn(f'[视频号] [调试] [{source}] 内容预览: {preview}')

        elif isinstance(data, list):
            for item in data:
                _handle_wechat_json(item, irc, log_fn, source, raw_text)
    except Exception as e:
        log_fn(f'[视频号] [调试] JSON处理异常: {e}')



def _try_extract_wechat_dict(data, irc, log_fn):
    """尝试从单个字典中提取弹幕/礼物/点赞/进入消息
    返回是否成功提取
    """
    if not isinstance(data, dict):
        return False

    # 收集可能的字段名
    nick_keys = ['nickname', 'nickName', 'userName', 'username', 'name', 'nick', 'user_name', 'viewerName']
    content_keys = ['content', 'text', 'message', 'msg', 'comment', 'body', 'words', 'wording']
    gift_keys = ['giftName', 'giftname', 'gift_name', 'giftId', 'gift_id', 'giftid', 'gift']

    nick = None
    for k in nick_keys:
        if k in data and data[k]:
            nick = data[k]
            break

    content = None
    for k in content_keys:
        if k in data and data[k]:
            content = data[k]
            break

    gift = None
    for k in gift_keys:
        if k in data and data[k]:
            gift = data[k]
            break

    if not nick:
        # 尝试嵌套 user 对象
        user = data.get('user', data.get('userInfo', data.get('fromUser', data.get('viewer', {}))))
        if isinstance(user, dict):
            for k in nick_keys:
                if k in user and user[k]:
                    nick = user[k]
                    break

    if not content and not gift:
        return False

    if not nick:
        nick = '?'

    # 礼物
    if gift or any(k in data for k in gift_keys):
        count = data.get('count', data.get('num', data.get('number', data.get('comboCount', 1))))
        gift_name = str(gift) if gift else 'gift'
        irc.broadcast('GIFT', nick, gift_name, str(count))
        return True

    # 弹幕
    if content and isinstance(content, str):
        irc.broadcast('CHAT', nick, content)
        return True

    # 点赞
    if any(k in data for k in ['like', 'praise', 'heart']):
        irc.broadcast('LIKE', nick, '')
        return True

    # 进入房间
    if any(k in data for k in ['enter', 'join', 'member', 'come']):
        irc.broadcast('JOIN', nick, '')
        return True

    return False



def _handle_wechat_proto(data, irc, log_fn):
    """处理 Protobuf 格式的微信视频号消息"""
    try:
        fp = proto_fields(data)

        # 尝试常见字段位置
        # 弹幕: field 1 或 2 可能是消息列表
        for field_num in [1, 2, 3, 5, 8, 9, 12]:
            items = pL(fp, field_num)
            if not items:
                continue
            for item_bytes in items:
                if not isinstance(item_bytes, (bytes, bytearray)):
                    continue
                try:
                    msg = proto_fields(item_bytes)
                    # 尝试提取用户名和内容
                    nick = pS(msg, 1) or pS(msg, 2) or '?'
                    content = pS(msg, 3) or pS(msg, 5) or pS(msg, 7) or ''

                    # 尝试 JSON 内容
                    if content and (content.startswith('{') or content.startswith('[')):
                        _handle_wechat_json(json.loads(content), irc, log_fn)
                        continue

                    if content and nick != '?':
                        irc.broadcast('CHAT', nick, content)
                except:
                    pass
    except:
        pass


async def run_wechat_channels(room_id, irc, log_fn, stop_event):
    """微信视频号直播弹幕读取 — 通过 Playwright 拦截 WebSocket + HTTP 响应

    与其他平台不同：
    - 需要打开视频号助手后台 (channels.weixin.qq.com)
    - 需要微信扫码登录（主播账号）
    - room_id 参数在此平台不使用，留空即可
    - 视频号弹幕主要通过 HTTP API 返回，同时监听 WebSocket 作为备用
    """
    from playwright.async_api import async_playwright
    log_fn('[视频号] 正在启动浏览器...')
    log_fn('[视频号] ⚠️ 请在弹出的浏览器中扫码登录微信视频号')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=CHROMIUM_EXE, args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--mute-audio',
        ])
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
        )
        page = await ctx.new_page()

        ws_connected = False
        frame_count = 0
        resp_count = 0

        async def on_ws(ws):
            nonlocal ws_connected
            url = ws.url
            log_fn(f'[视频号] [调试] 检测到 WebSocket: {url}')

            # 匹配微信视频号相关 WebSocket
            ws_keywords = ['weixin', 'channels', 'live.weixin', 'finder']
            if not any(kw in url.lower() for kw in ws_keywords):
                log_fn(f'[视频号] [调试] URL 不匹配关键词，跳过')
                return

            ws_connected = True
            log_fn(f'[视频号] ✓ WebSocket 已连接 — {url}')
            log_fn('[视频号] ✓ 正在监听弹幕...')

            async def on_frame(payload):
                nonlocal frame_count
                frame_count += 1
                raw = payload if isinstance(payload, bytes) else b''
                if raw:
                    if frame_count <= 10:
                        log_fn(f'[视频号] [调试] 收到第 {frame_count} 帧，长度 {len(raw)} 字节')
                    process_wechat_frame(raw, irc, log_fn)

            ws.on('framereceived', on_frame)
            ws.on('close', lambda: log_fn('[视频号] WebSocket 已断开'))

        page.on('websocket', on_ws)

        # 监听 HTTP 响应 — 视频号弹幕主要通过 API 返回
        async def on_response(response):
            nonlocal resp_count
            url = response.url

            # 只关注视频号相关 API
            resp_keywords = ['channels.weixin.qq.com', 'live.weixin.qq.com', 'finder.weixin.qq.com']
            if not any(kw in url.lower() for kw in resp_keywords):
                return

            # 过滤静态资源
            content_type = ''
            try:
                content_type = response.headers.get('content-type', '')
            except:
                pass
            if content_type and not any(t in content_type for t in ['json', 'javascript', 'text/plain']):
                return

            resp_count += 1
            if resp_count <= 50:
                log_fn(f'[视频号] [调试] [Response] {url[:120]}')

            try:
                body = await response.body()
                if not body:
                    return

                # 尝试 JSON 解析
                text = body.decode('utf-8', errors='ignore')
                if text.startswith('{') or text.startswith('['):
                    try:
                        data = json.loads(text)
                        _handle_wechat_json(data, irc, log_fn, source='HTTP', raw_text=text)
                    except json.JSONDecodeError:
                        # JSON 解析失败，可能是 protobuf 或压缩数据
                        if resp_count <= 20:
                            log_fn(f'[视频号] [调试] [Response] JSON解析失败，可能是二进制: {url[:120]}')
                else:
                    # 不是 JSON，记录前200字符
                    if resp_count <= 20:
                        log_fn(f'[视频号] [调试] [Response] 非JSON响应: {url[:120]} preview={text[:200]}')
            except Exception as e:
                log_fn(f'[视频号] [调试] 读取响应失败: {e}')


        page.on('response', on_response)

        # 监听页面 console 消息
        console_skip_patterns = ['该方法即将废弃', 'absoluteFormat', 'deprecated']
        def on_console(msg):
            text = msg.text if hasattr(msg, 'text') else str(msg)
            if any(p in text for p in console_skip_patterns):
                return
            log_fn(f'[视频号] [Console] {text}')
        page.on('console', on_console)

        # 监听页面导航
        def on_nav(frame):
            log_fn(f'[视频号] [导航] {frame.url}')
        page.on('framenavigated', on_nav)

        # 打开视频号助手后台
        url = 'https://channels.weixin.qq.com/platform/live/liveBuild'
        log_fn(f'[视频号] [调试] 正在打开: {url}')
        await page.goto(url, wait_until='domcontentloaded')

        # 等待用户扫码登录
        log_fn('[视频号] 📱 请在浏览器中扫码登录微信视频号')
        log_fn('[视频号] 登录后进入直播间管理页面，开始直播即可接收弹幕')

        # 等待 WebSocket 或 HTTP 响应（最多等 300 秒 = 5 分钟给用户扫码）
        for i in range(600):  # 600 * 0.5s = 300s
            if stop_event.is_set():
                break
            if ws_connected or resp_count > 0:
                break
            await page.wait_for_timeout(500)

        if not ws_connected and resp_count == 0:
            current_url = page.url
            log_fn(f'[视频号] [调试] 当前页面 URL: {current_url}')
            title = await page.title()
            log_fn(f'[视频号] [调试] 页面标题: {title}')
            if 'login' in current_url.lower():
                log_fn('[视频号] ⚠️ 仍在登录页，请扫码登录')
            log_fn('[视频号] ℹ️ 登录并进入直播管理页面后，弹幕数据会自动获取')
        else:
            log_fn(f'[视频号] ✓ 已连接到视频号后台，开始监听弹幕')

        # 持续等待接收弹幕
        while not stop_event.is_set():
            await page.wait_for_timeout(500)

        log_fn('[视频号] 正在关闭...')
        await ctx.close()
        await browser.close()


# ─── GUI 应用 ───
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Burgie 直播弹幕助手')
        self.root.geometry('620x580')
        self.root.resizable(False, False)
        self.root.configure(bg='#1a1a2e')

        self.irc = IRCServer(self.log)
        self.stop_ev = asyncio.Event()
        self.loop = None
        self.thread = None
        self.connected = False

        self._build_ui()
        self.irc.start()
        self.log('就绪。选择平台，输入房间号或链接，点击连接。')
        self.log(f'游戏内输入 BLRMod 连接 | IRC: localhost:{IRC_PORT} 频道 {IRC_CHANNEL}')

    def _build_ui(self):
        # 标题
        tk.Label(self.root, text='🎮 Burgie 直播弹幕助手',
                 font=('Segoe UI', 16, 'bold'),
                 bg='#1a1a2e', fg='#e94560').pack(pady=(10, 2))

        tk.Label(self.root,
                 text='抖音 / B站 / 小红书 / 快手 / 视频号 直播弹幕读取器',
                 font=('Segoe UI', 9),
                 bg='#1a1a2e', fg='#aaaaaa').pack()

        tk.Label(self.root,
                 text='游戏内输入  BLRMod  即可从 Burgie\'s Cozy Kitchen 连接',
                 font=('Segoe UI', 8),
                 bg='#1a1a2e', fg='#4fc3f7').pack(pady=(0, 8))

        # 平台选择
        pf = tk.Frame(self.root, bg='#1a1a2e')
        pf.pack(pady=5)

        tk.Label(pf, text='平台：', bg='#1a1a2e', fg='white',
                 font=('Segoe UI', 10)).grid(row=0, column=0, padx=(0, 5))

        self.platform_var = tk.StringVar(value='douyin')

        platforms = [
            ('douyin', '抖音 Douyin'),
            ('bilibili', 'B站 哔哩哔哩'),
            ('xhs', '小红书 XHS'),
            ('kuaishou', '快手 Kuaishou'),
            ('wechat', '视频号 WeChat'),
        ]
        for i, (val, label) in enumerate(platforms):
            rb = tk.Radiobutton(pf, text=label, variable=self.platform_var,
                               value=val, bg='#16213e', fg='white',
                               selectcolor='#16213e', activebackground='#16213e',
                               activeforeground='white', font=('Segoe UI', 9),
                               padx=5, pady=2)
            rb.grid(row=0, column=i+1, padx=2)

        # 输入框
        inp_frame = tk.Frame(self.root, bg='#1a1a2e')
        inp_frame.pack(pady=8, padx=20, fill='x')

        tk.Label(inp_frame, text='房间号或链接：', bg='#1a1a2e', fg='white',
                 font=('Segoe UI', 10)).pack(side='left')

        self.entry = tk.Entry(inp_frame, font=('Segoe UI', 11), width=35)
        self.entry.pack(side='left', padx=5, expand=True, fill='x')

        self.btn = tk.Button(self.root, text='连接', command=self.toggle,
                            bg='#e94560', fg='white', font=('Segoe UI', 11, 'bold'),
                            relief='flat', padx=30, pady=5, cursor='hand2')
        self.btn.pack(pady=5)

        # 状态
        self.status_var = tk.StringVar(value='⚫ 未连接')
        tk.Label(self.root, textvariable=self.status_var,
                 bg='#1a1a2e', fg='#aaaaaa', font=('Segoe UI', 10)).pack()

        tk.Label(self.root,
                 text=f'IRC:  localhost:{IRC_PORT}   频道: {IRC_CHANNEL}',
                 bg='#1a1a2e', fg='#4fc3f7', font=('Segoe UI', 8)).pack()

        # 日志
        self.log_box = scrolledtext.ScrolledText(self.root,
            bg='#0f0f23', fg='#cccccc', font=('Consolas', 9),
            height=16, relief='flat', state='disabled')
        self.log_box.pack(pady=8, padx=15, fill='both', expand=True)

        self.log_box.tag_config('chat', foreground='#ffffff')
        self.log_box.tag_config('gift', foreground='#ffd700')
        self.log_box.tag_config('like', foreground='#ff69b4')
        self.log_box.tag_config('join', foreground='#90ee90')
        self.log_box.tag_config('sc', foreground='#ff9800')
        self.log_box.tag_config('sys', foreground='#888888')

    def log(self, msg):
        def _do():
            self.log_box.configure(state='normal')
            ts = datetime.now().strftime('%H:%M:%S')
            tag = 'sys'
            if msg.startswith('💬'):
                tag = 'chat'
            elif msg.startswith('🎁'):
                tag = 'gift'
            elif msg.startswith('❤'):
                tag = 'like'
            elif msg.startswith('👋'):
                tag = 'join'
            elif msg.startswith('⭐'):
                tag = 'sc'
            self.log_box.insert('end', f'[{ts}] {msg}\n', tag)
            self.log_box.see('end')
            self.log_box.configure(state='disabled')
        self.root.after(0, _do)

    def toggle(self):
        if self.connected:
            self.stop()
        else:
            self.start()

    def start(self):
        raw = self.entry.get().strip()
        platform = self.platform_var.get()

        if platform == 'wechat':
            # 视频号不需要房间号，通过扫码登录
            room_id = ''
        elif platform == 'kuaishou':
            # 快手房间号可能是数字或字母数字混合
            if raw.startswith('http'):
                m = re.search(r'live\.kuaishou\.com/(?:u/)?([^/?]+)', raw)
                if m:
                    room_id = m.group(1)
                else:
                    self.log('⚠ 请输入有效的房间号或链接')
                    return
            elif raw:
                room_id = raw
            else:
                self.log('⚠ 请输入有效的房间号或链接')
                return
        else:
            m = re.search(r'(\d{5,})', raw)
            if not m:
                self.log('⚠ 请输入有效的房间号或链接')
                return
            room_id = m.group(1)

        self.connected = True
        self.btn.config(text='断开', bg='#555555')
        self.status_var.set(f'🟡 正在连接 {platform}...')

        async def run(e):
            try:
                if platform == 'bilibili':
                    await run_bilibili(room_id, self.irc, self.log, self.stop_ev)
                elif platform == 'xhs':
                    await run_xhs(room_id, self.irc, self.log, self.stop_ev)
                elif platform == 'kuaishou':
                    await run_kuaishou(room_id, self.irc, self.log, self.stop_ev)
                elif platform == 'wechat':
                    await run_wechat_channels(room_id, self.irc, self.log, self.stop_ev)
                else:
                    await run_douyin(room_id, self.irc, self.log, self.stop_ev)
            except Exception as e:
                self.log(f'[错误] {e}')
            finally:
                self.root.after(0, self._on_stopped)

        def _thread():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(run(self.stop_ev))

        self.thread = threading.Thread(target=_thread, daemon=True)
        self.thread.start()
        self.status_var.set(f'🟢 已连接 — {platform}' + (f' 房间 {room_id}' if room_id else ''))

    def stop(self):
        if self.stop_ev and self.loop:
            self.loop.call_soon_threadsafe(self.stop_ev.set)

    def _on_stopped(self):
        self.connected = False
        self.btn.config(text='连接', bg='#e94560')
        self.status_var.set('⚫ 未连接')
        self.log('[系统] 已断开。')

    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.stop()
        self.irc.stop()
        self.root.destroy()

if __name__ == '__main__':
    App().run()
