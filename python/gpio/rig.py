import sys, os, json
import time, datetime

DEFAULT_POWER = 1
RESCUE_MODE   = 0

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

class PiJuiceClass(object):
    class Status(object):
        def SetIoDigitalOutput(self, p, v):
            return True
        def getStatus(self):
            return {}
        def GetIoDigitalInput(self, p):
            return True

    def __init__(self, x, y):
        self.status = PiJuiceClass.Status()


try:
    import RPi.GPIO as GPIO
except:
    print "Can't find GPIO module. Using dummy one..."
    # sys.exit()
    GPIO = GPIOClass()


try:
    from pijuice import PiJuice # Import pijuice module
except:
    print "Cant' find pijuice module. Using dummy one..."
    PiJuice = PiJuiceClass

# Instantiate PiJuice interface object
pijuice = PiJuice(1, 0x14) 

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
    angle = 485.333333333333333333
    pins  =[Pin("y_pulse",     5),
            Pin("y_direct",    6),
            Pin("x_pulse",     13),
            Pin("x_direct",    19),
            Pin("zoom_pulse",  12),
            Pin("zoom_direct", 16)]
    axis  = {'y':    (pins[0], pins[1]), 
             'x':    (pins[2], pins[3]), 
             'zoom': (pins[4], pins[5])}
    logfilename = "/tmp/gpio.rig.json"
    log = {'state':{'y': 0.0, 'x': 0.0, 'zoom': 0.0}, "events":[]}
    turn_off_on_exit = True

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
        # Turn on power for rig 
        self.turn_on()

    def __del__(self):
        """ Turn off rig's power when destroying object. This might not be good idea
            for strong wind. Set 'turn_off_on_exit' to False to allow leaving rig
            with power turned on (it gonna eat ???mA at 12V)
        """
        if self.turn_off_on_exit:
            self.turn_off()
        GPIO.cleanup()

    def _update_log(self):
        with open(self.logfilename, 'w') as file:
            json.dump(self.log, file, indent=4)
            return True

    def rotate(self, axe, angle):
        """
        """
        # Revert sign for x
        if axe == "x": angle *= -1
        # 
        range_ = self.angle * abs(angle)
        # TODO Multiplier for rotations in angles (360 misses 0.7 percent)
        range_ = range_ + self.angle*abs(angle)*.00733333333
        if angle < 0: 
            sign = GPIO.HIGH
        else: 
            sign = GPIO.LOW

        assert axe in self.axis
        GPIO.output(self.axis[axe][1].number, sign)

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

    def get_power_status(self):
        return pijuice.status.GetStatus() # Read PiJuice staus.

    def turn_on(self):

        #turn on 12V (ramie)
        pijuice.status.GetIoDigitalInput(1)
        pijuice.status.SetIoDigitalOutput(1, 1)

    def turn_off(self):
        #turn off 12V
        pijuice.status.GetIoDigitalInput(1)
        pijuice.status.SetIoDigitalOutput(1, 0)
        pijuice.status.GetIoDigitalInput(1)

    def force_rescue_power(self, value=RESCUE_MODE):
        #force select solar (0 - ratunek dla raspberry, 1 - default)
        pijuice.status.GetIoDigitalInput(2)
        pijuice.status.SetIoDigitalOutput(2, value)
        pijuice.status.GetIoDigitalInput(2)

    def force_state(self, y, x, z):
        """Forces to set current state as one provided. 
            Useful for calibration. First set position
            to required values, then set state for (0,0,0).
        """
        self.log['state']['y']    = y
        self.log['state']['x']    = x
        self.log['state']['zoom'] = z
        self._update_log()
        return self.log['state']





