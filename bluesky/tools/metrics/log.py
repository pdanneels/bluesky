"""
    Functions to log data

"""
import os
from time import strftime, gmtime
from bluesky.tools.misc import tim2txt

class MetricsLog(object):
    """ Class containing functions to log metrics data """
    def __init__(self, sim):
        self.sim = sim
        # Create a buffer and save filename
        self.fname = os.path.dirname(__file__) + "/../../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSky-metricsstats.txt", gmtime())
        self.buffer = []
        return

    def update(self, var, val):
        """ Add data to log """
        sim = self.sim
        tim = tim2txt(sim.simt)
        self._write_(tim, var, val)
        return

    def _write_(self, tim, var, val):
        """ Write data to buffer """
        self.buffer.append(tim + ";" + var + ";" + val + "\n")
        return

    def save(self):  # Write buffer to file
        """ Write buffer to file """
        writefile = open(self.fname, "w")
        writefile.writelines(self.buffer)
        writefile.close()
        return

    @staticmethod
    def _listtostring_(name, array):
        """ Make CSV style line """
        string = name + ":"
        for i in array:
            string += str(i) + ";"
        return string

    def savemetrics_evolution(self, rdot, other, confperac, conflictrate, vrel, dhdg, trafficdensity):
        """ Write evolution data to file """
        fname = os.path.dirname(__file__) + "/../../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSky-metrics-evolution.txt", gmtime())
        writebuffer = []
        if self.sim.traf.ntraf < 2:
            print "ERROR: not saving metrics, ntraf < 2"
            return

        # evolution data
        histgs, histntraf, histrantraf = other.gethist()
        histrdot = rdot.gethist()
        histconfperac = confperac.gethist()
        histtrafficdensity = trafficdensity.gethist()
        histdhdg = dhdg.gethist()
        histvrel = vrel.gethist()
        histcr = conflictrate.gethist()
        
        writebuffer.append(self._listtostring_("Timevector", histgs[0, :])+"\n")
        writebuffer.append(self._listtostring_("Groundspeed", histgs[1, :])+"\n")
        writebuffer.append(self._listtostring_("NumberofAC", histntraf[1, :])+"\n")
        writebuffer.append(self._listtostring_("NumberofACinRA", histrantraf[1, :])+"\n")
        writebuffer.append(self._listtostring_("ConflictsperAC", histconfperac[1, :])+"\n")
        writebuffer.append(self._listtostring_("dHDG", histdhdg[1, :])+"\n")
        writebuffer.append(self._listtostring_("relV", histvrel[1, :])+"\n")
        writebuffer.append(self._listtostring_("TrafficDensity", histtrafficdensity[1, :])+"\n")
        writebuffer.append(self._listtostring_("Cr", histcr[1, :])+"\n")
        writebuffer.append(self._listtostring_("rdot", histrdot[1, :])+"\n")

        writefile = open(fname, "w")
        writefile.writelines(["Sim time: " + tim2txt(self.sim.simt) + "\n"])
        writefile.writelines(writebuffer)
        writefile.close()
        return
