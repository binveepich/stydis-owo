import time
import random
from utils.helpers import UI
from utils.colors import color
from utils.constants import BotConstants

class PrayModule:
    def __init__(self):
        self.first_pray = True
        self.ui = UI()
        self.bot = None
    
    def setup(self, bot):
        self.bot = bot
        if self.bot.config.pm == "YES":
            self.bot.scheduler.register_task(
                name="pray",
                func=self.execute,
                min_interval=BotConstants.PRAY_INTERVAL_MIN,
                max_interval=BotConstants.PRAY_INTERVAL_MAX,
                priority=5,
            )
    
    def execute(self):
        if self.bot.config.stopped:
            return
        
        if self.bot.config.pm != "YES":
            return
        
        if self.first_pray and self.bot.hunt_cycles < BotConstants.PRAY_REQUIRED_CYCLES:
            return
        
        try:
            self.bot.discord_bot.typingAction(self.bot.config.channel)
            time.sleep(random.randint(5, 15))
            
            send_response = self.bot.discord_bot.sendMessage(
                self.bot.config.channel, 
                "owo pray"
            )
            
            if send_response and send_response.status_code == 429:
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                    "Rate limit on pray, waiting 120s"
                )
                time.sleep(120)
                return
            
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} owo pray"
            )
            self.bot.total_commands += 1
            self.first_pray = False
            
            time.sleep(random.randint(60, 120))
            
        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Pray error: {str(e)[:50]}"
            )
            time.sleep(10)