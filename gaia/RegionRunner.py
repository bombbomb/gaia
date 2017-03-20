import threading
import boto3


class RegionRunner(threading.Thread):
    def __init__(self, region, config, aws_config):
        threading.Thread.__init__(self)
        self.region = region
        self.config = config
        self.aws_config = aws_config

        self.aws_eb = self.aws_client('elasticbeanstalk')
        self.aws_s3 = self.aws_client('s3')
        self.aws_iam = self.aws_client('iam')

    def run(self):
        self.log("Started")
        self.configure_elastic_beanstalk()

    def configure_elastic_beanstalk(self):
        self.log("Configuring Elastic Beanstalk")
        apps = self.aws_eb.describe_applications(
            ApplicationNames=[
                self.config['appName'],
            ]
        )

        self.log(apps)

        if len(apps['Applications']) == 0:
            self.create_eb_app()
        else:
            self.log("EB Application exists")

        self.create_eb_version()
        self.create_eb_environment()

    def log(self, msg):
        print("Region: " + self.region + ": ",  msg)

    def create_eb_app(self):
        self.log("Creating Elastic Beanstalk App")
        self.aws_eb.create_application(
            ApplicationName=self.config['appName']
        )

    def aws_client(self, client_name):
        return boto3.client(client_name,
                          aws_access_key_id=self.aws_config['key'],
                          aws_secret_access_key=self.aws_config['secret'],
                          region_name=self.region)

    def create_eb_version(self):
        bucket_name = "bb-gaia-versions-" + self.region + "-" + self.config['appName']
        try:
            self.aws_s3.head_bucket(Bucket=bucket_name)
            self.log("Version bucket exists")
        except:
            location_contraint = {'LocationConstraint': self.region}

            if self.region == 'us-east-1':
                location_contraint = None

            self.aws_s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration=location_contraint
            )
            self.log("Created Version Bucket")

        self.log("Uploading Version to S3...")
        version_key = 'version' + self.config['version_num'] + '.zip'
        self.aws_s3.upload_file(
            self.config['zip_path'],
            bucket_name,
            version_key
        )

        self.log("Creating Elastic Beanstalk Version")
        self.aws_eb.create_application_version(
            ApplicationName=self.config['appName'],
            VersionLabel=self.config['version_num'],
            SourceBundle={
                'S3Bucket': bucket_name,
                'S3Key': version_key
            }
        )
        pass

    def create_eb_environment(self):
        self.log("Creating Elastic Beanstalk Environment")
        version_num = 'version' + self.config['version_num']

        option_settings = self.config['elasticBeanstalk']['optionSettings']
        option_settings.append({
            'Namespace': 'aws:autoscaling:launchconfiguration',
            'OptionName': 'IamInstanceProfile',
            'Value': self.config['instance_profile']
        })

        response = self.aws_eb.create_environment(
            ApplicationName=self.config['appName'],
            EnvironmentName=version_num,
            CNAMEPrefix=self.config['appName'] + '-' + version_num,
            VersionLabel=self.config['version_num'],
            SolutionStackName=self.config['elasticBeanstalk']['solutionStack'],
            OptionSettings=option_settings
        )
        self.log(response)

        # poll for environment to go green
