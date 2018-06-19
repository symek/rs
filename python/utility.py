

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
