"""
CPU Controller - Kiểm soát việc sử dụng CPU khi khởi động/kết nối lại
"""

import time
import threading
from typing import Optional, Callable
from utils.colors import color
from utils.helpers import UI


class CPUController:
    """Kiểm soát CPU usage khi khởi động/kết nối lại"""
    
    def __init__(self, 
                 max_cpu_percent: float = 90.0,
                 check_interval: float = 1.0,
                 max_wait_time: float = 300.0,
                 bot=None):
        """
        Args:
            max_cpu_percent: Ngưỡng CPU tối đa cho phép (%), mặc định 90%
            check_interval: Thời gian giữa các lần kiểm tra (giây)
            max_wait_time: Thời gian chờ tối đa (giây), sau đó vẫn khởi động
            bot: Instance của OwOBot để log
        """
        self.max_cpu_percent = max_cpu_percent
        self.check_interval = check_interval
        self.max_wait_time = max_wait_time
        self.bot = bot
        self.ui = UI()
        
        # Trạng thái
        self._is_waiting = False
        self._stop_waiting = False
        
        # Kiểm tra xem có psutil không
        self._has_psutil = False
        try:
            import psutil
            self._psutil = psutil
            self._has_psutil = True
        except ImportError:
            self._log("WARN", "psutil not installed. CPU monitoring disabled.")
            self._log("INFO", "Install with: pip install psutil")
        
    def _log(self, level: str, msg: str):
        if self.bot:
            self.bot.log(level, f"[CPU] {msg}")
        else:
            print(f"[CPU] {msg}")
    
    def get_cpu_usage(self) -> float:
        """Lấy CPU usage hiện tại (%)"""
        if not self._has_psutil:
            return 0.0
        try:
            return self._psutil.cpu_percent(interval=0.1)
        except Exception as e:
            self._log("WARN", f"Failed to get CPU usage: {e}")
            return 0.0
    
    def get_cpu_usage_per_core(self) -> list:
        """Lấy CPU usage từng core (%)"""
        if not self._has_psutil:
            return []
        try:
            return self._psutil.cpu_percent(interval=0.1, percpu=True)
        except Exception as e:
            self._log("WARN", f"Failed to get per-core CPU: {e}")
            return []
    
    def is_cpu_safe(self) -> bool:
        """Kiểm tra CPU có an toàn để khởi động không"""
        cpu_usage = self.get_cpu_usage()
        return cpu_usage < self.max_cpu_percent
    
    def wait_for_cpu(self, 
                     on_waiting: Optional[Callable] = None,
                     on_ready: Optional[Callable] = None,
                     on_timeout: Optional[Callable] = None) -> bool:
        """
        Chờ CPU xuống dưới ngưỡng cho phép
        
        Returns:
            bool: True nếu CPU sẵn sàng, False nếu timeout
        """
        if not self._has_psutil:
            self._log("INFO", "psutil not available, skipping CPU check")
            return True
            
        if self.is_cpu_safe():
            self._log("INFO", f"✅ CPU safe: {self.get_cpu_usage():.1f}% < {self.max_cpu_percent}%")
            if on_ready:
                on_ready()
            return True
        
        self._is_waiting = True
        self._stop_waiting = False
        start_time = time.time()
        
        self._log("WARN", f"⚠️ CPU high: {self.get_cpu_usage():.1f}% >= {self.max_cpu_percent}%")
        self._log("INFO", f"⏳ Waiting for CPU to drop below {self.max_cpu_percent}%...")
        
        if on_waiting:
            on_waiting()
        
        last_log_time = 0
        
        while not self._stop_waiting:
            # Kiểm tra timeout
            elapsed = time.time() - start_time
            if elapsed >= self.max_wait_time:
                self._log("WARN", f"⏰ Timeout after {self.max_wait_time}s, proceeding anyway...")
                self._is_waiting = False
                if on_timeout:
                    on_timeout()
                return False
            
            # Kiểm tra CPU
            current_cpu = self.get_cpu_usage()
            
            # Hiển thị tiến trình mỗi 5 giây
            if int(elapsed) % 5 == 0 and int(elapsed) != last_log_time:
                last_log_time = int(elapsed)
                cores = self.get_cpu_usage_per_core()
                if cores and len(cores) > 1:
                    core_str = ", ".join([f"{c:.1f}%" for c in cores[:4]])
                    if len(cores) > 4:
                        core_str += f", ... ({len(cores)} cores)"
                    self._log("INFO", f"⏳ CPU: {current_cpu:.1f}% | Cores: [{core_str}] | Waiting: {elapsed:.0f}s")
                else:
                    self._log("INFO", f"⏳ CPU: {current_cpu:.1f}% | Waiting: {elapsed:.0f}s")
            
            if current_cpu < self.max_cpu_percent:
                self._log("SUCCESS", f"✅ CPU dropped to {current_cpu:.1f}% (after {elapsed:.1f}s)")
                self._is_waiting = False
                if on_ready:
                    on_ready()
                return True
            
            # Chờ một khoảng trước khi kiểm tra lại
            time.sleep(self.check_interval)
        
        self._is_waiting = False
        return False
    
    def wait_for_cpu_with_progress(self, 
                                   message: str = "Checking CPU...",
                                   bot_name: str = "") -> bool:
        """
        Chờ CPU với hiển thị tiến trình đơn giản
        
        Args:
            message: Thông báo hiển thị
            bot_name: Tên bot để hiển thị
        """
        if not self._has_psutil:
            return True
            
        if self.is_cpu_safe():
            return True
        
        max_wait = self.max_wait_time
        wait_count = 0
        
        print(f"\n{color.warning}⚠️ {message}{color.reset}")
        print(f"{color.okcyan}📊 CPU: {self.get_cpu_usage():.1f}% (threshold: {self.max_cpu_percent}%){color.reset}")
        
        while wait_count < max_wait:
            current_cpu = self.get_cpu_usage()
            
            # Tạo thanh tiến trình
            bar_length = 30
            progress = min(current_cpu / 100, 1.0)
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            # Màu sắc dựa trên CPU
            if current_cpu < 50:
                bar_color = color.okgreen
            elif current_cpu < 80:
                bar_color = color.warning
            else:
                bar_color = color.fail
            
            # Hiển thị thông tin
            prefix = f"{bot_name} " if bot_name else ""
            print(f"\r{prefix}{bar_color}{bar}{color.reset} {current_cpu:.1f}% | "
                  f"Wait: {wait_count:.0f}s/{max_wait}s", end="")
            
            if current_cpu < self.max_cpu_percent:
                print(f"\n{color.okgreen}✅ CPU safe!{color.reset}")
                return True
            
            time.sleep(self.check_interval)
            wait_count += self.check_interval
        
        print(f"\n{color.warning}⏰ Timeout! Proceeding anyway...{color.reset}")
        return False
    
    def stop_waiting(self):
        """Dừng việc chờ CPU"""
        self._stop_waiting = True
    
    def is_waiting(self) -> bool:
        """Kiểm tra có đang chờ CPU không"""
        return self._is_waiting