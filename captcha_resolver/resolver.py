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
        
        # Status file path
        self.status_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'captcha_status.json'
        )
        
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
                service = config.get('service', 'yescaptcha')
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
                # Tim model trong cac thu muc
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

    def _write_status(self, status: str, result: Optional[str] = None, retry: int = 0):
        """Ghi trang thai vao file"""
        try:
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            with open(self.status_file, 'w') as f:
                json.dump({
                    'status': status,
                    'result': result,
                    'retry': retry,
                    'timestamp': time.time(),
                    'max_retries': self.max_retries
                }, f)
        except Exception as e:
            self._log("ERROR", f"Write status failed: {e}")

    def _read_status(self) -> dict:
        """Doc trang thai tu file"""
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except:
            return {'status': 'idle', 'result': None}

    def _clear_status(self):
        """Xoa file status"""
        try:
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
        except:
            pass

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
        """Giai captcha 1 lan"""
        self._log("INFO", "=" * 50)
        self._log("INFO", f"Attempt {self.retry_count + 1}/{self.max_retries}")
        self._log("INFO", "=" * 50)

        # Try web solver first
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
        """Giai captcha voi retry 3 lan"""
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
                self._write_status('solving', retry=self.retry_count)
                
                success = await self._solve_once()
                
                if success:
                    self._write_status('success')
                    self._clear_status()
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

            self._write_status('failed')
            self._log("ERROR", "=" * 50)
            self._log("ERROR", f"ALL {self.max_retries} ATTEMPTS FAILED!")
            self._log("ERROR", "=" * 50)
            self._is_running = False
            return False

        except Exception as e:
            self._log("ERROR", f"Solve error: {e}")
            self._write_status('failed')
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