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
        access_key = "PARM1"
        secret_token = "PARM2"
        bucket_name = "BUCKETNAME"

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
import weewx.manager

# Inherit from the base class ReportGenerator
class S3uploadGenerator(weewx.reportengine.ReportGenerator):
    """Custom service to upload files to an S3 bucket"""

    def run(self):
        syslog.syslog(syslog.LOG_INFO, """reportengine: S3uploadGenerator""")

        try:
            # Get the options from the configuration dictionary.
            # Raise an exception if a required option is missing.
            html_root = self.config_dict['StdReport']['HTML_ROOT']
            self.local_root = os.path.join(self.config_dict['WEEWX_ROOT'], html_root) + "/"
            self.access_key = self.skin_dict['access_key']
            self.secret_token = self.skin_dict['secret_token']
            self.bucket_name = self.skin_dict['bucket_name']

            syslog.syslog(syslog.LOG_INFO, "S3upload: upload configured from '%s' to '%s'" % (self.local_root, self.bucket_name)) 
            
        except KeyError, e:
            syslog.syslog(syslog.LOG_INFO, "S3upload: no upload configured. %s" % e)

        syslog.syslog(syslog.LOG_DEBUG, "S3upload: uploading")

        # Launch in a separate thread so it doesn't block the main LOOP thread:
        t  = threading.Thread(target=S3uploadGenerator.uploadFiles, args=(self, ))
        t.start()
        syslog.syslog(syslog.LOG_DEBUG, "S3upload: return from upload thread")

    def uploadFiles(self):
        start_ts = time.time()
        t_str = timestamp_to_string(start_ts)
        syslog.syslog(syslog.LOG_INFO, "S3upload: start upload at %s" % t_str)

        # Build command
        cmd = ["/usr/local/bin/s3cmd"]
        cmd.extend(["sync"])
        cmd.extend(["--access_key=%s" % self.access_key])
        cmd.extend(["--secret_key=%s" % self.secret_token])
        cmd.extend([self.local_root])
        cmd.extend(["s3://%s" % self.bucket_name])

        syslog.syslog(syslog.LOG_DEBUG, "S3upload command: %s" % cmd)
        try:
            S3upload_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            stdout = S3upload_cmd.communicate()[0]
            stroutput = stdout.strip()
        except OSError, e:
            if e.errno == errno.ENOENT:
                syslog.syslog(syslog.LOG_ERR, "S3upload: s3cmd does not appear to be installed on this system. (errno %d, \"%s\")" % (e.errno, e.strerror))
            raise
        
        if weewx.debug == 1:
            syslog.syslog(syslog.LOG_DEBUG, "S3upload: s3cmd output: %s" % stroutput)
            for line in iter(stroutput.splitlines()):
                syslog.syslog(syslog.LOG_DEBUG, "S3upload: s3cmd output: %s" % line)

        # S3upload output. generate an appropriate message
        if stroutput.find('Done. Uploaded ') >= 0:
            file_cnt = 0
            for line in iter(stroutput.splitlines()):
                if line.find('File ') >= 0:
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
            syslog.syslog(syslog.LOG_INFO, "S3upload: s3cmd reported errors")
            for line in iter(stroutput.splitlines()):
                syslog.syslog(syslog.LOG_INFO, "S3upload: s3cmd error: %s" % line)
            S3upload_message = "executed in %0.2f seconds"
        
        stop_ts = time.time()
        syslog.syslog(syslog.LOG_INFO, "S3upload: "  + S3upload_message % (stop_ts - start_ts))

        t_str = timestamp_to_string(stop_ts)
        syslog.syslog(syslog.LOG_INFO, "S3upload: end upload at %s" % t_str)

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
    
