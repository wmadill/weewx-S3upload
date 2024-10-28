# Change Log

## v2.3 = 28 October 2024
- Ensure that s3cmd_path, if specified, exists
- Add support for s3cfg path

## v2.2 - 12 October 2024
Released to newly built weewx
- Add config option for s3cmd path, clean up bucket name config
- Removed threading since not needed
- Cleaned up logging s3cmd output
- Add search list extension for "version"

## v2.1 - 19 May 2020
Now work on Python 2.7/weewx 3.9.2 and Python 3.7.3/weewx 4.0.0
on Debian 10.3
- Fixed errors running on Python 2.7
- Tested on both environments

## v2.0 - 15 May 2020
Python3/weewx 4 initial release - NOT TESTED against weewx 3
- Convert to python3
- Convert to use new weewx logging but maintain backwards
  compatibility

## v1.3 - 15 May 2020
Final Python2/weewx 3 version - CAUTION this version is not yet tested
- Update install script and README - Fixes #2 and #3
- Remove irrelevant comments
- Dynamically get path to "s3cmd" - Fixes #r

## v1.2 - 28 March 2019
- Remove AWS credentials from weewx.conf stanza in favor of .s3cfg file

## v1.1 - 12 May 2015
- Fix typo preventing processing of s3cmd output
- Add formatting of s3cmd errors

## v1.0 - 2 May 2015
- Fix generator name in skin.conf which was missed in earlier
extension renaming.
- Fix log message in generator; same missed renaming
- Tested against weewx 3.1.0
- Minor update to README.md

## v0.1 - 29 April 2015
- Initial upload.  This one is not ready for prime time.
