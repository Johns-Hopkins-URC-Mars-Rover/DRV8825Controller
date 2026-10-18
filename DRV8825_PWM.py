"""Hardware-PWM control for a NEMA 23 stepper motor and TB6600 driver.

The TB6600 advances one motor step for each STEP pulse.  PWM frequency
therefore controls speed; the duty cycle is kept constant while running.
"""

from __future__ import annotations

import math
import time
from typing import Any, Optional


class TB6600:
    """Simple TB6600 controller using GPIO and hardware PWM.

    ``pwm_channel`` is the hardware-PWM channel provided by
    :mod:`rpi_hardware_pwm`; its physical GPIO pin is determined by the
    Raspberry Pi and PWM chip configuration.  ``enable_pin`` and
    ``direction_pin`` are regular GPIO pins.
    """

    MOTOR_STEPS_PER_REVOLUTION = 200
    MOTOR_STEP_ANGLE_DEGREES = 1.8
    DEFAULT_DUTY_CYCLE = 50.0
    PWM_DELAY = 1.01

    def __init__(
        self,
        enable_pin: int,
        direction_pin: int,
        pwm_channel: int = 0,
        *,
        pwm_chip: int = 0,
        microsteps: int = 1,
        duty_cycle: float = DEFAULT_DUTY_CYCLE,
        enable_active_low: bool = True,
        clockwise_direction_high: bool = True,
        gpio: Optional[Any] = None,
        pwm: Optional[Any] = None,
        delay: float = PWM_DELAY,
    ) -> None:
        """Initialize the driver and leave it stopped.

        ``microsteps`` must match the TB6600's configured microstep switches.
        For example, use ``microsteps=8`` when the driver is configured for
        1/8 stepping.  ``pwm`` and ``gpio`` are optional injection points for
        tests or compatible hardware implementations.
        """
        if not isinstance(microsteps, int) or microsteps < 1:
            raise ValueError("microsteps must be a positive integer")
        if not 0 < duty_cycle <= 100:
            raise ValueError("duty_cycle must be greater than 0 and at most 100")

        self.enable_pin = enable_pin
        self.direction_pin = direction_pin
        self.pwm_channel = pwm_channel
        self.pwm_chip = pwm_chip
        self.microsteps = microsteps
        self.steps_per_revolution = (
            self.MOTOR_STEPS_PER_REVOLUTION * microsteps
        )
        self.duty_cycle = duty_cycle
        self.enable_active_low = enable_active_low
        self.clockwise_direction_high = clockwise_direction_high

        self._gpio = gpio if gpio is not None else self._import_gpio()
        self._pwm = (
            pwm
            if pwm is not None
            else self._create_pwm(pwm_channel, pwm_chip)
        )
        self.delay = delay
        self._owns_pwm = pwm is None
        self._rpm = 0.0
        self._frequency = 0

        self._gpio.setmode(self._gpio.BCM)
        self._gpio.setup(self.enable_pin, self._gpio.OUT)
        self._gpio.setup(self.direction_pin, self._gpio.OUT)
        self._set_enabled(False)
        self.set_direction(True)

        # Start hardware PWM with no pulses.  A zero duty cycle is the
        # stopped state; the output is enabled only when an RPM is selected.
        self._pwm.start(0)

    @staticmethod
    def _import_gpio() -> Any:
        try:
            import RPi.GPIO as gpio
        except ImportError as error:
            raise RuntimeError(
                "RPi.GPIO is required unless a GPIO implementation is supplied"
            ) from error
        return gpio

    @staticmethod
    def _create_pwm(pwm_channel: int, pwm_chip: int) -> Any:
        try:
            from rpi_hardware_pwm import HardwarePWM
        except ImportError as error:
            raise RuntimeError(
                "rpi_hardware_pwm is required unless a PWM implementation is supplied"
            ) from error
        return HardwarePWM(pwm_channel=pwm_channel, hz=1, chip=pwm_chip)

    def _set_enabled(self, enabled: bool) -> None:
        active = self._gpio.LOW if self.enable_active_low else self._gpio.HIGH
        inactive = self._gpio.HIGH if self.enable_active_low else self._gpio.LOW
        self._gpio.output(
            self.enable_pin,
            active if enabled else inactive,
        )

    def set_direction(self, clockwise: bool = True) -> None:
        """Set the TB6600 direction input for subsequent movement."""
        direction_high = clockwise == self.clockwise_direction_high
        self._gpio.output(
            self.direction_pin,
            self._gpio.HIGH if direction_high else self._gpio.LOW,
        )

    def set_rpm(self, rpm: float, clockwise: bool = True) -> None:
        """Run continuously at ``rpm``.

        The STEP frequency is ``rpm * steps_per_revolution / 60``.  Passing
        zero stops the motor and produces a 0% duty-cycle output.
        """
        if not math.isfinite(rpm) or rpm < 0:
            raise ValueError("rpm must be a finite value of zero or greater")

        if rpm == 0:
            self.stop()
            return

        frequency = rpm * self.steps_per_revolution / 60.0
        if frequency < 1:
            raise ValueError("rpm is too low to produce a 1 Hz PWM signal")

        self.set_direction(clockwise)
        self._pwm.change_frequency(frequency)
        self._pwm.change_duty_cycle(self.duty_cycle)
        self._set_enabled(True)
        self._rpm = rpm
        self._frequency = frequency

    def move_at_for(self, rpm: float, seconds: float, clockwise: bool = True):
        self.set_rpm(rpm, clockwise)
        time.sleep(seconds + self.delay)

    def move_degrees(
        self,
        degrees: float,
        clockwise: bool = True,
        rpm: Optional[float] = None,
    ) -> None:
        """Move the requested angle, then stop.

        Movement is timed from the configured PWM frequency.  Because generic
        hardware PWM does not expose a pulse-count limit, the final position
        is approximate by at most one configured step.
        """
        if not math.isfinite(degrees) or degrees < 0:
            raise ValueError("degrees must be a finite value of zero or greater")

        if rpm is not None:
            self.set_rpm(rpm, clockwise)
        elif self._rpm <= 0:
            raise RuntimeError("Set an RPM before calling move_degrees")
        else:
            self.set_direction(clockwise)

        steps = degrees * self.steps_per_revolution / 360
        if steps == 0:
            self.stop()
            return

        try:
            print(steps)
            print(self._frequency)
            print(steps/ self._frequency)
            start_time = time.perf_counter()
            time.sleep(self.delay + (steps / self._frequency))
            end_time = time.perf_counter()
            print(end_time-start_time)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop pulses, set duty cycle to 0%, and disable the driver."""
        self._pwm.change_duty_cycle(0)
        self._set_enabled(False)
        self._rpm = 0.0
        self._frequency = 0

    def cleanup(self) -> None:
        """Stop the motor and release GPIO/PWM resources."""
        self.stop()
        self._gpio.cleanup()
        if self._owns_pwm:
            self._pwm.stop()


# Compatibility name matching the module filename and the original project.
DRV8825_PWM = TB6600
