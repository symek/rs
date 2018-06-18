


def mock_auto_filename(camera, appendix=None):
    """ Creates filename from date and time. 
    """
    def auto_name_image(prefix=None, appendix=None, postfix=None):
        import datetime, os
        now = datetime.datetime.now().replace(microsecond=0).isoformat()
        folder, file_ = now.split("T")
        file_ = file_.replace(":", "_")
        return os.path.join(prefix, folder, appendix+file_ + postfix)

    extension = '.jpg'
    current_quality = camera.get_current_config('imagequality')
    if current_quality in ('3', '4', '5', '6', 'RAW', "RAW+JPEG"):
        extension = '.arw'

    return auto_name_image(prefix=RS_IMAGES, appendix=appendix,  postfix=extension)

