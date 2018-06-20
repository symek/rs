

RS_ROTATE_ALL=True

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
            if  error <= tmp:
                tmp = error
                zoom_level = zoom

        fov  = self.focals[zoom_level]['fov']
        fovv = self.focals[zoom_level]['fov'] * self.aspect_ratio
        colums = int(ceil(float(hangle) / (fov  * self.overlap)))
        rows   = int(ceil(float(vangle) / (fovv * self.overlap)))
        
        if verbose:
            print "\tclosest match: " + str(fov)
            print "%s wide panorama x %s: " % (hangle, fov)
            print "\tcolums %s, rows: %s (including %s overlap)" % (colums, rows, self.overlap)

         # Compute rig movements:
        hstep, vstep = (fov * self.overlap, -fovv * self.overlap)
        y_start_pos, x_start_pos = (0, 0)
        if self.pano_start_at == self.PANO_CENTER:
            y_start_pos, x_start_pos = (-float(hangle)/2, -float(vangle)/2)
        elif self.pano_start_at == self.PANO_RIGHT:
            y_start_pos, x_start_pos = (float(hangle)/2, float(vangle)/2)
            hstep, vstep             = (-fov * self.overlap, -fovv * self.overlap)

        zoom_degrees = float(zoom_level) - self.rig.log['state']['zoom']
        new_zoom = self.rig.log['state']['zoom']
        new_fov  = self.focals[str(int(new_zoom))]

        y_current_pos = self.rig.log['state']['y']
        x_current_pos = self.rig.log['state']['x']
        current_zoom  = self.rig.log['state']['zoom']

        self.pano_details = {'colums': colums, 'rows': rows, 
                            'x_start_pos': x_start_pos, 
                            'y_start_pos': y_start_pos, 
                            'zoom' : zoom_level,
                            'vstep': vstep,
                            'hstep': hstep,
                            'y_current_pos': y_current_pos,
                            'x_current_pos': x_current_pos,
                            'current_zoom':  current_zoom}

        return self.pano_details


    def move_to_start_position(self, details=None, verbose=True, rotate_all=RS_ROTATE_ALL):
        """
        """
        if not details:
            details = self.pano_details
        req_zoom = details['zoom']
        new_zoom = float(req_zoom) - self.rig.log['state']['zoom']

        if verbose:
            print "Proposed zoom setting: " + str(self.focals[req_zoom])
            print "Movig rig to: y: %s, x: %s" % (details['y_start_pos'],  details['x_start_pos'])

        if rotate_all:
            self.rig.rotate_all({'y': details['y_start_pos'], 
                                 'x': details['x_start_pos'],
                                 'zoom': new_zoom})
        else:
            self.rig.rotate('zoom', new_zoom)
            self.rig.rotate('y',    details['y_start_pos'])
            self.rig.rotate('x',    details['x_start_pos'])
        return True

    def move_back_after_pano(self, details=None, verbose=True, rotate_all=RS_ROTATE_ALL):
        """
        """
        if not details:
            detail = self.pano_details

        delta_y = self.rig.log['state']['y'] - details['y_current_pos']
        delta_x = self.rig.log['state']['x'] - details['x_current_pos']

        if verbose:
            print "Moving back to: %s, %s" % (details['y_current_pos'], details['x_current_pos']) 

        if rotate_all:
            self.rig.rotate_all({'y': delta_y, 
                                 'x': delta_x,
                                 'zoom': 0})
        else:
            self.rig.rotate('y', delta_y)
            self.rig.rotate('x', delta_x)
        return True   


    def make_panorama(self, filename, details=None, download=False, hdri=False):
        """ Perform pan capture based on previously computed details.
        """
        from os.path import splitext
        #from threading import Thread

        if not details:
            details = self.pano_details
            
        file, ext = splitext(filename)
        hstep     = details['hstep']
        vstep     = details['vstep']
        direction = 1
        rows = details['rows']
        cols = details['colums']
        worker = None
        for row in range(rows):
            for col in range(cols):
                image_number = row*details['colums']+col
                filename = file + "_part_" + str(image_number) + ext
                print "Making panorama image row:%s, col: %s(%s out of %s): %s" \
                        % (row, col, image_number, rows*cols, filename)
                output, error = self.camera.capture_image(filename, download=download, hdri=hdri)
                #if worker: 
                #    worker.join()
                #worker = Thread(target=self.camera.capture_image, args=(filename, download, hdri))
                #worker.start()
                print "Moving rig for next %s" % hstep
                print "Rig Y at %s, X at %s" % (self.rig.log['state']['y'], self.rig.log['state']['x'])
                #worker.join()
                self.rig.rotate('y', hstep*direction)
                #worker.join()
            direction *= -1
            self.rig.rotate('x', vstep)
        
