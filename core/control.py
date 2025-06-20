import time
from functools import wraps
from bots.core.cfg_types import BreakCfgParam
from core.logger import get_logger


class SingletonMeta(type):
    """A thread-safe implementation of a Singleton metaclass."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class ScriptControl(metaclass=SingletonMeta):
    def __init__(self):
        self._terminate = False
        self._pause = False
        self.break_until: float = 0
        self.break_config: BreakCfgParam = None
        self.log = get_logger("ScriptControl")
        self.start_listener()

    
    def start_listener(self):
        """Start a thread to listen for termination and pause requests."""
        import threading
        threading.Thread(target=self._listen_for_control, daemon=True).start()


    def propose_break(self):
        """Propose break based on configuration."""
        if self.break_config:
            if self.break_config.should_break():
                sec = int(self.break_config.break_duration.choose())
                self.initialize_break(
                    sec
                )
                self.log.info(f"Sleeping for {sec} seconds.")
        else:
            self.log.warning("Break proposed but no break configuration set.")
    def _listen_for_control(self):
        """Thread function to listen for control signals."""
        import keyboard
        while True:
            if keyboard.is_pressed('page up'):
                self.terminate = True
                return
            if keyboard.is_pressed('page down'):
                self.pause = not self.pause
                while keyboard.is_pressed('page down'):
                    # Wait until the key is released
                    time.sleep(0.1)
            time.sleep(0.05)

    @property
    def terminate(self):
        return self._terminate

    @terminate.setter
    def terminate(self, value: bool):
        if self._terminate != value:
            self.log.info(f"Terminate set to {value}")
        self._terminate = value

    @property
    def pause(self):
        return self._pause

    @pause.setter
    def pause(self, value: bool):
        if self._pause != value:
            self.log.info(f"Pause {'enabled' if value else 'disabled'}")
        self._pause = value

    def initialize_break(self, seconds: int):
        """Set the break duration without causing the caller to sleep."""
        self.break_until = time.time() + int(seconds)

    def guard(self, func):
        """
        Decorator to enforce termination and break logic.
        Raises RuntimeError if termination is requested.
        Waits if a break is active.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            while time.time() < self.break_until or self.pause:
                if self.terminate:
                    raise ScriptTerminationException()
                time.sleep(1)
            if self.terminate:
                raise ScriptTerminationException()
            return func(*args, **kwargs)
        return wrapper


class ScriptTerminationException(Exception):
    """Exception raised when script termination is requested."""
    def __init__(self, message="Script termination requested."):
        self.message = message
        super().__init__(self.message)
        
    def __str__(self):
        return self.message