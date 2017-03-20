import json
import time
import shutil
import boto3
import sys

from gaia.DNSManager import DNSManager
from gaia.RegionRunner import RegionRunner

print("Welcome to Gaia")

args = sys.argv

if len(args) == 1:
    print("You must pass in a path")
    exit()

code_path = args[1]

with open(code_path + '/gaia.json') as json_data:
    gaia_config = json.load(json_data)
    print(gaia_config)

with open('aws.json') as json_data:
    aws_config = json.load(json_data)
    print("Got AWS creds")


def create_version_zip():
    gaia_config['version_num'] = str(round(time.time()))
    gaia_config['zip_path'] = "build/version_" + gaia_config['version_num']
    print("Zipping " + code_path)
    shutil.make_archive(gaia_config['zip_path'], 'zip', code_path)
    path_ = gaia_config['zip_path']
    gaia_config['zip_path'] = path_ + '.zip'


def get_iam_policy_doc():
    return """{
"Version": "2012-10-17",
"Statement": [
{
  "Sid": "BucketAccess",
  "Action": [
    "s3:Get*",
    "s3:List*",
    "s3:PutObject"
  ],
  "Effect": "Allow",
  "Resource": [
    "arn:aws:s3:::elasticbeanstalk-*",
    "arn:aws:s3:::elasticbeanstalk-*/*"
  ]
},
{
  "Sid": "XRayAccess",
  "Action":[
    "xray:PutTraceSegments",
    "xray:PutTelemetryRecords"
  ],
  "Effect": "Allow",
  "Resource": "*"
},
{
  "Sid": "CloudWatchLogsAccess",
  "Action": [
    "logs:PutLogEvents",
    "logs:CreateLogStream"
  ],
  "Effect": "Allow",
  "Resource": [
    "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*"
  ]
}
]
}"""


def create_iam_assets():
    # create policy
    iam = boto3.client('iam',
                          aws_access_key_id=aws_config['key'],
                          aws_secret_access_key=aws_config['secret'])

    policy_name = "GaiaAppPolicy-" + gaia_config['appName']
    path_prefix = '/GaiaApp/'
    policy_list_response = iam.list_policies(PathPrefix=path_prefix)
    policy_arn = None
    for p in policy_list_response['Policies']:
        if p['PolicyName'] == policy_name:
            policy_arn = p['Arn']
            print("Found policy")

    if policy_arn is None:
        create_policy_response = iam.create_policy(
            PolicyName=policy_name,
            Path=path_prefix,
            PolicyDocument=get_iam_policy_doc()
        )
        policy_arn = create_policy_response['Policy']['Arn']

    # create role attached to policy
    role_name = "GaiaAppRole-" + gaia_config['appName']
    role_list_response = iam.list_roles(PathPrefix=path_prefix)
    role_arn = None

    for r in role_list_response['Roles']:
        if r['RoleName'] == role_name:
            role_arn = r['Arn']
            print("Found Role!")

    if role_arn is None:
        create_role_response = iam.create_role(
            RoleName=role_name,
            Path=path_prefix,
            AssumeRolePolicyDocument="""{
           "Version" : "2012-10-17",
           "Statement": [ {
              "Effect": "Allow",
              "Principal": {
                 "Service": [ "ec2.amazonaws.com" ]
              },
              "Action": [ "sts:AssumeRole" ]
           }
          ]
        }"""
        )
        role_arn = create_role_response['Role']['Arn']

    # create instance profile  create_instance_profile()
    instance_profile_name = "GaiaAppInstanceProfile-" + gaia_config['appName']
    try:
        profile_response = iam.create_instance_profile(
            InstanceProfileName=instance_profile_name,
            Path=path_prefix
        )
        print("Instance Profile Created")
    except Exception as e:
        print("Instance Profile Already Exists")
        pass

    # attach role to policy   add_role_to_instance_profile()
    try:
        add_response = iam.add_role_to_instance_profile(
            InstanceProfileName=instance_profile_name,
            RoleName=role_name
        )
        print(add_response)
    except Exception as e:
        pass
    gaia_config['instance_profile'] = instance_profile_name


create_version_zip()
create_iam_assets()

dnsManager = DNSManager(gaia_config, aws_config)

for region_name in gaia_config['regions']:
    region_runner = RegionRunner(region_name, gaia_config, aws_config, dnsManager)
    dnsManager.add_region_runner(region_runner)
    region_runner.start()

dnsManager.await_lights()
