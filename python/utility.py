

def mock_auto_filename(camera, prefix, appendix,  postfix=None):
    """ Creates filename from date and time. 
    """
    def auto_name_image(prefix, postfix, appendix=""):
        import datetime, os
        now = datetime.datetime.now().replace(microsecond=0).isoformat()
        folder, file_ = now.split("T")
        file_ = file_.replace(":", "_")
        return os.path.join(prefix, folder, appendix+file_ + postfix)

    if not postfix:
        postfix = '.jpg'
        current_quality = camera.get_current_config('imagequality')
        if current_quality in ('3', '4', '5', '6', 'RAW', "RAW+JPEG"):
            postfix = '.arw'

    return auto_name_image(prefix=prefix, appendix=appendix, postfix=postfix)


def easeInOutQuad(t):
    """"""
    if t<.5:
        return 2.0*t*t
    else:
        return -1.0+(4.0-2.0*t)*t

def easeInOutCubic(t):
    """"""
    if t<.5:
        return 4*t*t*t
    else:
        return (t-1.0)*(2.0*t-2.0)*(2.0*t-2.0)+1.0

def easeInOutSine(t,b,c,d):
    """"""
    from math import cos, pi
    return -c/2.0 * (cos(pi* t/d) -1.0)+b
