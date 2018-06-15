
from utils import Executor

class Camera(object):
    GPHOTO_MAKE_PREVIEW = "gphoto2 --show-preview --force-overwrite --filename %s"
    GPHOTO_CAPTURE_DOWN = "gphoto2 --capture-image-and-download --force-overwrite --filename %s"
    GPHOTO_SET_ISO      = "gphoto2 --set-config iso=%s"
    GPHOTO_SET_FSTOPS   = "gphoto2 --set-config f-number=%s"
    GPHOTO_SET_SHUTTER  = "gphoto2 --set-config shutterspeed=%s"
    GPHOTO_SET_CONFIG   = "gphoto2 --set-config %s=%s"
    GPHOTO_CAPTURE_MOVIE = "gphoto2 --set-config movie=1 --wait-event=%ss --set-config movie=0"
    executor = Executor()

    def make_preview(self, filename):
        command = self.GPHOTO_MAKE_PREVIEW % filename
        command = command.split()
        out, err = self.executor.open_pipe(command)
        return out, err

    def list_config(self, item=None):
        config, err = self.executor.open_pipe(['gphoto2', '--list-config'])
        if err: 
            print err
            return   False
        config = config.split()
        for item in config:
            command = ['gphoto2', '--get-config=%s' % item]
            out, err = self.executor.open_pipe(command)
            print out

    def set_config(self, config, value):
        command = self.GPHOTO_SET_CONFIG % (config, str(value))
        command = command.split()
        o, e = self.executor.open_pipe(command)
        return o, e

    def get_config(self, config):
        command = "gphoto2 --get-config %s" % config
        command = command.split()
        return self.executor.open_pipe(command)

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


    def capture_and_download_to_PI(self, filename):
        """ Capture and download photo.
        """
        command = self.GPHOTO_CAPTURE_DOWN % filename
        command = command.split()
        return self.executor.open_pipe(command)
        

    def capture_movie(self, time=10):
        """ Capture 'time' length video.
            Note: Unlike photos, movie file will remain on camera.
        """
        command = self.GPHOTO_CAPTURE_MOVIE % str(time)
        command = command.split()
        return self.executor.open_pipe(command)

    def get_current(self,config):
        # print config.split()
        config = [line.split(":") for line in config.split("\n")]
        # print config
        for line in config:
            if line[0] == "Current":
                return line[1].strip()



