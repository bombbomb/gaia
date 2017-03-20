import json

from gaia.RegionRunner import RegionRunner

print("Welcome to Gaia")

with open('config.json') as json_data:
    gaia_config = json.load(json_data)
    print(gaia_config)

# zone checking

for region_name in gaia_config['regions']:
    region_runner = RegionRunner(region_name, gaia_config)
    region_runner.run()


# check if EB App needs to be created

# figure out current running version
