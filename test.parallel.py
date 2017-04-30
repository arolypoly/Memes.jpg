from __future__ import print_function
import RPi.GPIO as GPIO
import threading
import sys

sys.path.insert(0, '/home/pi/dynamixel_hr')
from dxl.dxlchain import DxlChain

chain = DxlChain("/dev/ttyUSB0", rate=1000000)
print(chain.get_motor_list())
chain.goto(1, 0, 1023, True)
chain.goto(1, 500, 1023, True)
chain.goto(1, 0, 1023, True)
chain.goto(2, 0, 1023, True)
chain.goto(2, 500, 1023, True)
chain.goto(2, 0, 1023, True)
chain.goto(3, 0, 1023, True)
chain.goto(3, 500, 1023, True)
chain.goto(3, 0, 1023, True)
chain.goto(4, 0, 1023, True)
chain.goto(4, 500, 1023, True)
chain.goto(4, 0, 1023, True)
chain.goto(5, 0, 1023, True)
chain.goto(5, 500, 1023, True)
chain.goto(5, 0, 1023, True)


class Encoder(object):
    """
    4 Wire Encoder
    """
    Rotary_counter = 0
    Current_A = 1
    Current_B = 1
    motor = 0

    LockRotary = threading.Lock()

    enc_a = 0
    enc_b = 0

    position = 0

    def update_position(self, new_position):
        """
        Updates position2
        :param new_position: 
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
        Gets called when an edge is detected
        :param a_or_b: Which pin initiated the call
        :param enc_a: Pin 1
        :param enc_b: Pin 2
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

    def __init__(self, enc_a, enc_b, motor):
        self.enc_a = enc_a
        self.enc_b = enc_b
        self.motor = motor

        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(self.enc_a, GPIO.IN)
        GPIO.setup(self.enc_b, GPIO.IN)

        GPIO.add_event_detect(self.enc_a, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(self.enc_b, GPIO.RISING, callback=self.rotary_interrupt)


def update(encoder):
    """
    Update position.
    :param encoder: 
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

while True:
    try:
        update(Encoder1)
        update(Encoder2)
        update(Encoder3)
        update(Encoder4)
        update(Encoder5)

    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Bye! \n")
