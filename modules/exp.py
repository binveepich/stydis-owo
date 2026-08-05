import time
import random
from requests import get
from utils.helpers import UI
from utils.colors import color
from utils.constants import BotConstants

class ExpModule:
    def __init__(self):
        self.ui = UI()
        self.bot = None
        self.quote_count = 0
        self.quote_threshold = random.randint(2, 4)
    
    def setup(self, bot):
        self.bot = bot
        if self.bot.config.em.get('text') == "YES":
            self.bot.scheduler.register_task(
                name="exp",
                func=self.execute,
                min_interval=BotConstants.EXP_INTERVAL_MIN,
                max_interval=BotConstants.EXP_INTERVAL_MAX,
                priority=3
            )
    
    def execute(self):
        if self.bot.config.stopped:
            return
        
        if self.bot.config.em.get('text') != "YES":
            return
        
        try:
            response = get("https://dummyjson.com/quotes/random")
            if response.status_code == 200:
                json_data = response.json()
                quote = f"{json_data['quote']}"
                
                self.bot.discord_bot.typingAction(self.bot.config.channel)
                time.sleep(random.randint(2, 6))
                
                send_response = self.bot.discord_bot.sendMessage(
                    self.bot.config.channel, 
                    quote
                )
                
                if send_response and send_response.status_code == 429:
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                        "Rate limit on exp, waiting 120s"
                    )
                    time.sleep(120)
                    return
                
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} {quote}"
                )
                self.bot.total_texts += 1
                self.quote_count += 1
                
                if (self.bot.config.em.get('owo') == "YES" and 
                    self.quote_count >= self.quote_threshold):
                    time.sleep(random.randint(10, 30))
                    owo = random.choice(['owo', 'uwu'])
                    
                    self.bot.discord_bot.typingAction(self.bot.config.channel)
                    time.sleep(random.randint(2, 6))
                    
                    send_response = self.bot.discord_bot.sendMessage(
                        self.bot.config.channel, 
                        owo
                    )
                    
                    if send_response and send_response.status_code == 429:
                        self.ui.slowPrinting(
                            f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                            "Rate limit on owo/uwu, waiting 120s"
                        )
                        time.sleep(120)
                        return
                    
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.okgreen} [SENT]{color.reset} {owo}"
                    )
                    
                    self.quote_count = 0
                    self.quote_threshold = random.randint(2, 4)
                
                time.sleep(random.randint(15, 40))
                
            else:
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                    f"DummyJSON API failed: {response.status_code}"
                )
                
        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Exp error: {str(e)[:50]}"
            )
            time.sleep(10)