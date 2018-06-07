#!/opt/local/bin/python2
#!/usr/bin/python
import os, time, sys
from multiprocessing import Process
from optparse import OptionParser
import sys

RS_EXECUTE_REMOTE = False

try:
    from paramiko import client
    RS_EXECUTE_REMOTE = os.getenv("RS_EXECUTE_REMOTE", False)
    print "RS_EXECUTE_REMOTE: ", RS_EXECUTE_REMOTE
except:
    print "Can't import paramiko. No remote execution will take place."

# ENV controling our behaviour
RS_REMOTE_HOST    = os.getenv("RS_REMOTE_HOST", "10.20.6.217")
RS_USER_NAME      = os.getenv("RS_USER_NAME",   "pi")


# Command line patterns
GPHOTO_SHOW_PREVIEW = "gphoto2 --show-preview --force-overwrite"
GPHOTO_CAPTURE_DOWN = "gphoto2 --capture-image-and-download --force-overwrite --filename %s"
GPHOTO_SET_ISO      = "gphoto2 --set-config iso=%s"
GPHOTO_SET_FSTOPS   = "gphoto2 --set-config f-number=%s"
GPHOTO_SET_SHUTTER  = "gphoto2 --set-config shutterspeed=%s"
GPHOTO_SET_CONFIG   = "gphoto2 --set-config %s=%s"
GPHOTO_CAPTURE_MOVIE = "gphoto2 --set-config movie=1 --wait-event=%ss --set-config movie=0"


# CLI interface. 
def parseOptions(argv):
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)


    #Options:
    parser.add_option("-m", "--move",       dest="move",    action="store",  default=None,  help="Move head.")
    parser.add_option("-c", "--capture",    dest="capture", action="store",  default=None,  help="Capture an image")
    parser.add_option("-p", "--preview",    dest="preview", action="store_true",   default=False, help="Preview an image")
    parser.add_option("-M", "--movie",      dest="movie",   action="store",   default=None,  help="Capture the movie.")
    parser.add_option("-s", "--shutter",    dest="shutter", action="store",   default=None,  help="Sets shutter speed.")
    parser.add_option("-f", "--fstop",      dest="fstop",   action="store",   default=None,  help="Sets fstop of camera.")
    parser.add_option("-i", "--iso",        dest="iso",     action="store",   default=None,  help="Sets ISO of camera.")
    parser.add_option("-P", "--panorama",   dest="panorama",action="store",   default=None,  help="Creates panoramic image.")
    parser.add_option("",   "--rotate",     dest="rotate",  action="store", type="int",    default=0,       help="Rotate the image.")
    parser.add_option("",   "--resize",     dest="resize",  action="store", type="float",  default=1.0,     help="Resize the image.")
    parser.add_option("",   "--set-config", dest="config",  action="store", default=None,                   help="Sets various camera settings.")
    parser.add_option("",   "--execute",    dest="execute", action="store", type='string', default=None,   help="Executes arbitrary command.")
    # parser.add_option("",   "--proxy",   dest="proxy",   action="store_true", default=False, help="Convert textures to jpeg proxies (2048x2048).")
    # parser.add_option("",   "--scale",   dest="scale",   action="store",      default=1,     help="Scale factor (default x1")
    (opts, args) = parser.parse_args(argv)
    return opts, args, parser


# Class handing ssh connection.
class SSHClient:
    """Sends a single command to the remote host.
       Looks for ssh keys. 
    """
    client = None
    
    def __init__(self, address, username, password):
        print("Connecting to server.")
        self.client = client.SSHClient()
        self.address = address
        self.username = username
        self.password = password
        self.client.set_missing_host_key_policy(client.AutoAddPolicy())
        self.client.connect(address, username=username, password=password, look_for_keys=True)
 
    def send_command(self, command):
        if(self.client):
            stdin, stdout, stderr = self.client.exec_command(command)
            while not stdout.channel.exit_status_ready():
                # Print data when available
                if stdout.channel.recv_ready():
                    stdout_data = stdout.channel.recv(1024)
                    stderr_data = stderr.channel.recv(2014)
                    prev_stdout_data = b"1"
                    prev_stderr_data = b"1"
                    while prev_stdout_data:
                        prev_stdout_data = stdout.channel.recv(1024)
                        stdout_data += prev_stdout_data
                    while prev_stderr_data:
                        prev_stderr_data = stderr.channel.recv(1024)
                        stderr_data += prev_stderr_data
                    return stdout_data, stderr_data
        else:
             print("Connection not opened: %s, %s, %s" % (self.address, self.username, self.password))
        return None, None




