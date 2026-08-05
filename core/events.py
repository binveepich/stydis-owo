import time
import json
import asyncio
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
            if result == "captcha" and not self.captcha_detected and not self._is_solving and not self._solving_lock:
                self.captcha_detected = True
                self._handle_captcha()

        except Exception as e:
            pass

    def _handle_captcha(self):
        try:
            if self._is_solving:
                self.bot.log("INFO", "Captcha solve already in progress...")
                return

            if not self.bot.has_captcha_resolver():
                self.bot.log("WARN", "No captcha resolver available")
                self._pause_bot_no_resolver()
                return

            if self.bot.captcha_resolver.is_running():
                self.bot.log("INFO", "Resolver already running...")
                return

            self.bot.log("DETECTED", "CAPTCHA DETECTED! Pausing bot to solve...")
            
            # Pause bot
            self._stop_bot_for_captcha()

            # Start solving
            self._is_solving = True
            self._solving_lock = True
            
            if self._loop:
                self._solve_task = self._loop.create_task(self._auto_solve_captcha())
            else:
                self._solve_task = asyncio.ensure_future(self._auto_solve_captcha())

        except Exception as e:
            self.bot.log("ERROR", f"Handle captcha error: {e}")
            self._pause_bot_no_resolver()

    def _stop_bot_for_captcha(self):
        try:
            self.bot.log("INFO", "Pausing bot for captcha solving...")

            if self.bot.scheduler:
                try:
                    self.bot.log("INFO", "Stopping scheduler...")
                    self.bot.scheduler.stop()
                except Exception as e:
                    self.bot.log("WARN", f"Scheduler stop error: {e}")

            self.bot.config.stopped = True
            self.bot.running = False

            self.bot.log("INFO", "Bot paused. Gateway still connected. Starting captcha solve...")

        except Exception as e:
            self.bot.log("ERROR", f"Pause bot failed: {e}")

    async def _auto_solve_captcha(self):
        try:
            self.bot.log("INFO", "=" * 50)
            self.bot.log("INFO", "CAPTCHA RESOLVER STARTED")
            self.bot.log("INFO", "=" * 50)

            # Giai captcha voi retry 3 lan
            success = await self.bot.captcha_resolver.solve()

            if success:
                self.bot.log("SUCCESS", "Captcha solved! Resuming bot...")
                await self._resume_bot()
            else:
                self.bot.log("ERROR", "Auto-solve failed after 3 attempts. Waiting for user action...")
                await self._wait_for_user_exit()

        except asyncio.CancelledError:
            self.bot.log("WARN", "Captcha solve was cancelled")
            await self._wait_for_user_exit()
        except Exception as e:
            self.bot.log("ERROR", f"Captcha solve error: {e}")
            await self._wait_for_user_exit()
        finally:
            self._is_solving = False
            self._solving_lock = False
            self._solve_task = None

    async def _resume_bot(self):
        try:
            self.bot.log("INFO", "Resuming bot...")

            self.captcha_detected = False
            self.bot.config.stopped = False
            self.bot.running = True

            if self.bot.scheduler and not self.bot.scheduler.running:
                self.bot.log("INFO", "Starting scheduler...")
                self.bot.scheduler.start()

            self.bot.log("SUCCESS", "Bot resumed successfully!")

        except Exception as e:
            self.bot.log("ERROR", f"Resume failed: {e}")
            await self._wait_for_user_exit()

    async def _wait_for_user_exit(self):
        try:
            self.bot.log("INFO", "Bot is paused. Gateway still connected.")
            self.bot.log("INFO", "Press ENTER to exit the tool, or Ctrl+C to force quit.")

            print()
            print("=" * 60)
            print(f"{color.warning}CAPTCHA SOLVE FAILED AFTER 3 ATTEMPTS{color.reset}")
            print(f"{color.okcyan}Bot is paused. Gateway still connected.{color.reset}")
            print(f"{color.okcyan}Press ENTER to exit the tool safely.{color.reset}")
            print(f"{color.okcyan}Or press Ctrl+C to force quit.{color.reset}")
            print("=" * 60)
            print()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, input)

            self.bot.log("INFO", "User requested exit. Closing gateway...")
            self._user_confirmed_exit = True
            self._exit_tool()

        except asyncio.CancelledError:
            self.bot.log("WARN", "User cancelled with Ctrl+C")
            self._exit_tool()
        except Exception as e:
            self.bot.log("ERROR", f"Wait for user exit error: {e}")
            self._exit_tool()

    def _exit_tool(self):
        try:
            try:
                self.bot.discord_bot.gateway.close()
            except:
                pass

            if self.bot.scheduler:
                try:
                    self.bot.scheduler.stop()
                except:
                    pass

            self.bot.log("INFO", "Tool exited. Goodbye!")

            import os
            time.sleep(0.5)
            os._exit(0)

        except Exception as e:
            import os
            os._exit(0)

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