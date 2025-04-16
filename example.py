from DRV8825 import DRV8825
import time
import math

motor = DRV8825(13, 18, 24, 10, 9, 11)

motor.move_speed(60)
time.sleep(3)

motor.move_speed(450)
time.sleep(3)

motor.stop()
