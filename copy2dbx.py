#!/usr/bin/python

import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
import sys, os

dbx_token = os.getenv("RS_DROPBOX_ACCESS_TOKEN", None)

if not dbx_token:
    try:
        with open("./scripts/.dbxkey") as key:
            lines = key.readlines()
            for line in lines:
                if line.startswith("RS_DROPBOX_ACCESS_TOKEN"):
                    dbx_token = line.split("=")[-1].strip()
    except err:
        print err
        print "Can't authorize the access to Dropbox."
        sys.exit()

def upload_files(filenames):
    result = []
    for file in filenames:
        err = upload_to_dropbox(file)
        result += [(file, err)]
        print "File: " + file + " ? " + str(err)
    return result

def upload_to_dropbox(filename):
    """"""
    import os.path
    if filename.startswith("./"):
        filename = filename[2:]

    absfilename = os.path.join("/", filename)

    dbx = dropbox.Dropbox(dbx_token)

    with open(filename, 'rb') as file:
        try:
            dbx.files_upload(file.read(), absfilename, mode=WriteMode('overwrite'))
        except ApiError as err:
            if err.user_message_text:
                print err.user_message_text
            print err
            return False
            
    return True


def main():
    if len(sys.argv) < 2:
        return 1

    filenames = sys.argv[1:]
    result = upload_files(filenames)

if __name__ == "__main__": main()
