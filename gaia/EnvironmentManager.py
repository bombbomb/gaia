
from gaia.EnvironmentLauncher import EnvironmentLauncher


class EnvironmentManager:
    def __init__(self, gaia):
        self.gaia = gaia
        self.ensure_eb_app_in_all_regions()
        self.environment_launchers = []
        self.cb = None

    def ensure_eb_app_in_all_regions(self):
        for region in self.gaia.config['regions']:
            eb = self.gaia.create_aws_client('elasticbeanstalk', region)
            apps = eb.describe_applications(ApplicationNames=[self.gaia.config['appName'], ])

            if len(apps['Applications']) == 0:
                eb.create_application(
                    ApplicationName=self.gaia.config['appName']
                )
                print("EB Application created in %s" % region)
            else:
                print("EB Application exists in %s" % region)

    def create_eb_environments(self, version_num, cb=None):
        self.cb = cb
        for region in self.gaia.config['regions']:
            launcher = EnvironmentLauncher(self.gaia, region, version_num)
            self.environment_launchers.append(launcher)
            launcher.start()

    def environment_launcher_callback(self):
        num_goal = len(self.environment_launchers)
        num_ready = 0
        num_green = 0
        for launcher in self.environment_launchers:
            if launcher.color == 'Green':
                num_green += 1
            if launcher.status == 'Ready':
                num_ready += 1

            if launcher.color == 'Red':
                print("The %s environment went Red, aborting deployment" % launcher.region)
                break

        if num_goal == num_ready == num_ready and self.cb is not None:
            self.cb()

    def list_environments(self):
        envs = {}
        for region in self.gaia.config['regions']:
            envs[region] = []
            eb = self.gaia.create_aws_client('elasticbeanstalk', region)
            eb_envs = eb.describe_environments(ApplicationName=self.gaia.config['appName'])
            for environment in eb_envs['Environments']:
                env = {
                    'EnvironmentName': environment['EnvironmentName'],
                    'CNAME': environment['CNAME'],
                    'VersionLabel': environment['VersionLabel'],
                    'Health': environment['Health'],
                    'Status': environment['Status']
                }
                envs[region].append(env)

        return envs

    def terminate_all_environments_except(self, good_environment_name):
        pass
