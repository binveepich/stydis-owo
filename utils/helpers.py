import os
import time
import sys
import random
from utils.colors import color
from utils.constants import BotConstants

START_TIME = time.time()

def at():
    elapsed = int(time.time() - START_TIME)
    h = elapsed // 3600
    m = (elapsed % 3600) // 60
    s = elapsed % 60
    return f'\033[0;43m{h:02}:{m:02}:{s:02}\033[0;21m'

class UI:
    @classmethod
    def slowPrinting(cls, text):
        for letter in text:
            time.sleep(0.002)
            print(letter, end="", flush=True)
        print("")
    
    @classmethod
    def logo(cls):
        version = BotConstants.VERSION
        
        cls.slowPrinting("░█████╗░░██╗░░░░░░░██╗░█████╗░  ░██████╗███████╗██╗░░░░░███████╗  ██████╗░░█████╗░████████╗")
        cls.slowPrinting("██╔══██╗░██║░░██╗░░██║██╔══██╗  ██╔════╝██╔════╝██║░░░░░██╔════╝  ██╔══██╗██╔══██╗╚══██╔══╝")
        cls.slowPrinting("██║░░██║░╚██╗████╗██╔╝██║░░██║  ╚█████╗░█████╗░░██║░░░░░█████╗░░  ██████╦╝██║░░██║░░░██║░░░")
        cls.slowPrinting("██║░░██║░░████╔═████║░██║░░██║  ░╚═══██╗██╔══╝░░██║░░░░░██╔══╝░░  ██╔══██╗██║░░██║░░░██║░░░")
        cls.slowPrinting("╚█████╔╝░░╚██╔╝░╚██╔╝░╚█████╔╝  ██████╔╝███████╗███████╗██║░░░░░  ██████╦╝╚█████╔╝░░░██║░░░")
        cls.slowPrinting("░╚════╝░░░░╚═╝░░░╚═╝░░░╚════╝░  ╚═════╝░╚══════╝╚══════╝╚═╝░░░░░  ╚═════╝░░╚════╝░░░░╚═╝░░░")
        cls.slowPrinting(f"                                {color.purple}Version: {version}{color.reset}")
        time.sleep(0.5)
        print()

def slow_print(text, delay=0.002):
    UI.slowPrinting(text)

def show_logo():
    UI.logo()

def print_sent(cmd):
    print(f"{at()}{color.okgreen} [SENT]{color.reset} {cmd}")

def print_info(msg):
    print(f"{at()}{color.okcyan} [INFO]{color.reset} {msg}")

def print_warning(msg):
    print(f"{at()}{color.warning} [WARN]{color.reset} {msg}")

def print_error(msg):
    print(f"{at()}{color.fail} [ERROR]{color.reset} {msg}")

def print_success(msg):
    print(f"{at()}{color.okgreen} [SUCCESS]{color.reset} {msg}")

def print_debug(msg):
    print(f"{at()}{color.purple} [DEBUG]{color.reset} {msg}")

def get_random_delay(min_seconds, max_seconds):
    return random.uniform(min_seconds, max_seconds)

def get_random_int_delay(min_seconds, max_seconds):
    return random.randint(min_seconds, max_seconds)

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h{m}m{s}s"
    elif m > 0:
        return f"{m}m{s}s"
    else:
        return f"{s}s"

def truncate_text(text, max_length=100):
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."