def clamp(x, m=-1023, M=1023):
    """Basic clamp"""
    if x < m: return m
    if x > M: return M
    return x


def move_head_smooth(ax, ay, az, pow_=2.2, steps=10.0):
    """WIP."""
    from time import sleep
    x = (clamp(ax) + 1024)
    y = (clamp(ay) + 1024)
    z = (clamp(az) + 1024)
    step = 1.0 / steps
    for i in range(int(steps)):
        ps = pow(step*i, pow_)
        command = ["./ronin", "0", str(x*ps), "1", str(y*ps), "3", str(z*ps)]
        open_pipe(command)
    sleep(2)



def move_head(ax, ay, az):
    """ ax, ay, az acceleration in x, y, z of a motor.
    Values between -1023 and 1023 are valid.
    """
    from time import sleep
    x = clamp(ax) + 1024
    y = clamp(ay) + 1024
    z = clamp(az) + 1024
    command = ["./ronin", "0", str(x), "1", str(y), "3", str(z)]
    open_pipe(command)
    sleep(2)



def open_pipe_ssh(command, verbose=True):
    """ Executes command in ssh. 
        Command: list of words in shell command.
    """
    import subprocess
    HOST = 'pi@192.168.1.50'
    COMMAND = " ".join(command)
    ssh = subprocess.Popen(["ssh", "-t", "-t", "%s" % HOST, COMMAND],
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    error  = ssh.stderr.readlines()
    return result, error

def open_pipe_ssh2(command, verbose=True):
    """ Executes command remotly via paramiko 
        Command: list of words in shell command.
    """
    if not RS_EXECUTE_REMOTE:
        print "This shouldn't be called at all (not paramiko or remote model not allowed)."
        return None, None

    client = SSHClient(RS_REMOTE_HOST, RS_USER_NAME, "")
    ssh_command = " ".join(command)
    print "Sends %s to %s as %s" % (ssh_command, RS_REMOTE_HOST, RS_USER_NAME)
    result, error = client.send_command(ssh_command)
    return result, error

def open_pipe(command, verbose=True, ssh=RS_EXECUTE_REMOTE):
    """ Executes command in subshell. 
        Command: list of words in shell command. 
    """
    from subprocess import Popen, PIPE 
    if verbose:
        print "Command: ", 
        print " ".join(command)

    if ssh:
        return open_pipe_ssh2(command)

    o, e =  Popen(command, shell=False, 
                stdout=PIPE, stderr=PIPE, 
                universal_newlines=True).communicate()

    if o: print o
    if e: print e
    return o, e

def show_preview(filename="capture_preview.jpg", refresh=False, rotate=0, resize=1):
    from sys import platform
    print make_preview(filename)
    if platform == "darwin":
        return open_pipe(['open', filename])
    elif platform == "linux2":
        print open_pipe(['oiiotool', filename, "--rotate", str(rotate), "--resize", "%s" % str(resize*100),  '-o', filename])
        return open_pipe(['feh', filename])

def make_preview(filename):
    command = GPHOTO_SHOW_PREVIEW.split()
    out, err = open_pipe(command)
    return out, err

def list_config(item=None):
    config, err = open_pipe(['gphoto2', '--list-config'])
    if err: 
        print err
        return   False
    config = config.split()
    for item in config:
        command = ['gphoto2', '--get-config=%s' % item]
        out, err = open_pipe(command)
        print out

def set_config(config, value):
    command = GPHOTO_SET_CONFIG % (config, str(value))
    command = command.split()
    o, e = open_pipe(command)
    return o, e

def get_config(config):
    command = "gphoto2 --get-config %s" % config
    command = command.split()
    return open_pipe(command)

def set_autofocus(autofocus):
    """ Set autofocus: True / False
    """
    return set_config('autofocus', autofocus)

def set_iso(iso):
    """ Set ISO: (SLog3 needs above 350)
    """
    return set_config('iso', iso)

def set_shutter(shutterspeed):
    return set_config("shutterspeed", shutterspeed)

def set_fstop(fstop):
    return set_config("f-number", str(fstop))


def capture_and_download(filename, preview=False):
    """ Capture and download photo.
    """
    command = GPHOTO_CAPTURE_DOWN % filename
    command = command.split()
    o, e  = open_pipe(command)
    if not e and preview:
        show_preview(filename)

def capture_movie(time=10):
    """ Capture 'time' length video.
        Note: Unlike photos, movie file will remain on camera.
    """
    command = GPHOTO_CAPTURE_MOVIE % str(time)
    command = command.split()
    return open_pipe(command)


def aov_from_focal_length(length, sensor_width=36.0, sensor_hight=24.0):
    """ Compute field of view in radians 
        from focal length and sensor size (default 35mm).
    """
    from math import atan
    h = 2 * atan(length / 2.0*sensor_width)
    v = 2 * atan(length / 2.0*sensor_hight)
    return h, v


def compute_panorama(haov, vaov, hangle, vangle, overlap=.3):
    """ Given horizontal and vertical field of view (in radians) and requested
        panorama angle (in radians), compute set of commands for shooting panorama. 
    """
    from math import ceil
    n_h_steps = int(ceil(hangle / haov))
    h_shift   = haov * overlap
    n_v_steps = int(ceil(vangle / vaov))
    v_shift   = vaov * overlap
    panorama = []
    for vstep in range(n_v_steps):
        for hstep in range(n_h_steps):
            step_info = {}
            step_info['shift'] = (h_shift, v_shift)
            panorama += [step_info]
    return panorama



def compute_hdri(fstops=5):
    for stop in range(fstops):
        current_fstop = get_current(get_config("f-number")[0])
        current_fstop = float(current_fstop)
        filename = "hdri_%s.arw" % stop
        set_fstop(current_fstop+1)
        capture_and_download(filename, 0)


def get_current(config):
    # print config.split()
    config = [line.split(":") for line in config.split("\n")]
    # print config
    for line in config:
        if line[0] == "Current":
            return line[1].strip()


def main():
    """ Main. Parse commnd lines, sets camera config first, then executes shoot. 
    """
    opts, args, parser = parseOptions(sys.argv[1:])
   

    # CLI.
    if opts.config:
        items = opts.config.split("=")
        assert len(items) == 2
        name, value = items
        set_config(name, value)

    # Back door to remotly execute anything
    if opts.execute:
        print open_pipe(opts.execute.split(" "))

    # Sets camera shooting properties:
    if opts.shutter:
        set_shutter(opts.shutter)
    if opts.fstop:
        set_fstop(opts.fstop)
    if opts.iso:
        set_iso(opts.iso)

    # Ronin control: 
    if opts.move:
        move_arg = opts.move.split(",")
        if not len(move_arg) == 3:
            print "Needs three coordinates like 0,0,0"
        accel = []
        for i in move_arg:
            accel += [int(i)]
        move_head(*accel)

    # Preview:
    if opts.preview and not opts.capture:
        show_preview(rotate=opts.rotate, resize=opts.resize)

    # Capture the image:
    if opts.capture and not opts.preview:
        capture_and_download(opts.capture, False)
    elif opts.capture and opts.preview:
        capture_and_download(opts.capture, True)

    # Record video: 
    if opts.movie:
        capture_movie(opts.movie)

    if opts.panorama:
        pano_detail = compute_panorama()




if __name__ == "__main__": 
    main()


# print get_config("capturemode")
# print list_config()
# print open_pipe_ssh(['ls', '-la', '/tmp'])
# capture_movie(5)
# print haov_from_focal_length(50)
# h, v = aov_from_focal_length(24.0)
# print compute_panorama(h, v, 180, 180)
# show_preview()
# set_autofocus(True)
# set_shutter("1/50")
# set_fstop(4.0)
# fstop = get_config("f-number")
# print get_current(fstop[0])
# compute_hdri()
# set_config("/main/capturesettings/expprogram", 5)
# set_config("/main/capturesettings/capturemode", 0)
# set_config("/main/capturesettings/imagequality", 3)
# set_config("/main/other/d21b", 0 )
# show_preview()
# set_iso(10000)

# raspberry
# /main/actions/autofocus                                                        
# /main/actions/capture
# /main/actions/bulb
# /main/actions/movie
# /main/actions/opcode
# /main/status/serialnumber
# /main/status/manufacturer
# /main/status/cameramodel
# /main/status/deviceversion
# /main/status/vendorextension
# /main/status/batterylevel
# /main/imgsettings/imagesize
# /main/imgsettings/iso
# /main/imgsettings/colortemperature
# /main/imgsettings/whitebalance
# /main/capturesettings/exposurecompensation
# /main/capturesettings/flashmode
# /main/capturesettings/f-number
# /main/capturesettings/imagequality
# /main/capturesettings/focusmode
# /main/capturesettings/expprogram
# /main/capturesettings/aspectratio
# /main/capturesettings/capturemode
# /main/capturesettings/exposuremetermode
# /main/capturesettings/shutterspeed
