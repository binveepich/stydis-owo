import json
import os


class Config:
    def __init__(self, config_file="settings.json"):
        self.config_file = config_file
        self.data = self._load()
        self.token = self.get('token')
        self.channel = self.get('channel')
        self.gm = self.get('gm')
        self.wm = self.get('wm')
        self.sm = self.get('sm')
        self.pm = self.get('pm')
        self.em = self.get('em', {})
        self.webhook = self.get('webhook', {})
        self.daily = self.get('daily')
        self.stop = self.get('stop')
        self.sell = self.get('sell', {})
        self.OwOID = '408785106942164992'
        self.totalcmd = 0
        self.totaltext = 0
        self.stopped = False
        
        # === THÊM CẤU HÌNH CPU ===
        self.cpu = self.get('cpu', {})
        self._ensure_cpu_config()

    def _ensure_cpu_config(self):
        """Đảm bảo có cấu hình CPU trong data"""
        if 'cpu' not in self.data:
            self.data['cpu'] = {
                'max_percent': 90.0,
                'check_interval': 1.0,
                'max_wait_time': 300.0
            }
            self._save()
        elif not isinstance(self.data['cpu'], dict):
            self.data['cpu'] = {
                'max_percent': 90.0,
                'check_interval': 1.0,
                'max_wait_time': 300.0
            }
            self._save()

    def _load(self):
        if not os.path.exists(self.config_file):
            self._create_default()

        with open(self.config_file, 'r') as f:
            return json.load(f)

    def _create_default(self):
        default = {
            "token": "",
            "channel": "",
            "gm": "YES",
            "wm": "YES",
            "sm": "YES",
            "pm": "YES",
            "em": {"text": "YES", "owo": "YES"},
            "webhook": {"link": None, "ping": None},
            "daily": "YES",
            "stop": "22222",
            "sell": {"enable": "YES", "types": "all"},
            "captcha": {
                "enabled": False,
                "api_key": "",
                "service": "yescaptcha",
                "enable_image": True,
                "model_path": "best.onnx"
            },
            "cpu": {
                "max_percent": 90.0,
                "check_interval": 1.0,
                "max_wait_time": 300.0
            }
        }
        self.data = default
        self._save()

    def _save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get(self, key, default=None):
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key, value):
        keys = key.split('.')
        target = self.data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._save()

    def get_captcha_config(self):
        captcha = self.get('captcha', {})
        defaults = {
            'enabled': False,
            'api_key': '',
            'service': 'yescaptcha',
            'enable_image': True,
            'model_path': 'best.onnx'
        }
        result = defaults.copy()
        for key, value in captcha.items():
            if value is not None:
                result[key] = value
        return result

    def get_cpu_config(self):
        """Lấy cấu hình CPU"""
        self._ensure_cpu_config()
        return self.data.get('cpu', {
            'max_percent': 90.0,
            'check_interval': 1.0,
            'max_wait_time': 300.0
        })

    def check(self):
        from utils.helpers import slow_print
        from utils.colors import color

        if not self.token or not self.channel:
            slow_print(f"{color.fail} !!! [ERROR] !!! {color.reset} Please enter Token and Channel ID in settings.json")
            raise SystemExit
        else:
            try:
                from requests import get
                response = get('https://discord.com/api/v9/users/@me', headers={"Authorization": self.token})
                if not response.ok:
                    slow_print(f"{color.fail} !!! [ERROR] !!! {color.reset} Invalid Token")
                    raise SystemExit
            except Exception as e:
                slow_print(f"{color.fail} !!! [ERROR] !!! {color.reset} Network error: {str(e)}")
                raise SystemExit