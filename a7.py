#!/usr/local/bin/python
#!/opt/local/bin/python2
import os, time, sys, re
from multiprocessing import Process
import threading
from optparse import OptionParser


RS_EXECUTE_REMOTE = False

try:
    import rpyc
    RS_EXECUTE_REMOTE = os.getenv("RS_EXECUTE_REMOTE", False)
except:
    print "Can't import rpyc. No remote execution will take place."

print "RS_EXECUTE_REMOTE:", bool(RS_EXECUTE_REMOTE)
# ENV controling our behaviour
RS_REMOTE_HOST    = os.getenv("RS_REMOTE_HOST", "10.20.6.217")
RS_USER_NAME      = os.getenv("RS_USER_NAME",   "pi")
RPYC_PORT         = os.getenv("RPYC", 55653)

if RS_EXECUTE_REMOTE:
    print "Host: " + RS_REMOTE_HOST
    print "User: " + RS_USER_NAME
    print "port: " + str(RPYC_PORT) 


RS_DROPBOX_AVAIABLE = False
RS_DROPBOX_ACCESS_TOKEN = "WW-HJbGm1E4AAAAAAAARz8mU2nGfZv0YNqZGVvmm2PBxQuHAcZ6a7RH2J1ER31_l"

try:
    import dropbox
    from dropbox.files import WriteMode
    from dropbox.exceptions import ApiError, AuthError
    RS_DROPBOX_AVAIABLE = True
except:
    pass



# Command line patterns
GPHOTO_MAKE_PREVIEW = "gphoto2 --show-preview --force-overwrite --filename %s"
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
    parser.add_option("-m", "--move",       dest="move",    action="store",   default=None,  help="Move head.")
    parser.add_option("-c", "--capture",    dest="capture", action="store",   default=None,  help="Capture an image")
    parser.add_option("-p", "--preview",    dest="preview", action="store",   default=0,     help="Preview an image")
    parser.add_option("-M", "--movie",      dest="movie",   action="store",   default=None,  help="Capture the movie.")
    parser.add_option("-s", "--shutter",    dest="shutter", action="store",   default=None,  help="Sets shutter speed.")
    parser.add_option("-f", "--fstop",      dest="fstop",   action="store",   default=None,  help="Sets fstop of camera.")
    parser.add_option("-i", "--iso",        dest="iso",     action="store",   default=None,  help="Sets ISO of camera.")
    parser.add_option("-P", "--panorama",   dest="panorama",action="store",   default=None,  help="Creates panoramic image.")
    parser.add_option("",   "--rotate",     dest="rotate",  action="store", type="int",    default=0,       help="Rotate the image.")
    parser.add_option("",   "--resize",     dest="resize",  action="store", type="float",  default=1.0,     help="Resize the image.")
    parser.add_option("",   "--set-config", dest="config",  action="store", default=None,                   help="Sets various camera settings.")
    parser.add_option("",   "--execute",    dest="execute", action="store", type='string', default=None,   help="Executes arbitrary command.")
    parser.add_option("",   "--sync",       dest="sync",    action="store_true", default=False, help="Synchronize entire remote folder.")
    parser.add_option("-d", "--download",   dest="download", action="store_true", default=False,     help="Download the image after caputer (only with capture.")
    parser.add_option("-U", "--upload-file",dest="upload_file",   action="store", type='string', default=None,   help="Upload specific file to internet account (Dropbox). ")
    parser.add_option("-u", "--upload",     dest="upload",   action="store_true", type='string', default=None,   help="Upload the image to internet account (Dropbox). ")
        
    (opts, args) = parser.parse_args(argv)
    return opts, args, parser

# Class handing ssh connection with paramiko
# Not in use atm.
class SSHClient:
    """Sends a single command to the remote host.
       Looks for ssh keys. 
    """
    client = None
    
    def __init__(self, address, username, password):
        import paramiko
        print("Connecting to server.")
        self.client = paramiko.client.SSHClient()
        self.address = address
        self.username = username
        self.password = password
        self.client.set_missing_host_key_policy(client.AutoAddPolicy())
        self.client.connect(address, username=username, password=password, look_for_keys=True)

    def __del__(self):
        self.client.close()

 
    def send_command(self, command):
        """Sends command without running shell."""
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

