import time

from DRV8825_PWM import DRV8825_PWM


motor = DRV8825_PWM(
    enable_pin=17,
    direction_pin=27,
    pwm_channel=1,
    pwm_chip=0,
    microsteps=8,
    duty_cycle=50,
)

try:
    motor.move_at_for(30, 2)

finally:
    motor.cleanup()
