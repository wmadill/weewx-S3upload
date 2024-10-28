# weewx-S3upload
This is a weewx extension to upload web files to an AWS S3 bucket.

Rather than serving the web pages generated by weewx directly from a 
webserver running on the same system as weewx, I upload those pages 
to an AWS S3 bucket. The bucket is configured to be a static website
and is costing me around USD 0.50/month. This is cheaper than usual 
website hosting and saves me the worry of someone hacking into the
system running weewx.

This has been tested against Python 3.7/weewx 4.0.0 and Python 2.7/
weewx 3.9.2 on Debian 10.3.

## Setup

Before installing this extensions, get an S3 bucket at Amazon
https://aws.amazon.com/. Sign into the management consule, create an
account if necessary, then create an S3 bucket.

Search their help pages for how to set up the bucket as a static
website. You'll need to add a DNS record for the URL you choose for
accessing the bucket.

Install `s3cmd` from http://s3tools.org/s3cmd. Version 2 is compatible
with both Python 2 and Python 3 so will work on either weewx 3 and
weewx 4. Be careful about using the version packaged with your distro
because they are often quite old.

Clone this repo to your weewx extensions directory; for example

```
git clone git@github.com:wmadill/weewx-S3upload ~/weewx-S3upload
```

## Installation instructions

1. run the installer (using the cloned location from above)

  ```
  cd /home/weewx
  sudo bin/wee_extension --install=~/weewx-S3upload
  ```

2. modify the S3upload stanza in weewx.conf and set your S3 bucket name.

3. create .s3cfg in the weewx home directory if it doesn't already exist.
Set the "access_key" and the "secret_key" values for the IAM user that
runs s3cmd (you get these when you create the bucket at AWS). Refer to
the s3cmd man page for details. Set the file permissions to 0600 but
DO NOT CHECK THIS INTO A PUBLIC git REPOSITORY.

4. restart weewx:

  ```
  sudo systemctl restart weewx
  ```

## Manual installation instructions:

1. copy files to the weewx user directory:

  ```
  cp -rp skins/S3upload /home/weewx/skins
  cp -rp bin/user/S3upload /home/weewx/bin/user
  ```

2. add the following to weewx.conf

  ```
  [StdReport]
      ...
      [[S3upload]]
          skin = S3upload
          enable = yes
          bucket_name = 'REPLACE_WITH_YOUR_S3_BUCKET_NAME'
  ```

3. if necessary, add either or both of these to the [[S3upload]]
   stanza if they are not automatically found
   ...
      [[S3upload]]
      ...
          s3cmd_path = /full/path/to/s3cmd
          s3cfg_path = /full/path/to/.s3cfg
   ...

3. create .s3cfg as described above.

4. restart weewx

  ```
  sudo systemctl restart weewx
  ```
