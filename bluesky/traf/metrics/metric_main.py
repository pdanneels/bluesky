"""
Metrics module
Created by  : P. Danneels, 2016

"""

# To ignore numpy errors in pylint static code analyser:
#     pylint: disable=E1101

import os
import numpy as np
from time import strftime, gmtime
from ... import stack
from .metrics import MetricRelativeVelocity, MetricConflictRate, \
    MetricTrafficDensity, MetricConflictsPerAc, MetricRangeDot, \
    MetricSeverityTime, MetricRelativeHeading, MetricOther, \
    MetricDynmaicDensity
from .plot import MetricsPlot
from .stats import MetricsStats
from ...tools import geo
from ...tools.misc import degto180, tim2txt

class Geometric():
    """
    calculating geometric data for current traffic
        - speed vector components in Fe
        - relative speed vector components
        - relative speed squared
        - relative bearing
        - relative distance
        - relative heading

    The difference between relative bearing and heading is that relative bearing is
    calculated through qero_np.qdrdist which accounts for the wgs84 model

    """
    def __init__(self, sim):
        self.sim = sim
        self.size = 0

    def calcgeo(self): # perform calculations on traf set in simulation object
        traf = self.sim.traf
        size = self.size
        self.vectV = np.zeros((self.size, 1, 3))
        self.vectdV = np.zeros((size, size, 3))
        self.qdrdist = np.zeros((size, size, 2))
        self.dVsqr = np.zeros((size, size))
        self.dhdg = np.zeros((size, size))
        vectV = self.vectV
        vectdV = self.vectdV
        qdrdist = self.qdrdist
        dhdg = self.dhdg

        # speed vectors in Earth-Fixed reference frame
        # meaning x points towards North, Z towards center of the Earth, right hand system
        # vectV[AC,1,[Vx,Vy,Vz]]
        vectV[:, :, 0] = (traf.gs*np.sin(traf.hdg*np.pi/180)).reshape((size, 1))
        vectV[:, :, 1] = (traf.gs*np.cos(traf.hdg*np.pi/180)).reshape((size, 1))
        vectV[:, :, 2] = -traf.vs.reshape((size, 1))

        # relative speed vectors vectdV[AC1, AC2, [Vx,Vy,Vz]]
        vectdV[:, :, 0] = np.subtract.outer(vectV[:, 0, 0], vectV[:, 0, 0])
        vectdV[:, :, 1] = np.subtract.outer(vectV[:, 0, 1], vectV[:, 0, 1])
        vectdV[:, :, 2] = np.subtract.outer(vectV[:, 0, 2], vectV[:, 0, 2])

        #vx = vectV[:, :, 0]
        #vy = vectV[:, :, 1]
        #vz = vectV[:, :, 2]
        # rdot = ((x[j]-x[i])*(vx[j]-vx[i])+(y[j]-y[i])*(vy[j]-vy[i]))/dr

        # relative speed squared
        dVsqr = np.sum(np.square(vectdV), axis=2)

        # realtive bearing and distance
        combslatA, combslatB = np.meshgrid(traf.lat, traf.lat)
        combslonA, combslonB = np.meshgrid(traf.lon, traf.lon)
        truebearing, distance = geo.qdrdist_matrix(combslatA.flatten(), \
                combslonA.flatten(), combslatB.flatten(), combslonB.flatten())
        relativebearing = truebearing%360 - np.tile(traf.trk, size)%360
        qdrdist[:, :, 0] = np.reshape(relativebearing, (size, size))
        qdrdist[:, :, 1] = np.reshape(distance, (size, size))

        # delta heading
        dhdg = degto180(np.subtract.outer(traf.trk, traf.trk)) # in plane, no wgs

        # speed vector matrix in Fe [AC,1,[Vx,Vy,Vz]],
        # distance matrix [AC,AC,[relativebearing,distance]] 
        #   relative bearing on diagonal is -heading
        # relative speed matrix, deltaheading
        return vectV, qdrdist, dVsqr, dhdg
    def update(self):
        self.size = self.sim.traf.gs.size
        self.vectV, self.qdrdist, self.dVsqr, self.dhdg = self.calcgeo()
        return

class MetricsLog():
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

