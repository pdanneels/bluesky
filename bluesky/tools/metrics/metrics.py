"""
Part of metrics module, contains all classes for different metrics

"""
# To ignore numpy errors:
#     pylint: disable=E1101

import numpy as np
from math import sqrt
import math
from bluesky.tools.misc import degto180
from bluesky.tools import geo

class Metrics(object):
    """ Main class for metrics """
    def __init__(self, sim, geodata, swprint, metrictype):
        self.sim = sim
        self.traf = sim.traf
        self.asas = sim.traf.asas
        # Instance of this class containing the geodata
        self.geodata = geodata
        self.swprint = swprint
        self.timehist = []
        self.hist = []
        self.metrictype = metrictype

        # Number of AC in geodata arrays
        self.size = 0

    def gethist(self):
        """ returns history arrays """
        return np.array((self.timehist, self.hist))

    def updategeodata(self):
        """ returns the set of geometric data """
        self.size = self.traf.gs.size
        self.vectV, self.qdrdist, self.dVsqr, self.dhdg = self._calcgeodata_(self.size)
        return

    def _calcgeodata_(self, size): # perform calculations on traf set in simulation object
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
        self.vectV = np.zeros((size, 1, 3))
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
        vectV[:, :, 0] = (self.traf.gs*np.sin(self.traf.hdg*np.pi/180)).reshape((size, 1))
        vectV[:, :, 1] = (self.traf.gs*np.cos(self.traf.hdg*np.pi/180)).reshape((size, 1))
        vectV[:, :, 2] = -self.traf.vs.reshape((size, 1))

        # relative speed vectors vectdV[AC1, AC2, [Vx,Vy,Vz]]
        vectdV[:, :, 0] = np.subtract.outer(vectV[:, 0, 0], vectV[:, 0, 0])
        vectdV[:, :, 1] = np.subtract.outer(vectV[:, 0, 1], vectV[:, 0, 1])
        vectdV[:, :, 2] = np.subtract.outer(vectV[:, 0, 2], vectV[:, 0, 2])

        # relative speed squared
        dVsqr = np.sum(np.square(vectdV), axis=2)

        # realtive bearing and distance
        combslatA, combslatB = np.meshgrid(self.traf.lat, self.traf.lat)
        combslonA, combslonB = np.meshgrid(self.traf.lon, self.traf.lon)
        truebearing, distance = geo.qdrdist_matrix(combslatA.flatten(), \
                combslonA.flatten(), combslatB.flatten(), combslonB.flatten())
        relativebearing = truebearing%360 - np.tile(self.traf.trk, size)%360
        qdrdist[:, :, 0] = np.reshape(relativebearing, (size, size))
        qdrdist[:, :, 1] = np.reshape(distance, (size, size))

        # delta heading
        dhdg = degto180(np.subtract.outer(self.traf.trk, self.traf.trk)) # in plane, no wgs

        # speed vector matrix in Fe [AC,1,[Vx,Vy,Vz]],
        # distance matrix [AC,AC,[relativebearing,distance]]
        #   relative bearing on diagonal is -heading
        # relative speed matrix, deltaheading
        return vectV, qdrdist, dVsqr, dhdg

