import os

RS_REMOTE=None

try:
    import rpyc
    RS_REMOTE    = os.getenv("RS_REMOTE",    None)
    RS_USERNAME  = os.getenv("RS_USER_NAME", None)
    RPYC_PORT    = os.getenv("RPYC",         55653)
    print "RS_REMOTE: " + RS_REMOTE
    print "User: " + RS_USER_NAME
    print "port: " + str(RPYC_PORT) 
except:
    print "Can't import rpyc. No remote execution will take place."


RS_DROPBOX_AVAIABLE = False

try:
    import dropbox
    from dropbox.files import WriteMode
    from dropbox.exceptions import ApiError, AuthError
    RS_DROPBOX_AVAIABLE = True
except:
    pass


class Executor(object):
    def open_pipe_rpyc(shell, command, verbose=True):
        """RPyc take on remote execution.
        """
        assert 'rpyc' in globals()
        r_command = " ".join(command)
        connection = rpyc.classic.connect(RS_REMOTE, port=RPYC_PORT)
        return connection.modules.os.system(r_command)

    def open_pipe_remote(self, command, verbose=True):
        """ Testing different approaches.
        """
        # return open_pipe_ssh(command, verbose)
        # return open_pipe_paramiko(command, verbose)
        code = open_pipe_rpyc(command, verbose)
        return str(code), None

    def rsync(self, filename):
        """Use rsync to retrive file from remote host.
        """
        command =["rsync", "-va", "--progress", "%s@%s:~/sony7iii/%s" \
            % (RS_USER_NAME, RS_REMOTE, filename), filename] 

        return open_pipe(command, remote=False)


    def open_pipe(self, command, verbose=True, remote=RS_REMOTE):
        """ Executes command in subshell. 
            Command: list of words in shell command. 
        """
        from subprocess import Popen, PIPE 
        exec_mode = " (localy)"
        if remote:
            exec_mode = " (remotely: %s)" % str(RS_REMOTE)
        if verbose:
            print "Command: ", 
            print " ".join(command) + exec_mode

        if remote:
            return self.open_pipe_remote(command, verbose)

        o, e =  Popen(command, stdout=PIPE, stderr=PIPE, 
                    universal_newlines=True).communicate()

        if o: print o
        if e: print e
        return o, e


# Class handing ssh connection with paramiko
# Not in use atm.
class SSHClient:
    """Sends a single command to the remote host.
       Looks for ssh keys. 
    """
    client = None
    
    def __init__(self, address, username, password):
        import paramiko
        print("Connecting to server.")
        self.client = paramiko.client.SSHClient()
        self.address = address
        self.username = username
        self.password = password
        self.client.set_missing_host_key_policy(client.AutoAddPolicy())
        self.client.connect(address, username=username, password=password, look_for_keys=True)

    def __del__(self):
        self.client.close()

 
    def send_command(self, command):
        """Sends command without running shell."""
        if(self.client):
            stdin, stdout, stderr = self.client.exec_command(command)
            while not stdout.channel.exit_status_ready():
                # Print data when available
                if stdout.channel.recv_ready():
                    stdout_data = stdout.channel.recv(1024)
                    stderr_data = stderr.channel.recv(2014)
                    prev_stdout_data = b"1"
                    prev_stderr_data = b"1"
                    while prev_stdout_data:
                        prev_stdout_data = stdout.channel.recv(1024)
                        stdout_data += prev_stdout_data
                    while prev_stderr_data:
                        prev_stderr_data = stderr.channel.recv(1024)
                        stderr_data += prev_stderr_data
                    return stdout_data, stderr_data
        else:
             print("Connection not opened: %s, %s, %s" % (self.address, self.username, self.password))
        return None, None


def upload_to_dropbox(filename):
    """Upload file to the dropbox using access token.
    """
    import os.path

    if filename.startswith("./"):
        filename = filename[2:]

    absfilename = os.path.join("/", filename)

    dbx = dropbox.Dropbox(RS_DROPBOX_ACCESS_TOKEN)
    with open(filename, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        print("Uploading " + filename  + " to Dropbox as " + filename + "...")
        try:
            dbx.files_upload(f.read(), absfilename, mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().reason.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                return None
            else:
                print(err)
                return None

    return True


def open_pipe_ssh(command, verbose=True):
    """ Executes command in ssh. 
        Command: list of words in shell command.
    """
    import subprocess
    HOST = RS_REMOTE_HOST
    COMMAND = " ".join(command)
    ssh = subprocess.Popen(["ssh", "-t", "-t", "%s" % HOST, COMMAND],
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    error  = ssh.stderr.readlines()
    return result, error

def open_pipe_paramiko(command, verbose=True):
    """ Executes command remotly via paramiko 
        Command: list of words in shell command.
    """
    if not RS_EXECUTE_REMOTE:
        print "This shouldn't be called at all (not paramiko or remote model not allowed)."
        return None, None

    client = SSHClient(RS_REMOTE_HOST, RS_USER_NAME, "")
    ssh_command = " ".join(command)
    print "Sends %s to %s as %s" % (ssh_command, RS_REMOTE_HOST, RS_USER_NAME)
    result, error = client.send_command(ssh_command)
    return result, error