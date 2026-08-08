import time
import random
import threading
from threading import Lock
from utils.helpers import UI
from utils.colors import color
from utils.constants import BotConstants

class CommandExecutor:
    def __init__(self, bot):
        self.bot = bot
        self.ui = UI()
        self.cmd_lock = Lock()
        self.last_global_cmd_time = 0
        self.GLOBAL_DELAY = getattr(BotConstants, 'GLOBAL_CMD_DELAY', 5)
        self.CMD_COOLDOWN = getattr(BotConstants, 'CMD_COOLDOWN', {})
        self.last_cmd_time = {}
        self.pending_commands = set()
        self.command_timestamps = {}

    def send_command(self, cmd: str, extra_delay: bool = True) -> bool:
        if self.bot.config.stopped:
            return False

        with self.cmd_lock:
            now = time.time()
            cmd_key = f"{cmd}_{int(now // 10)}"

            if self.bot.config.stopped:
                return False

            if cmd_key in self.pending_commands:
                return False

            if now - self.last_global_cmd_time < self.GLOBAL_DELAY:
                return False

            if cmd in self.last_cmd_time:
                elapsed = now - self.last_cmd_time[cmd]
                if elapsed < self.CMD_COOLDOWN.get(cmd, 5):
                    return False

            try:
                if extra_delay:
                    self.bot.discord_bot.typingAction(self.bot.config.channel)
                    time.sleep(random.uniform(2.5, 5.5))

                    if self.bot.config.stopped:
                        return False

                full_cmd = f"owo {cmd}"
                response = self.bot.discord_bot.sendMessage(
                    self.bot.config.channel,
                    full_cmd
                )

                if response and response.status_code == 429:
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                        f"Rate limit on '{full_cmd}', waiting 120s"
                    )
                    time.sleep(120)
                    return False

                self.last_cmd_time[cmd] = now
                self.last_global_cmd_time = now
                self.pending_commands.add(cmd_key)
                threading.Timer(10, lambda: self.pending_commands.discard(cmd_key)).start()

                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} {full_cmd}"
                )
                self.bot.total_commands += 1
                return True

            except Exception as e:
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                    f"Send failed: {str(e)[:50]}"
                )
                time.sleep(5)
                return False

    def send_hunt_battle(self) -> bool:
        if self.bot.config.stopped:
            return False

        try:
            self.bot.discord_bot.typingAction(self.bot.config.channel)
            
            if self.bot.hunt_cycles == 0:
                time.sleep(random.randint(1, 4))
            else:
                time.sleep(random.randint(8, 18))

            if self.bot.config.stopped:
                return False

            if not self.bot.config.stopped:
                self.send_command("hunt")

            if self.bot.hunt_cycles == 0:
                time.sleep(random.randint(1, 3))
            else:
                time.sleep(random.randint(6, 14))

            if self.bot.config.stopped:
                return False

            self.send_command("battle")

            self.bot.hunt_cycles += 1
            return True

        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Hunt/Battle error: {str(e)[:50]}"
            )
            time.sleep(5)
            return False

    def send_pray(self) -> bool:
        if self.bot.config.pm != "YES" or self.bot.config.stopped:
            return False

        try:
            self.bot.discord_bot.typingAction(self.bot.config.channel)
            time.sleep(random.randint(5, 15))

            response = self.bot.discord_bot.sendMessage(
                self.bot.config.channel,
                "owo pray"
            )

            if response and response.status_code == 429:
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                    "Rate limit on pray, waiting 120s"
                )
                time.sleep(120)
                return False

            self.ui.slowPrinting(
                f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} owo pray"
            )
            self.bot.total_commands += 1
            return True

        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Pray error: {str(e)[:50]}"
            )
            time.sleep(10)
            return False

    def send_daily(self) -> bool:
        if self.bot.config.daily != "YES" or self.bot.config.stopped:
            return False

        try:
            self.bot.discord_bot.typingAction(self.bot.config.channel)
            time.sleep(3)

            self.bot.discord_bot.sendMessage(self.bot.config.channel, "owo daily")
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} owo daily"
            )
            self.bot.total_commands += 1

            time.sleep(3)
            msgs = self.bot.getMessages(num=5) or []

            daily_string = ""
            length = len(msgs)
            i = 0
            while i < length:
                if (msgs[i]['author']['id'] == self.bot.config.OwOID and
                    msgs[i]['content'] != "" and
                    ("Nu" in msgs[i]['content'] or "daily" in msgs[i]['content'])):
                    daily_string = msgs[i]['content']
                    i = length
                else:
                    i += 1

            if not daily_string:
                time.sleep(5)
                self.bot.total_commands -= 1
                return self.send_daily()
            else:
                from re import findall
                if "Nu" in daily_string:
                    daily_string = findall('[0-9]+', daily_string)
                    wait_time = str(int(daily_string[0]) * 3600 +
                                  int(daily_string[1]) * 60 +
                                  int(daily_string[2]))
                    from datetime import timedelta
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
                        f"Next Daily: {str(timedelta(seconds=int(wait_time)))}"
                    )
                if "Your next daily" in daily_string:
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
                        "Claimed Daily"
                    )
            return True

        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Daily error: {str(e)[:50]}"
            )
            time.sleep(5)
            return False

    def send_sell(self) -> bool:
        if self.bot.config.sell.get('enable') != "YES" or self.bot.config.stopped:
            return False

        try:
            sell_type = self.bot.config.sell.get('types', 'all')
            self.bot.discord_bot.typingAction(self.bot.config.channel)
            time.sleep(random.randint(20, 60))

            self.bot.discord_bot.sendMessage(
                self.bot.config.channel,
                f"owo sell {sell_type}"
            )

            self.ui.slowPrinting(
                f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} "
                f"owo sell {sell_type}"
            )
            self.bot.total_commands += 1
            return True

        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Sell error: {str(e)[:50]}"
            )
            time.sleep(5)
            return False

    def send_raw(self, message: str) -> bool:
        if self.bot.config.stopped:
            return False

        try:
            self.bot.discord_bot.typingAction(self.bot.config.channel)
            time.sleep(random.randint(2, 6))

            response = self.bot.discord_bot.sendMessage(
                self.bot.config.channel,
                message
            )

            if response and response.status_code == 429:
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                    "Rate limit on text, waiting 120s"
                )
                time.sleep(120)
                return False

            self.ui.slowPrinting(
                f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} {message}"
            )
            self.bot.total_texts += 1
            return True

        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Send text error: {str(e)[:50]}"
            )
            time.sleep(10)
            return False