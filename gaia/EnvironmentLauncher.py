import copy
import threading
import time


class EnvironmentLauncher(threading.Thread):
    def __init__(self, gaia, region, version):
        threading.Thread.__init__(self)
        self.region = region
        self.version = version
        self.gaia = gaia

        self.cname = None
        self.color = None
        self.status = None

    def run(self):
        eb = self.gaia.create_aws_client('elasticbeanstalk', self.region)
        self.log("Creating Elastic Beanstalk Environment")
        version_num = 'version' + self.version

        option_settings = copy.copy(self.gaia.config['elasticBeanstalk']['optionSettings'])
        option_settings.append({
            'Namespace': 'aws:autoscaling:launchconfiguration',
            'OptionName': 'IamInstanceProfile',
            'Value': self.gaia.iam_manager.instance_profile
        })

        option_settings = self.add_environment_vars(option_settings, self.region, self.version)

        create_response = eb.create_environment(
            ApplicationName=self.gaia.config['appName'],
            EnvironmentName=version_num,
            CNAMEPrefix=self.gaia.config['appName'] + '-' + version_num,
            VersionLabel=self.version,
            SolutionStackName=self.gaia.config['elasticBeanstalk']['solutionStack'],
            OptionSettings=option_settings
        )
        self.log(create_response)

        # poll for environment to go green
        health_check_interval_seconds = 15
        self.log("Awaiting green environments in " + str(health_check_interval_seconds) + " second intervals")
        for loop_count in range(1, 100):
            time.sleep(health_check_interval_seconds)
            try:
                health_response = eb.describe_environments(
                    EnvironmentNames=[version_num]
                )

                env = health_response['Environments'][0]
                self.log("%s: %s" % (env['Status'], env['Health']))
                self.color = env['Health']
                self.status = env['Status']

            except Exception as e:
                self.log(e)

            if self.color is not None and self.color in ['Green', 'Red']:
                self.log("Environment %s!" % self.color)
                break

        self.gaia.environment_manager.environment_launcher_callback()

    def log(self, msg):
        self.gaia.region_log(self.region, msg)

    def add_environment_vars(self, option_settings, region, version):

        flattened_environment_vars = {
            'GAIA_VERSION': version,
            'GAIA_REGION': region
        }

        if 'environmentVariables' in self.gaia.config:
            ev = self.gaia.config['environmentVariables']
            if 'global' in ev:
                for key in ev['global']:
                    flattened_environment_vars[key] = ev['global'][key]

            if 'regional' in ev:
                if region in ev['regional']:
                    for key in ev['regional'][region]:
                        flattened_environment_vars[key] = ev['regional'][region][key]

        for key in flattened_environment_vars:
            option_settings.append({
                'Namespace': 'aws:elasticbeanstalk:application:environment',
                'OptionName': key,
                'Value': flattened_environment_vars[key]
            })

        return option_settings
