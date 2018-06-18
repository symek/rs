
from shell import ShellCommander



class ImageQualityEnum(dict):
    def __init__(self):
        # Note strings all together
         self['Standard']   = '0'
         self["Fine"]       = '1'
         self['Extra Fine'] = '2'
         self['RAW']        = '3'
         self['RAW+JPEG']   = '4'
         self['Unknown value 0014']= '5'
         self['Unknown value 0012']= '6'


class ConfigEnum(dict):
    def __init__(self):
        self['imagequality'] = ImageQualityEnum()


class NonLegalConfigValue(Exception):
    """ This is raised if config has an enumaration class 
    (like one above), and value set by user is not there.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class Camera(object):
    GPHOTO_MAKE_PREVIEW = "gphoto2 --show-preview --force-overwrite --filename %s"
    GPHOTO_CAPTURE_DOWN = "gphoto2 --capture-image-and-download --force-overwrite --filename %s"
    GPHOTO_CAPTURE      = "gphoto2 --trigger-capture "
    GPHOTO_SET_ISO      = "gphoto2 --set-config iso=%s"
    GPHOTO_SET_FSTOPS   = "gphoto2 --set-config f-number=%s"
    GPHOTO_SET_SHUTTER  = "gphoto2 --set-config shutterspeed=%s"
    GPHOTO_SET_CONFIG   = "gphoto2 --set-config %s=%s"
    GPHOTO_CAPTURE_MOVIE = "gphoto2 --set-config movie=1 --wait-event=%ss --set-config movie=0"
    commander   = ShellCommander()
    config_enum = ConfigEnum()

    def make_preview(self, filename):
        command = self.GPHOTO_MAKE_PREVIEW % filename
        command = command.split()
        out, err = self.commander.open_pipe(command)
        return out, err

    def list_config(self, item=None):
        config, err = self.commander.open_pipe(['gphoto2', '--list-config'])
        if err: 
            print err
            return   False
        config = config.split()
        for item in config:
            command = ['gphoto2', '--get-config=%s' % item]
            out, err = self.commander.open_pipe(command)
            print out

    def set_config(self, config, value):
        """ Sets camera config to a new value. 
            If enumaration of legal value are present,
            it disallow setting anything not present there.
        """
        if config in self.config_enum.keys():
            if value not in self.config_enum[config].values() \
                and value not in self.config_enum[config].keys():
                raise NonLegalConfigValue("%s not present in enum." % value) 

        command = self.GPHOTO_SET_CONFIG % (config, str(value))
        command = command.split()
        o, e = self.commander.open_pipe(command)
        return o, e

    def get_config(self, config):
        command = "gphoto2 --get-config %s" % config
        command = command.split()
        return self.commander.open_pipe(command)

    def set_autofocus(self, autofocus):
        """ Set autofocus: True / False
        """
        return set_config('autofocus', autofocus)

    def set_iso(self, iso):
        """ Set ISO: (SLog3 needs above 350)
        """
        return self.set_config('iso', iso)

    def set_shutter(self, shutterspeed):
        return self.set_config("shutterspeed", shutterspeed)

    def set_fstop(self, fstop):
        return self.set_config("f-number", str(fstop))

    def set_exposure_compensation(self, exposure):
        return self.set_config("exposurecompensation", exposure)

    def capture_and_download_to_PI(self, filename):
        """ Capture and download photo.
        """
        command = self.GPHOTO_CAPTURE_DOWN % filename
        command = command.split()
        return self.commander.open_pipe(command)

    def capture_and_leave_on_device(self, filename):
        """ Capture photo but leave it on a device. 
        """
        command = self.GPHOTO_CAPTURE
        command = command.split()
        return self.commander.open_pipe(command)

    def capture_image(self, filename, download=False):
        """ Switcher to select between two policies.
        """
        if not download:
            return self.capture_and_leave_on_device(filename)
        else:
            return self.capture_and_download_to_PI(filename)
        
    def capture_movie(self, time=10):
        """ Capture 'time' length video.
            Note: Unlike photos, movie file will remain on camera.
        """
        command = self.GPHOTO_CAPTURE_MOVIE % str(time)
        command = command.split()
        return self.commander.open_pipe(command)

    def get_current_config(self, config):
        """Parses current value of confing as returne by gphoto2
           from camera.
        """
        command = ['gphoto2', '--get-config', config]
        output, error =  self.commander.open_pipe(command)
        if error:
            print error
            return False
        for line in output.split("\n"):
            if line.startswith("Current:"):
                return line.split(":")[-1].strip()
        return False


class Lens(object):
    """ Minimal lens class. 
    """
    max_focal_length = 28
    min_focal_length = 70
    angular_length   = 36
    length_table     = {}

    def __init__(self, max_focal_length=None, min_focal_length=None):
        if max:
            self.maxfocallenth = max_focal_length
        if min:
            self.maxfocallenth = min_focal_length

