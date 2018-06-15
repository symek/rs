import os

RS_REMOTE=None

try:
    import rpyc
    RS_REMOTE = os.getenv("RS_REMOTE", None)
    RS_USER   = os.getenv("RS_USER", None)
    RPYC_PORT = os.getenv("RPYC_PORT", None)
except:
    pass

class Executor(object):
    def open_pipe_rpyc(command, verbose=True):
        """RPyc take on remote execution.
        """
        assert 'rpyc' in globals()
        r_command = " ".join(command)
        connection = rpyc.classic.connect(RS_REMOTE, port=RPYC_PORT)
        return connection.modules.os.system(r_command)

    def open_pipe_remote(command, verbose=True):
        """ Testing different approaches.
        """
        # return open_pipe_ssh(command, verbose)
        # return open_pipe_paramiko(command, verbose)
        code = open_pipe_rpyc(command, verbose)
        return str(code), None

    def rsync(filename):
        """Use rsync to retrive file from remote host.
        """
        command =["rsync", "-va", "--progress", "%s@%s:~/sony7iii/%s" \
            % (RS_USER_NAME, RS_REMOTE_HOST, filename), filename] 

        return open_pipe(command, remote=False)


    def open_pipe(command, verbose=True, remote=RS_REMOTE):
        """ Executes command in subshell. 
            Command: list of words in shell command. 
        """
        from subprocess import Popen, PIPE 
        exec_mode = " (localy)"
        if remote:
            exec_mode = " (remotely: %s)" % RS_REMOTE_HOST
        if verbose:
            print "Command: ", 
            print " ".join(command) + exec_mode

        if remote:
            return open_pipe_remote(command, verbose)

        o, e =  Popen(command, shell=False, 
                    stdout=PIPE, stderr=PIPE, 
                    universal_newlines=True).communicate()

        if o: print o
        if e: print e
        return o, e