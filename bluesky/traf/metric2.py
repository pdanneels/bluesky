"""
Metrics

Classes:
    Geometric()             : calculate geometric data
    metric_TD()             : traffic density
    metric_CA()             : collisions per aircraft
    metric_Cr()             : conflict rate
    metric_dHDG()           : delta heading
    metric_rdot()           : range rate
    metric_severitytime()   :
    metric_Vrel()           : relative velocity

Created by  : P. Danneels, spring 2016

"""

# To ignore numpy errors:
#     pylint: disable=E1101

import numpy as np
from math import sqrt
import matplotlib.pyplot as plt

from ..tools import geo
from ..tools.misc import degto180

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
        vectV[:, :, 0] = (traf.gs*np.sin(traf.ahdg*np.pi/180)).reshape((size, 1))
        vectV[:, :, 1] = (traf.gs*np.cos(traf.ahdg*np.pi/180)).reshape((size, 1))
        vectV[:, :, 2] = -traf.vs.reshape((size, 1))

        # relative speed vectors
        vectdV[:, :, 0] = np.subtract.outer(vectV[:, 0, 0], vectV[:, 0, 0])
        vectdV[:, :, 1] = np.subtract.outer(vectV[:, 0, 1], vectV[:, 0, 1])
        vectdV[:, :, 2] = np.subtract.outer(vectV[:, 0, 2], vectV[:, 0, 2])

        # relative speed squared
        dVsqr = np.sum(np.square(vectdV), axis=2)

        # realtive bearing and distance
        combslatA, combslatB = np.meshgrid(traf.lat, traf.lat)
        combslonA, combslonB = np.meshgrid(traf.lon, traf.lon)
        truebearing, distance = geo.qdrdist_matrix(combslatA.flatten(), combslonA.flatten(), combslatB.flatten(), combslonB.flatten())
        relativebearing = truebearing%360 - np.tile(traf.trk, size)%360
        qdrdist[:, :, 0] = np.reshape(relativebearing, (size, size))
        qdrdist[:, :, 1] = np.reshape(distance, (size, size))

        # delta heading
        dhdg = degto180(np.subtract.outer(traf.trk, traf.trk)) # in plane, no wgs

        # speed vector matrix in Fe [AC,1,[Vx,Vy,Vz]],
        # distance matrix [AC,AC,[relativebearing,distance]] relative bearing on diagonal is -heading
        # relative speed matrix, deltaheading
        return vectV, qdrdist, dVsqr, dhdg
    def update(self):
        self.size = self.sim.traf.gs.size
        self.vectV, self.qdrdist, self.dVsqr, self.dhdg = self.calcgeo()

class MetricConflictsPerAc():
    """
    METRIC: CONFLICTS/AC

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint
        self.timehist = []
        self.hist = []

    def update(self, geo):
        traf = self.sim.traf
        self.conflictsperac = float(traf.asas.nconf)/traf.ntraf
        self.timehist.append(self.sim.simt)
        self.hist.append(self.conflictsperac)
        if self.swprint:
            print "Conflicts per AC: " + str(self.conflictsperac)
        return self.conflictsperac

    def gethist(self):
        return np.array((self.timehist, self.hist))

class MetricConflictRate():
    """
    METRIC: CONFLICT RATE

    Cr = avgVg * R * avgT / ( A * totT )
    with:   - avgVg is average ground velocity
            - R is speration mimimum
            - avgT is average time in research area
            - A is research area
            - totT is total observation time

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint
        self.sep = 10000
        self.timehist = []
        self.hist = []

    def update(self, geo):
        sim = self.sim
        rarea = sim.rarea
        self.conflictrate = -1
        if rarea.surfacearea != 0: # only perform calculations if a research area is defined
            i = 0
            ioac = []
            iot = []
            iov = []
            for i, recordedleave in enumerate(rarea.leavetime): # loop over tracking DB
                if recordedleave != 0:
                    ioac.append(rarea.atimeid[i])
                    iot.append(rarea.leavetime[i]-rarea.entertime[i])
                    iov.append(rarea.gs[i])
            self.timehist.append(sim.simt)
            if len(ioac) != 0:
                self.conflictrate = np.average(np.array(iov))*self.sep*np.average(np.array(iot))/rarea.surfacearea/(sim.simt - rarea.entertime[1])
                self.hist.append(self.conflictrate)
                if self.swprint:
                    print "Collision rate: " + str(self.conflictrate)
            else:
                self.hist.append(0)
        return self.conflictrate

    def gethist(self):
        return np.array((self.timehist, self.hist))

