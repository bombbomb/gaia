import boto3


class DNSManager:
    def __init__(self, config, aws_config):
        self.config = config
        self.aws_config = config
        self.regionRunners = {}
        self.regions = []

    def add_region_runner(self, region_runner):
        self.regionRunners[region_runner.region] = region_runner
        self.regions.append(region_runner.region)

    def receive_new_endpoint(self, region, endpoint):
        print("New endpoint: " + region + " " + endpoint)

    def await_lights(self):
        pass
