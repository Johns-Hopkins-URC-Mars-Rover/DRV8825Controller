import RPi.GPIO as GPIO
from typing import Tuple, Callable, Optional, Any
from enum import Enum
import threading
from time import sleep
import functools
import math

class StepSize(Enum):
    full = (0, 0, 0)
    half = (1, 0, 0)
    quarter = (0, 1, 0)
    eighth = (1, 1, 0)
    sixteenth = (0,  0, 1)
    thirty_second = (1, 0, 1)


class RunThread(threading.Thread):
    def __init__(self, target: Callable[[int], None], args = ()):
        super().__init__(target=target, args=args)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def is_stopped(self):
        return self._stop.is_set()


class DRV8825:
    STEP_DELAY = .0005
    DELTA_STEP_DELAY = .000001
    STEPS_PER_REVOLUTION = 200

    def __init__(self, direction_pin: int, step_pin: int, enable_pin: int, m0_pin: int, m1_pin: int, m2_pin: int):
        self.direction_pin: int = direction_pin
        self.step_pin: int = step_pin
        self.enable_pin: int = enable_pin

        # these control which step size the motor does
        self.mode_pins: Tuple[int, int, int] = (m0_pin, m1_pin, m2_pin)

        # setup gpio pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.enable_pin, GPIO.OUT)
        # GPIO.output(self.enable_pin, GPIO.HIGH)
        GPIO.setup(self.direction_pin, GPIO.OUT)
        # GPIO.setup(self.step_pin, GPIO.OUT)
        for pin in self.mode_pins:
            GPIO.setup(pin, GPIO.OUT)

        self.run_thread: Optional[RunThread] = None
        self._cur_speed = 0

    @staticmethod
    def clear_motor(func: Callable[[...], Any]):
        functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.run_thread and not self.run_thread.is_stopped():
                self.run_thread.stop()
                sleep(self.STEP_DELAY)
                GPIO.output(self.enable_pin, GPIO.LOW)

            return func(self, *args, **kwargs)

        return wrapper

    def set_revolution(self, step_size: StepSize):
        for pin in range(3):
            GPIO.output(self.mode_pins[pin], step_size.value[pin])

    def move_speed(self, rpm: int = 60, clockwise: bool = True):
        GPIO.output(self.enable_pin, GPIO.LOW)
        GPIO.output(self.direction_pin, clockwise)

        if not self.run_thread or self.run_thread.is_stopped():
            self._cur_speed = rpm
            self.run_thread = RunThread(target=self._speed_up, args=( ))
            self.run_thread.start()
        else:
            self._cur_speed = rpm


        GPIO.output(self.enable_pin, GPIO.HIGH)

    def _speed_up(self):
        min_step_delay = 1 / ((self._cur_speed * self.STEPS_PER_REVOLUTION) / 60 * 2)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.step_pin, GPIO.OUT)

        i = 1
        speed = self._cur_speed
        delay = max(self.STEP_DELAY, min_step_delay)
        while True:
            if self.run_thread.is_stopped():
                break

            if self._cur_speed != speed:
                speed = self._cur_speed
                min_step_delay = 1 / ((speed * self.STEPS_PER_REVOLUTION) / 60 * 2)
                delay = min_step_delay

            if i % 30 == 0 and delay > min_step_delay:
                delay -= self.DELTA_STEP_DELAY

            GPIO.output(self.step_pin, GPIO.HIGH)
            sleep(delay)
            GPIO.output(self.step_pin, GPIO.LOW)
            sleep(delay)
            i+=1

    def move_pos(self, rad: float, clockwise: bool = True):
        GPIO.output(self.enable_pin, GPIO.HIGH)
        GPIO.output(self.direction_pin, clockwise)

        self._pos_to(rad)

    def _pos_to(self, rad: float):
        num_steps: int = math.floor((self.STEPS_PER_REVOLUTION / (2 * math.pi)) * rad)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.step_pin, GPIO.OUT)
        for _ in range(num_steps):
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.output(self.step_pin, GPIO.HIGH)
                sleep(self.STEP_DELAY)
                GPIO.output(self.step_pin, GPIO.LOW)
                sleep(self.STEP_DELAY)
            except KeyboardInterrupt:
                self.run_thread.stop()
                quit()

    @clear_motor
    def stop(self):
        self.run_thread.stop()

    @clear_motor
    def cleanup(self):
        GPIO.cleanup()
