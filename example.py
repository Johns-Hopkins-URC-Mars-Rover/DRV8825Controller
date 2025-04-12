from DRV8825 import DRV8825
import time
import math

motor = DRV8825(13, 18, 24, 10, 9, 11)
motor.move_speed(rpm=400)
# motor.move_pos(2*math.pi, True)
# motor.cleanup()
