from DRV8825 import DRV8825
import time
import math

motor = DRV8825(22, 23, 24, 10, 9, 11)
motor.move_pos( 2*math.pi)
time.sleep(10)

motor.cleanup()