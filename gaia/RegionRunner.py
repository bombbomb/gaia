import threading


class RegionRunner(threading.Thread):
    def __init__(self, region, config):
        threading.Thread.__init__(self)
        self.region = region
        self.config = config

    def run(self):
        print("Ran " + self.region)
