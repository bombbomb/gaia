import boto3


class DNSManager:
    def __init__(self, gaia):
        self.gaia = gaia
        self.regionRunners = {}
        self.regions = []
        self.region_endpoints = {}
        self.r53 = boto3.client('route53',
                          aws_access_key_id=self.gaia.aws_config['key'],
                          aws_secret_access_key=self.gaia.aws_config['secret'])

    def transition_dns(self, destination_version, destination_amt=100):
        pass

    def get_dns_configuration(self):
        zone_id = self.get_zone_id()

        config = {
            'region_latency_records': [],
            'environment_weight_records': []
        }
        records_response = self.r53.list_resource_record_sets(HostedZoneId=zone_id)

        for record in records_response['ResourceRecordSets']:
            if record['Name'] == self.gen_cname_for_app() and record['Region'] is not None:
                config['region_latency_records'].append(record)

            for region in self.gaia.config['regions']:
                if record['Name'] == self.gen_cname_for_regional_endpoint(region) and record['Weight'] is not None:
                    config['environment_weight_records'].append(record)

        return config

    def get_zone_id(self):
        hosted_zone_id = None
        zone_response = self.r53.list_hosted_zones()
        for zone in zone_response['HostedZones']:
            if zone['Name'] == self.gaia.config['dnsZone']:
                hosted_zone_id = zone['Id']
                break

        return hosted_zone_id

    def gen_cname_for_regional_endpoint(self, region):
        return "%s.%s.%s." % (region, self.gaia.config['appName'], self.gaia.config['dnsZone'])

    def gen_cname_for_app(self):
        return self.gaia.config['appName'] + '.' + self.gaia.config['dnsZone']