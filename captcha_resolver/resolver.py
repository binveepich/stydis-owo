import asyncio
import aiohttp
import time
import sys
import os
import json
import subprocess
from typing import Optional

from .web_solver import WebSolver
from .image_solver import ImageSolver


class CaptchaResolver:
    def __init__(self, bot):
        self.bot = bot
        self.web_solver = None
        self.image_solver = None
        self.max_retries = 3
        self.retry_count = 0
        self._is_running = False
        
        self._init_solvers()
        
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

    def _log(self, level: str, msg: str):
        if self.bot:
            self.bot.log(level, f"[Resolver] {msg}")

    def _init_solvers(self):
        config = self.bot.config.get('captcha', {})

        if not config.get('enabled', False):
            self._log("INFO", "Captcha resolver disabled")
            return

        api_key = config.get('api_key')
        if api_key:
            try:
                service = config.get('service', '2captcha')
                self.web_solver = WebSolver(
                    api_key=api_key,
                    service=service,
                    bot=self.bot
                )
                self._log("INFO", f"Web solver ready (service: {service})")
            except Exception as e:
                self._log("ERROR", f"Failed to init web solver: {e}")

        if config.get('enable_image', True):
            try:
                model_path = config.get('model_path', 'best.onnx')
                if not os.path.exists(model_path):
                    possible_paths = [
                        model_path,
                        os.path.join('captcha_resolver', 'models', 'best.onnx'),
                        os.path.join('captcha_resolver', 'best.onnx'),
                        os.path.join('models', 'best.onnx'),
                    ]
                    for p in possible_paths:
                        if os.path.exists(p):
                            model_path = p
                            break
                
                self.image_solver = ImageSolver(
                    model_path=model_path,
                    bot=self.bot
                )
                if self.image_solver.is_available():
                    self._log("INFO", "Image solver ready")
                else:
                    self._log("WARN", "Image solver not available (model not found)")
            except Exception as e:
                self._log("ERROR", f"Failed to init image solver: {e}")

    async def _fetch_captcha_image(self) -> Optional[bytes]:
        try:
            headers = {
                "Authorization": self.bot.config.token,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                self._log("INFO", "  Fetching from owobot.com...")
                
                async with session.get("https://owobot.com/captcha/image", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        self._log("SUCCESS", f"  Image received: {len(data)} bytes")
                        return data
                    else:
                        self._log("WARN", f"  Status: {resp.status}")

                async with session.get("https://owobot.com/captcha", timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        import re
                        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
                        if match:
                            img_url = match.group(1)
                            if not img_url.startswith('http'):
                                img_url = 'https://owobot.com' + img_url
                            self._log("INFO", f"  Fetching from: {img_url[:50]}...")
                            async with session.get(img_url, timeout=10) as img_resp:
                                if img_resp.status == 200:
                                    data = await img_resp.read()
                                    self._log("SUCCESS", f"  Image received: {len(data)} bytes")
                                    return data

                return None
        except Exception as e:
            self._log("ERROR", f"Fetch image failed: {e}")
            return None

    async def _submit_captcha(self, token: str) -> bool:
        try:
            headers = {
                "Authorization": self.bot.config.token,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://owobot.com/captcha",
                "Origin": "https://owobot.com",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(
                    "https://owobot.com/api/captcha/verify",
                    json={"token": token}
                ) as resp:
                    if resp.status == 200:
                        self._log("SUCCESS", "  Verified by server!")
                        return True
                    else:
                        self._log("ERROR", f"  Server rejected: {resp.status}")
                        return False
        except Exception as e:
            self._log("ERROR", f"Submit error: {e}")
            return False

    async def _solve_once(self) -> bool:
        self._log("INFO", "=" * 50)
        self._log("INFO", f"Attempt {self.retry_count + 1}/{self.max_retries}")
        self._log("INFO", "=" * 50)

        # Try web solver
        if self.web_solver:
            self._log("INFO", "[Web Solver]")
            
            try:
                balance = await self.web_solver.get_balance()
                self._log("INFO", f"Balance: ${balance:.2f}")
                
                if balance >= self.web_solver.min_balance:
                    self._log("INFO", "Solving via web service...")
                    success = await self.web_solver.solve(self.bot.config.token)
                    
                    if success:
                        self._log("SUCCESS", "Captcha solved by web solver!")
                        return True
                    else:
                        self._log("WARN", "Web solver failed")
                else:
                    self._log("WARN", f"Balance too low: ${balance:.2f}")
            except Exception as e:
                self._log("ERROR", f"Web solver error: {e}")

        # Try image solver
        if self.image_solver and self.image_solver.is_available():
            self._log("INFO", "[Image Solver]")
            
            self._log("INFO", "Fetching captcha image...")
            image_data = await self._fetch_captcha_image()
            
            if not image_data:
                self._log("ERROR", "Failed to fetch image")
                return False
            
            self._log("SUCCESS", f"Image fetched: {len(image_data)} bytes")
            self._log("INFO", "Analyzing image with ONNX model...")
            
            result = self.image_solver.solve(image_data, expected_length=6)
            
            if result:
                self._log("INFO", f"Result: {result}")
                self._log("INFO", "Submitting...")
                
                if await self._submit_captcha(result):
                    self._log("SUCCESS", "Captcha solved by image solver!")
                    return True
                else:
                    self._log("ERROR", "Result rejected")
            else:
                self._log("WARN", "No result from image solver")

        return False

    async def solve(self) -> bool:
        if self._is_running:
            self._log("WARN", "Resolver already running")
            return False

        self._is_running = True
        self.retry_count = 0
        
        self._log("INFO", "=" * 50)
        self._log("INFO", "CAPTCHA SOLVING STARTED")
        self._log("INFO", f"Max retries: {self.max_retries}")
        self._log("INFO", "=" * 50)

        try:
            while self.retry_count < self.max_retries:
                success = await self._solve_once()
                
                if success:
                    self._log("SUCCESS", "=" * 50)
                    self._log("SUCCESS", "CAPTCHA SOLVED SUCCESSFULLY!")
                    self._log("SUCCESS", "=" * 50)
                    self._is_running = False
                    return True
                
                self.retry_count += 1
                
                if self.retry_count < self.max_retries:
                    wait_time = 5 * self.retry_count
                    self._log("INFO", f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    self._log("INFO", "Retrying...")

            self._log("ERROR", "=" * 50)
            self._log("ERROR", f"ALL {self.max_retries} ATTEMPTS FAILED!")
            self._log("ERROR", "=" * 50)
            self._is_running = False
            return False

        except Exception as e:
            self._log("ERROR", f"Solve error: {e}")
            self._is_running = False
            return False

    def is_available(self) -> bool:
        if self.web_solver:
            return True
        if self.image_solver and self.image_solver.is_available():
            return True
        return False
    
    def is_running(self) -> bool:
        return self._is_running


def run_resolver_standalone():
    """Chay resolver nhu app doc lap - CHI GIAI CAPTCHA"""
    from utils.colors import color
    
    print()
    print("=" * 60)
    print(f"{color.warning}CAPTCHA DETECTED!{color.reset}")
    print(f"{color.okcyan}Starting captcha resolver...{color.reset}")
    print("=" * 60)
    print()
    
    # Load config tu settings.json
    try:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'settings.json'
        )
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Tao mock config - CHI LAY THONG TIN CAN THIET CHO CAPTCHA
        class MockConfig:
            def __init__(self, data):
                self.token = data.get('token', '')
                self.channel = data.get('channel', '')
                self.OwOID = data.get('OwOID', '')
                self.captcha_config = data.get('captcha', {})
                self.stopped = False
            
            def get_captcha_config(self):
                return self.captcha_config
            
            def get(self, key, default=None):
                return getattr(self, key, default)
        
        # Tao mock bot - CHI CO LOG VA CONFIG
        class MockBot:
            def __init__(self, config):
                self.config = config
                self.start_time = time.time()
            
            def log(self, level, msg):
                from utils.colors import color
                level_colors = {
                    'INFO': color.okcyan,
                    'SUCCESS': color.okgreen,
                    'WARN': color.warning,
                    'ERROR': color.fail,
                }
                color_code = level_colors.get(level, color.reset)
                timestamp = time.strftime('%H:%M:%S')
                print(f"{timestamp} {color_code}[{level}]{color.reset} {msg}")
        
        mock_config = MockConfig(config_data)
        mock_bot = MockBot(mock_config)
        
        # Tao resolver
        resolver = CaptchaResolver(mock_bot)
        
        if not resolver.is_available():
            print(f"{color.fail}ERROR: No solver available!{color.reset}")
            print("Please check your captcha configuration in settings.json")
            input("Press ENTER to exit...")
            return
        
        # Chay resolver
        result = asyncio.run(resolver.solve())
        
        if result:
            print()
            print("=" * 60)
            print(f"{color.okgreen}CAPTCHA SOLVED SUCCESSFULLY!{color.reset}")
            print(f"{color.okcyan}Restarting main bot...{color.reset}")
            print("=" * 60)
            print()
            
            # Restart main bot
            main_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'main.py'
            )
            
            if os.path.exists(main_path):
                # Chay main moi va thoat resolver
                os.execv(sys.executable, [sys.executable, main_path])
            else:
                print(f"{color.fail}ERROR: main.py not found!{color.reset}")
                input("Press ENTER to exit...")
        else:
            print()
            print("=" * 60)
            print(f"{color.fail}CAPTCHA SOLVE FAILED AFTER 3 ATTEMPTS{color.reset}")
            print(f"{color.okcyan}Press ENTER to exit, or Ctrl+C to force quit.{color.reset}")
            print("=" * 60)
            print()
            
            # Cho user nhan Enter de thoat
            try:
                input()
            except:
                pass
            
            print("Exiting...")
            time.sleep(0.5)
            sys.exit(1)
        
    except FileNotFoundError:
        print(f"{color.fail}ERROR: settings.json not found!{color.reset}")
        input("Press ENTER to exit...")
    except Exception as e:
        print(f"{color.fail}ERROR: {e}{color.reset}")
        import traceback
        traceback.print_exc()
        input("Press ENTER to exit...")