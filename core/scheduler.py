import time
import random
import threading
from threading import Thread, Event
from utils.helpers import UI
from utils.colors import color
from utils.constants import BotConstants


class Scheduler:
    def __init__(self, bot):
        self.bot = bot
        self.ui = UI()
        self.running = False
        self.thread = None
        self._stop_event = Event()

        self.queue = []
        self.queue_lock = threading.Lock()
        self.command_timestamps = {}
        self.min_command_interval = 3

        self.is_sleeping = False
        self.sleep_until = 0
        self.active_until = 0
        self._schedule_sleep()

        self.hunt_cycles = 0
        self.weapon_counter = 0
        self.daily_done = False
        self.gems_check_time = 0
        self.stop_time = time.time()

        self.pray_next_time = time.time() + random.randint(333, 666)
        self.sell_next_time = time.time() + 3333
        self.exp_next_time = time.time() + random.randint(17, 55)

        self.last_command_time = 0
        self.tasks = {}

    def _schedule_sleep(self):
        if self.bot.config.sm != "YES":
            self.is_sleeping = False
            return

        active_duration = random.randint(600, 900)
        break_duration = random.randint(333, 666)

        self.active_until = time.time() + active_duration
        self.sleep_until = self.active_until + break_duration

        self.ui.slowPrinting(
            f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
            f"Schedule: Active {active_duration}s, Break {break_duration}s"
        )

    def register_task(self, name, func, min_interval, max_interval,
                     priority=0, depends_on=None):
        self.tasks[name] = {
            'func': func,
            'min_interval': min_interval,
            'max_interval': max_interval,
            'last_run': 0,
            'priority': priority,
            'depends_on': depends_on,
            'running': False
        }

    def _add_to_queue(self, func, priority=0):
        with self.queue_lock:
            func_name = func.__name__
            now = time.time()

            if func_name in self.command_timestamps:
                if now - self.command_timestamps[func_name] < self.min_command_interval:
                    return

            for _, existing_func in self.queue:
                if existing_func.__name__ == func_name:
                    return

            self.queue.append((priority, func))
            self.queue.sort(key=lambda x: x[0])
            self.command_timestamps[func_name] = now

    def _is_in_queue(self, func):
        with self.queue_lock:
            for _, existing_func in self.queue:
                if existing_func == func:
                    return True
            return False

    def _should_sleep(self):
        if self.bot.config.sm != "YES" or self.bot.config.stopped:
            return False

        now = time.time()

        if self.is_sleeping:
            if now < self.sleep_until:
                return True
            else:
                self.is_sleeping = False
                self._schedule_sleep()
                return False

        if now >= self.active_until:
            self.is_sleeping = True
            return True

        return False

    def _do_sleep(self):
        if self.bot.config.stopped:
            return

        remaining = int(self.sleep_until - time.time())
        if remaining > 0:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
                f"💤 Sleeping for {remaining}s..."
            )

            while time.time() < self.sleep_until and not self.bot.config.stopped and not self._stop_event.is_set():
                time.sleep(1)

            if not self.bot.config.stopped and not self._stop_event.is_set():
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
                    "☀️ Wake up!"
                )
                self.is_sleeping = False
                self._schedule_sleep()

    def _queue_commands(self):
        if self.bot.config.stopped or self._stop_event.is_set():
            return

        now = time.time()

        if not self.queue or (now - self.last_command_time > 2):
            if not self._is_in_queue(self._do_hunt_battle):
                self._add_to_queue(self._do_hunt_battle, priority=0)

        if (self.bot.config.gm == "YES" and
            self.bot.gems and
            self.hunt_cycles >= 1 and
            self.gems_check_time == 0):
            if not self._is_in_queue(self._do_gems):
                self._add_to_queue(self._do_gems, priority=6)
                self.gems_check_time = now
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.okblue} [INFO]{color.reset} "
                    "Triggering first gem check after initial hunt..."
                )

        if (self.bot.config.gm == "YES" and
            self.bot.gems and
            self.gems_check_time > 0):
            if not self._is_in_queue(self._do_gems):
                self._add_to_queue(self._do_gems, priority=6)

        if (not self.daily_done and
            self.hunt_cycles >= 2 and
            self.bot.config.daily == "YES"):
            if not self._is_in_queue(self._do_daily):
                self._add_to_queue(self._do_daily, priority=1)
                self.daily_done = True

        if (self.bot.config.wm == "YES" and
            self.weapon_counter >= 1 and
            self.bot.weapons):
            if not self._is_in_queue(self._do_weapons):
                self._add_to_queue(self._do_weapons, priority=2)
                self.weapon_counter = 0

        if now >= self.exp_next_time:
            if self.bot.config.em.get('text') == "YES":
                if not self._is_in_queue(self._do_exp):
                    self._add_to_queue(self._do_exp, priority=3)
                    self.exp_next_time = now + random.randint(17, 55)

        if now >= self.pray_next_time:
            if self.bot.config.pm == "YES":
                if not self._is_in_queue(self._do_pray):
                    self._add_to_queue(self._do_pray, priority=4)
                    self.pray_next_time = now + random.randint(333, 666)

        if now >= self.sell_next_time:
            if self.bot.config.sell.get('enable') == "YES":
                if not self._is_in_queue(self._do_sell):
                    self._add_to_queue(self._do_sell, priority=5)
                    self.sell_next_time = now + 3333

        if (self.bot.config.stop and
            self.bot.config.stop.isdigit() and
            now - self.stop_time > int(self.bot.config.stop)):
            if not self._is_in_queue(self._do_stop):
                self._add_to_queue(self._do_stop, priority=0)

    def _do_hunt_battle(self):
        if self.bot.config.stopped or self._stop_event.is_set():
            return

        self.bot.executor.send_command("hunt")
        time.sleep(random.randint(3, 7))
        self.bot.executor.send_command("battle")
        self.hunt_cycles += 1
        self.weapon_counter += 1

    def _do_daily(self):
        if self.bot.config.stopped or self._stop_event.is_set():
            return
        self.bot.executor.send_daily()

    def _do_weapons(self):
        if self.bot.config.stopped or not self.bot.weapons or self._stop_event.is_set():
            return
        self.bot.weapons.buy_one_crate()

    def _do_exp(self):
        if self.bot.config.stopped or self._stop_event.is_set():
            return

        try:
            from requests import get

            if not hasattr(self.bot.config, 'quote_count'):
                self.bot.config.quote_count = 0
            if not hasattr(self.bot.config, 'quote_threshold'):
                self.bot.config.quote_threshold = random.randint(2, 4)

            response = get("https://dummyjson.com/quotes/random", timeout=10)
            if response.status_code == 200:
                json_data = response.json()
                quote = f"{json_data['quote']}"
                self.bot.executor.send_raw(quote)

                self.bot.config.quote_count += 1
                if (self.bot.config.em.get('owo') == "YES" and
                    self.bot.config.quote_count >= self.bot.config.quote_threshold):
                    time.sleep(random.randint(10, 30))
                    owo = random.choice(['owo', 'uwu'])
                    self.bot.executor.send_raw(owo)
                    self.bot.config.quote_count = 0
                    self.bot.config.quote_threshold = random.randint(2, 4)
            else:
                self.ui.slowPrinting(
                    f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                    f"DummyJSON API failed: {response.status_code}"
                )
        except Exception as e:
            self.ui.slowPrinting(
                f"{self.bot.at()}{color.warning} [WARN]{color.reset} "
                f"Exp error: {str(e)[:50]}"
            )

    def _do_pray(self):
        if self.bot.config.stopped or self._stop_event.is_set():
            return
        self.bot.executor.send_pray()

    def _do_sell(self):
        if self.bot.config.stopped or self._stop_event.is_set():
            return
        self.bot.executor.send_sell()

    def _do_gems(self):
        if self.bot.config.stopped or not self.bot.gems or self._stop_event.is_set():
            return
        self.bot.gems.gem_cycle()

    def _do_stop(self):
        if self._stop_event.is_set():
            return
        self.ui.slowPrinting(
            f"{self.bot.at()}{color.okcyan} [INFO]{color.reset} "
            f"Stopping after {self.bot.config.stop}s"
        )
        self.bot.stop()

    def start(self):
        self.running = True
        self._stop_event.clear()
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.ui.slowPrinting(f"{self.bot.at()} Scheduler started")

    def _run_loop(self):
        while self.running and not self._stop_event.is_set() and not self.bot.config.stopped:
            try:
                if self._stop_event.is_set() or self.bot.config.stopped:
                    break

                if self._should_sleep():
                    self._do_sleep()
                    continue

                self._queue_commands()

                if self.queue and not self._stop_event.is_set() and not self.bot.config.stopped:
                    with self.queue_lock:
                        _, command = self.queue.pop(0)

                    if self.last_command_time > 0:
                        delay = random.randint(3, 7)
                        elapsed = time.time() - self.last_command_time
                        if elapsed < delay:
                            time.sleep(delay - elapsed)

                    if not self.bot.config.stopped and not self._stop_event.is_set():
                        command()
                        self.last_command_time = time.time()

                time.sleep(0.1)

            except Exception as e:
                if not self._stop_event.is_set():
                    self.ui.slowPrinting(
                        f"{self.bot.at()}{color.fail}[ERROR]{color.reset} "
                        f"Scheduler error: {str(e)[:50]}"
                    )
                    time.sleep(5)

    def stop(self):
        self.running = False
        self._stop_event.set()
        with self.queue_lock:
            self.queue.clear()
        self.ui.slowPrinting(f"{self.bot.at()} Scheduler stopped (signal sent)")