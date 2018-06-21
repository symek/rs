import sys, os, json
import time, datetime
try:
    import numpy
except:
    print "Can't import numpy. Some might not work as expected."

DEFAULT_POWER = 1
RESCUE_MODE   = 0
DEFAULT_TIME_TICK = 0.0000001
SLOWDOWN = 20
RS_SLOW_THRESHOLD = os.getenv("RS_SLOW_THRESHOLD", 10)
RS_MAX_SPEED =  int(os.getenv("RS_MAX_SPEED", 10))
RS_MIN_SPEED =  int(os.getenv("RS_MIN_SPEED", 35))

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
        # print "pin %s" % pin,
        print "%s" % ('.'),
        sys.stdout.flush()
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
    DEFAULT_SLEEP_PERIOD = 0.01


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

    def _compute_ticks2(self, range_):
        from curves import Curve
        curve = Curve(range_)
        ticks_final = [RS_MIN_SPEED + int(div*x) for x in curve.poly(range_)]
        return ticks_final


    def _compute_ticks(self, range_, easing='c'):
        """ Computes varible ticks to control serve in head.
            Sleep has to be small and constant, because timer
            isn't good enough to give us control. 
        """
        from curves import Curve

        fixodd = False
        if range_%4:
            fixodd = True

        curve = Curve(range_)
        # Dirty I know
        if easing == 'q':
            f = curve.easeInOutQuad
        elif easing == 'c':
            f = curve.easeInOutCubic
        elif easing == 's':
            f = curve.easeInOutSine
        else:
            print "Unknown easing functin."
            return [RS_MIN_SPEED] * range_

        step = 1.0/range_*4
        div  = RS_MAX_SPEED - RS_MIN_SPEED
        zero_based_range = range_ / 4
        ticks_to_half  = [RS_MIN_SPEED + int(div*f(x*step)) for x in xrange(zero_based_range)]
        ticks_to_one   = list(ticks_to_half)
        ticks_to_one.reverse()
        ticks_full = [ticks_to_half[-1]]*zero_based_range*2
        ticks_final = ticks_to_half + ticks_full + ticks_to_one
        if fixodd:
            while len(ticks_final) < range_:
                ticks_final += [RS_MIN_SPEED]
        return ticks_final


    def rotate_all(self, axes):
        """ Interleaves ticks for all axes into a single list, so camera can rotate in
            all directions at once. Ugly.
        """
        axes['x'] *= -1
        for axe in axes:
            if axes[axe] < 0:
                GPIO.output(self.axis[axe][1].number, GPIO.HIGH)
            else:
                GPIO.output(self.axis[axe][1].number, GPIO.LOW)

        ticks = []
        for axe in axes:
            if axes[axe]:
                _range = self.angle * abs(axes[axe])
                _range = _range + self.angle*abs(axes[axe])*.007333333
                if abs(axes[axe]) > RS_SLOW_THRESHOLD:
                    _ticks = [(self.axis[axe][0].number, tick) for tick in self._compute_ticks(int(_range))]
                else:
                    _ticks = [(self.axis[axe][0].number, RS_MIN_SPEED)] * int(_range)
                ticks.append(_ticks)
            else:
                ticks.append([])

        limit = 0 
        for a in ticks:
            if len(a):
                limit+= 1
        limit = 3
        while(True):
            counter = 0
            for axe in ticks:
                if axe:
                    tick  = axe.pop()
                    sleep = DEFAULT_TIME_TICK
                    GPIO.output(tick[0], GPIO.HIGH)
                    for t in range(tick[1]):
                        time.sleep(sleep)
                    GPIO.output(tick[0], GPIO.LOW)
                    for t in range(tick[1]):
                        time.sleep(sleep)
                else:
                    counter +=1
                    if counter == limit:
                        return

        nowiso = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.log['events'] += [{'y': axes['y'], 'x': axes['x'], 'zoom': axes['zoom'],  'date': nowiso}]
        self.log['state']['y']    += axes['y']
        self.log['state']['x']    += axes['x']
        self.log['state']['zoom'] += axes['zoom']
        self._update_log()



    def rotate(self, axe, angle):
        """
        """
        #TODO: Implement rotation LIMITS so that we won't brake cables. 
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
        if range_:
            if abs(angle) > 5:
                timeticks = self._compute_ticks(int(range_))
            else:
                # This is to a lame of our easying functions...
                timeticks = [RS_MIN_SPEED] * int(range_)
        else:
            timeticks = [0]
        for step in range(int(range_)):
            sleep = DEFAULT_TIME_TICK
            GPIO.output(self.axis[axe][0].number, GPIO.HIGH)
            for t in range(timeticks[step]):
                time.sleep(sleep)
            GPIO.output(self.axis[axe][0].number, GPIO.LOW)
            for t in range(timeticks[step]):
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





