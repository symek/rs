#!/usr/bin/python

import sys, getopt
import time

# Dummy object replacing real GPIO module
class GPIOClass(object):
    OUT = None
    LOW = None
    HIGH = None
    BCM = None

    def setmode(self, mode):
        pass
    def setup(self, pin, mode):
        pass
    def output(self, v):
        pass
    def cleanup(self):
        pass

try:
    import RPi.GPIO as GPIO
except:
    print "Can't find GPIO module. Exiting now."
    # sys.exit()
    GPIO = GPIOClass()

class Pin(object):
    name   = None
    number = None
    mode   = None
    state  = None
    def __init__(self, name, number, 
        mode=GPIO.OUT, state=GPIO.LOW):
        self.name   = name
        self.number = number
        self.mode   = mode
        self.state  = state

class DitoGear(object):
    angle = 485.3333333333333
    pins  =[Pin("y_pulse",     5),
            Pin("y_direct",    6),
            Pin("z_pulse",     13),
            Pin("z_direct",    19),
            Pin("zoom_pulse",  12),
            Pin("zoom_direct", 16),
            Pin("dito_power", None)]
    axis  = {'y':    (pins[0], pins[1]), 
             'z':    (pins[2], pins[3]), 
             'zoom': (pins[4], pins[5])}

    def __init__(self):
        # Pin Setup:
        GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
        for pin in self.pins:
            GPIO.setup(pin.number, GPIO.OUT)

    def rotate(axe, angle):
        """
        """
        range_ = self.ange * abs(angle)
        if angle < 0: sign = GPIO.HIGH
        else: sign = GPIO.LOW

        assert axe in self.axis
        GPIO.output(self.axis[axe][1], sign)

        for step in range(range_):
            sleep = 0.000001
            GPIO.output(self.axis[axe][0], GPIO.HIGH)
            time.sleep(sleep)
            GPIO.output(self.axis[axe][0], GPIO.LOW)
            time.sleep(sleep)





# "z_pulse" : 13,
# "z_direct": 19,
# "zoom_pulse": 12,
# "zoom_direct": 16,
# "dito_power": None


def main():

    dg = DitoGear()
    print dg
    print  dg.pins

    # if len (sys.argv) < 7 :
    #     print "Usage: script direc #steps"
    #     sys.exit (1)

    # # Pin Definitons:
    # xp = 5
    # xd = 6

    # yp = 13
    # yd = 19

    # zp = 12
    # zd = 16


    # xpv, xdv, ypv, ydv, zpv, zdv = sys.argv[1:]


    # #174720 steps for full range 
    # #61472 for lens driver
    # # Pin Setup:
    # GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
    # GPIO.setup(xp, GPIO.OUT)
    # GPIO.setup(xd, GPIO.OUT)
    # GPIO.setup(yp, GPIO.OUT)
    # GPIO.setup(yd, GPIO.OUT)
    # GPIO.setup(zp, GPIO.OUT)
    # GPIO.setup(zd, GPIO.OUT)

    # if int(xdv) > 0 :
    #     GPIO.output(xd, GPIO.HIGH)
    # else :
    #     GPIO.output(xd, GPIO.LOW)

    # if int(ydv) > 0 :
    #     GPIO.output(yd, GPIO.HIGH)
    # else :
    #     GPIO.output(yd, GPIO.LOW)

    # if int(zdv) > 0 :
    #     GPIO.output(zd, GPIO.HIGH)
    # else :
    #     GPIO.output(zd, GPIO.LOW)

    # print 'xpv'
    # for x in range(int(xpv)):
    #     GPIO.output(xp, GPIO.HIGH)
    #     time.sleep(0.00001)
    #     GPIO.output(xp, GPIO.LOW)
    #     time.sleep(0.00001)

    # #sys.exit()
    # print 'ypv'
    # for x in range(int(ypv)):
    #     GPIO.output(yp, GPIO.HIGH)
    #     time.sleep(0.00001)
    #     GPIO.output(yp, GPIO.LOW)
    #     time.sleep(0.00001)

    # print 'zpv'
    # for x in range(int(zpv)):
    #     GPIO.output(zp, GPIO.HIGH)
    #     time.sleep(0.00001)
    #     GPIO.output(zp, GPIO.LOW)
    #     time.sleep(0.00001)


    # GPIO.cleanup() # cleanup all GPIO

if __name__ == "__main__": 
    sys.exit(main())


