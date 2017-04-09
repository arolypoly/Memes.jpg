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

    def rotary_interrupt(A_or_B, Enc_A, Enc_B):
        global Rotary_counter, Current_A, Current_B, LockRotary

        Switch_A = GPIO.input(Enc_A)
        Switch_B = GPIO.input(Enc_B)

        if Current_A == Switch_A and Current_B == Switch_B:
            return

        Current_A = Switch_A
        Current_B = Switch_B

        if (Switch_A and Switch_B):
            LockRotary.acquire()
            if A_or_B == Enc_B:
                Rotary_counter += 1
            else:
                Rotary_counter -= 1
            LockRotary.release()
        return  # THAT'S IT

    def __init__(self, Enc_A, Enc_B):
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(Enc_A, GPIO.IN)
        GPIO.setup(Enc_B, GPIO.IN)

        GPIO.add_event_detect(Enc_A, GPIO.RISING, callback=self.rotary_interrupt)  # NO bouncetime
        GPIO.add_event_detect(Enc_B, GPIO.RISING, callback=self.rotary_interrupt)  # NO bouncetime

        thread = threading.Thread(target=self.start(), args=())
        thread.daemon = False
        thread.start()

    @staticmethod
    def start():
        global Rotary_counter, LockRotary

        Position = 0
        New_Position = 0

        while True:
            sleep(1 / 125)

            LockRotary.acquire()
            New_Position = Rotary_counter
            Rotary_counter = 0
            LockRotary.release()

            if (New_Position != 0):
                Position = Position + New_Position * abs(New_Position)
                print(New_Position, Position)


Encoder1 = Encoder(14, 15)
