#
#    Copyright (c) 2015-2020 Bill Madill <wm@wmadill.com>
#    Derivative of extensions/alarm.py, credit to Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Upload the generated HTML files to an S3 bucket

********************************************************************************

To use this uploader, add the following to your configuration file in the
[StdReport] section:

    [[S3upload]]
        skin = S3upload
        bucket_name = "BUCKET_NAME"
        s3cmd_path = /full/path/to/s3cmd

In the weewx home directory, create a file named ".s3cfg" if it doesn't 
already exist and set the "access_key" and "secret_key" values for the
IAM user that runs s3cmd. Refer to the s3cmd man page for details.

Set the ".s3cfg" file permissions to 0600 but DO NOT CHECK IT INTO a pulbic 
git repository.

********************************************************************************
"""

import errno
import glob
import os.path
import re
import subprocess
import sys
import threading
import time
import traceback
import configobj

from weeutil.weeutil import timestamp_to_string, option_as_list
import weewx

MSG_BASE = "s3uploadgenerator: "

# Inherit from the base class ReportGenerator
class S3uploadGenerator(weewx.reportengine.ReportGenerator):
    """Custom service to upload files to an S3 bucket"""

    # Set up logging for both weewx 3 and weewx 4 from tkeffer's blog
    # post.
    try:
        # Test for new-style weewx logging by trying to import weeutil.logger
        import weeutil.logger
        import logging
        log = logging.getLogger(__name__)

        def logdbg(self, msg):
            self.log.debug(MSG_BASE + msg)
        
        def loginf(self, msg):
            self.log.info(MSG_BASE + msg)
        
        def logerr(self, msg):
            self.log.error(MSG_BASE + msg)
        
    except ImportError:
        # Old-style weewx logging
        import syslog

        def logmsg(self, level, msg):
            self.syslog.syslog(level, MSG_BASE + "%s:" % msg)
        
        def logdbg(self, msg):
            self.logmsg(self.syslog.LOG_DEBUG, msg)

        def loginf(self, msg):
            self.logmsg(self.syslog.LOG_INFO, msg)

        def logerr(self, msg):
            self.logmsg(self.syslog.LOG_ERR, msg)

    def run(self):
        self.logdbg("start S3uploadGenerator")
        self.logdbg("python version: "  + sys.version)

        # Get the options from the configuration dictionary and credential file.
        # Raise an exception if a required option is missing.
        html_root = self.config_dict['StdReport']['HTML_ROOT']
        self.local_root = os.path.join(self.config_dict['WEEWX_ROOT'], html_root) + "/"
        try:
            self.bucket_name = self.skin_dict['bucket_name']
        except KeyError as e:
            self.logerr("required %s not set." % e)
            return

        # validate that bucket_name is set to something other than
        # blank or the default
        if self.bucket_name is None or self.bucket_name.startswith('BUCKET_'):
            self.logerr("bucket name not set")
            return

        self.logdbg("upload configured from '%s' to '%s'" % (self.local_root, self.bucket_name)) 
            
        
        # Get full path to "s3cmd"; exit if not installed
        # use 's3cmd_path' from configuration dictionary if set
        self.s3cmd_path = None
        try:
            self.s3cmd_path = self.skin_dict['s3cmd_path']
        except KeyError as e:
            self.logdbg("s3cmd_path not set")
        
        # Full path to "s3cmd" not set; try to find it
        if self.s3cmd_path is None:
            path_proc = subprocess.Popen(["which", "s3cmd"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.s3cmd_path = path_proc.communicate()[0].decode().strip()
            # 'which' returns an empty string if "s3cmd" not in $PATH
            if self.s3cmd_path == '':
                self.logerr("'s3cmd' cannot be found")
                return

        # Validate that the file is executble
        if not os.access(self.s3cmd_path, os.X_OK):
            self.logerr("%s is not an executable file" % self.s3cmd_path)
            return

        self.logdbg("s3cmd location: "  + self.s3cmd_path)
        self.logdbg("uploading")

        # Launch in a separate thread so it doesn't block the main LOOP thread:
        t  = threading.Thread(target=self.uploadFiles)
        t.start()

    # The thread that does all the work
    def uploadFiles(self):
        start_ts = time.time()
        t_str = timestamp_to_string(start_ts)
        self.logdbg("start upload at %s" % t_str)

        # Build s3cmd command string
        cmd = [self.s3cmd_path]
        cmd.extend(["sync"])
        ##FIXME need to find correct directory
        cmd.extend(["--config=/home/weewx/.s3cfg"])
        cmd.extend([self.local_root])
        cmd.extend(["s3://%s" % self.bucket_name])
        # Hopefully css files get set correctly
        ##FIXME remove comment when below is tested
        cmd.extend(["--guess-mime-type"])
        cmd.extend(["--no-mime-magic"])

        self.logdbg("command: %s" % cmd)
        try:
            S3upload_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout = S3upload_cmd.communicate()[0]
            stroutput = stdout.strip()
        except OSError as e:
            if e.errno == errno.ENOENT:
                self.logerr("s3cmd not installed at %s. (errno %d, \"%s\")" % (self.s3cmd_path, e.errno, e.strerror))
            raise
        
        stop_ts = time.time()
        time_msg = "executed in %0.2f seconds" % (stop_ts - start_ts)
        upload_msg = self.parseoutput(stroutput)
        if upload_msg == "":
            self.loginf(time_msg)
        else:
            self.loginf(upload_msg + "; " + time_msg)

        t_str = timestamp_to_string(stop_ts)
        self.logdbg("end upload at %s" % t_str)
    # Parse s3cmd output, generate, and return an appropriate message.
    # This output parsing routine is based on what s3cmd 1.6.1 returned
    # with various tests. While the output returned from a successful
    # upload is tested, I could not provoke any upload errors so
    # they are just returned as is.
    # Also tested with s3cmd version 2.4.
    def parseoutput(self, stroutput):
        self.logdbg("s3cmd full output: %s" % stroutput)

        # If only an empty string returned, there was nothing to upload
        if stroutput == b'':
            return "no changes to upload"

        line_num = 0
        for line in iter(stroutput.splitlines()):
            line_num += 1
            self.logdbg("s3cmd line %s: %s" % (line_num, line))

        if stroutput.find(b'Done. Uploaded ') < 0:
            # suspect we have an s3cmd error so display a message
            self.loginf("s3cmd reported errors")
            line_num = 0
            for line in iter(stroutput.splitlines()):
                line_num += 1
                self.loginf("s3cmd line %s: %s" % (line_num, line))
            return ""

        file_cnt = 0
        for line in iter(stroutput.splitlines()):
            if line.find(b'upload: ') >= 0:
                file_cnt += 1
            if line.find(b'Done. Uploaded ') >= 0:
                # get number of bytes uploaded
                m = re.search(r"Uploaded (\d*) bytes", str(line))
                if m:
                    byte_msg = "(%d bytes)" % int(m.group(1))
                else:
                    byte_msg = "Unknown number of bytes"

        return "uploaded %d files " % file_cnt + byte_msg

if __name__ == '__main__':
    """This section is used for testing the code. """
    exit(0)
    # Note that this fails!
    import sys
    import configobj
    from optparse import OptionParser


    usage_string ="""Usage: 
    
    S3upload.py config_path 
    
    Arguments:
    
      config_path: Path to weewx.conf"""

    parser = OptionParser(usage=usage_string)
    (options, args) = parser.parse_args()
    
    if len(args) < 1:
        sys.stderr.write("Missing argument(s).\n")
        sys.stderr.write(parser.parse_args(["--help"]))
        exit()
        
    config_path = args[0]
    
    weewx.debug = 1
    
    try :
        config_dict = configobj.ConfigObj(config_path, file_error=True)
    except IOError:
        print ("Unable to open configuration file ", config_path)
        exit()
        
    if 'S3upload' not in config_dict:
        print >>sys.stderr, "No [S3upload] section in the configuration file %s" % config_path
        exit(1)
    
    engine = None
    S3upload = uploadFiles(engine, config_dict)
    
    rec = {'extraTemp1': 1.0,
           'outTemp'   : 38.2,
           'dateTime'  : int(time.time())}

    event = weewx.Event(weewx.NEW_ARCHIVE_RECORD, record=rec)
    S3upload.newArchiveRecord(event)
    