class Metrics():
    """
    Metric class definition : traffic metrics

    Methods:
        __init__()              : constructor, configuration of module resides here
        update()                : main update function for metrics

    """

    def __init__(self, sim):
        self.sim = sim
        self.add_stack_commands(sim)

        # Toggle calculations and output
        self.swsingleshot = True    # Toggle single shot operation
        self.swmetrics = False       # Toggle metrics
        self.swplot = True          # Toggle plot
        self.swprint = False        # Toggle print
        self.swmetricslog = True   # Toggle metrics log
        self.swstats = True         # Toggle stats output

        # Time
        self.timer0 = -9999         # Force first time call, update
        self.timer1 = -9999         # Force first time call, plot
        self.intervalmetrics = 1    # [seconds]
        self.intervalplot = 15      # [seconds]

        self.init_instances(sim)
    
    def add_stack_commands(self, sim):
        cmddict = {"METRICS": [
                    "METRICS ON/OFF",
                    "onoff",
                    lambda *args: sim.metrics.toggle(*args)]
                    }
        stack.append_commands(cmddict)

    def init_instances(self, sim):
        """ Initiate instances for metrics and plot/log/stats modules"""
        self.vrel = MetricRelativeVelocity(sim, self.swprint)
        self.conflictrate = MetricConflictRate(sim, self.swprint)
        self.trafficdensity = MetricTrafficDensity(sim, self.swprint)
        self.ca = MetricConflictsPerAc(sim, self.swprint)
        self.rdot = MetricRangeDot(sim, self.swprint)
        self.sevtime = MetricSeverityTime(sim, self.swprint)
        self.dhdg = MetricRelativeHeading(sim, self.swprint)
        self.ot = MetricOther(sim, sim.rarea, self.swprint)
        self.dd = MetricDynmaicDensity(sim, self.swprint)

        self.plot = MetricsPlot(sim)
        self.log = MetricsLog(sim)
        self.stats = MetricsStats(sim)

    def toggle(self, flag):
        if self.swmetrics:
            self.swmetrics = False
        else:
            self.swmetrics = True

    def update(self):
        sim = self.sim
        log = self.log
        plot = self.plot
        stats = self.stats
        rarea = sim.rarea

        # Check if metrics is actually switched on
        if not self.swmetrics:
            return

        if sim.simt < 0:
            return
        # Check if there is actual traffic
        if sim.traf.ntraf < 1:
            return

        # Only do something when time is there
        if abs(sim.simt-self.timer0) < self.intervalmetrics:
            return
        self.timer0 = sim.simt  # Update time for scheduler

        if rarea is not None:  # Update tracking DB for research area
            if sim.rarea.surfacearea <= 0:
                print "Defining default research area"
                stack.stack("RAREA %f,%f,%f,%f" % (51.6, 4, 53, 6))
            rarea.update()

        sim.pause() # "Lost time is never found again" - Benjamin Franklin -

        geo = Geometric(sim)        # fresh instance of geo data
        geo.update()
        if self.swmetricslog:
            log.update("CA", str(self.ca.update(geo)))                # collisions devided by #AC
            log.update("Cr", str(self.conflictrate.update(geo)))      # collision rate
            log.update("avgdHDG", str(self.dhdg.update(geo)))         # average range rate
            log.update("avgrdot", str(self.rdot.update(geo)))         # average range rate
            log.update("Td", str(self.trafficdensity.update(geo)))    # traffic density
            log.update("avgdV", str(self.vrel.update(geo)))           # average relative velocity
            log.update("avgV", str(np.average(sim.traf.gs)))          # average groundspeed
            #log.update("dd", str(self.dd.update(geo,self.rdot)))
        else:
            self.ca.update(geo)
            self.conflictrate.update(geo)
            self.dhdg.update(geo)
            self.rdot.update(geo)
            self.trafficdensity.update(geo)
            self.vrel.update(geo)
            #self.dd.update(geo,self.rdot)
        self.ot.update()
        if self.swprint:
            print "------------------------"

        if self.swplot: # Plot
            if abs(sim.simt-self.timer1) < self.intervalplot:
                sim.start() # "The show must go on" - Freddie Mercury, Queen -
                return
            if self.swsingleshot:
                sim.mdb.MDBrun.clear() # free up resources
            self.timer1 = sim.simt
            plot.plothistograms(geo, self.rdot)
            plot.plotdynamicdensity(geo, self.rdot)
            plot.plot3d(self.rdot)

        if self.swstats: # Stats
            stats.printstats(geo, self.rdot)

        if not self.swsingleshot:
            sim.start() # "The show must go on" - Freddie Mercury, Queen -
        else:
            log.update("Number of AC: " + str(sim.traf.ntraf), \
                "Number of conflicts: " + str(sim.traf.asas.nconf / 2))
            log.update("------------------------------------------------", "")
            log.update("Velocity;;;;;;Relative Veolocity;;;;;;Relative Range;;;;;;Relative Heading;;;;;Range Rate", "")
            line = "Average;Mean;Skewness;Variation;STD;SEM;"
            log.update(line + line + line + line + line, "")
            log.update(stats.logstatsline(geo, self.rdot), "")
            log.save()
            plot.saveplot()
            print ""
            print " -- Finished single shot operation -- "
            print ""
        return
