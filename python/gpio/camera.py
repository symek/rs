import sys, os
import time, datetime, json

# Dummy object replacing real GPIO module
class GPIOClass(object):
    OUT = None
    LOW = False
    HIGH = True
    BCM = None

    def setmode(self, mode):
        pass
    def setup(self, pin, mode):
        pass
    def output(self, pin, v):
        print pin, v
    def cleanup(self):
        pass

# For testing purposes:
try:
    import RPi.GPIO as GPIO
except:
    print "Can't find GPIO module. Using dummy one..."
    GPIO = GPIOClass()


class Camera(object):
    """ Basic class implementing switching camera ON/OFF 
        via lanc cabale connected to RPi pin.
    """
    logfilename = "/tmp/gpio.camera.json"
    log = {'state':"ON", "events":[]}
    camera_pin  = 17
    def __init__(self):
        if os.path.isfile(self.logfilename):
            with open(self.logfilename) as file:
                try:
                    self.log = json.load(file)
                except:
                    print "Can't read log. Creating new one."
        else:
            with open(self.logfilename, 'w') as file:
                json.dump(self.log, file)

    def _trigger_pin(self):
        """
        """
        GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
        GPIO.setup(self.camera_pin, GPIO.OUT)
        GPIO.output(self.camera_pin, GPIO.LOW)
        time.sleep(1)
        GPIO.output(self.camera_pin, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(self.camera_pin, GPIO.LOW)

    def _update_log(self):
        with open(self.logfilename, 'w') as file:
            json.dump(self.log, file, indent=4)
            return True

    def _turn_on_off(self, state):
        if self.log['state'] == state:
            print "Warning! Camera should be in %s state already." % state
        self._trigger_pin()
        nowiso = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.log['events'] += [{'date': nowiso, 'event': state}]
        self.log['state'] =  state
        self._update_log()
        return True

    def turn_on(self):
        return self._turn_on_off("ON")

    def turn_off(self):
        return self._turn_on_off("OFF")




