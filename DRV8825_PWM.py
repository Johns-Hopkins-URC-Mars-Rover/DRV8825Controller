from rpi_hardware_pwm import HardwarePWM
from time import sleep

pwm = HardwarePWM(pwm_channel = 0, hz = 400, chip = 0)
pwm.start(50)
time.sleep(10)
pwm.change_duty_cycle(75)
time.sleep(10)
pwm.stop()
