from time import sleep, time
from re import findall
from random import randint
from utils.helpers import print_info, print_warning

class GemModule:
    def __init__(self, bot, start_time):
        self.bot = bot
        self.start_time = start_time
        self.last_inv = 0
        self.last_use = 0
        self.inv_cooldown = 15
        self.use_cooldown = 10
        self.last_used_gems = []
        self.available = [1, 3, 4, 5]
        self.gemtypes = [1, 3, 4, 5]
        self.regex = r"gem(\d):\d+>`\[(\d+)"
        self.owo_id = '408785106942164992'
        self.last_detect_time = 0
        self.detect_cooldown = 5
        
        self.inv_cache = None
        self.inv_cache_time = 0
        self.inv_cache_ttl = randint(222, 777)
        
        self.gem_mapping = {
            51: 1, 52: 1, 53: 1, 54: 1, 55: 1, 56: 1, 57: 1,
            65: 3, 66: 3, 67: 3, 68: 3, 69: 3, 70: 3, 71: 3,
            72: 4, 73: 4, 74: 4, 75: 4, 76: 4, 77: 4, 78: 4,
            79: 5, 80: 5, 81: 5, 82: 5, 83: 5, 84: 5, 85: 5,
        }

    def setup(self, bot):
        if bot.config.gm == "YES":
            bot.scheduler.register_task(
                name="gem",
                func=self.detect,
                min_interval=60,
                max_interval=120,
                priority=6
            )

    def _get_inventory(self, force=False):
        now = time()
        
        if not force and self.inv_cache and (now - self.inv_cache_time < self.inv_cache_ttl):
            return self.inv_cache
        
        self.bot.executor.send_command("inv")
        sleep(3)
        
        msgs = self.bot.getMessages(num=10, channel=self.bot.config.channel)
        if not msgs:
            return None, None
        
        inv_content = None
        for msg in msgs:
            if msg['author']['id'] == self.owo_id and 'Inventory' in msg['content']:
                inv_content = msg['content']
                break
        
        if not inv_content:
            return None, None
        
        inv_items = findall(r'`(.*?)`', inv_content)
        
        if '050' in inv_items:
            self.bot.executor.send_command("lb all")
            sleep(5)
            result = (list(self.gemtypes), {})
            self.inv_cache = result
            self.inv_cache_time = now
            self.inv_cache_ttl = randint(222, 777)
            return result
        
        if '049' in inv_items:
            self.bot.executor.send_command("lb f all")
            sleep(5)
            result = (list(self.gemtypes), {})
            self.inv_cache = result
            self.inv_cache_time = now
            self.inv_cache_ttl = randint(222, 777)
            return result
        
        if '100' in inv_items:
            self.bot.executor.send_command("crate all")
            sleep(5)
        
        if '028' in inv_items:
            sleep(3)
            self.bot.executor.send_command("use 28")
            result = (list(self.gemtypes), {})
            self.inv_cache = result
            self.inv_cache_time = now
            self.inv_cache_ttl = randint(222, 777)
            return result
        
        gem_codes = []
        for item in inv_items:
            if item.isdigit():
                code = int(item)
                if 50 < code < 100:
                    gem_codes.append(code)
        
        available_tiers = []
        tier_codes = {1: [], 3: [], 4: [], 5: []}
        
        for code in gem_codes:
            if code in self.gem_mapping:
                tier = self.gem_mapping[code]
                if tier not in available_tiers:
                    available_tiers.append(tier)
                tier_codes[tier].append(code)
        
        for tier in tier_codes:
            tier_codes[tier].sort(reverse=True)
        
        result = (available_tiers, tier_codes)
        
        self.inv_cache = result
        self.inv_cache_time = now
        self.inv_cache_ttl = randint(222, 777)
        
        print_info(f"Inventory refreshed (next check in {self.inv_cache_ttl}s)")
        
        return result

    def useGems(self, gemslist=None, tier_codes=None):
        if gemslist is None:
            gemslist = [1, 3, 4, 5]
        
        if self.bot is None or self.bot.config.stopped:
            return
        
        if time() - self.last_inv < self.inv_cooldown:
            return
        
        self.last_inv = time()
        
        if tier_codes is None:
            available_tiers, tier_codes = self._get_inventory()
            if available_tiers is None:
                return
            self.available = available_tiers
        else:
            self.available = [tier for tier in tier_codes if tier_codes[tier]]
        
        use = []
        for tier in gemslist:
            if tier in tier_codes and tier_codes[tier]:
                codes = tier_codes[tier]
                if codes:
                    best_code = codes[0]
                    use.append(str(best_code))
        
        if not use:
            return
        
        if time() - self.last_use < self.use_cooldown:
            return
        
        if use == self.last_used_gems:
            return
        
        self.last_used_gems = use.copy()
        self.last_use = time()
        
        sleep(5)
        self.bot.executor.send_command("use " + ' '.join(use))
        print_info(f"Used gems: {' '.join(use)}")

    def detect(self):
        if self.bot is None or self.bot.config.stopped:
            return
        
        if time() - self.last_detect_time < self.detect_cooldown:
            return
        
        self.last_detect_time = time()
        
        msgs = self.bot.getMessages(num=10, channel=self.bot.config.channel)
        if not msgs:
            return
        
        target = None
        for msg in msgs:
            if msg['author']['id'] == self.owo_id and "**🌱" in msg['content']:
                target = msg
                break
        
        if not target:
            return
        
        gems = findall(self.regex, target['content'])
        used_tiers = []
        for gem in gems:
            used_tiers.append(int(gem[0]))
        
        if not used_tiers:
            print_info("Hunt detected: no gems used")
            return
        
        all_tiers = [1, 3, 4, 5]
        missing_tiers = [t for t in all_tiers if t not in used_tiers]
        
        if not missing_tiers:
            return
        
        available_tiers, tier_codes = self._get_inventory()
        if available_tiers is None:
            return
        
        usable_tiers = [t for t in missing_tiers if t in available_tiers and tier_codes.get(t, [])]
        
        if not usable_tiers:
            return
        
        self.useGems(usable_tiers, tier_codes)