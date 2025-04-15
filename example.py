from DRV8825 import DRV8825
import time
import math

motor = DRV8825(13, 18, 24, 10, 9, 11)
motor.move_speed(rpm=400)
# alt = True
# for _ in range(10):
#     motor.move_pos(7*math.pi, alt)
#     alt = not alt

# motor.cleanup()
