# installer for S3 file upload extension

from setup import ExtensionInstaller

def loader():
    return S3uploadInstaller()

class S3uploadInstaller(ExtensionInstaller):
    def __init__(self):
        super(S3uploadInstaller, self).__init__(
            version="0.1",
            name='S3upload',
            description='Upload files to an S3 bucket',
            author='Bill Madill',
            author_email='bill@jamimi.com',
            config={
                'StdReport': {
                    'S3upload': {
                        'skin': 'S3upload',
                        'access_key': 'REPLACE_WITH_YOUR_S3_ACCESS_KEY',
                        'secrect_token': 'REPLACE_WITH_YOUR_SECRET_TOKEN',
                        'bucket_name': 'REPLACE_WITH_YOUR_S3_BUCKET_NAME',}}},
            files=[('bin/user', ['bin/user/S3upload.py']),
                   ('skins/S3upload', ['skins/S3upload/skin.conf'])],
            )
