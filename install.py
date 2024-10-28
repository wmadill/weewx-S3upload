# installer for S3 file upload extension

from setup import ExtensionInstaller

def loader():
    return S3uploadInstaller()

class S3uploadInstaller(ExtensionInstaller):
    def __init__(self):
        super(S3uploadInstaller, self).__init__(
            version="2.3",
            name='S3upload',
            description='Upload files to an S3 bucket',
            author='Bill Madill',
            author_email='wm@wmadill.com',
            config={
                'StdReport': {
                    'S3upload': {
                        'skin': 'S3upload',
                        'bucket_name': 'BUCKET_NAME',}}},
            files=[('bin/user', ['bin/user/S3upload.py']),
                   ('skins/S3upload', ['skins/S3upload/skin.conf'])],
            )
