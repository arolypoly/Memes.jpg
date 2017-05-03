# coding=utf-8
from __future__ import print_function
import RPi.GPIO as GPIO
import threading
import sys

sys.path.insert(0, '/home/pi/dynamixel_hr')
from dxl.dxlchain import DxlChain

chain = DxlChain("/dev/ttyUSB0", rate=1000000)
print(chain.get_motor_list())


class Encoder(object):
    """
    A quadrature encoder
    """
    Rotary_counter = 0
    Current_A = 1
    Current_B = 1
    id = 0

    LockRotary = threading.Lock()

    enc_a = 0
    enc_b = 0

    position = 0

    def update_position(self, new_position):
        """
        Makes sure that the position is sane
        :param new_position: Position value
        """
        self.position += new_position * abs(new_position)
        if self.position > 1000:
            self.position = 1000
        elif self.position < 0:
            self.position = 0
        else:
            return

    def rotary_interrupt(self, a_or_b):

        """
        Gets called when a change in voltage is detected
        :param a_or_b: Which pin called back
        """

        switch_a = GPIO.input(self.enc_a)
        switch_b = GPIO.input(self.enc_b)

        if self.Current_A == switch_a and self.Current_B == switch_b:
            return

        self.Current_A = switch_a
        self.Current_B = switch_b

        if switch_a and switch_b:
            self.LockRotary.acquire()
            if a_or_b == self.enc_b:
                self.Rotary_counter += 1
            else:
                self.Rotary_counter -= 1
            self.LockRotary.release()
        return

    def __init__(self, enc_a, enc_b, id):
        self.enc_a = enc_a
        self.enc_b = enc_b
        self.id = id

        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(self.enc_a, GPIO.IN)
        GPIO.setup(self.enc_b, GPIO.IN)

        GPIO.add_event_detect(self.enc_a, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(self.enc_b, GPIO.RISING, callback=self.rotary_interrupt)

    def startup(self):
        """
        Wiggles the finger 
        """
        chain.goto(self.id, 0, 1023, True)
        chain.goto(self.id, 250, 1023, True)
        chain.goto(self.id, 0, 1023, True)


def update(encoder):
    """
    Update an Encoder's position value.
    :param encoder: An Encoder object
    """
    encoder.LockRotary.acquire()
    new_position = encoder.Rotary_counter
    encoder.Rotary_counter = 0
    encoder.LockRotary.release()
    if new_position != 0:
        encoder.update_position(new_position)
        chain.goto(encoder.motor, encoder.position, 1000, False)


Encoder1 = Encoder(8, 10, 1)
Encoder2 = Encoder(11, 12, 2)
Encoder3 = Encoder(15, 16, 3)
Encoder4 = Encoder(21, 22, 4)
Encoder5 = Encoder(23, 24, 5)
array = [Encoder1, Encoder2, Encoder3, Encoder4, Encoder5]

for encoder in array:
    encoder.startup()

while True:
    try:
        for encoder in array:
            update(encoder)

    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Bye! \n")
