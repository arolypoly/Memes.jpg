import RPi.GPIO as GPIO
import threading
from time import sleep

# GPIO Ports
Encoders = [(7, 8), (11, 12), (15, 16), (17, 18), (21, 22), (23, 24)]


class Encoder:
    Rotary_counter = 0
    Current_A = 1
    Current_B = 1

    LockRotary = threading.Lock()

    enc_a = 0
    enc_b = 0

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

    def start(self):

        position = 0

        while True:
            sleep(1 / 125)

            self.LockRotary.acquire()
            new_position = self.Rotary_counter
            self.Rotary_counter = 0
            self.LockRotary.release()

            if new_position != 0:
                position = position + new_position * abs(new_position)
                print(new_position, position)

    def __init__(self, enc_a, enc_b):
        self.enc_a = enc_a
        self.enc_b = enc_b

        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(self.enc_a, GPIO.IN)
        GPIO.setup(self.enc_b, GPIO.IN)

        GPIO.add_event_detect(self.enc_a, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(self.enc_b, GPIO.RISING, callback=self.rotary_interrupt)

        thread = threading.Thread(target=self.start(), args=())
        thread.daemon = False
        thread.start()


Encoder1 = Encoder(8, 10)
