from time import sleep, time
from re import findall
import random
from utils.helpers import print_info, print_warning


class GemModule:
    def __init__(self, bot, start_time):
        self.bot = bot
        self.start_time = start_time
        
        self.inv_cooldown = 333
        self.use_cooldown = 10
        self.last_inv_check = 0
        self.last_use_time = 0
        
        self.last_used_gems = []
        
        self.owo_id = '408785106942164992'
        
        self.gem_priority = [5, 4, 3, 1]
        
        self.gem_mapping = {
            51: 1, 52: 1, 53: 1, 54: 1, 55: 1, 56: 1, 57: 1,
            65: 3, 66: 3, 67: 3, 68: 3, 69: 3, 70: 3, 71: 3,
            72: 4, 73: 4, 74: 4, 75: 4, 76: 4, 77: 4, 78: 4,
            79: 5, 80: 5, 81: 5, 82: 5, 83: 5, 84: 5, 85: 5,
        }
        
        self.regex = r"gem(\d):\d+>`\[(\d+)"
        
        self.first_check_done = False
        self.initialized = False
        self.has_active_gems = False
        
        self.use_failures = 0
        self.max_failures = 3
        self._last_items_check = 0
        
    def setup(self, bot):
        if bot.config.gm == "YES":
            bot.scheduler.register_task(
                name="gem",
                func=self.gem_cycle,
                min_interval=15,
                max_interval=15,
                priority=6
            )
            if not self.initialized:
                self.initialized = True
                print_info("Gem module initialized")

    def gem_cycle(self):
        if self.bot is None or self.bot.config.stopped:
            return

        try:
            hunt_msg = self._get_hunt_message()
            
            is_empowered = False
            active_tiers = []
            
            if hunt_msg:
                if "**🌱" in hunt_msg and "hunt is empowered by" in hunt_msg.lower():
                    is_empowered = True
                    gems_in_use = self._parse_hunt_gems_from_message(hunt_msg)
                    active_tiers = [int(gem[0]) for gem in gems_in_use] if gems_in_use else []
                    self.has_active_gems = True
                    self.use_failures = 0
                else:
                    self.has_active_gems = False
            
            needed_tiers = list(self.gem_priority)
            
            if self.has_active_gems and active_tiers:
                for tier in active_tiers:
                    if tier in needed_tiers:
                        needed_tiers.remove(tier)
            elif not self.has_active_gems:
                needed_tiers = list(self.gem_priority)
            
            if needed_tiers:
                gems_used = self._check_and_use_gems(needed_tiers)
                if gems_used:
                    return
            
            if self.has_active_gems or not needed_tiers:
                self._handle_items_if_needed()
                
        except Exception as e:
            print_warning(f"Gem error: {str(e)[:50]}")

    def _get_hunt_message(self):
        msgs = self.bot.getMessages(num=10, channel=self.bot.config.channel)
        if not msgs:
            return None
            
        for msg in msgs:
            if msg.get('author', {}).get('id') == self.owo_id:
                content = msg.get('content', '')
                if 'spent 5' in content and 'caught a' in content:
                    return content
                if 'hunt is empowered by' in content.lower():
                    return content
        return None

    def _parse_hunt_gems_from_message(self, content):
        if not content:
            return []
        return findall(self.regex, content)

    def _check_and_use_gems(self, needed_tiers):
        now = time()
        
        if self.use_failures >= self.max_failures:
            if now - self.last_inv_check < 600:
                return False
            self.use_failures = 0
        
        if not self.first_check_done:
            self.first_check_done = True
            print_info("Initial gems check...")
        elif now - self.last_inv_check < self.inv_cooldown:
            return False
            
        self.last_inv_check = now
        
        self.bot.executor.send_command("inv", extra_delay=True)
        sleep(random.uniform(2, 4))

        if self.bot.config.stopped:
            return False

        msgs = self.bot.getMessages(num=10, channel=self.bot.config.channel)
        if not msgs:
            return False

        inv_content = None
        for msg in msgs:
            if (msg.get('author', {}).get('id') == self.owo_id and
                'Inventory' in msg.get('content', '')):
                inv_content = msg['content']
                break

        if not inv_content:
            return False

        inv_items = findall(r'`(.*?)`', inv_content)

        gems_by_tier = {1: [], 3: [], 4: [], 5: []}
        
        for item in inv_items:
            if item.isdigit():
                code = int(item)
                if 50 < code < 100:
                    tier = self.gem_mapping.get(code)
                    if tier and tier in needed_tiers:
                        gems_by_tier[tier].append(code)

        gems_to_use = []
        for tier in needed_tiers:
            if gems_by_tier[tier]:
                best_gem = max(gems_by_tier[tier])
                gems_to_use.append(str(best_gem))

        if not gems_to_use:
            return False

        if gems_to_use == self.last_used_gems:
            return False

        if time() - self.last_use_time < self.use_cooldown:
            return False

        print_info(f"Gems to use: {' '.join(gems_to_use)}")
        
        self.bot.executor.send_command(f"use {' '.join(gems_to_use)}", extra_delay=True)
        sleep(random.uniform(2, 4))

        msgs = self.bot.getMessages(num=5, channel=self.bot.config.channel)
        use_success = False
        
        for msg in msgs:
            if msg.get('author', {}).get('id') == self.owo_id:
                content = msg.get('content', '').lower()
                if 'you do not own this gem' in content or 'already have an active' in content:
                    self.use_failures += 1
                    print_warning(f"Gem use failed ({self.use_failures}/{self.max_failures})")
                    return False
                if 'equipped' in content or 'active' in content:
                    use_success = True
                    self.use_failures = 0
                    break

        if use_success:
            self.last_used_gems = gems_to_use.copy()
            self.last_use_time = time()
            self.has_active_gems = True
            return True
        
        return False

    def _handle_items_if_needed(self):
        now = time()
        
        if now - self._last_items_check < 60:
            return
            
        self._last_items_check = now
        
        msgs = self.bot.getMessages(num=10, channel=self.bot.config.channel)
        if not msgs:
            return

        inv_content = None
        for msg in msgs:
            if (msg.get('author', {}).get('id') == self.owo_id and
                'Inventory' in msg.get('content', '')):
                inv_content = msg['content']
                break

        if not inv_content:
            return

        inv_items = findall(r'`(.*?)`', inv_content)
        
        if '050' in inv_items:
            print_info("Found Lootbox(es)...")
            self.bot.executor.send_command("lb all", extra_delay=True)
            sleep(5)
            return
            
        if '049' in inv_items:
            print_info("Found Fabled Lootbox(es)...")
            self.bot.executor.send_command("lb f all", extra_delay=True)
            sleep(5)
            return
            
        if '100' in inv_items:
            print_info("Found Crate(s)...")
            self.bot.executor.send_command("crate all", extra_delay=True)
            sleep(5)
            return
            
        if '028' in inv_items:
            print_info("Found Lucky Box(es)...")
            sleep(3)
            self.bot.executor.send_command("use 28", extra_delay=True)
            sleep(5)
            return

    def reset(self):
        self.last_inv_check = 0
        self.last_use_time = 0
        self.last_used_gems = []
        self.first_check_done = False
        self.has_active_gems = False
        self.use_failures = 0
        self._last_items_check = 0
        print_info("Gem module reset")