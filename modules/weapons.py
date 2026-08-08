from time import time, sleep
from re import findall
import random
from utils.colors import color


class WeaponModule:
    def __init__(self, bot, start_time):
        self.bot = bot
        self.start_time = start_time
        self.last_buy_time = 0
        self.buy_cooldown_min = 11
        self.buy_cooldown_max = 33
        self.skip_probability = 0.05
        self.failed_attempts = 0
        self.max_retries = random.randint(3, 6)
        self.has_enough_shards = True
        self.is_initialized = False
        self.remaining_crates = 0
        self.total_crates = 0
        self.OwOID = "408785106942164992"
        self.last_check = 0
        self.ui = bot.ui
        
        self.last_ws_sent_time = 0
        self.last_ws_message_id = None
        self.pending_ws_check = False
        
        self.max_parse_retries = 5
        self.current_parse_retry = 0
        self.parse_retry_delay = 3
    
    def setup(self, bot):
        self.bot = bot
        if bot.config.wm == "YES":
            bot.scheduler.register_task(
                name="weapon",
                func=self.buy_one_crate,
                min_interval=11,
                max_interval=33,
                priority=2
            )
    
    def at(self):
        elapsed = int(time() - self.start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f'\033[0;43m{h:02}:{m:02}:{s:02}\033[0;21m'
    
    def _send_ws_command(self):
        now = time()
        
        if now - self.last_ws_sent_time < 10:
            return False
            
        try:
            self.bot.discord_bot.typingAction(str(self.bot.config.channel))
            sleep(random.uniform(1, 2))
            self.bot.discord_bot.sendMessage(str(self.bot.config.channel), "owo ws")
            self.ui.slowPrinting(f"{self.at()}{color.okgreen} [SENT]{color.reset} owo ws")
            self.bot.total_commands += 1
            self.last_ws_sent_time = now
            self.pending_ws_check = True
            return True
        except Exception as e:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Failed to send ws: {e}")
            return False
    
    def _parse_shards(self, messages):
        if not messages:
            return None, False
        
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            
            if msg.get('author', {}).get('id') != self.OwOID:
                continue
            
            content = msg.get('content', '')
            if not content or "Weapon Shards" not in content:
                continue
            
            msg_id = msg.get('id')
            if msg_id == self.last_ws_message_id:
                continue
            
            if "currently have 0 Weapon Shards" in content:
                return 0, True
            
            numbers = findall(r'[\d,]+', content)
            if numbers:
                try:
                    shard_count = int(numbers[-1].replace(',', ''))
                    self.last_ws_message_id = msg_id
                    self.pending_ws_check = False
                    return shard_count, True
                except ValueError:
                    continue
        
        return None, False
    
    def _check_purchase_success(self, messages):
        if not messages:
            return False
        
        for msg in messages[:3]:
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
        
        if not self._send_ws_command():
            self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} WS command already sent recently")
            return
        
        shard_count = self._get_shard_count_with_retry()
        
        if shard_count is None:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Failed to get shard count after {self.max_parse_retries} retries")
            return
        
        if shard_count == 0:
            self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} You have 0 Weapon Shards! Module stopped")
            self.has_enough_shards = False
            self.is_initialized = True
            self.remaining_crates = 0
            self.total_crates = 0
            return
        
        max_crates = shard_count // 40
        if max_crates <= 0:
            self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} Only {shard_count:,} Shards! Need ≥40. Module stopped!")
            self.has_enough_shards = False
            self.is_initialized = True
            self.remaining_crates = 0
            self.total_crates = 0
            return
        
        self.remaining_crates = max_crates
        self.total_crates = max_crates
        self.is_initialized = True
        self.has_enough_shards = True
        self.failed_attempts = 0
        self.current_parse_retry = 0
        
        self.ui.slowPrinting(f"{self.at()}{color.okgreen} [WEAPONS]{color.reset} Found {shard_count:,} Shards! Can buy {max_crates:,} CRATE(s)")
    
    def _get_shard_count_with_retry(self):
        for attempt in range(self.max_parse_retries):
            msgs = self.bot.getMessages(num=10, channel=self.bot.config.channel)
            
            if not msgs:
                if attempt < self.max_parse_retries - 1:
                    self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} Retry {attempt + 1}/{self.max_parse_retries}...")
                    sleep(self.parse_retry_delay)
                    continue
                return None
            
            shard_count, found = self._parse_shards(msgs)
            
            if found:
                return shard_count
            
            if attempt < self.max_parse_retries - 1:
                self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} Retry {attempt + 1}/{self.max_parse_retries}...")
                sleep(self.parse_retry_delay)
        
        return None
    
    def buy_one_crate(self):
        if self.bot.config.stopped or not self.has_enough_shards:
            return
        
        if not self.is_initialized:
            self.initialize()
            return
        
        if self.failed_attempts >= self.max_retries:
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Failed {self.max_retries} times, stopping module")
            self.has_enough_shards = False
            return
        
        if self.remaining_crates <= 0:
            self.ui.slowPrinting(f"{self.at()}{color.okgreen} [WEAPONS]{color.reset} Bought all {self.total_crates:,} CRATE(s)! Module stopped")
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
            self.ui.slowPrinting(f"{self.at()}{color.fail} [WEAPONS]{color.reset} Failed to send buy: {e}")
            self.failed_attempts += 1
            return
        
        sleep(random.uniform(3, 5))
        if self.bot.config.stopped:
            return
        
        msgs = self.bot.getMessages(num=5, channel=self.bot.config.channel)
        if not msgs:
            self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} Could not get messages")
            self.failed_attempts += 1
            return
        
        if self._check_purchase_success(msgs):
            self.remaining_crates -= 1
            self.failed_attempts = 0
            self.ui.slowPrinting(f"{self.at()}{color.okblue} [WEAPONS]{color.reset} Bought CRATE, {self.remaining_crates:,} left")
            
            self.pending_ws_check = False
            self.last_ws_sent_time = 0
        else:
            self.failed_attempts += 1
            self.ui.slowPrinting(f"{self.at()}{color.warning} [WEAPONS]{color.reset} Failed to buy (attempt {self.failed_attempts}/{self.max_retries})")
    
    def reset_state(self):
        self.has_enough_shards = True
        self.is_initialized = False
        self.remaining_crates = 0
        self.total_crates = 0
        self.last_check = 0
        self.last_buy_time = 0
        self.failed_attempts = 0
        self.max_retries = random.randint(3, 6)
        self.current_parse_retry = 0
        self.last_ws_sent_time = 0
        self.last_ws_message_id = None
        self.pending_ws_check = False
        self.ui.slowPrinting(f"{self.at()}{color.okblue} [INFO]{color.reset} Weapon module state reset")