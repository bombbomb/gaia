import datetime
import os

import boto3

from gaia.DNSManager import DNSManager
from gaia.EnvironmentManager import EnvironmentManager
from gaia.IAMManager import IAMManager
from gaia.VersionManager import VersionManager


class Gaia:
    def __init__(self, config, aws_config):
        self.config = config
        self.aws_config = aws_config
        self.iam_manager = IAMManager(self)
        self.version_manager = VersionManager(self)
        self.dns_manager = DNSManager(self)
        self.environment_manager = EnvironmentManager(self)

    def run(self):
        self.iam_manager.create_iam_assets()

        self.main_menu()

        self.log("Gaia sleeps")
        # for region_name in self.config['regions']:
        #     region_runner = RegionRunner(region_name, gaia_config, aws_config, dns_manager)
        #     dns_manager.add_region_runner(region_runner)
        #     region_runner.start()

    def main_menu(self):
        self.log("Choose a path:\n"
                 "1. Immediate Full Deployment\n"
                 "2. Canary Deployment\n"
                 "3. Background Deployment\n"
                 "4. Create Eb Version\n"
                 "5. DNS Status\n"
                 "6. DNS Transition\n"
                 "7. List Existing Versions\n"
                 "8. List Running Environments\n"
                 "9. Tear Down Environment\n"
                 "0. Exit\n")

        user_entry = input()

        if user_entry == '1':
            self.run_immediate_full()
        elif user_entry == '3':
            self.release_bg_version()
        elif user_entry == '4':
            self.run_create_eb_version()
        elif user_entry == '5':
            self.run_dns_status()
        elif user_entry == '6':
            self.run_dns_transition()
        elif user_entry == '8':
            self.run_list_environments()
        elif user_entry == '9':
            self.tear_down_env()
        else:
            self.log("Not implemented...")
            pass

    def run_immediate_full(self):
        version_num = self.version_manager.release_version()

        def cb():
            self.log("run_immediate_full")
            self.dns_manager.transition_dns(version_num)

        self.environment_manager.create_eb_environments(version_num, cb)

    def run_create_eb_version(self):
        self.version_manager.release_version()

    def release_bg_version(self):
        version_num = self.version_manager.release_version()
        self.environment_manager.create_eb_environments(version_num)

    def run_dns_status(self):
        dns = self.dns_manager.get_dns_configuration()
        for region in self.config['regions']:
            self.log(region)
            self.log(" - Region DNS: %s" % dns[region]['region_record'])
            for record in dns[region]['environment_records']:
                self.log("   - Environment Weight: %s %s" % (record['Weight'], record['Value']))
        self.main_menu()

    def run_dns_transition(self):
        self.print_running_environments_to_screen()
        v_to_move_to = input("Which Version do you want to move to?\n")
        self.dns_manager.transition_dns(v_to_move_to)

    def run_list_environments(self):
        self.print_running_environments_to_screen()
        self.main_menu()

    def tear_down_env(self):
        self.print_running_environments_to_screen()
        v_to_rem = input("Which Version's environments do you want to terminate?\n")
        self.environment_manager.terminate_environments_for_version(v_to_rem)
        self.main_menu()

    def print_running_environments_to_screen(self):
        envs = self.environment_manager.list_environments()
        for region in self.config['regions']:
            self.log(region)
            for env in envs[region]:
                if 'VersionLabel' not in env:
                    env['VersionLabel'] = 'n/a'
                self.log(" - %s | %s | %s" % (env['VersionLabel'], env['Health'], env['CNAME']))

    @staticmethod
    def region_log(region, msg):
        Gaia.log("%s: %s" % (region, msg))

    @staticmethod
    def log(msg):
        print("%s %s" % ('{:%Y-%m-%d %H:%M:%S}: '.format(datetime.datetime.now()), msg))

    def create_aws_client(self, client_name, region=None):
        return boto3.client(client_name,
                            aws_access_key_id=self.aws_config['key'],
                            aws_secret_access_key=self.aws_config['secret'],
                            region_name=region)
