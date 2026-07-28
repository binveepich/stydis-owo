#!/usr/bin/python

from os import execl, name, system
from sys import executable, argv
from signal import signal, SIGINT
from time import sleep, time
from datetime import timedelta
import atexit
import random
import ctypes
from re import findall
import json
import logging
from threading import Lock

from requests import get
import discum
from discord_webhook import DiscordWebhook

from menu import UI
from color import color
from data import data
from gems import gems
from weapons import weapons

# Configure logging
logger = logging.getLogger(__name__)

# Locks & timing
cmd_lock = Lock()
last_global_cmd_time = 0
GLOBAL_DELAY = 5  # tối thiểu 5s giữa mọi lệnh

# Random delay config
wbm = [10, 30]

# Initialize
ui = UI()
client = data()
start_time = time()

last_cmd_time = {}
CMD_COOLDOWN = {
    "hunt": 15,
    "battle": 15,
    "pray": 120
}
errors = []
# Check token
if not hasattr(client, 'token') or not client.token:
    errors.append("TOKEN is missing in settings.json")
# Check channel
if not hasattr(client, 'channel') or not client.channel:
    errors.append("Channel ID is missing in settings.json")
# Nếu có lỗi → in tất cả rồi exit
if errors:
    for err in errors:
        ui.slowPrinting(f"{color.fail} !!! [ERROR] !!! {color.reset} {err}")
        sleep(1)
    raise SystemExit
# Nếu ok hết thì mới chạy tiếp
client.check()

def safe_get(d, *keys):
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d

def move_window_to_center():
    try:
        if name != "nt":
            return

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            return

        # Lấy kích thước màn hình chính (monitor 1)
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)

        # Kích thước window hiện tại
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))

        win_width = rect.right - rect.left
        win_height = rect.bottom - rect.top

        # Tính center
        x = int((screen_width - win_width) / 2)
        y = int((screen_height - win_height) / 2)

        # Move window
        user32.MoveWindow(hwnd, x, y, win_width, win_height, True)

        # Bring to front
        user32.SetForegroundWindow(hwnd)

    except Exception as e:
        logger.error(f"Move window error: {str(e)}")


def trigger_alert(title="ALERT"):
    try:
        if name == "nt":
            ctypes.windll.user32.FlashWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), True
            )
            move_window_to_center() 
        print('\a')

    except Exception as e:
        logger.error(f"Alert trigger error: {str(e)}")

def fatal_error(msg: str):
    logger.error(msg)
    ui.slowPrinting(f"{color.fail}[FATAL ERROR]{color.reset} {msg}")
    logger.error(f"[FATAL] {msg}")
    trigger_alert("!!! FATAL ERROR !!!")

    try:
        input(f"\n{color.warning}Nhấn ENTER để thoát...{color.reset}")
    except:
        pass

    raise SystemExit

def signal_handler(sig: object, frame: object):
    sleep(0.5)
    logger.info("Detected Ctrl + C, Stopping...")
    ui.slowPrinting(f"\n{color.fail}[INFO] {color.reset}Detected Ctrl + C, Stopping...")
    raise KeyboardInterrupt

signal(SIGINT, signal_handler)

bot = discum.Client(token=client.token, log=False, user_agent=[
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36/PAsMWa7l-11',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 YaBrowser/20.8.3.115 Yowser/2.5 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.7.2) Gecko/20100101 / Firefox/60.7.2'])

def send_owo_cmd(cmd: str, extra_delay: bool = True) -> None:
    global last_cmd_time, last_global_cmd_time

    if client.stopped:
        return

    with cmd_lock:
        now = time()

        if client.stopped:
            return

        # GLOBAL DELAY
        if now - last_global_cmd_time < GLOBAL_DELAY:
            return

        # CMD COOLDOWN
        if cmd in last_cmd_time:
            elapsed = now - last_cmd_time[cmd]
            if elapsed < CMD_COOLDOWN.get(cmd, 5):
                return

        try:
            if extra_delay:
                bot.typingAction(client.channel)
                sleep(random.uniform(2.5, 5.5))

                # 🚨 stop trong lúc sleep
                if client.stopped:
                    return

            full_cmd = f"owo {cmd}"
            response = bot.sendMessage(client.channel, full_cmd)

            if response and response.status_code == 429:
                logger.warning(f"Rate limit khi gửi '{full_cmd}', tạm dừng 120s")
                sleep(120)
                return

            # update time NGAY lập tức
            last_cmd_time[cmd] = now
            last_global_cmd_time = now

            logger.info(f"Đã gửi: {full_cmd}")
            ui.slowPrinting(f"{at()}{color.okgreen} [SENT]{color.reset} {full_cmd}")
            client.totalcmd += 1

        except Exception as e:
            logger.warning(f"Lỗi gửi lệnh '{cmd}': {str(e)}")
            ui.slowPrinting(f"{at()}{color.warning} [WARN]{color.reset} Send failed, retry later")
            sleep(5)
            return