def upload_to_dropbox(filename):
    """Upload file to the dropbox using access token.
    """
    import os.path

    if filename.startswith("./"):
        filename = filename[2:]

    absfilename = os.path.join("/", filename)

    dbx = dropbox.Dropbox(RS_DROPBOX_ACCESS_TOKEN)
    with open(filename, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        print("Uploading " + filename  + " to Dropbox as " + filename + "...")
        try:
            dbx.files_upload(f.read(), absfilename, mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().reason.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                return None
            else:
                print(err)
                return None

    return True


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
    HOST = RS_REMOTE_HOST
    COMMAND = " ".join(command)
    ssh = subprocess.Popen(["ssh", "-t", "-t", "%s" % HOST, COMMAND],
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    error  = ssh.stderr.readlines()
    return result, error

def open_pipe_paramiko(command, verbose=True):
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


def open_pipe_rpyc(command, verbose=True):
    """RPyc take on remote execution."""
    assert 'rpyc' in globals()
    r_command = " ".join(command)
    connection = rpyc.classic.connect(RS_REMOTE_HOST, port=RPYC_PORT)
    return connection.modules.os.system(r_command)

def open_pipe_remote(command, verbose=True):
    """"""
    # return open_pipe_ssh(command, verbose)
    # return open_pipe_paramiko(command, verbose)
    code = open_pipe_rpyc(command, verbose)
    return str(code), None

def rsync(filename):
    """Use rsync to retrive file from remote host."""
    command =["rsync", "-va", "--progress", "%s@%s:~/sony7iii/%s" % (RS_USER_NAME, RS_REMOTE_HOST, filename), filename] 

    return open_pipe(command, remote=False)


def open_pipe(command, verbose=True, remote=RS_EXECUTE_REMOTE):
    """ Executes command in subshell. 
        Command: list of words in shell command. 
    """
    from subprocess import Popen, PIPE 
    exec_mode = " (localy)"
    if remote:
        exec_mode = " (remotely: %s)" % RS_REMOTE_HOST
    if verbose:
        print "Command: ", 
        print " ".join(command) + exec_mode

    if remote:
        return open_pipe_remote(command, verbose)

    o, e =  Popen(command, shell=False, 
                stdout=PIPE, stderr=PIPE, 
                universal_newlines=True).communicate()

    if o: print o
    if e: print e
    return o, e

def show_image(filename, refresh=False, rotate=0, resize=1):
    from sys import platform

    if not RS_EXECUTE_REMOTE:    
        if platform == "darwin":
            return open_pipe(['open', filename])
        elif platform == "linux2":
            print open_pipe(['oiiotool', filename, "--rotate", str(rotate), 
                "--resize", "%s" % str(resize*100),  '-o', filename])
            return open_pipe(['feh', filename])
    else:
        if platform == "darwin":
            command = ["open", filename]
        elif platform == "linux2":
            command = ['xdg-open', filename]
        return open_pipe(command, remote=False)


def sync_images():
    command = ["./sync",]
    o, e = open_pipe(command, remote=False)
    return o, e

def make_preview(filename):
    command = GPHOTO_MAKE_PREVIEW % filename
    command = command.split()
    out, err = open_pipe(command)
    return out, err

def make_preview_from_raw(filename):
    command = "ufraw-batch --overwrite --embedded-image \
        --out-type=jpg --shrink=2 %s" % filename
    command = command.split()
    return open_pipe(command)

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


def capture_and_download_to_PI(filename):
    """ Capture and download photo.
    """
    command = GPHOTO_CAPTURE_DOWN % filename
    command = command.split()
    return open_pipe(command)
    

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

def auto_name_image(prefix=None, postfix=None):
    import datetime, os
    now = datetime.datetime.now().isoformat()
    folder, file_ = now.split("T")
    return os.path.join(prefix, folder, file_ + postfix)

def main():
    """ Main. Parse commnd lines, sets camera config first, then executes shoot. 
    """
    opts, args, parser = parseOptions(sys.argv[1:])

    if opts.capture == "auto":
        opts.capture = auto_name_image(prefix="./images/", postfix=".arw")
   

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
        preview_number = opts.preview.split(",")
        # Single preview means do and show: 
        if len(preview_number) == 1:
            stupid_filename = "./images/preview_%s.jpg" % opts.preview
            real_filename   = "./images/thumb_preview_%s.jpg" % opts.preview
            out, err = make_preview(stupid_filename)
            if err:
                print "WARNING: Can't make new preview. Outdated image!!!"
            out, err = rsync(real_filename)
            print out
            show_image(real_filename, rotate=opts.rotate, resize=opts.resize)
        else:
            #We allow showiong more then one preview, if it's alread was taken:
            files = []
            for image in preview_number:
                files += ['images/thumb_preview_%s.jpg' % image]
            files = " ".join(files)
            show_image(files, rotate=0, resize=1)


    # Capture the image:
    if opts.capture:
        o, e = capture_and_download_to_PI(opts.capture)
        print o, e
        e, o = make_preview_from_raw(opts.capture)
        print o, e
        if opts.download:
            o, e = rsync(opts.capture)
            show_image(opts.capture)
        elif opts.upload:
            command = ["./rs", "-U", opts.capture]
            open_pipe(command, remote=RS_EXECUTE_REMOTE)
        else:
            # Download just embedded jpg from a raw footage.
            file_, ext = os.path.splitext(opts.capture)
            preview    = file_ + ".embedded" + ".jpg"
            o, e = rsync(preview)
            show_image(preview, rotate=0, resize=1)
        

    # Record video: 
    if opts.movie:
        capture_movie(opts.movie)

    if opts.panorama:
        pano_detail = compute_panorama()


    if opts.sync:
        sync_images()

    if opts.upload_file:
        upload_to_dropbox(opts.upload_file)




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
