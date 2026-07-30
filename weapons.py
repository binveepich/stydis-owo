# weapons.py
from time import time, sleep
from re import findall
import random
from color import color
from data import data
from menu import UI

client = data()
ui = UI()


class weapons:
    def __init__(self, bot, start_time):
        self.bot = bot
        self.start_time = start_time
        self.last_buy_time = 0
        self.buy_cooldown_min = 7
        self.buy_cooldown_max = 25
        self.skip_probability = 0.2
        self.failed_attempts = 0
        self.max_retries = random.randint(2, 5)
        self.has_enough_shards = True
        self.is_initialized = False
        self.remaining_crates = 0
        self.total_crates = 0
        self.OwOID = "408785106942164992"

    def at(self):
        elapsed = int(time() - self.start_time)
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        return f'\033[0;43m{h:02}:{m:02}:{s:02}\033[0;21m'

    def _parse_shards(self, messages):
        if not messages:
            return 0
        for msg in messages[:2]:
            if not isinstance(msg, dict):
                continue
            if msg.get('author', {}).get('id') != self.OwOID:
                continue
            content = msg.get('content', '')
            if "Weapon Shards" in content:
                numbers = findall(r'[\d,]+', content)
                if numbers:
                    try:
                        return int(numbers[-1].replace(',', ''))
                    except ValueError:
                        continue
        return 0

    def _check_purchase_success(self, messages):
        if not messages:
            return False
        for msg in messages[:2]:
            if not isinstance(msg, dict):
                continue
            if msg.get('author', {}).get('id') == self.OwOID:
                content = msg.get('content', '')
                if "purchased a" in content and "Weapon Crate" in content:
                    return True
        return False

    def initialize(self):
        if self.is_initialized or not self.has_enough_shards or client.stopped:
            return

        ui.slowPrinting(f"{self.at()}{color.okblue} [INFO] {color.reset} Checking weapon shards...")

        try:
            self.bot.typingAction(str(client.channel))
            sleep(random.uniform(1, 2))
            self.bot.sendMessage(str(client.channel), "owo ws")
            ui.slowPrinting(f"{self.at()}{color.okgreen} [SENT] {color.reset} owo ws")
            client.totalcmd += 1
            self.last_check = time()
        except Exception as e:
            ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS] {color.reset} Failed: {e}")
            return

        sleep(3)
        if client.stopped:
            return

        try:
            msgs = self.bot.getMessages(str(client.channel), num=5).json()
            if not isinstance(msgs, list):
                msgs = []
        except Exception as e:
            ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS] {color.reset} Error: {e}")
            return

        shard_count = self._parse_shards(msgs)
        if shard_count == 0:
            ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS] {color.reset} Could not parse shard count")
            return

        max_crates = shard_count // 40
        if max_crates <= 0:
            ui.slowPrinting(f"{self.at()}{color.warning} [INFO] {color.reset} Only {shard_count:,} Shards! Need ≥40")
            self.has_enough_shards = False
            self.is_initialized = True
            return

        self.remaining_crates = max_crates
        self.total_crates = max_crates
        self.is_initialized = True
        ui.slowPrinting(f"{self.at()}{color.okblue} [INFO] {color.reset} Found {shard_count:,} Shards! Can buy {max_crates:,} CRATE(s)")

    def buy_one_crate(self):
        if client.stopped or not self.has_enough_shards:
            return

        if not self.is_initialized:
            self.initialize()
            return

        if self.failed_attempts >= self.max_retries:
            ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS] {color.reset} Failed {self.max_retries} times, stopping")
            self.has_enough_shards = False
            return

        if self.remaining_crates <= 0:
            ui.slowPrinting(f"{self.at()}{color.okblue} [INFO] {color.reset} Bought all {self.total_crates:,} CRATE(s)!")
            self.has_enough_shards = False
            return

        if random.random() < self.skip_probability:
            return

        now = time()
        cooldown = random.randint(self.buy_cooldown_min, self.buy_cooldown_max)
        if now - self.last_buy_time < cooldown:
            return

        try:
            self.bot.typingAction(str(client.channel))
            sleep(random.uniform(0.5, 1.5))
            self.bot.sendMessage(str(client.channel), "owo buy 100")
            ui.slowPrinting(f"{self.at()}{color.okgreen} [SENT] {color.reset} owo buy 100")
            client.totalcmd += 1
            self.last_buy_time = now
        except Exception as e:
            ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS] {color.reset} Failed: {e}")
            self.failed_attempts += 1
            return

        sleep(3)
        if client.stopped:
            return

        try:
            msgs = self.bot.getMessages(str(client.channel), num=5).json()
            if not isinstance(msgs, list):
                msgs = []
        except Exception as e:
            ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS] {color.reset} Error: {e}")
            self.failed_attempts += 1
            return

        if self._check_purchase_success(msgs):
            self.remaining_crates -= 1
            self.failed_attempts = 0
            ui.slowPrinting(f"{self.at()}{color.okblue} [INFO] {color.reset} Bought CRATE, {self.remaining_crates:,} left")
        else:
            self.failed_attempts += 1
            ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS] {color.reset} Failed (attempt {self.failed_attempts}/{self.max_retries})")

    def reset_state(self):
        self.has_enough_shards = True
        self.is_initialized = False
        self.remaining_crates = 0
        self.total_crates = 0
        self.last_check = 0
        self.last_buy_time = 0
        self.failed_attempts = 0
        self.max_retries = random.randint(5, 12)
        ui.slowPrinting(f"{self.at()}{color.okblue} [INFO] {color.reset} Weapon state reset")