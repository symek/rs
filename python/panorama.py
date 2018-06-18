

class Panoramic(object):
    """ Simplifies sequential shooting. 
    """
    pano_details  = {}
    PANO_CENTER   = 0
    PANO_LEFT     = 1
    PANO_RIGHT    = 2
    pano_start_at = PANO_LEFT
    def __init__(self, camera, rig, aspect_ratio=.66666666666, overlap=.333333333):
        self.camera       = camera
        self.rig          = rig
        self.aspect_ratio = aspect_ratio
        self.overlap      = overlap
        self.focals       = None

    def __load_lens_calibration(self, lensfile):
        from json import load
        try:
            with open(lensfile) as file:
                self.focals = load(file)
        except:
            print "Can't open %s" % lensfile
            return False
        return True

    def __log(self, desc, value):
        pass
            
    def compute_panorama_details(self, angles, images, lensfile, verbose=True):
        """ Given h/v angles and requested number of images and lens calibration
            file estimages focal length and rotor step for panorama. 
        """
        from math import ceil
        hangle, vangle   = angles
        himages, vimages = images

        if not self.__load_lens_calibration(lensfile):
            return False

        zoom_angle = self.rig.log['state']['zoom']
        fov        = float(hangle) / float(himages)
        zoom_level = -1

        if verbose:
            print "Requested panorama details: "
            print "\thorizontal spread: %s" % hangle
            print "\tvertical spread: %s" % vangle
            print "\tcolumns: %s, rows: %s" % (himages, vimages)
            print "\tinitial request for focal setting: " + str(fov)
            print "\tlooking for options...."

        tmp = 1000000
        # Choose the closest match
        for zoom in self.focals:
            error = abs(float(self.focals[zoom]['fov']) - fov)
            if  error < tmp:
                tmp = error
                zoom_level = zoom

        fov  = self.focals[zoom_level]['fov']
        fovv = self.focals[zoom_level]['fov'] * self.aspect_ratio
        colums = int(ceil(float(hangle) / (fov  / 3)))
        rows   = int(ceil(float(vangle) / (fovv / 3)))
        
        if verbose:
            print "\tclosest match: " + str(fov)
            print "%s wide panorama x %s: " % (hangle, fov)
            print "\tcolums %s, rows: %s (including 30 percent overlap)" % (colums, rows)

         # Compute rig movements:
        hstep, vstep = (fov/3, -fovv/3)
        y_start_pos, x_start_pos = (0, 0)
        if self.pano_start_at == self.PANO_CENTER:
            y_start_pos, x_start_pos = (-float(hangle)/2, -float(vangle)/2)
        elif self.pano_start_at == self.PANO_RIGHT:
            y_start_pos, x_start_pos = (float(hangle)/2, float(vangle)/2)
            hstep, vstep             = (-fov/3, -fovv/3)

        zoom_degrees = float(zoom_level) - self.rig.log['state']['zoom']
        new_zoom = self.rig.log['state']['zoom']
        new_fov  = self.focals[str(int(new_zoom))]

        if verbose:
            print "New lenses: " + str(new_fov)

        self.pano_details = {'colums': colums, 'rows': rows, 
                            'x_start_pos': x_start_pos, 
                            'y_start_pos': y_start_pos, 
                            'zoom' : zoom_level,
                            'vstep': vstep,
                            'hstep': hstep }

        return self.pano_details


    def set_camera_into_start_position(self, details=None):
        """
        """
        if not details:
            details = self.pano_details
        req_zoom = details['zoom']
        new_zoom = float(req_zoom) - self.rig.log['state']['zoom']
        self.rig.rotate('zoom', new_zoom)
        self.rig.rotate('y',    details['y_start_pos'])
        self.rig.rotate('x',    details['x_start_pos'])
        return True


    def make_panorama(self, filename, details=None, dowload=False):
        """ Perform pan capture based on previously computed details.
        """
        from os.path import splitext

        if not details:
            details = self.pano_details
            
        file, ext = splitext(filename)
        hstep     = details['hstep']
        vstep     = details['vstep']
        direction = 1
        for row in range(details['rows']):
            for col in range(details['colums']):
                filename = file + "_part_" + str(row*details['colums']+col) + ext
                print "Making picture: %s" % filename
                output, error = self.camera.capture_image(filename)
                print "Moving rig for next %s" % hstep
                print "Rig Y at %s, X at %s" % (self.rig.log['state']['y'], self.rig.log['state']['x'])
                self.rig.rotate('y', hstep*direction)
            direction *= -1
            self.rig.rotate('x', vstep)
        