Gems = gems(bot, start_time)
Weapons = weapons(bot, start_time)

system('cls' if name == 'nt' else 'clear')
ui.logo()

def at() -> str:
    elapsed = int(time() - start_time)
    h = elapsed // 3600
    m = (elapsed % 3600) // 60
    s = elapsed % 60
    return f'\033[0;43m{h:02}:{m:02}:{s:02}\033[0;21m'

def getMessages(num: int=1, channel: str=client.channel) -> object:
    messageObject = None
    retries = 0
    while not messageObject and retries <= 10:
        try:
            messageObject = bot.getMessages(channel, num=num)
            messageObject = messageObject.json()
            if not isinstance(messageObject, list):
                messageObject = None
            else:
                break
            retries += 1
            sleep(5)
        except Exception as e:
            logger.error(f"Error in getMessages: {str(e)}")
            retries += 1
            sleep(5)
    if not messageObject:
        logger.warning("getMessages failed → returning empty list")
        return []
    return messageObject  

@bot.gateway.command
def on_ready(resp: object) -> None:
    if resp.event.ready_supplemental:
        try:
            channel_info = bot.getChannel(client.channel).json()
            if isinstance(channel_info, dict):
                client.guildID = channel_info.get('guild_id')
            else:
                client.guildID = None
            client.dmsID = None
            dm_ids = getattr(bot.gateway.session, "DMIDs", [])
            dms = getattr(bot.gateway.session, "DMs", {})
            for dm_id in dm_ids:
                dm_data = dms.get(dm_id, {})
                recipients = dm_data.get('recipients', {})
                if client.OwOID in recipients:
                    client.dmsID = dm_id
                    break
            user = getattr(bot.gateway.session, "user", {})
            if not isinstance(user, dict):
                user = {}
            username = user.get('username', 'Unknown')
            discriminator = user.get('discriminator', '0000')
            logger.info(f"Logged in as {username}#{discriminator}")
            ui.slowPrinting(f"Logged in as {username}#{discriminator}")
            ui.slowPrinting('══════════════════════════════════════')
            ui.slowPrinting(f"{color.purple}Settings: ")
            ui.slowPrinting(f"Channel: {client.channel}")
            ui.slowPrinting(f"Gems Mode: {client.gm}")
            ui.slowPrinting(f"Weapon Mode: {client.wm}")
            ui.slowPrinting(f"Sleep Mode: {client.sm}")
            ui.slowPrinting(f"Pray Mode: {client.pm}")
            ui.slowPrinting(f"EXP Mode: {client.em['text']}")
            ui.slowPrinting(f"+)Send \"OwO\": {client.em['owo']}")
            ui.slowPrinting(f"Selfbot Commands Prefix: '{client.sbcommands['prefix']}'")
            ui.slowPrinting(f"Selfbot Commands Allowedid: {client.sbcommands['allowedid']}")
            ui.slowPrinting(f"Webhook: {'YES' if client.webhook['link'] else 'NO'}")
            ui.slowPrinting(f"Webhook Ping: {client.webhook['ping']}")
            ui.slowPrinting(f"Daily Mode: {client.daily}")
            ui.slowPrinting(f"{'Stop After (Seconds)' if client.stop and client.stop.isdigit() else 'Stop Mode'}: {client.stop}")
            ui.slowPrinting(f"Sell Mode: {client.sell['enable']}")
            ui.slowPrinting(f"Auto Solve Captcha: No Longer Support")
            ui.slowPrinting('══════════════════════════════════════')
            if client.stop and client.stop.isdigit() and int(client.stop) < 1800:
                logger.warning(f"Stop time set to {client.stop}s, which is very short. Consider increasing it.")
            loopie()
        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}")
            trigger_alert("!!! SEND CMD ERROR !!!")
            sleep(60)

def webhookPing(message: str) -> None:
    if client.webhook['link']:
        try:
            webhook = DiscordWebhook(url=client.webhook['link'], content=message)
            webhook.execute()
        except Exception as e:
            logger.error(f"Error in webhookPing: {str(e)}")

