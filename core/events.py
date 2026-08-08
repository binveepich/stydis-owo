import time
import json
import asyncio
import sys
import os
import subprocess
import ctypes
from utils.helpers import UI
from utils.colors import color


class EventHandler:
    def __init__(self, bot):
        self.bot = bot
        self.ui = UI()
        self.captcha_keywords = [
            "captcha", "verify that you are human", "please complete",
            "(1/5)", "(2/5)", "(3/5)", "(4/5)", "(5/5)",
            "⚠", "banned", "macros or botting"
        ]
        self.is_ready = False
        self.captcha_detected = False
        self._solve_task = None
        self._is_solving = False
        self._user_confirmed_exit = False
        self._loop = None
        self._solving_lock = False

    def connect(self):
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        @self.bot.discord_bot.gateway.command
        def on_ready(resp):
            if resp.event.ready_supplemental:
                self._on_ready(resp)

        @self.bot.discord_bot.gateway.command
        def security(resp):
            self._security(resp)

    def _on_ready(self, resp):
        if self.is_ready:
            return

        try:
            channel_info = self.bot.discord_bot.getChannel(self.bot.config.channel).json()
            if isinstance(channel_info, dict):
                self.bot.config.guildID = channel_info.get('guild_id')
            else:
                self.bot.config.guildID = None

            self.bot.config.dmsID = None
            dm_ids = getattr(self.bot.discord_bot.gateway.session, "DMIDs", [])
            dms = getattr(self.bot.discord_bot.gateway.session, "DMs", {})
            for dm_id in dm_ids:
                dm_data = dms.get(dm_id, {})
                recipients = dm_data.get('recipients', {})
                if self.bot.config.OwOID in recipients:
                    self.bot.config.dmsID = dm_id
                    break

            user = getattr(self.bot.discord_bot.gateway.session, "user", {})
            if not isinstance(user, dict):
                user = {}
            username = user.get('username', 'Unknown')
            discriminator = user.get('discriminator', '0000')

            self.ui.slowPrinting(f"Logged in as {username}#{discriminator}")
            self.ui.slowPrinting('══════════════════════════════════════')
            self.ui.slowPrinting(f"{color.purple}Settings: ")
            self.ui.slowPrinting(f"Channel: {self.bot.config.channel}")
            self.ui.slowPrinting(f"Gems Mode: {self.bot.config.gm}")
            self.ui.slowPrinting(f"Weapon Mode: {self.bot.config.wm}")
            self.ui.slowPrinting(f"Sleep Mode: {self.bot.config.sm}")
            self.ui.slowPrinting(f"Pray Mode: {self.bot.config.pm}")
            self.ui.slowPrinting(f"EXP Mode: {self.bot.config.em.get('text', 'NO')}")
            self.ui.slowPrinting(f"+)Send \"OwO\": {self.bot.config.em.get('owo', 'NO')}")
            self.ui.slowPrinting(f"Webhook: {'YES' if self.bot.config.webhook.get('link') else 'NO'}")
            self.ui.slowPrinting(f"Daily Mode: {self.bot.config.daily}")
            self.ui.slowPrinting(f"{'Stop After (Seconds)' if self.bot.config.stop and self.bot.config.stop.isdigit() else 'Stop Mode'}: {self.bot.config.stop}")
            self.ui.slowPrinting(f"Sell Mode: {self.bot.config.sell.get('enable', 'NO')}")
            self.ui.slowPrinting('══════════════════════════════════════')

            self.is_ready = True

        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                f"Ready error: {str(e)[:50]}"
            )
            time.sleep(60)

    def _security(self, resp):
        try:
            if not resp.event.message:
                return

            m = resp.parsed.auto()
            if not isinstance(m, dict):
                return

            result = self._issue_checker(m)
            if result == "captcha" and not self.captcha_detected and not self._solving_lock:
                self.captcha_detected = True
                self._handle_captcha()

            if self.bot.gems and self.bot.config.gm == "YES":
                content = m.get('content', '')
                author = m.get('author', {})
                author_id = author.get('id')

                if author_id == self.bot.config.OwOID and content:
                    if 'hunt is empowered by' in content.lower():
                        self.bot.gems.check_and_use_gems_from_hunt(content)

                    if 'already have an active' in content.lower() or 'you do not own this gem' in content.lower():
                        self.bot.gems.handle_use_response(content)

        except Exception as e:
            pass

    def _handle_captcha(self):
        try:
            if self._solving_lock:
                self.bot.log("INFO", "Captcha solve already in progress...")
                return

            if not self.bot.has_captcha_resolver():
                self.bot.log("WARN", "No captcha resolver available")
                self._pause_bot_no_resolver()
                return

            self.bot.log("DETECTED", "=" * 50)
            self.bot.log("DETECTED", "CAPTCHA DETECTED!")
            self.bot.log("DETECTED", "=" * 50)

            self._trigger_alert()

            self.bot.log("INFO", "Stopping bot...")

            if self.bot.scheduler:
                try:
                    self.bot.scheduler.stop()
                except:
                    pass

            try:
                self.bot.discord_bot.gateway.close()
            except:
                pass

            self.bot.config.stopped = True
            self.bot.running = False

            self.bot.log("INFO", "Bot stopped. Starting resolver...")

            self._run_resolver_in_place()

            self.bot.log("INFO", "Exiting main process...")
            time.sleep(0.5)
            os._exit(0)

        except Exception as e:
            self.bot.log("ERROR", f"Handle captcha error: {e}")
            self._pause_bot_no_resolver()

    def _trigger_alert(self):
        try:
            import os

            if os.name == "nt":
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                hwnd = kernel32.GetConsoleWindow()
                if hwnd:
                    user32.FlashWindow(hwnd, True)

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

            print('\a')
            print('\a')

        except Exception as e:
            pass

    def _run_resolver_in_place(self):
        try:
            resolver_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'captcha_resolver',
                'resolver_runner.py'
            )

            if not os.path.exists(resolver_script):
                self._create_resolver_runner(resolver_script)

            self.bot.log("INFO", f"Starting resolver...")

            os.execv(sys.executable, [sys.executable, resolver_script])

        except Exception as e:
            self.bot.log("ERROR", f"Failed to start resolver: {e}")

    def _create_resolver_runner(self, path):
        content = '''#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from captcha_resolver.resolver import run_resolver_standalone

if __name__ == "__main__":
    run_resolver_standalone()
'''
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            pass

    def _pause_bot_no_resolver(self):
        try:
            self.bot.config.stopped = True
            self.bot.running = False

            if self.bot.scheduler:
                try:
                    self.bot.scheduler.stop()
                except:
                    pass

            self.bot.log("INFO", "Bot paused due to captcha. Please restart tool to continue.")
            self.bot.log("INFO", "If you want to auto-solve captcha, configure API key in config.")

            self.ui.slowPrinting(
                f'{self.bot.at()}{color.warning} '
                '!! [CAPTCHA DETECTED] !! Bot Paused'
            )
            self.ui.slowPrinting(
                f'{color.okcyan}[INFO]{color.reset} '
                'Captcha detected but no resolver configured.'
            )
            self.ui.slowPrinting(
                f'{color.okcyan}[INFO]{color.reset} '
                'Bot is paused. Press Ctrl+C to exit.'
            )

        except Exception as e:
            self.bot.log("ERROR", f"Pause bot failed: {e}")

    def _issue_checker(self, m):
        try:
            channel_id = m.get('channel_id')
            content = m.get('content', '')

            author = m.get('author', {})
            author_id = author.get('id')
            author_name = author.get('username')
            author_disc = author.get('discriminator')

            session_user = getattr(self.bot.discord_bot.gateway.session, "user", {})
            if not isinstance(session_user, dict):
                session_user = {}

            if self.captcha_detected or self.bot.config.stopped:
                return None

            if ((channel_id == self.bot.config.channel or
                 channel_id == self.bot.config.dmsID) and
                not self.bot.config.stopped):

                is_owo = (
                    author_id == self.bot.config.OwOID or
                    author_name == 'OwO' or
                    author_disc == '8456'
                )

                my_id = session_user.get('id') if isinstance(session_user, dict) else None

                mentioned_me = (
                    f"<@{my_id}>" in content or
                    f"<@!{my_id}>" in content
                ) if my_id and isinstance(content, str) else False

                if is_owo and mentioned_me and not self.bot.config.stopped:
                    lowered = content.lower()
                    if any(k in lowered for k in self.captcha_keywords):
                        return "captcha"
            return None

        except Exception as e:
            return None

    def disconnect(self):
        try:
            self.bot.discord_bot.gateway.close()
        except:
            pass