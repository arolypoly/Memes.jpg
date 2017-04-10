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

    @staticmethod
    def rotary_interrupt(ab, enc_a, enc_b):
        global Rotary_counter, Current_A, Current_B, LockRotary

        switch_a = GPIO.input(enc_a)
        switch_b = GPIO.input(enc_b)

        if Current_A == switch_a and Current_B == switch_b:
            return

        Current_A = switch_a
        Current_B = switch_b

        if switch_a and switch_b:
            LockRotary.acquire()
            if ab == enc_b:
                Rotary_counter += 1
            else:
                Rotary_counter -= 1
            LockRotary.release()
        return

    def __init__(self, enc_a, enc_b):
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(enc_a, GPIO.IN)
        GPIO.setup(enc_b, GPIO.IN)

        GPIO.add_event_detect(enc_a, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(enc_b, GPIO.RISING, callback=self.rotary_interrupt)

        thread = threading.Thread(target=self.start(), args=())
        thread.daemon = False
        thread.start()

    @staticmethod
    def start():
        global Rotary_counter, LockRotary

        position = 0

        while True:
            sleep(1 / 125)

            LockRotary.acquire()
            new_position = Rotary_counter
            Rotary_counter = 0
            LockRotary.release()

            if new_position != 0:
                position = position + new_position * abs(new_position)
                print(new_position, position)


Encoder1 = Encoder(14, 15)