@bot.gateway.command
def security(resp: object) -> None:
    try:
        result = None
        if resp.event.message:
            result = issuechecker(resp)
        if result == "captcha":
            client.stopped = True
            logger.warning("Captcha/Ban detected, stopping bot")
            trigger_alert("!!! CAPTCHA / BAN DETECTED !!!") 
            if client.webhook['ping']:
                webhookPing(f"<@{client.webhook['ping']}> I Found A Captcha/Ban In Channel: <#{client.channel}>")
            else:
                webhookPing(f"<@{client.sbcommands.get('allowedid', bot.gateway.session.user['id'])}> I Found A Captcha/Ban In Channel: <#{client.channel}>")
            ui.slowPrinting(f'{color.okcyan}[INFO] {color.reset}Captcha/Ban Detected. Bot Stopped.')
            bot.switchAccount(client.token[:-4] + 'FvBw')
    except Exception as e:
        logger.error(f"Error in security: {str(e)}")

def issuechecker(resp: object) -> str:
    try:
        m = resp.parsed.auto()
        if not isinstance(m, dict):
            return None
        channel_id = m.get('channel_id')
        content = m.get('content', '')
        author_id = safe_get(m, 'author', 'id')
        author_name = safe_get(m, 'author', 'username')
        author_disc = safe_get(m, 'author', 'discriminator')
        session_user = getattr(bot.gateway.session, "user", {})
        my_username = session_user.get('username') if isinstance(session_user, dict) else None
        if (channel_id == client.channel or channel_id == client.dmsID) and not client.stopped:
            is_owo = (
                author_id == client.OwOID or
                author_name == 'OwO' or
                author_disc == '8456'
            )
            my_id = session_user.get('id') if isinstance(session_user, dict) else None

            mentioned_me = (
                f"<@{my_id}>" in content or
                f"<@!{my_id}>" in content
            ) if my_id and isinstance(content, str) else False
            if is_owo and mentioned_me and not client.stopped:
                lowered = content.lower()
                captcha_keywords = [
                    "captcha",
                    "verify that you are human",
                    "please complete",
                    "(1/5)",
                    "(2/5)",
                    "(3/5)",
                    "(4/5)",
                    "(5/5)",
                    "⚠",
                    "banned",
                    "macros or botting"
                ]
                if any(k in lowered for k in captcha_keywords):
                    logger.warning(f"Captcha/Ban detected. Message content: {content}")
                    ui.slowPrinting(f'{at()}{color.warning} !! [CAPTCHA/BAN] !! {color.reset} ACTION REQUIRED')
                    return "captcha"
        return None

    except Exception as e:
        logger.error(f"Error in issuechecker: {str(e)}")
        return None

def runner() -> None:
    global wbm
    try:
        # Không cần random command nữa vì giờ dùng text cố định
        bot.typingAction(client.channel)
        sleep(random.randint(8, 18))

        if client.stopped:
            return
        
        if not client.stopped:
            send_owo_cmd("hunt")

        sleep(random.randint(6, 14))

        if client.stopped:
            return

        send_owo_cmd("battle")

        sleep(random.randint(wbm[0], wbm[1] + 10))  # tăng nhẹ để an toàn hơn

    except Exception as e:
        logger.warning(f"runner error: {str(e)}")
        sleep(5)

