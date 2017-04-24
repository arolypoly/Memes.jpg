# coding=utf-8
# Stolen from https://www.raspberrypi.org/forums/viewtopic.php?f=37&t=140250
from __future__ import print_function
from __future__ import print_function
import RPi.GPIO as GPIO
import threading
import sys

sys.path.insert(0, '/home/pi/dynamixel_hr')
from dxl.dxlchain import DxlChain

# GPIO Ports
Enc_A = 14  # Encoder input A: input GPIO 15
Enc_B = 15  # Encoder input B: input GPIO 14
Rotary_counter = 0  # Start counting from 0
Current_A = 1  # Assume that rotary switch is not
Current_B = 1  # moving while we init software
Encoder_Min = 0
Encoder_Max = 720

Chain = DxlChain("/dev/ttyUSB0", rate=1000000)
print(Chain.get_motor_list())

LockRotary = threading.Lock()  # create lock for rotary switch


# initialize interrupt handlers
def init():
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)  # Use BCM mode
    # define the Encoder switch inputs
    GPIO.setup(Enc_A, GPIO.IN)
    GPIO.setup(Enc_B, GPIO.IN)
    # setup callback thread for the A and B encoder
    # use interrupts for all inputs
    GPIO.add_event_detect(Enc_A, GPIO.RISING, callback=rotary_interrupt)  # NO bouncetime
    GPIO.add_event_detect(Enc_B, GPIO.RISING, callback=rotary_interrupt)  # NO bouncetime

    # Move a bit
    Chain.goto(1, 1, speed=1000)  # Motor ID 1 is sent to position 500 with high speed
    Chain.goto(1, 999)  # Motor ID 1 is sent to position 100 with last speed value
    Chain.goto(1, 1)

    return


# Rotarty encoder interrupt:
# this one is called for both inputs from rotary switch (A and B)
def rotary_interrupt(A_or_B):
    global Rotary_counter, Current_A, Current_B, LockRotary
    # read both of the switches
    switch__a = GPIO.input(Enc_A)
    switch__b = GPIO.input(Enc_B)
    # now check if state of A or B has changed
    # if not that means that bouncing caused it
    if Current_A == switch__a and Current_B == switch__b:  # Same interrupt as before (Bouncing)?
        return  # ignore interrupt!

    Current_A = switch__a  # remember new state
    Current_B = switch__b  # for next bouncing check

    if switch__a and switch__b:  # Both one active? Yes -> end of sequence
        LockRotary.acquire()  # get lock
        if A_or_B == Enc_B:  # Turning direction depends on
            Rotary_counter += 1  # which input gave last interrupt
        else:  # so depending on direction either
            Rotary_counter -= 1  # increase or decrease counter
        LockRotary.release()  # and release lock
    return  # THAT'S IT


# Main loop. Demonstrate reading, direction and speed of turning left/rignt
def main():
    global Rotary_counter, LockRotary, Chain

    volume = 0  # Current Volume
    new_counter = 0  # for faster reading with locks

    init()  # Init interrupts, GPIO, ...

    while True:  # start test

        # because of threading make sure no thread
        # changes value until we get them
        # and reset them

        LockRotary.acquire()  # get lock for rotary switch
        new_counter = Rotary_counter  # get counter value
        Rotary_counter = 0  # RESET IT TO 0
        LockRotary.release()  # and release lock

        if new_counter != 0:  # Counter has CHANGED
            volume += new_counter * abs(new_counter)  # Decrease or increase volume
            print(new_counter, volume)  # some test print
            if volume < 0:
                volume = 0
                Chain.goto(1, 1)
            if volume > 1000:
                volume = 999
                Chain.goto(1, 999)
        Chain.goto(1, volume)


# start main demo function
try:
    main()
except KeyboardInterrupt:
    print("\n" + "Bye!" + "\n")
    GPIO.cleanup()