class MetricRelativeHeading():
    """
    METRIC: RELATIVE HEADING

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint
        self.timehist = []
        self.hist = []

    def update(self, geo):
        mask = np.ones(geo.dhdg.shape, dtype=bool)
        mask = np.triu(mask, 1)
        self.avgdHDG = np.average(np.abs(geo.dhdg[mask]))
        self.timehist.append(self.sim.simt)
        self.hist.append(self.avgdHDG)
        if self.swprint:
            print "Average dHDG: " + str(int(self.avgdHDG)) + " deg"
        return self.avgdHDG

    def gethist(self):
        return np.array((self.timehist, self.hist))

class MetricRangeDot():
    """
    METRIC: RANGE RATE
    project vectV on dist to get rdot, requires qdrdist (from speed_vectors function)

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint
        self.timehist = []
        self.hist = []

    def calcrdot(self, bearing):
        traf = self.sim.traf
        #bearingcomponent = np.cos(np.radians(qdrdist[:,:,0])) # get cosine out of for-loop and do once with np
        bearingcomponent = np.cos(np.radians(bearing))
        np.fill_diagonal(bearingcomponent, 0) # set zero for own
        for i in range(self.numberofac):
            for j in range(self.numberofac):
                self.rdot[i, j] = traf.gs[i]*bearingcomponent[i][j]+traf.gs[j]*bearingcomponent[j][i]
        return

    def update(self, geo):
        self.numberofac = len(self.sim.traf.gs)
        self.rdot = np.zeros((self.numberofac, self.numberofac))
        #self.calcrdot(geo.qdrdist)
        self.calcrdot(geo.dhdg)
        mask = np.ones(self.rdot.shape, dtype=bool)
        mask = np.triu(mask, 1)
        self.avgrdot = np.average(self.rdot[mask])
        self.timehist.append(self.sim.simt)
        self.hist.append(self.avgrdot)
        if self.swprint:
            print "Average rdot: " + str(int(self.avgrdot)) + " m/s"
        return self.avgrdot

    def gethist(self):
        return np.array((self.timehist, self.hist))

class MetricSeverityTime():
    """
    METRIC: SEVERITY TIME

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint

    def update(self):
        pass

    def gethist(self):
        return 0

class MetricTrafficDensity():
    """
    METRIC: TRAFFIC DENSITY

    AC/sqkm

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint
        self.timehist = []
        self.hist = []

    def update(self, geo):
        sim = self.sim
        self.interval = 0
        if sim.rarea.surfacearea != 0:
            self.interval = sim.traf.ntraf / sim.rarea.surfacearea * 1000000.0
            self.timehist.append(sim.simt)
            self.hist.append(self.interval)
            if self.swprint:
                print "Traffic density: " + str(self.interval) + " AC/km2"
        return self.interval

    def gethist(self):
        return np.array((self.timehist, self.hist))

