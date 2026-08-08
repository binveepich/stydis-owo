import time
import asyncio
import discum
from utils.helpers import UI
from utils.colors import color
from utils.constants import BotConstants
from utils.cpu_controller import CPUController


class OwOBot:
    def __init__(self, config, start_time=None):
        self.modules = []
        self.config = config
        self.start_time = start_time if start_time else time.time()
        self.executor = None
        self.scheduler = None
        self.events = None

        self.discord_bot = discum.Client(
            token=config.token,
            log=False,
            user_agent=[
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36/PAsMWa7l-11',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 YaBrowser/20.8.3.115 Yowser/2.5 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.7.2) Gecko/20100101 / Firefox/60.7.2'
            ]
        )

        self.ui = UI()
        self.running = False
        self.hunt_cycles = 0
        self.total_commands = config.totalcmd
        self.total_texts = config.totaltext

        self.gems = None
        self.weapons = None

        self.last_command_id = None
        self.last_command_time = 0
        self.command_history = []

        cpu_config = config.get_cpu_config() if hasattr(config, 'get_cpu_config') else {}
        self.cpu_controller = CPUController(
            max_cpu_percent=cpu_config.get('max_percent', 90.0),
            check_interval=cpu_config.get('check_interval', 1.0),
            max_wait_time=cpu_config.get('max_wait_time', 300.0),
            bot=self
        )

        self.captcha_resolver = None
        self._init_captcha_resolver()

    def _init_captcha_resolver(self):
        try:
            captcha_config = self.config.get_captcha_config()
            if captcha_config.get('enabled', False):
                from captcha_resolver import CaptchaResolver
                self.captcha_resolver = CaptchaResolver(self)
                self.log("INFO", "Captcha resolver initialized")
        except Exception as e:
            self.log("ERROR", f"Failed to init captcha resolver: {e}")

    def log(self, level: str, msg: str):
        from utils.colors import color
        level_colors = {
            'INFO': color.okcyan,
            'SUCCESS': color.okgreen,
            'WARN': color.warning,
            'ERROR': color.fail,
            'SECURITY': color.purple,
            'SYS': color.okblue,
            'DETECTED': color.warning,
        }
        color_code = level_colors.get(level, color.reset)
        self.ui.slowPrinting(f"{self.at()} {color_code}[{level}]{color.reset} {msg}")

    def register_module(self, module):
        self.modules.append(module)
        if hasattr(module, 'setup'):
            try:
                module.setup(self)
            except Exception as e:
                print(f"Error setting up module {module.__class__.__name__}: {e}")

    def set_gems_module(self, gems_module):
        self.gems = gems_module

    def set_weapons_module(self, weapons_module):
        self.weapons = weapons_module

    def start(self):
        self.running = True
        
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        self.log("INFO", "Checking CPU before starting...")
        
        if not self.cpu_controller.is_cpu_safe():
            self.log("WARN", f"CPU high: {self.cpu_controller.get_cpu_usage():.1f}% >= {self.cpu_controller.max_cpu_percent}%")
            self.log("INFO", "Waiting for CPU to stabilize...")
            
            ready = self.cpu_controller.wait_for_cpu(
                on_waiting=lambda: self.log("INFO", "Waiting for CPU to drop..."),
                on_ready=lambda: self.log("SUCCESS", "CPU ready, starting bot..."),
                on_timeout=lambda: self.log("WARN", "Timeout, starting bot anyway...")
            )
            
            if ready:
                self.log("SUCCESS", "CPU safe, starting bot...")
            else:
                self.log("WARN", "CPU timeout, starting bot anyway...")
        else:
            self.log("SUCCESS", f"CPU safe: {self.cpu_controller.get_cpu_usage():.1f}% < {self.cpu_controller.max_cpu_percent}%")
        
        self.discord_bot.gateway.run(auto_reconnect=True)

    def stop(self):
        self.running = False
        self.config.stopped = True

        if self.scheduler:
            try:
                self.scheduler.stop()
            except:
                pass

        try:
            self.discord_bot.gateway.close()
        except:
            pass

        self.ui.slowPrinting(f"\n{self.at()} Bot stopped!")
        self.ui.slowPrinting(f"{self.at()} Total Commands: {self.total_commands}")
        self.ui.slowPrinting(f"{self.at()} Total Texts: {self.total_texts}")
        self.ui.slowPrinting(f"{self.at()} Status: IDLE")

    def resume(self):
        try:
            self.log("INFO", "Resuming bot...")
            
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            self.log("INFO", "Checking CPU before resuming...")
            
            if not self.cpu_controller.is_cpu_safe():
                self.log("WARN", f"CPU high: {self.cpu_controller.get_cpu_usage():.1f}% >= {self.cpu_controller.max_cpu_percent}%")
                self.log("INFO", "Waiting for CPU to stabilize before resuming...")
                
                ready = self.cpu_controller.wait_for_cpu(
                    on_waiting=lambda: self.log("INFO", "Waiting for CPU to drop..."),
                    on_ready=lambda: self.log("SUCCESS", "CPU ready, resuming bot..."),
                    on_timeout=lambda: self.log("WARN", "Timeout, resuming bot anyway...")
                )
                
                if ready:
                    self.log("SUCCESS", "CPU safe, resuming bot...")
                else:
                    self.log("WARN", "CPU timeout, resuming bot anyway...")
            else:
                self.log("SUCCESS", f"CPU safe: {self.cpu_controller.get_cpu_usage():.1f}% < {self.cpu_controller.max_cpu_percent}%")
            
            self.config.stopped = False
            self.running = True

            try:
                if not self.discord_bot.gateway._ws:
                    self.discord_bot.gateway.run(auto_reconnect=True)
                else:
                    self.log("INFO", "Gateway already running")
            except Exception as e:
                self.log("ERROR", f"Gateway restart failed: {e}")

            if self.scheduler and not self.scheduler.running:
                self.log("INFO", "Starting scheduler...")
                self.scheduler.start()

            self.log("SUCCESS", "Bot resumed successfully!")

        except Exception as e:
            self.log("ERROR", f"Resume failed: {e}")

    def has_captcha_resolver(self) -> bool:
        return (self.captcha_resolver is not None and
                self.captcha_resolver.is_available())

    def is_captcha_mode(self) -> bool:
        return (self.events and self.events._is_solving)

    def at(self):
        elapsed = int(time.time() - self.start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f'\033[0;43m{h:02}:{m:02}:{s:02}\033[0;21m'

    def getMessages(self, num=1, channel=None):
        if channel is None:
            channel = self.config.channel

        messageObject = None
        retries = 0
        while not messageObject and retries <= 10:
            try:
                messageObject = self.discord_bot.getMessages(channel, num=num)
                messageObject = messageObject.json()
                if not isinstance(messageObject, list):
                    messageObject = None
                else:
                    break
                retries += 1
                time.sleep(5)
            except Exception as e:
                retries += 1
                time.sleep(5)
        if not messageObject:
            return []
        return messageObject