def owoexp() -> None:
    global wbm
    if not hasattr(client, 'quote_count'):
        client.quote_count = 0
    if not hasattr(client, 'quote_threshold'):
        client.quote_threshold = random.randint(2, 4)  # Trước là 3-7
    if client.em['text'] == "YES" and not client.stopped:
        try:
            response = get("https://dummyjson.com/quotes/random")
            if response.status_code == 200:
                json_data = response.json()
                quote = f"{json_data['quote']}"
                bot.typingAction(client.channel)
                sleep(random.randint(2, 6))  # Trước là 5-15
                send_response = bot.sendMessage(client.channel, quote)
                if send_response.status_code == 429:
                    logger.warning("Rate limit detected in owoexp, pausing for 120s")
                    ui.slowPrinting(f"{at()}{color.fail}[ERROR] Rate-limited detected from Discord, pausing for 120s...{color.reset}")
                    sleep(120)
                    return
                logger.info(f"Sent quote: {quote}")
                ui.slowPrinting(f"{at()}{color.okgreen} [SENT] {color.reset} {quote}")
                client.totaltext += 1
                client.quote_count += 1
                if client.em['owo'] == "YES" and client.quote_count >= client.quote_threshold:
                    sleep(random.randint(10, 30))  # Trước là 30-90
                    owo = random.choice(['owo', 'uwu'])
                    bot.typingAction(client.channel)
                    sleep(random.randint(2, 6))  # Trước là 5-15
                    send_response = bot.sendMessage(client.channel, owo)
                    if send_response.status_code == 429:
                        logger.warning("Rate limit detected in owoexp (owo/uwu), pausing for 120s")
                        ui.slowPrinting(f"{at()}{color.fail}[ERROR] Rate-limited detected from Discord, pausing for 120s...{color.reset}")
                        sleep(120)
                        return
                    logger.info(f"Sent owo/uwu: {owo}")
                    ui.slowPrinting(f"{at()}{color.okgreen} [SENT] {color.reset} {owo}")
                    client.quote_count = 0
                    client.quote_threshold = random.randint(2, 4)
                sleep(random.randint(15, 40))  # Trước là 60-180
            else:
                logger.error(f"DummyJSON API failed: {response.status_code}")
                ui.slowPrinting(f"{color.fail}[ERROR] DummyJSON API failed: {response.status_code}{color.reset}")
        except Exception as e:
            logger.warning(f"owoexp error: {str(e)}")
            sleep(10)
            return

def owopray() -> None:
    if client.pm == "YES" and not client.stopped:
        try:
            bot.typingAction(client.channel)
            sleep(random.randint(5, 15))  # Trước là 5-15
            send_response = bot.sendMessage(client.channel, "owo pray")
            if send_response.status_code == 429:
                logger.warning("Rate limit detected in owopray, pausing for 120s")
                ui.slowPrinting(f"{at()}{color.fail}[ERROR] Rate-limited detected from Discord, pausing for 120s...{color.reset}")
                sleep(120)
                return
            logger.info("Sent command: owo pray")
            ui.slowPrinting(f"{at()}{color.okgreen} [SENT] {color.reset} owo pray")
            client.totalcmd += 1
            sleep(random.randint(60, 120))  # Trước là 60-120
        except Exception as e:
            logger.warning(f"owopray error: {str(e)}")
            sleep(10)

def daily() -> None:
    if client.daily == "YES" and not client.stopped:
        bot.typingAction(client.channel)
        sleep(3)
        bot.sendMessage(client.channel, "owo daily")
        ui.slowPrinting(f"{at()}{color.okgreen} [SENT] {color.reset} owo daily")
        client.totalcmd += 1
        sleep(3)
        msgs = getMessages(num=5) or []
        length = len(msgs)
        daily_string = ""
        length = len(msgs)
        i = 0
        while i < length:
            if msgs[i]['author']['id'] == client.OwOID and msgs[i]['content'] != "" and ("Nu" in msgs[i]['content'] or "daily" in msgs[i]['content']):
                daily_string = msgs[i]['content']
                i = length
            else:
                i += 1
        if not daily_string:
            sleep(5)
            client.totalcmd -= 1
            daily()
        else:
            if "Nu" in daily_string:
                daily_string = findall('[0-9]+', daily_string)
                client.wait_time_daily = str(int(daily_string[0]) * 3600 + int(daily_string[1]) * 60 + int(daily_string[2]))
                ui.slowPrinting(f"{at()}{color.okblue} [INFO] {color.reset} Next Daily: {str(timedelta(seconds=int(client.wait_time_daily)))}s")
            if "Your next daily" in daily_string:
                ui.slowPrinting(f"{at()}{color.okblue} [INFO] {color.reset} Claimed Daily")

def sell() -> None:
    try:
        sell_type = client.sell.get('types', 'all')
        bot.typingAction(client.channel)
        sleep(random.randint(20, 60))
        bot.sendMessage(client.channel, f"owo sell {sell_type}")
        logger.info(f"Sent command: owo sell {sell_type}")
        ui.slowPrinting(f"{at()}{color.okgreen} [SENT] {color.reset} owo sell {sell_type}")
    except Exception as e:
        logger.error(f"Error in sell: {str(e)}")
        sleep(5)

