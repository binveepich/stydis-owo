import time
import random
from re import findall
from datetime import timedelta
from utils.helpers import UI
from utils.colors import color

class DailyModule:
    def __init__(self):
        self.done = False
        self.ui = UI()
        self.bot = None
    
    def setup(self, bot):
        self.bot = bot
        if self.bot.config.daily == "YES":
            pass
    
    def execute(self):
        if self.bot.config.stopped:
            return
        
        if self.done:
            return
        
        if self.bot.config.daily != "YES":
            return
        
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
                self.execute()
                return
            else:
                if "Nu" in daily_string:
                    daily_numbers = findall('[0-9]+', daily_string)
                    wait_time = str(int(daily_numbers[0]) * 3600 + 
                                  int(daily_numbers[1]) * 60 + 
                                  int(daily_numbers[2]))
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
                        f"Next Daily: {str(timedelta(seconds=int(wait_time)))}"
                    )
                    self.bot.config.wait_time_daily = wait_time
                
                if "Your next daily" in daily_string:
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
                        "Claimed Daily"
                    )
                
                self.done = True
                
        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Daily error: {str(e)[:50]}"
            )
            time.sleep(5)