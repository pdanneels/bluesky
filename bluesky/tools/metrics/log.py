import os
from time import strftime, gmtime
from bluesky.tools.misc import tim2txt

class MetricsLog(object):
    def __init__(self, sim):
        self.sim = sim
        # Create a buffer and save filename
        self.fname = os.path.dirname(__file__) + "/../../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSky-metricsstats.txt", gmtime())
        self.buffer = []
        return

    def update(self, var, val):
        sim = self.sim
        t = tim2txt(sim.simt)
        self._write(t, var, val)
        return

    def _write(self, t, var, val):
        self.buffer.append(t + ";" + var + ";" + val + "\n")
        return

    def save(self):  # Write buffer to file
        f = open(self.fname, "w")
        f.writelines(self.buffer)
        f.close()
        return