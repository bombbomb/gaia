import shutil
import time


class VersionManager:
    def __init__(self, gaia):
        self.gaia = gaia

    def release_version(self):
        version_num = str(round(time.time()))
        print("Releasing new version: %s" % version_num)
        zip_path = self.create_version_zip(version_num)
        self.create_eb_version(version_num, zip_path)
        return version_num

    def create_version_zip(self, version_num):
        zip_path = "build/version_" + version_num
        print("Zipping " + self.gaia.config['code_path'])
        shutil.make_archive(zip_path, 'zip', self.gaia.config['code_path'])
        return zip_path + '.zip'

    def create_eb_version(self, version_num, zip_path):

        for region in self.gaia.config['regions']:
            aws_s3 = self.gaia.create_aws_client('s3', region)
            aws_eb = self.gaia.create_aws_client('elasticbeanstalk', region)
            bucket_name = "bb-gaia-versions-" + region + "-" + self.gaia.config['appName']
            try:
                aws_s3.head_bucket(Bucket=bucket_name)
                self.gaia.region_log(region, "Version bucket exists")
            except:
                location_constraint = {'LocationConstraint': region}

                if region == 'us-east-1':
                    location_constraint = None

                aws_s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration=location_constraint
                )
                self.gaia.region_log(region, "Created Version Bucket")

            self.gaia.region_log(region, "Uploading Version to S3...")
            version_key = 'version' + version_num + '.zip'
            aws_s3.upload_file(zip_path, bucket_name, version_key)

            self.gaia.region_log(region, "Creating Elastic Beanstalk Version")
            aws_eb.create_application_version(
                ApplicationName=self.gaia.config['appName'],
                VersionLabel=version_num,
                SourceBundle={
                    'S3Bucket': bucket_name,
                    'S3Key': version_key
                }
            )
