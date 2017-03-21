import boto3


class DNSManager:
    def __init__(self, gaia):
        self.gaia = gaia
        self.regionRunners = {}
        self.regions = []
        self.region_endpoints = {}
        self.hosted_zone_id = None
        self.r53 = boto3.client('route53',
                          aws_access_key_id=self.gaia.aws_config['key'],
                          aws_secret_access_key=self.gaia.aws_config['secret'])
        self.get_zone_id()

    def transition_dns(self, destination_version, destination_amt=100):
        print("Transitioning DNS to %s in the amount of %s" % (destination_version, destination_amt))
        self.ensure_region_records()

        regional_environments = self.gaia.environment_manager.list_environments()

        new_endpoints = {}
        for region in self.gaia.config['regions']:
            new_endpoint = None
            for environment in regional_environments[region]:
                if environment['VersionLabel'] == destination_version:
                    new_endpoint = environment['CNAME']

            if new_endpoint is None:
                print("Aborting: Could not determine new endpoint in %s" % region)
                exit()
            else:
                new_endpoints[region] = new_endpoint

        print("Changing Endpoints to: %s" % new_endpoints)

        for region in self.gaia.config['regions']:
            if destination_amt == 100:
                change_result = self.r53.change_resource_record_sets(
                    HostedZoneId=self.hosted_zone_id,
                    ChangeBatch={
                        'Changes': [
                            {
                                'Action': 'UPSERT',
                                'ResourceRecordSet': {
                                    'Name': self.gen_cname_for_regional_endpoint(region),
                                    'Type': 'CNAME',
                                    'SetIdentifier': destination_version,
                                    'Weight': 100,
                                    'TTL': 60,
                                    'ResourceRecords': [
                                        {
                                            'Value': new_endpoints[region]
                                        }
                                    ]
                                }
                            },
                        ]
                    }
                )
                print(change_result)

        print("Transition Complete")

    def get_dns_configuration(self):
        zone_id = self.get_zone_id()

        config = {}
        records_response = self.r53.list_resource_record_sets(HostedZoneId=zone_id)

        for region in self.gaia.config['regions']:
            config[region] = {
                'region_record': None,
                'environment_records': []
            }
            for record in records_response['ResourceRecordSets']:
                if record['Name'] == self.gen_cname_for_app() and record['Region'] == region:
                    config[region]['region_record'] = {
                        'Name': record['Name'],
                        'Region': record['Region'],
                        'Value': record['ResourceRecords'][0]['Value']
                    }

                if record['Name'] == self.gen_cname_for_regional_endpoint(region) and record['Weight'] is not None:
                    config[region]['environment_records'].append({

                    })

        return config

    def get_zone_id(self):
        if self.hosted_zone_id is not None:
            return self.hosted_zone_id

        hosted_zone_id = None
        zone_response = self.r53.list_hosted_zones()
        for zone in zone_response['HostedZones']:
            if zone['Name'] == self.gaia.config['dnsZone']:
                hosted_zone_id = zone['Id']
                break

        self.hosted_zone_id = hosted_zone_id
        print("Got hosted zone id: %s" % self.hosted_zone_id)
        return self.hosted_zone_id

    def gen_cname_for_regional_endpoint(self, region):
        return "%s.%s.%s" % (region, self.gaia.config['appName'], self.gaia.config['dnsZone'])

    def gen_cname_for_app(self):
        return self.gaia.config['appName'] + '.' + self.gaia.config['dnsZone']

    def ensure_region_records(self):
        existing_records = self.get_dns_configuration()

        for region in self.gaia.config['regions']:
            if existing_records[region]['region_record'] is None:
                self.gaia.region_log(region, "Creating regional DNS entry")
                change_result = self.r53.change_resource_record_sets(
                    HostedZoneId=self.hosted_zone_id,
                    ChangeBatch={
                        'Changes': [
                            {
                                'Action': 'CREATE',
                                'ResourceRecordSet': {
                                    'Name': self.gen_cname_for_app(),
                                    'Type': 'CNAME',
                                    'SetIdentifier': region,
                                    'Region': region,
                                    'TTL': 60,
                                    'ResourceRecords': [
                                        {
                                            'Value': self.gen_cname_for_regional_endpoint(region)
                                        }
                                    ]
                                }
                            },
                        ]
                    }
                )
                print(change_result)
