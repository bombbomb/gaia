import boto3


class IAMManager:
    def __init__(self, gaia):
        self.gaia = gaia
        self.instance_profile = None
        pass

    @staticmethod
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

    def create_iam_assets(self):
        # create policy
        iam = boto3.client('iam',
                           aws_access_key_id=self.gaia.aws_config['key'],
                           aws_secret_access_key=self.gaia.aws_config['secret'])

        policy_name = "GaiaAppPolicy-" + self.gaia.config['appName']
        path_prefix = '/GaiaApp/'
        policy_list_response = iam.list_policies(PathPrefix=path_prefix)
        policy_arn = None
        for p in policy_list_response['Policies']:
            if p['PolicyName'] == policy_name:
                policy_arn = p['Arn']
                print("Found Policy!")

        if policy_arn is None:
            create_policy_response = iam.create_policy(
                PolicyName=policy_name,
                Path=path_prefix,
                PolicyDocument=self.get_iam_policy_doc()
            )
            policy_arn = create_policy_response['Policy']['Arn']

        # create role attached to policy
        role_name = "GaiaAppRole-" + self.gaia.config['appName']
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
        instance_profile_name = "GaiaAppInstanceProfile-" + self.gaia.config['appName']
        try:
            profile_response = iam.create_instance_profile(
                InstanceProfileName=instance_profile_name,
                Path=path_prefix
            )
            print("Instance Profile Created")
        except Exception as e:
            print("Found Instance Profile!")
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
        self.instance_profile = instance_profile_name
