#!/usr/bin/python

import sys, getopt
import RPi.GPIO as GPIO
import time


# Pin Definitons:
pin = 17

# Pin Setup:
GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
GPIO.setup(pin, GPIO.OUT)
GPIO.output(pin, GPIO.LOW)
time.sleep(1)
GPIO.output(pin, GPIO.HIGH)
time.sleep(1)
GPIO.output(pin, GPIO.LOW)