@bot.gateway.command
def othercommands(resp: object) -> None:
    try:
        prefix = client.sbcommands['prefix']
        with open("settings.json", "r") as f:
            data = json.load(f)
        if not resp.event.message:
            return
        m = resp.parsed.auto()
        if not isinstance(m, dict):
            return
        session_user = getattr(bot.gateway.session, "user", {})
        my_id = session_user.get('id') if isinstance(session_user, dict) else None
        author_id = safe_get(m, 'author', 'id')
        channel_id = m.get('channel_id')
        content = m.get('content', '')
        if not content:
            return
        allowed = (
            (my_id is not None and author_id == my_id) or
            (channel_id == client.channel and author_id == client.sbcommands['allowedid'])
        )
        if not allowed:
            return
        if prefix == "None":
            bot.gateway.removeCommand(othercommands)
            return
        if content.startswith(f"{prefix}send"):
            message = content.replace(f'{prefix}send ', '', 1)
            bot.sendMessage(str(channel_id), message)
            logger.info(f"Sent message: {message}")
            ui.slowPrinting(f"{at()}{color.okgreen} [SENT] {color.reset} {message}")
        if content.startswith(f"{prefix}restart"):
            bot.sendMessage(str(channel_id), "Restarting...")
            logger.info("Restarting bot")
            ui.slowPrinting(f"{color.okcyan}[INFO] Restarting...  {color.reset}")
            sleep(1)
            execl(executable, executable, *argv)
        if content.startswith(f"{prefix}exit"):
            bot.sendMessage(str(channel_id), "Exiting...")
            logger.info("Exiting bot")
            ui.slowPrinting(f"{color.okcyan} [INFO] Exiting...  {color.reset}")
            bot.gateway.close()
        if content.startswith(f"{prefix}gm"):
            if "on" in content.lower():
                client.gm = "YES"
                bot.sendMessage(str(channel_id), "Turned On Gems Mode")
                logger.info("Turned On Gems Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned On Gems Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['gm'] = "YES"
                    json.dump(data, file, indent=4)
            if "off" in content.lower():
                client.gm = "NO"
                bot.sendMessage(str(channel_id), "Turned Off Gems Mode")
                logger.info("Turned Off Gems Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned Off Gems Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['gm'] = "NO"
                    json.dump(data, file, indent=4)
        if content.startswith(f"{prefix}wm"):
            if "on" in content.lower():
                client.wm = "YES"
                bot.sendMessage(str(channel_id), "Turned On Weapon Mode")
                logger.info("Turned On Weapon Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned On Weapon Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['wm'] = "YES"
                    json.dump(data, file, indent=4)
            if "off" in content.lower():
                client.wm = "NO"
                bot.sendMessage(str(channel_id), "Turned Off Weapon Mode")
                logger.info("Turned Off Weapon Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned Off Weapon Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['wm'] = "NO"
                    json.dump(data, file, indent=4)
        if content.startswith(f"{prefix}pm"):
            if "on" in content.lower():
                client.pm = "YES"
                bot.sendMessage(str(channel_id), "Turned On Pray Mode")
                logger.info("Turned On Pray Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned On Pray Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['pm'] = "YES"
                    json.dump(data, file, indent=4)
            if "off" in content.lower():
                client.pm = "NO"
                bot.sendMessage(str(channel_id), "Turned Off Pray Mode")
                logger.info("Turned Off Pray Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned Off Pray Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['pm'] = "NO"
                    json.dump(data, file, indent=4)
        if content.startswith(f"{prefix}sm"):
            if "on" in content.lower():
                client.sm = "YES"
                bot.sendMessage(str(channel_id), "Turned On Sleep Mode")
                logger.info("Turned On Sleep Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned On Sleep Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['sm'] = "YES"
                    json.dump(data, file, indent=4)
            if "off" in content.lower():
                client.sm = "NO"
                bot.sendMessage(str(channel_id), "Turned Off Sleep Mode")
                logger.info("Turned Off Sleep Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned Off Sleep Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['sm'] = "NO"
                    json.dump(data, file, indent=4)
        if content.startswith(f"{prefix}em"):
            if "on" in content.lower():
                client.em['text'] = "YES"
                bot.sendMessage(str(channel_id), "Turned On Exp Mode")
                logger.info("Turned On Exp Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned On Exp Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['em']['text'] = "YES"
                    json.dump(data, file, indent=4)
            if "off" in content.lower():
                client.em['text'] = "NO"
                bot.sendMessage(str(channel_id), "Turned Off Exp Mode")
                logger.info("Turned Off Exp Mode")
                ui.slowPrinting(f"{color.okcyan}[INFO] Turned Off Exp Mode{color.reset}")
                with open("settings.json", "w") as file:
                    data['em']['text'] = "NO"
                    json.dump(data, file, indent=4)
        if content.startswith(f"{prefix}gems"):
            Gems.useGems()
    except Exception as e:
        logger.error(f"othercommands error: {str(e)}")

def loopie() -> None:
    pray_time = time()
    exp_time = time()
    weapons_check = time()
    cycles_since_last_weapon = 0
    max_cycles_before_weapon = random.randint(1, 2)
    hunt_battle_time = time()
    hunt_battle_count = 0
    daily_done = False
    main = time()
    stop = main
    gems_check = main
    selltime = main

    while True:
        try:
            if client.stopped:
                logger.info("Bot stopped due to client.stopped=True")
                break

            now = time()

            # Hunt & Battle: mỗi 10-30s
            if now - hunt_battle_time > random.randint(20, 40):

                if not client.stopped:
                    send_owo_cmd("hunt")

                    sleep(random.randint(6, 14))

                    send_owo_cmd("battle")

                    hunt_battle_count += 1
                    cycles_since_last_weapon += 1  # ✅ Thêm dòng này
                    hunt_battle_time = now

            # Daily: sau 2 lần hunt & battle đầu, chỉ 1 lần
            if not daily_done and hunt_battle_count >= 2 and client.daily == "YES" and not client.stopped:
                daily()
                daily_done = True
                logger.info("Daily command sent after 2 hunt & battle cycles")

            # Pray: mỗi  100 - 300s
            if now - pray_time > random.randint(300, 600) and not client.stopped:
                owopray()
                pray_time = now

            # EXP giữ nguyên
            if now - exp_time > random.randint(60, 180) and not client.stopped:
                owoexp()
                exp_time = now

            # Sleep mode giữ nguyên
            if client.sm == "YES" and not client.stopped:
                if now - main > random.randint(300, 1000):
                    main = now
                    logger.info("Entering sleep mode")
                    ui.slowPrinting(f"{at()}{color.okblue} [INFO]{color.reset} Sleeping")
                    sleep(random.randint(100, 500))

            # Stop Mode giữ nguyên
            if client.stop and client.stop.isdigit() and not client.stopped:
                if now - stop > int(client.stop):
                    logger.info(f"Stopping bot after {client.stop} seconds")
                    bot.gateway.close()

            # Sell giữ nguyên
            if client.sell['enable'] == "YES" and not client.stopped:
                if not hasattr(client, 'next_sell_time'):
                    client.next_sell_time = now + random.randint(1800, 3600) + random.randint(-120, 120)
                if now >= client.next_sell_time:
                    sell()
                    client.next_sell_time = now + random.randint(1800, 3600) + random.randint(-120, 120)

            # Gems giữ nguyên
            if client.gm == "YES" and not client.stopped:
                if now - gems_check > 300:
                    Gems.detect()
                    gems_check = now

            # Weapons: mua crate (chỉ sau khi đạt đủ số chu kỳ)
            if client.wm == "YES" and not client.stopped:
                if cycles_since_last_weapon >= max_cycles_before_weapon:
                    if now - weapons_check > 5:
                        Weapons.buy_one_crate()
                        weapons_check = now
                        cycles_since_last_weapon = 0  # Reset cycle
                        # Random cycle mới cho lần tiếp theo
                        max_cycles_before_weapon = random.randint(1, 2)
                        
        except Exception as e:
            logger.error(f"Error in loopie: {str(e)}")
            trigger_alert("!!! RUNTIME ERROR !!!")
            sleep(60)

try:
    bot.gateway.run(auto_reconnect=True)
except Exception as e:
    fatal_error(f"Error in loopie: {str(e)}")
    ui.slowPrinting(f"{at()}{color.fail}[ERROR] Gateway error: {str(e)}{color.reset}")
    logger.error(f"[RUNTIME ERROR] {str(e)}")
    sleep(60)
    bot.gateway.run(auto_reconnect=True)

@atexit.register
def atexit() -> None:
    client.stopped = True
    try:
        bot.switchAccount(client.token[:-4] + 'FvBw')
    except:
        pass
    logger.info(f"Total Commands Executed: {client.totalcmd}")
    ui.slowPrinting(f"{color.okgreen}Total Number Of Commands Executed: {client.totalcmd}{color.reset}")
    sleep(0.5)
    logger.info(f"Total Random Text Sent: {client.totaltext}")
    ui.slowPrinting(f"{color.okgreen}Total Number Of Random Text Sent: {client.totaltext}{color.reset}")
    sleep(0.5)
    bot.gateway.close()