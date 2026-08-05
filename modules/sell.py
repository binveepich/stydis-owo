import time
import random
from utils.helpers import UI
from utils.colors import color
from utils.constants import BotConstants

class SellModule:
    def __init__(self):
        self.ui = UI()
        self.bot = None
        self.next_sell_time = 0
    
    def setup(self, bot):
        self.bot = bot
        if self.bot.config.sell.get('enable') == "YES":
            self.next_sell_time = time.time() + random.randint(
                BotConstants.SELL_INTERVAL_MIN,
                BotConstants.SELL_INTERVAL_MAX
            )
            self.bot.scheduler.register_task(
                name="sell",
                func=self.execute,
                min_interval=BotConstants.SELL_INTERVAL_MIN,
                max_interval=BotConstants.SELL_INTERVAL_MAX,
                priority=1
            )
    
    def execute(self):
        if self.bot.config.stopped:
            return
        
        if self.bot.config.sell.get('enable') != "YES":
            return
        
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
            
            self.next_sell_time = time.time() + random.randint(
                BotConstants.SELL_INTERVAL_MIN,
                BotConstants.SELL_INTERVAL_MAX
            )
            
        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Sell error: {str(e)[:50]}"
            )
            time.sleep(5)