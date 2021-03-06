#!/usr/bin/python
import os, time, sys, re
from multiprocessing import Process
import threading
from optparse import OptionParser

# ENV controling our behaviour
# Do we have X forwarding?
RS_XFORWARD = os.getenv("DISPLAY", None)
if not RS_XFORWARD:
    print "Warning! No X forwarding will take place."

# Where is store images on RPi?
RS_IMAGES = os.getenv("RS_IMAGES", None)
if not RS_IMAGES:
    print "Error! Can't work without RS_IMAGES env var. Quiting now."
    sys.exit()

# CLI interface. 
def parseOptions(argv):
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)

    #Options:
    parser.add_option("-m", "--move",       dest="move",    action="store",   default=None,  help="Move head.")
    parser.add_option("-c", "--capture",    dest="capture", action="store",   default=None,  help="Capture an image")
    parser.add_option("-p", "--preview",    dest="preview", action="store",   default=None,  help="Make preview image")
    parser.add_option("-M", "--movie",      dest="movie",   action="store",   default=None,  help="Capture the movie.")
    parser.add_option("-s", "--show",       dest="show",    action="store",   default=None,  help="Show the image either by name or index.")
    parser.add_option("",   "--shutter",    dest="shutter", action="store",   default=None,  help="Sets shutter speed.")
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
    parser.add_option("-u", "--upload",     dest="upload",   action="store_true", default=None,   help="Upload the image to internet account (Dropbox). ")
        
    (opts, args) = parser.parse_args(argv)
    return opts, args, parser





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


def show_image(filename, console=False, rotate=0, resize=1.0):
    from sys import platform

    if not RS_EXECUTE_REMOTE:    
        if platform == "darwin":
            return open_pipe(['open', filename])
        elif platform == "linux2":
            if rotate != 0 or resize != 1.0:
                out, error = open_pipe(['oiiotool', filename, "--rotate", str(rotate), 
                    "--resize", "%s" % str(resize*100),  '-o', filename])
            if not console: 
                return open_pipe(['feh', filename])
            else:
                return open_pipe(['tiv', filename])
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


def make_preview_from_raw(filename):
    command = "ufraw-batch --overwrite --embedded-image \
        --out-type=jpg --shrink=2 %s" % filename
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



def auto_name_image(prefix=None, postfix=None):
    import datetime, os
    now = datetime.datetime.now().isoformat()
    folder, file_ = now.split("T")
    return os.path.join(prefix, folder, file_ + postfix)



def main():
    """ Main. Parse commnd lines, sets camera config first, then executes shoot. 
    """
    # Command line
    opts, args, parser = parseOptions(sys.argv[1:])
    # Camera setup
    

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
        preview_filename = os.path.join(RS_IMAGES, "preview_%s.jpg" % opts.preview)
        output, error    = make_preview(preview_filename)
        if error:
            print "WARNING: Can't make new preview. Outdated image!!!"
            print error
        print output

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


    # Show the image:
    if opts.show:
        if opts.show.isdigit():
            image_index = int(opts.show)
            image_filename = None
        else:
            image_index = -1
            image_filename = opts.show
        

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
