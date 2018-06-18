

class Panoramic(object):
    """ Simplifies sequential shooting. 
    """
    pano_details = {}
    def __init__(self, camera, rig, aspect_ratio=.66666666666):
        self.camera       = camera
        self.rig          = rig
        self.aspect_ratio = aspect_ratio
        self.focals       = None

    def __load_lens_calibration(self, lensfile):
        try:
            with open(lensfile) as file:
                self.focals = json.load(file)
        except:
            print "Can't open %s" % lensfile
            return False
        return True

    def __log(self, desc, value):
        pass
            
    def compute_pano_details(self, angles, images, lensfile, verbose=True):
        """ Given h/v angles and requested number of images and lens calibration
            file estimages focal length and rotor step for panorama. 
        """
        hangle, vangle   = angles
        himages, vimages = images

        if not self.__load_lens_calibration(lensfile):
            return False

        zoom_angle = self.rig.log['state']['zoom']
        h_angle    = float(hangle) / float(himages)
        zoom_level = -1

        if verbose:
            print "Requested panorama details: "
            print "\thorizontal spread: %s" % hangle
            print "\tvertical spread: %s" % v_spread
            print "\tcolumns: %s, rows: %s" % (himages, vimages)
            print "\tinitial request for focal setting: " + str(h_angle)
            print "\tlooking for options...."

        tmp = 1000000
        # Choose the closest match
        for zoom in self.focals:
            error = abs(float(self.focals[zoom]['fov']) - hangle)
            if  error < tmp:
                tmp = error
                zoom_level = zoom

        fov  = self.focals[zoom_level]['fov']
        fovv = self.focals[zoom_level]['fov'] * self.aspect_ratio
        colums = int(math.ceil(float(hangle) / (fov  / 3)))
        rows   = int(math.ceil(float(vangle) / (fovv / 3)))
        
        if verbose:
            print "\tclosest match: " + str(fov)
            print "%s wide panorama x %s: " % (hangle, fov)
            print "\tcolums %s, rows: %s (including 30 percent overlap)" % (colums, rows)

         # Compute rig movements:
        y_start_pos, x_start_pos = (-float(hangle)/2, -float(vangle)/2)
        hstep, vstep             = (fov/3, fovv/3)
        zoom_degrees             = float(zoom_level)-rig.log['state']['zoom']

        new_zoom = rig.log['state']['zoom']
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
        rig.rotate('zoom', new_zoom)
        rig.rotate('y',    details['y_start_pos'])
        rig.rotate('x',    details['x_start_pos'])
        return True


    def make_panorama(self, lebel="pano_"):
        """
        """
        from utility import mock_auto_filename
        for photo in range(self.pano_details['colums']):
            filename = mock_auto_filename(camera, appendix=lebel)
            print "Making picture: %s" % filename
            output, error = camera.capture_and_download_to_PI(filename)
            print "Moving rig for next %s" % h_move
            print "Rig Y at %s, X at %s" % (rig.log['state']['y'], rig.log['state']['x'])
            rig.rotate('y', h_move)
        