# coding=utf-8
from __future__ import print_function
import RPi.GPIO as GPIO
import threading
import sys

sys.path.insert(0, '/home/pi/dynamixel_hr')
from dxl.dxlchain import DxlChain

chain = DxlChain("/dev/ttyUSB0", rate=1000000)
print(chain.get_motor_list())


class Pair(object):
    """
    A quadrature encoder paired with one Dynamixel
    """
    counter = 0
    currentA = 1
    currentB = 1
    motor = 0

    lockRotary = threading.Lock()

    encoderA = 0
    encoderB = 0

    position = 0
    initialPosition = 0
    direction = 0

    def rotary_interrupt(self, a_or_b):

        """
        Interrupt callback
        Gets called when a change in voltage is detected
        :param a_or_b: Which pin called back
        """

        switch_a = GPIO.input(self.encoderA)
        switch_b = GPIO.input(self.encoderB)

        if self.currentA == switch_a and self.currentB == switch_b:
            return

        self.currentA = switch_a
        self.currentB = switch_b

        if switch_a and switch_b:
            self.lockRotary.acquire()
            if a_or_b == self.encoderB:
                self.counter += 1
            else:
                self.counter -= 1
            self.lockRotary.release()
        return

    def __init__(self, encoderA, encoderB, motor, initialPosition, direction):
        """
        Initializes an encoder and a Dynamixel
        :param encoderA: Encoder pin A 
        :param encoderB: Encoder pin B
        :param motor: Dynamixel ID number
        :param initialPosition: Starting position of Dynamixel
        :param direction: Direction that Dynamixel should turn
        """
        self.encoderA = encoderA
        self.encoderB = encoderB
        self.motor = motor
        self.initialPosition = initialPosition
        self.direction = direction

        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(self.encoderA, GPIO.IN)
        GPIO.setup(self.encoderB, GPIO.IN)

        GPIO.add_event_detect(self.encoderA, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(self.encoderB, GPIO.RISING, callback=self.rotary_interrupt)

    def startup(self):
        """
        Wiggles the finger 
        """
        chain.goto(self.motor, self.initialPosition, 1023, True)
        chain.goto(self.motor, self.initialPosition + (250 * self.direction), 1023, True)
        chain.goto(self.motor, self.initialPosition, 1023, True)

    def update(self):
        """
        Update an Encoder's position value.
        """
        self.lockRotary.acquire()
        new_position = self.counter
        self.counter = 0
        self.lockRotary.release()

        if new_position != 0:
            self.position += new_position * abs(new_position) * 10
            if self.position > 1000:
                self.position = 1000
            elif self.position < 0:
                self.position = 0
            else:
                return

            chain.goto(self.motor, self.position, 1000, False)

Pair1 = Pair(8, 10, 1, 0, 1)
Pair2 = Pair(11, 12, 2, 0, 1)
Pair3 = Pair(15, 16, 3, 0, 1)
Pair4 = Pair(21, 22, 4, 0, 1)
Pair5 = Pair(23, 24, 5, 0, 1)
Pair6 = Pair(27, 28, 6, 0, 1)
array = [Pair1, Pair2, Pair3, Pair4, Pair5, Pair6]

for Pair in array:
    Pair.startup()

while True:
    try:
        for Pair in array:
            Pair.update()

    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Bye! \n")
