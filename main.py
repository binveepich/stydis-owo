import sys
import time
import random
import ctypes
import asyncio  # THÊM IMPORT
from os import name, system
from signal import signal, SIGINT

from core.bot import OwOBot
from core.command import CommandExecutor
from core.scheduler import Scheduler
from core.events import EventHandler

from data.config import Config
from utils.colors import color
from utils.helpers import UI, print_info, print_error, print_warning

from modules import (
    GemModule,
    WeaponModule,
    PrayModule,
    ExpModule,
    DailyModule,
    SellModule,
)

ui = UI()
config = None
bot_instance = None

def signal_handler(sig, frame):
    print()
    print_warning("Detected Ctrl+C, stopping bot...")
    if bot_instance:
        bot_instance.stop()
    sys.exit(0)

signal(SIGINT, signal_handler)

def move_window_to_center():
    try:
        if name != "nt":
            return

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            return

        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)

        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))

        win_width = rect.right - rect.left
        win_height = rect.bottom - rect.top

        x = int((screen_width - win_width) / 2)
        y = int((screen_height - win_height) / 2)

        user32.MoveWindow(hwnd, x, y, win_width, win_height, True)
        user32.SetForegroundWindow(hwnd)

    except Exception:
        pass

def trigger_alert(title="ALERT"):
    try:
        if name == "nt":
            ctypes.windll.user32.FlashWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), True
            )
            move_window_to_center()
        print('\a')
    except Exception:
        pass

def main():
    global config, bot_instance

    # === THÊM: KHỞI TẠO EVENT LOOP ===
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    system('cls' if name == 'nt' else 'clear')
    UI.logo()

    print_info("Loading configuration...")

    try:
        config = Config()
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        sys.exit(1)

    try:
        config.check()
    except Exception as e:
        print_error(f"Token check failed: {e}")
        sys.exit(1)

    print_info("Configuration loaded successfully! Creating bot instance... ")

    bot_instance = OwOBot(config, start_time=time.time())

    bot_instance.executor = CommandExecutor(bot_instance)
    bot_instance.scheduler = Scheduler(bot_instance)
    bot_instance.events = EventHandler(bot_instance)

    bot_instance.gems = GemModule(bot_instance, bot_instance.start_time)
    bot_instance.register_module(bot_instance.gems)

    bot_instance.weapons = WeaponModule(bot_instance, bot_instance.start_time)
    bot_instance.register_module(bot_instance.weapons)

    bot_instance.register_module(PrayModule())
    bot_instance.register_module(ExpModule())
    bot_instance.register_module(DailyModule())
    bot_instance.register_module(SellModule())

    try:
        bot_instance.events.connect()
        bot_instance.scheduler.start()
        bot_instance.start()

    except KeyboardInterrupt:
        print()
        print_warning("Bot stopped by user")
        bot_instance.stop()
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        trigger_alert("!!! FATAL ERROR !!!")
        bot_instance.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()