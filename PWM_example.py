import time

from DRV8825_PWM import DRV8825_PWM


motor = DRV8825_PWM(
    enable_pin=24,
    direction_pin=13,
    # Hardware PWM channel 0 is GPIO 18 on the supported Raspberry Pi setup.
    pwm_channel=0,
    pwm_chip=0,
    microsteps=8,
)

try:
    motor.set_rpm(15)
    time.sleep(3)
    motor.move_degrees(360, clockwise=False, rpm=10)
finally:
    motor.cleanup()
