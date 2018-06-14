import sys, os, json
import time, datetime

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

class Rig(object):
    """ Class for controling DitoGear camera rig and Len driver via
        GPIO pins on RPi.
    """
    angle = 485.3333333333333
    pins  =[Pin("y_pulse",     5),
            Pin("y_direct",    6),
            Pin("z_pulse",     13),
            Pin("z_direct",    19),
            Pin("zoom_pulse",  12),
            Pin("zoom_direct", 16)]
    axis  = {'y':    (pins[0], pins[1]), 
             'z':    (pins[2], pins[3]), 
             'zoom': (pins[4], pins[5])}
    logfilename = "/tmp/gpio.rig.json"
    log = {'state':{'y': 0.0, 'z': 0.0, 'zoom': 0.0}, "events":[]}

    def __init__(self):
        # Pin Setup:
        if os.path.isfile(self.logfilename):
            with open(self.logfilename) as file:
                try:
                    self.log = json.load(file)
                except:
                    print "Can't read log. Creating new one."
        else:
            with open(self.logfilename, 'w') as file:
                json.dump(self.log, file)

        GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
        for pin in self.pins:
            GPIO.setup(pin.number, GPIO.OUT)

    def _update_log(self):
        with open(self.logfilename, 'w') as file:
            json.dump(self.log, file, indent=4)
            return True

    def rotate(self, axe, angle):
        """
        """
        range_ = self.angle * abs(angle)
        if angle < 0: sign = GPIO.HIGH
        else: sign = GPIO.LOW

        assert axe in self.axis
        GPIO.output(self.axis[axe][1], sign)

        for step in range(int(range_)):
            sleep = 0.000001
            GPIO.output(self.axis[axe][0].number, GPIO.HIGH)
            time.sleep(sleep)
            GPIO.output(self.axis[axe][0].number, GPIO.LOW)
            time.sleep(sleep)

        nowiso = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.log['events'] += [{axe: angle, 'date': nowiso}]
        self.log['state'][axe] += angle
        self._update_log()

    def __del__(self):
        GPIO.cleanup()


