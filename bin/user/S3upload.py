#
#    Copyright (c) 2015 Bill Madill <bill@jamimi.com>
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
        bucket_name = "BUCKETNAME"

In the weewx home directory, create a file named ".s3cfg" if it doesn't 
already exist and set the "access_key" and "secret_key" values for the
IAM user that runs s3cmd. Refer to the s3cmd man page for details.

Set the file permissions to 0600 but DO NOT CHECK THIS INTO a pulbic 
git repository.

********************************************************************************
"""

import errno
import glob
import os.path
import re
import subprocess
import sys
import syslog
import threading
import time
import traceback

import configobj

from weeutil.weeutil import timestamp_to_string, option_as_list

# from weewx.reportengine import ReportGenerator

# apparently not needed 3/15/19
#import weewx.manager

import weewx

# Inherit from the base class ReportGenerator
class S3uploadGenerator(weewx.reportengine.ReportGenerator):
    """Custom service to upload files to an S3 bucket"""

    def run(self):
        syslog.syslog(syslog.LOG_DEBUG, """s3uploadgenerator: start S3uploadGenerator""")

        try:
             
            # Get the options from the configuration dictionary and credential file.
            # Raise an exception if a required option is missing.
            html_root = self.config_dict['StdReport']['HTML_ROOT']
            self.local_root = os.path.join(self.config_dict['WEEWX_ROOT'], html_root) + "/"
            # May be able to pull bucket_name from .s3cfg
            # Depending on what $HOME is, put full path to .s3cfg as 'CFG_FILE'
            self.bucket_name = self.skin_dict['bucket_name']

            syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: upload configured from '%s' to '%s'" % (self.local_root, self.bucket_name)) 
            
        except KeyError, e:
            syslog.syslog(syslog.LOG_INFO, "s3uploadgenerator: no upload configured. %s" % e)
            # Bug? Does this return without running rest of the code?

        syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: uploading")

        # Launch in a separate thread so it doesn't block the main LOOP thread:
        t  = threading.Thread(target=S3uploadGenerator.uploadFiles, args=(self, ))
        t.start()
        syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: return from upload thread")

    def uploadFiles(self):
        start_ts = time.time()
        t_str = timestamp_to_string(start_ts)
        syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: start upload at %s" % t_str)

        # Build command
        cmd = ["/usr/bin/s3cmd"]
        cmd.extend(["sync"])
        cmd.extend(["--config=/home/weewx/.s3cfg"])
        cmd.extend([self.local_root])
        cmd.extend(["s3://%s" % self.bucket_name])

        syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: command: %s" % cmd)
        try:
            S3upload_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout = S3upload_cmd.communicate()[0]
            stroutput = stdout.strip()
        except OSError, e:
            if e.errno == errno.ENOENT:
                syslog.syslog(syslog.LOG_ERR, "s3uploadgenerator: s3cmd does not appear to be installed on this system. (errno %d, \"%s\")" % (e.errno, e.strerror))
            raise
        
        if weewx.debug == 1:
            syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: s3cmd output: %s" % stroutput)
            for line in iter(stroutput.splitlines()):
                syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: s3cmd output: %s" % line)

        # S3upload output. generate an appropriate message
        if stroutput.find('Done. Uploaded ') >= 0:
            file_cnt = 0
            for line in iter(stroutput.splitlines()):
                # Not sure what a specific upload failure looks like.
                # This is what s3cmd version 1.6.1 returns on successful upload.
                # Note that this is from the Debian repos and is ooolllldddd
                if line.find('upload: ') >= 0:
                    file_cnt += 1
                if line.find('Done. Uploaded ') >= 0:
                    # get number of bytes uploaded
                    m = re.search(r"Uploaded (\d*) bytes", line)
                    if m:
                        byte_cnt = int(m.group(1))
                    else:
                        byte_cnt = "Unknown"

            # format message
            try:
                if file_cnt is not None and byte_cnt is not None:
                    S3upload_message = "uploaded %d files (%s bytes) in %%0.2f seconds" % (int(file_cnt), byte_cnt)
                else:
                    S3upload_message = "executed in %0.2f seconds"
            except:
                S3upload_message = "executed in %0.2f seconds"
        else:
            # suspect we have an s3cmd error so display a message
            syslog.syslog(syslog.LOG_INFO, "s3uploadgenerator: s3cmd reported errors")
            for line in iter(stroutput.splitlines()):
                syslog.syslog(syslog.LOG_INFO, "s3uploadgenerator: s3cmd error: %s" % line)
            S3upload_message = "executed in %0.2f seconds"
        
        stop_ts = time.time()
        syslog.syslog(syslog.LOG_INFO, "s3uploadgenerator: results: "  + S3upload_message % (stop_ts - start_ts))

        t_str = timestamp_to_string(stop_ts)
        syslog.syslog(syslog.LOG_DEBUG, "s3uploadgenerator: end upload at %s" % t_str)

if __name__ == '__main__':
    """This section is used for testing the code. """
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
        print "Unable to open configuration file ", config_path
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
    