class MetricRelativeVelocity():
    """
    METRIC: RELATIVE VELOCITY

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint
        self.timehist = []
        self.hist = []

    def update(self, geo):
        self.avgdV = sqrt(np.average(geo.dVsqr))
        self.timehist.append(self.sim.simt)
        self.hist.append(self.avgdV)
        if self.swprint:
            print "Average dV: " + str(int(self.avgdV)) + " m/s"
        return self.avgdV

    def gethist(self):
        return np.array((self.timehist, self.hist))

class MetricOther():
    def __init__(self, sim, rarea, swprint):
        self.sim = sim
        self.rarea = rarea
        self.swprint = swprint
        self.timehist = []
        self.histgs = []
        self.histntraf = []
        self.histrantraf = []

    def update(self):
        traf = self.sim.traf
        self.timehist.append(self.sim.simt)
        self.histgs.append(np.average(traf.gs))
        if self.rarea.surfacearea > 0:
            self.histntraf.append(np.average(traf.ntraf))
            self.histrantraf.append(np.average(self.rarea.ntraf))
        else:
            self.histntraf.append(0)
            self.histrantraf.append(0)
        if self.swprint:
            print "Average V: " + str(np.average(traf.gs)) + " m/s"
            if self.rarea.surfacearea > 0:
                print "Number of AC: " + str(traf.ntraf)
                print "Number in RA: " + str(self.rarea.ntraf)
        return

    def gethist(self):
        return np.array((self.timehist, self.histgs)), \
                np.array((self.timehist, self.histntraf)), \
                np.array((self.timehist, self.histrantraf))

class Metrics():
    """
    Metric class definition : traffic metrics

    Methods:
        __init__()              : constructor
        update()                : calculate,export and plot the metrics

    """

    def __init__(self, sim):
        self.sim = sim

        # Toggle calculations and output
        self.swmetrics = True       # Toggle metrics
        self.swplot = True          # Toggle plot
        self.swprint = False        # Toggle print
        self.swmetricslog = False   # Toggle metrics log

        # Time
        self.timer0 = -9999         # Force first time call, update
        self.timer1 = -9999         # Force first time call, plot
        self.intervalmetrics = 1    # [seconds]
        self.intervalplot = 15      # [seconds]

        self.fig = None

        # Metrics instances
        self.vrel = MetricRelativeVelocity(sim, self.swprint)
        self.conflictrate = MetricConflictRate(sim, self.swprint)
        self.trafficdensity = MetricTrafficDensity(sim, self.swprint)
        self.ca = MetricConflictsPerAc(sim, self.swprint)
        self.rdot = MetricRangeDot(sim, self.swprint)
        self.sevtime = MetricSeverityTime(sim, self.swprint)
        self.dhdg = MetricRelativeHeading(sim, self.swprint)
        self.ot = MetricOther(sim, sim.rarea, self.swprint)
        return

    def update(self):
        sim = self.sim
        log = sim.datalog
        rarea = sim.rarea

        if sim.simt < 0:
            return
        # Check if there is actual traffic
        if sim.traf.ntraf < 1:
            return
        # Check if metrics is actually switched on
        if not self.swmetrics:
            return
        # Only do something when time is there
        if abs(sim.simt-self.timer0) < self.intervalmetrics:
            return
        self.timer0 = sim.simt  # Update time for scheduler

        if rarea is not None:  # Update tracking DB for research area
            if sim.rarea.surfacearea <= 0:
                print "Defining default research area"
                sim.stack.stack("RAREA %f,%f,%f,%f" % (51.6,4,53,6))
            rarea.update()

        sim.pause() # "Lost time is never found again" - Benjamin Franklin -

        geo = Geometric(sim)        # fresh instance of geo data
        geo.update()
        if self.swmetricslog:
            log.updatem1("CA", str(self.ca.update(geo)))            # collisions devided by #AC
            log.updatem1("Cr", str(self.conflictrate.update(geo)))            # collision rate
            log.updatem1("avgdHDG", str(self.dhdg.update(geo)))     # average range rate
            log.updatem1("avgrdot", str(self.rdot.update(geo)))     # average range rate
            log.updatem1("Td", str(self.trafficdensity.update(geo)))            # traffic density
            log.updatem1("avgdV", str(self.vrel.update(geo)))       # average relative velocity
            log.updatem1("avgV", str(np.average(sim.traf.gs)))      # average groundspeed
        else:
            self.ca.update(geo)
            self.conflictrate.update(geo)
            self.dhdg.update(geo)
            self.rdot.update(geo)
            self.trafficdensity.update(geo)
            self.vrel.update(geo)
        self.ot.update()
        if self.swprint:
            print "------------------------"

        if self.swplot: # Plot
            if abs(sim.simt-self.timer1) < self.intervalplot:
                sim.start() # "The show must go on" - Freddie Mercury, Queen -
                return
            self.timer1 = sim.simt
            self.plot(sim, geo)
            sim.start() # "The show must go on" - Freddie Mercury, Queen -
        return

    def plot(self, sim, geo):
        if self.fig is None:
            self.fig = plt.figure()
        plt.clf() # Fresh plots
        mask = np.ones((geo.size, geo.size), dtype=bool)
        #mask = np.triu(mask,1) # this is problematic for traf.ntraf<=2
        mask = np.fill_diagonal(mask, 0) # exclude diagonal from data
        ##################
        #   Histograms   #
        ##################
#        self.fig.add_subplot(231)
#        velocity = np.squeeze(sim.traf.gs)
#        plt.hist(velocity, bins=50)
#        plt.xlim(50, 450)
#        plt.title("Velocity")
#
#        self.fig.add_subplot(232)
#        dvelocity = np.sqrt(geo.dVsqr[mask]).flatten()
#        plt.hist(dvelocity, bins=50)
#        plt.xlim(-1, 800)
#        plt.title("Relative velocity")
#
#        self.fig.add_subplot(233)
#        drange = geo.qdrdist[:, :, 1][mask].flatten()
#        plt.hist(drange, bins=50)
#        plt.xlim(-1, 600)
#        plt.title("Relative distance")
#
#        self.fig.add_subplot(234)
#        dheading = geo.dhdg[mask].flatten()
#        plt.hist(dheading, bins=50)
#        plt.xlim(-180, 180)
#        plt.title("Relative bearing")
#
#        self.fig.add_subplot(235)
#        rangedot = self.rdot.rdot[mask].flatten()
#        plt.hist(rangedot, bins=50)
#        plt.xlim(-700, 700)
#        plt.title("Range rate")
        #######################################
        #   Evolution of averages over time   #
        #######################################
        if sim.rarea.surfacearea <= 0:
            return
        histgs,histntraf,histrantraf = self.ot.gethist()

        self.fig.add_subplot(331)
        plt.plot(histntraf[0,:],histntraf[1,:])
        plt.ylabel("#AC")
        plt.title("#AC evolution")

        self.fig.add_subplot(332)
        plt.plot(histrantraf[0,:],histrantraf[1,:])
        plt.title("#AC in RA evolution")
        plt.ylabel("#AC")

        self.fig.add_subplot(333)
        hist = self.ca.gethist()
        plt.plot(hist[0,:],hist[1,:])
        plt.title("Conflicts per AC evolution")

        self.fig.add_subplot(334)
        hist = self.conflictrate.gethist()
        plt.plot(hist[0,:],hist[1,:])
        plt.title("Cr evolution")

        self.fig.add_subplot(335)
        plt.plot(histgs[0,:],histgs[1,:])
        plt.ylabel("m/s")
        plt.title("Average V evolution")

        self.fig.add_subplot(336)
        hist = self.vrel.gethist()
        plt.plot(hist[0,:],hist[1,:])
        plt.ylabel("m/s")
        plt.title("Average dV evolution")

        self.fig.add_subplot(337)
        hist = self.dhdg.gethist()
        plt.plot(hist[0,:],hist[1,:])
        plt.ylabel("deg")
        plt.title("Average dHDG evolution")

        self.fig.add_subplot(338)
        hist = self.trafficdensity.gethist()
        plt.plot(hist[0,:],hist[1,:])
        plt.ylabel("#AC/km2")
        plt.title("Traffic density evolution")

        self.fig.add_subplot(339)
        hist = self.rdot.gethist()
        plt.plot(hist[0,:],hist[1,:])
        plt.ylabel("m/s")
        plt.title("Average range rate evolution")

        plt.draw()
        plt.show()

        return
