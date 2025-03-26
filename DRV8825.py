import RPi.GPIO as GPIO
from typing import Tuple, Callable, Optional, Any
from enum import Enum
import threading
import time
import functools
import math
import pigpio
from time import sleep


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
    STEP_DELAY = .005
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

    @staticmethod
    def clear_motor(func: Callable[[...], Any]):
        functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.run_thread and not self.run_thread.is_stopped():
                self.run_thread.stop()
                time.sleep(self.STEP_DELAY)
                GPIO.output(self.enable_pin, GPIO.LOW)

            return func(self, *args, **kwargs)

        return wrapper

    def set_revolution(self, step_size: StepSize):
        for pin in range(3):
            GPIO.output(self.mode_pins[pin], step_size.value[pin])

    # @clear_motor
    def move_speed(self, rpm: int = 60, clockwise: bool = True):
        GPIO.output(self.enable_pin, GPIO.LOW)
        GPIO.output(self.direction_pin, clockwise)

        self.run_thread = RunThread(target=self._speed_up, args=(rpm, ))
        self.run_thread.start()

        GPIO.output(self.enable_pin, GPIO.HIGH)

    def _speed_up(self, rpm: int, start_step_delay = 100, acceleration_time = 3):
        #start_step_delay = 1s /10 ms = 100

        #step_delay = self.STEP_DELAY
        min_step_delay = (rpm * self.STEPS_PER_REVOLUTION) / 60 / 2
        print(start_step_delay, min_step_delay, rpm)
        # min_step_delay = .000001
        rep = 1
        
        # I saw all examples doing this so I decided to copy this
        pi = pigpio.pi()
        if not pi.connected:
            exit(0)

        #not sure if the following code is necessary but the example has it
        #(seem to be already set up in class)
        #but I don't know since it's pi (new)
        pi.set_mode(self.direction_pin, pigpio.OUTPUT)
        pi.set_mode(self.step_pin, pigpio.OUTPUT)
        # pi.set_mode(self.enable_pin, pigpio.OUTPUT)

        print("setting hardware pwm")
        for i in range(100, 5000, 100):
            print(i)
            pi.hardware_PWM(self.step_pin, i, 250000)
            time.sleep(3)

        # pi.set_PWM_dutycycle(self.step_pin, 255) # PWM 1/2 on
        # for i in range(1000):
        #     # current_speed = start_step_delay - (start_step_delay - min_step_delay) * i / 1000
        # pi.set_PWM_frequency(self.step_pin, 100)
        #     sleep(acceleration_time/1000)
        time.sleep(10)
        pi.write(self.step_pin, 0)

        # while True:
        #     pi.write(self.step_pin, 1)
        #     time.sleep(self.STEP_DELAY)
        #     pi.write(self.step_pin, 0)
        #     time.sleep(self.STEP_DELAY)

        '''
        
            try:
                delay = max(10, int(step_delay / 1.4174580574035645e-05))
                if step_delay > min_step_delay:
                    step_delay -= self.DELTA_STEP_DELAY * (min(1, (500/rep) if delay < 15 else 1))
                    step_delay = max(step_delay, min_step_delay)
                GPIO.output(self.step_pin, GPIO.HIGH)

                for _ in range(delay):
                    print(delay)
                GPIO.output(self.step_pin, GPIO.LOW)
                for _ in range(delay):
                    print(delay)

                rep+=1
            except KeyboardInterrupt:
                self.run_thread.stop()
                self.cleanup()
                quit()
        '''

        # GPIO.output(self.enable_pin, GPIO.HIGH)

    def move_pos(self, rad: float, clockwise: bool = True):
        GPIO.output(self.enable_pin, GPIO.HIGH)
        GPIO.output(self.direction_pin, clockwise)

        self.run_thread = RunThread(target=self._pos_to, args=(rad, ))
        self.run_thread.start()

    def _pos_to(self, rad: float):
        num_steps: int = math.floor((self.STEPS_PER_REVOLUTION / (2 * math.pi)) * rad)
        for _ in range(num_steps):
            try:
                GPIO.output(self.step_pin, GPIO.HIGH)
                time.sleep(self.STEP_DELAY)
                GPIO.output(self.step_pin, GPIO.LOW)
                time.sleep(self.STEP_DELAY)
            except KeyboardInterrupt:
                self.run_thread.stop()
                self.cleanup()
                quit()

    @clear_motor
    def stop(self):
        self.run_thread.stop()

    @clear_motor
    def cleanup(self):
        GPIO.cleanup()