class AirspaceQuality(Metrics):
    """ METRIC: AirspaceQuality """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)
        self.pairsafetylevels = []

    @staticmethod
    def dcpa2todcpa(dcpa2):
        """ Convert DCPA2 to DCPA in meters, do not allow negative values"""
        dcpa = np.sqrt(dcpa2.clip(0))
        return dcpa # in meters

    @staticmethod
    def purgezeros(array, clip):
        """ Checks an array for zeros and replaces it with a small value """
        for val in np.nditer(array):
            if -1./clip < val < 0.:
                val = -1./clip
            elif 0. <= val < 1./clip:
                val = 1./clip
        return array

    def calcasq(self, rdotin):
        """ Calculates ASQ """
        if not self.traf.ntraf > 0:
            return
        rarea = self.sim.rarea
        acinsidera = rarea.acinarea()
        if not np.sum(acinsidera) > 0:
            return
        ramask = acinsidera*np.swapaxes([acinsidera], 0, 1)
        ramask = ramask.astype(bool)

        clip = 10000.
        dtlookahead = self.asas.dtlookahead
        sep = 10 * 1852.
        rsign = np.sign(rdotin[ramask])
        dcpa = self.dcpa2todcpa(self.asas.dcpa2[ramask])/sep
        tcpa = self.asas.tcpa[ramask]/dtlookahead

        size = int(math.sqrt(tcpa.size))
        mask = np.ones((size, size), dtype=bool)
        mask = np.triu(mask, 1).flatten()

        dcpa = dcpa[mask]
        tcpa = tcpa[mask]
        rsign = rsign[mask]

        interim = -tcpa*dcpa
        interim = self.purgezeros(interim, clip)

        asq = np.power(interim, rsign)
        if np.any(asq > clip) or np.any(asq < -clip):
            asq = np.clip(asq, -clip, clip)
            print "WARNING: Large values found in calculation, dataset clipped"

        globalasq = np.sum(asq)
        return asq, globalasq

    def update(self):
        """ Update metric DEPRICATED, NOT USED ANYMORE """
        tcpa = self.asas.tcpa
        dcpa = self.dcpa2todcpa(self.asas.dcpa2)
        mask = np.ones(tcpa.shape, dtype=bool)
        mask = np.triu(mask, 1)

        self.purgezeros(dcpa, 0.01)
        self.purgezeros(tcpa, 0.1)

        pairsafetylevels = 1. / (dcpa[mask] * tcpa[mask])

        averagesafetylevel = np.sum(pairsafetylevels)/pairsafetylevels.size

        self.timehist.append(self.sim.simt)
        self.hist.append(averagesafetylevel)
        self.pairsafetylevels.append(pairsafetylevels)
        if self.swprint:
            print "ASQ SL: %f" % averagesafetylevel
        return averagesafetylevel

class ConflictsPerAc(Metrics):
    """ METRIC: CONFLICTS/AC """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        conflictsperac = float(self.asas.nconf / 2) / self.traf.ntraf
        self.timehist.append(self.sim.simt)
        self.hist.append(conflictsperac)
        if self.swprint:
            print "Conflicts per AC: " + str(conflictsperac)
        return conflictsperac

class AverageConflictRate(Metrics):
    """ METRIC: Number of unique conflicts in the last 15min in RA """

    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)
        self.conflictratedata = []              # Conflictrates
        self.slidingwindowhorizon = 15*60       # [seconds]

    def update(self):
        """ update metric """
        self.timehist.append(self.sim.simt)
        rarea = self.sim.rarea

        # only perform calculations if a research area is defined
        if rarea.surfacearea == 0:
            self.hist.append(0)
            print "WARNING: NO RAREA FOUND FOR AVERAGE CR CALUCLATION"
            return

        count = 0
        horizon = self.sim.simt - self.slidingwindowhorizon
        if horizon < 0:
            horizon = 0
#            print "NOTICE: AVERAGE CR SET TO ZERO, NOT PAST FIRST HORIZON YET"
#            self.hist.append(0)
#            return

        for conflictrate in rarea.conflicts:
            if conflictrate[0] >= horizon:
                count += 1
        self.hist.append(count) # Number of unique conflicts in the last 15 minuties in RA

class ConflictRate(Metrics):
    """ METRIC: CONFLICT RATE DISTRIBUTION """

    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)
        self.conflictratedist = []              # Standard deviation

    def update(self):
        """ update metric """
        self.timehist.append(self.sim.simt)
        rarea = self.sim.rarea

        # only perform calculations if a research area is defined
        if rarea.surfacearea == 0:
            self.hist.append(0)
            print "WARNING: NO RAREA FOUND FOR CR CALUCLATION"
            return 0
        
        self.conflictratedist.append(rarea.confperac)
        self.hist.append(np.std(rarea.confperac))

class ConflictRatePrediction(Metrics):
    """ METRIC: CONFLICT RATE PREDICTION

    Cr = avgVg * R * avgT / ( A * totT )
    with:   - avgVg is average ground velocity [m/s]
            - R is speration mimimum [m]
            - avgT is average time in research area [s]
            - A is research area [m2]
            - totT is total observation time [s]
            totT is replaced by an expected max time for an aircraft flying
            the diagonal through the square area at 300m/s

    """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)
        self.conflictratedata = []     # Conflictrates times totaltime

    def update(self):
        """ update metric """
        rarea = self.sim.rarea
        sep = 10 * 1852.
        self.timehist.append(self.sim.simt)

        # only perform calculations if a research area is defined
        # only perform calculations if AC already passed through RA
        if rarea.surfacearea == 0 and len(rarea.passedthrough) != 0:
            self.hist.append(0)
            return 0

        # only calculate for new AC
        if len(self.conflictratedata) < len(rarea.passedthrough):
            for i in range(len(self.conflictratedata), len(rarea.passedthrough)):
                vaverage = rarea.passedthrough[i][3]
                tin = rarea.passedthrough[i][2] - rarea.passedthrough[i][1]
                area = rarea.surfacearea
                self.conflictratedata.append((vaverage, tin, area, sep))

        tmax = sqrt(2*self.sim.rarea.surfacearea)/300

        conflictrates = []
        for x in self.conflictratedata:
            vaverage, tin, area, sep = x
            conflictrates.append(vaverage * sep * tin / (area * tmax))
        self.hist.append(np.average(conflictrates))
        return

