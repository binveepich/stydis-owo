from time import time, sleep
from re import findall
import random
from utils.colors import color

class WeaponModule:
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
        self.last_check = 0
        self.ui = bot.ui
    
    def setup(self, bot):
        self.bot = bot
        if bot.config.wm == "YES":
            bot.scheduler.register_task(
                name="weapon",
                func=self.buy_one_crate,
                min_interval=66,
                max_interval=99,
                priority=2
            )
    
    def at(self):
        elapsed = int(time() - self.start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f'\033[0;43m{h:02}:{m:02}:{s:02}\033[0;21m'
    
    def _parse_shards(self, messages):
        """Returns (shard_count, found_info)"""
        if not messages:
            return 0, False
        
        for msg in messages[:2]:
            if not isinstance(msg, dict):
                continue
            if msg.get('author', {}).get('id') != self.OwOID:
                continue
            
            content = msg.get('content', '')
            if "Weapon Shards" not in content:
                continue
            
            # Check for explicit 0 shards
            if "currently have 0 Weapon Shards" in content:
                return 0, True
            
            numbers = findall(r'[\d,]+', content)
            if numbers:
                try:
                    return int(numbers[-1].replace(',', '')), True
                except ValueError:
                    continue
        
        return 0, False
    
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
        if self.is_initialized or not self.has_enough_shards or self.bot.config.stopped:
            return
        
        self.ui.slowPrinting(f"{self.at()}{color.okblue} [INFO]{color.reset} Checking weapon shards...")
        
        try:
            self.bot.discord_bot.typingAction(str(self.bot.config.channel))
            sleep(random.uniform(1, 2))
            self.bot.discord_bot.sendMessage(str(self.bot.config.channel), "owo ws")
            self.ui.slowPrinting(f"{self.at()}{color.okgreen} [SENT]{color.reset} owo ws")
            self.bot.total_commands += 1
            self.last_check = time()
        except Exception as e:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Failed: {e}")
            return
        
        sleep(3)
        if self.bot.config.stopped:
            return
        
        msgs = self.bot.getMessages(num=5, channel=self.bot.config.channel)
        if not msgs:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Could not get messages")
            return
        
        shard_count, found_info = self._parse_shards(msgs)
        
        # Không tìm thấy thông tin -> thử lại sau
        if not found_info:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Could not parse shard count")
            return
        
        # Có 0 shards -> disable hoàn toàn
        if shard_count == 0:
            self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} You have 0 Weapon Shards! Module stopped")
            self.has_enough_shards = False
            self.is_initialized = True
            self.remaining_crates = 0
            self.total_crates = 0
            return
        
        max_crates = shard_count // 40
        if max_crates <= 0:
            self.ui.slowPrinting(f"{self.at()}{color.warning} [INFO]{color.reset} Only {shard_count:,} Shards! Need ≥40")
            self.has_enough_shards = False
            self.is_initialized = True
            self.remaining_crates = 0
            self.total_crates = 0
            return
        
        self.remaining_crates = max_crates
        self.total_crates = max_crates
        self.is_initialized = True
        self.has_enough_shards = True
        self.ui.slowPrinting(f"{self.at()}{color.okblue} [INFO]{color.reset} Found {shard_count:,} Shards! Can buy {max_crates:,} CRATE(s)")
    
    def buy_one_crate(self):
        if self.bot.config.stopped or not self.has_enough_shards:
            return
        
        if not self.is_initialized:
            self.initialize()
            return
        
        if self.failed_attempts >= self.max_retries:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Failed {self.max_retries} times, stopping")
            self.has_enough_shards = False
            return
        
        if self.remaining_crates <= 0:
            self.ui.slowPrinting(f"{self.at()}{color.okblue} [INFO]{color.reset} Bought all {self.total_crates:,} CRATE(s)!")
            self.has_enough_shards = False
            return
        
        if random.random() < self.skip_probability:
            return
        
        now = time()
        cooldown = random.randint(self.buy_cooldown_min, self.buy_cooldown_max)
        if now - self.last_buy_time < cooldown:
            return
        
        try:
            self.bot.discord_bot.typingAction(str(self.bot.config.channel))
            sleep(random.uniform(0.5, 1.5))
            self.bot.discord_bot.sendMessage(str(self.bot.config.channel), "owo buy 100")
            self.ui.slowPrinting(f"{self.at()}{color.okgreen} [SENT]{color.reset} owo buy 100")
            self.bot.total_commands += 1
            self.last_buy_time = now
        except Exception as e:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Failed: {e}")
            self.failed_attempts += 1
            return
        
        sleep(3)
        if self.bot.config.stopped:
            return
        
        msgs = self.bot.getMessages(num=5, channel=self.bot.config.channel)
        if not msgs:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Could not get messages")
            self.failed_attempts += 1
            return
        
        if self._check_purchase_success(msgs):
            self.remaining_crates -= 1
            self.failed_attempts = 0
            self.ui.slowPrinting(f"{self.at()}{color.okblue} [INFO]{color.reset} Bought CRATE, {self.remaining_crates:,} left")
        else:
            self.failed_attempts += 1
            self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} Failed (attempt {self.failed_attempts}/{self.max_retries})")
    
    def reset_state(self):
        self.has_enough_shards = True
        self.is_initialized = False
        self.remaining_crates = 0
        self.total_crates = 0
        self.last_check = 0
        self.last_buy_time = 0
        self.failed_attempts = 0
        self.max_retries = random.randint(5, 12)
        self.ui.slowPrinting(f"{self.at()}{color.okblue} [INFO]{color.reset} Weapon state reset")