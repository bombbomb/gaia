import json
import sys

from gaia.Gaia import Gaia

print("Gaia Awakens")

args = sys.argv

if len(args) == 1:
    print("You must pass in a path")
    exit()

code_path = args[1]

with open(code_path + '/gaia.json') as json_data:
    gaia_config = json.load(json_data)
    print(gaia_config)

gaia_config['code_path'] = code_path

with open('aws.json') as json_data:
    aws_config = json.load(json_data)
    print("Got AWS creds")


g = Gaia(gaia_config, aws_config)
g.run()
