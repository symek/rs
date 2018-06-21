#!/usr/bin/python

import RPi.GPIO as GPIO
import time, sys

def main():
    if len(sys.argv) < 3:
        print "$program power (%) time (sec.)"
        return 1
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.OUT)
    pwm = GPIO.PWM(18,10)
    #GPIO.output(18,1)
    period = int(sys.argv[-1])
    power  = int(sys.argv[-2])
    print "Warning! Start hitting with %s percent of power for %s seconds" % (power, period)
    pwm.start(power)
    for sec in range(period):
        if sec%5 > 0:
            print ".",
            sys.stdout.flush()
        time.sleep(1)
    print 
    pwm.stop()
    #GPIO.output(18,0)
    GPIO.cleanup()
    print "End of hitting process"

if __name__ == "__main__": main()
