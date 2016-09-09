import numpy as np
from math import sqrt

# To ignore numpy errors:
#     pylint: disable=E1101

class MetricDynmaicDensity():
    """
    METRICS: DYNAMIC DENSITY METRIC

    """
    def __init__(self, sim, swprint):
        self.sim = sim
        self.swprint = swprint
        self.timehist = []
        self.hist = []

    def update(self, geo, rdot):
        traf = self.sim.traf
        self.timehist.append(self.sim.simt)
        mask = np.ones(traf.asas.tcpa.shape, dtype=bool)
        np.fill_diagonal(mask, 0)

        distance = geo.qdrdist[:, :, 1]
        dd1 = (distance < 100) & (traf.asas.tcpa < 1800)
        dd2 = (np.square(distance) < 10000) & (traf.asas.tcpa < 1800)
        rangeatcpa = np.sqrt(traf.asas.dcpa2)/1852.
        dd3 = (1. / traf.asas.tcpa) * rdot.rdot
        dd4 = (1. / traf.asas.tcpa) * (1. / rangeatcpa)

        return np.sum(dd1[mask]), np.sum(dd2[mask]), dd3, dd4

    def gethist(self):
        return np.array((self.timehist, self.hist))

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
        self.conflictsperac = float(traf.asas.nconf / 2) / traf.ntraf
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
                self.rdot[i, j] = -1*(traf.gs[i]*bearingcomponent[i][j]+traf.gs[j]*bearingcomponent[j][i])
        return

    def update(self, geo):
        self.numberofac = len(self.sim.traf.gs)
        self.rdot = np.zeros((self.numberofac, self.numberofac))
        self.calcrdot(geo.qdrdist[:, :, 0])
        #self.calcrdot(geo.dhdg)
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