class Other(Metrics):
    """ Other, simpel to calculate metrics """
    def __init__(self, sim, geodata, rarea, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)
        self.rarea = rarea
        self.histgs = []
        self.histntraf = []
        self.histrantraf = []

    def update(self):
        """ update metric """
        self.timehist.append(self.sim.simt)
        self.histgs.append(np.average(self.traf.gs))
        if self.rarea.surfacearea > 0:
            self.histntraf.append(self.traf.ntraf)
            self.histrantraf.append(self.rarea.ntraf)
        else:
            self.histntraf.append(0)
            self.histrantraf.append(0)
        if self.swprint:
            print "Average V: " + str(np.average(self.traf.gs)) + " m/s"
            if self.rarea.surfacearea > 0:
                print "Number of AC: " + str(self.traf.ntraf)
                print "Number in RA: " + str(self.rarea.ntraf)
        return

    def gethist(self):
        return np.array((self.timehist, self.histgs)), \
                np.array((self.timehist, self.histntraf)), \
                np.array((self.timehist, self.histrantraf))

class RangeDot(Metrics):
    """ METRIC: RANGE RATE

    project vectV on dist to get rdot, requires qdrdist (from speed_vectors function)

    """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def _calcrdot_(self, bearing):
        """ calculates rdot """
        #bearingcomponent = np.cos(np.radians(qdrdist[:,:,0]))
        # get cosine out of for-loop and do once with np
        bearingcomponent = np.cos(np.radians(bearing))
        np.fill_diagonal(bearingcomponent, 0) # set zero for own
        for i in range(self.asas.alt.size):
            for j in range(self.asas.alt.size):
                self.rdot[i, j] = -1*(self.traf.gs[i]*bearingcomponent[i][j]+ \
                    self.traf.gs[j]*bearingcomponent[j][i])
        return

    def update(self):
        """ update metric """
        numberofac = self.asas.alt.size
        self.rdot = np.zeros((numberofac, numberofac))
        self._calcrdot_(self.geodata.qdrdist[:, :, 0])
        #self.calcrdot(geo.dhdg)
        mask = np.ones(self.rdot.shape, dtype=bool)
        mask = np.triu(mask, 1)
        avgrdot = np.average(self.rdot[mask])
        self.timehist.append(self.sim.simt)
        self.hist.append(avgrdot)
        if self.swprint:
            print "Average rdot: " + str(int(avgrdot)) + " m/s"
        return avgrdot

class RelativeHeading(Metrics):
    """ METRIC: RELATIVE HEADING """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        mask = np.ones(self.geodata.dhdg.shape, dtype=bool)
        mask = np.triu(mask, 1)
        avgdHDG = np.average(np.abs(self.geodata.dhdg[mask]))
        self.timehist.append(self.sim.simt)
        self.hist.append(avgdHDG)
        if self.swprint:
            print "Average dHDG: " + str(int(avgdHDG)) + " deg"
        return avgdHDG

class RelativeVelocity(Metrics):
    """ METRIC: RELATIVE VELOCITY """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        avgdV = sqrt(np.average(self.geodata.dVsqr))
        self.timehist.append(self.sim.simt)
        self.hist.append(avgdV)
        if self.swprint:
            print "Average dV: " + str(int(avgdV)) + " m/s"
        return avgdV

class TrafficDensity(Metrics):
    """ METRIC: TRAFFIC DENSITY

    AC/sqkm

    """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        interval = 0
        if self.sim.rarea.surfacearea != 0:
            interval = self.sim.rarea.ntraf / self.sim.rarea.surfacearea * 1000000.0
            self.timehist.append(self.sim.simt)
            self.hist.append(interval)
            if self.swprint:
                print "Traffic density: " + str(interval) + " AC/km2"
        return interval
