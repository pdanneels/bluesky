"""
Part of metrics module, contains all classes for different metrics

"""
# To ignore numpy errors:
#     pylint: disable=E1101

import numpy as np
from math import sqrt
from bluesky.tools.misc import degto180
from bluesky.tools import geo

class Metrics(object):
    """ Main class for metrics """
    def __init__(self, sim, geodata, swprint, metrictype):
        self.sim = sim
        self.traf = self.sim.traf
        self.asas = self.sim.traf.asas
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

        #vx = vectV[:, :, 0]
        #vy = vectV[:, :, 1]
        #vz = vectV[:, :, 2]
        # rdot = ((x[j]-x[i])*(vx[j]-vx[i])+(y[j]-y[i])*(vy[j]-vy[i]))/dr

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

class DynamicDensity(Metrics):
    """ METRICS: DYNAMIC DENSITY METRIC """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self, rdot):
        """ update metric """
        self.timehist.append(self.sim.simt)
        mask = np.ones(self.asas.tcpa.shape, dtype=bool)
        np.fill_diagonal(mask, 0)

        distance = self.geodata.qdrdist[:, :, 1]
        dd1 = (distance < 100) & (self.asas.tcpa < 1800)
        dd2 = (np.square(distance) < 10000) & (self.asas.tcpa < 1800)
        rangeatcpa = np.sqrt(self.asas.dcpa2)/1852.
        dd3 = (1. / self.asas.tcpa) * rdot.rdot
        dd4 = (1. / self.asas.tcpa) * (1. / rangeatcpa)

        return np.sum(dd1[mask]), np.sum(dd2[mask]), dd3, dd4

class ConflictsPerAc(Metrics):
    """ METRIC: CONFLICTS/AC """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        self.conflictsperac = float(self.asas.nconf / 2) / self.traf.ntraf
        self.timehist.append(self.sim.simt)
        self.hist.append(self.conflictsperac)
        if self.swprint:
            print "Conflicts per AC: " + str(self.conflictsperac)
        return self.conflictsperac

class ConflictRate(Metrics):
    """ METRIC: CONFLICT RATE

    Cr = avgVg * R * avgT / ( A * totT )
    with:   - avgVg is average ground velocity
            - R is speration mimimum
            - avgT is average time in research area
            - A is research area
            - totT is total observation time

    """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)
        self.sep = 10000

    def update(self):
        """ update metric """
        rarea = self.sim.rarea
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
                    iov.append(rarea.groundspeed[i])
            self.timehist.append(self.sim.simt)
            if len(ioac) != 0:
                self.conflictrate = np.average(np.array(iov)) * self.sep * \
                    np.average(np.array(iot)) / rarea.surfacearea / \
                    (self.sim.simt - rarea.entertime[1])
                self.hist.append(self.conflictrate)
                if self.swprint:
                    print "Collision rate: " + str(self.conflictrate)
            else:
                self.hist.append(0)
        return self.conflictrate

class RelativeHeading(Metrics):
    """ METRIC: RELATIVE HEADING """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        mask = np.ones(self.geodata.dhdg.shape, dtype=bool)
        mask = np.triu(mask, 1)
        self.avgdHDG = np.average(np.abs(self.geodata.dhdg[mask]))
        self.timehist.append(self.sim.simt)
        self.hist.append(self.avgdHDG)
        if self.swprint:
            print "Average dHDG: " + str(int(self.avgdHDG)) + " deg"
        return self.avgdHDG

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
        for i in range(self.numberofac):
            for j in range(self.numberofac):
                self.rdot[i, j] = -1*(self.traf.gs[i]*bearingcomponent[i][j]+ \
                    self.traf.gs[j]*bearingcomponent[j][i])
        return

    def update(self):
        """ update metric """
        self.numberofac = len(self.traf.gs)
        self.rdot = np.zeros((self.numberofac, self.numberofac))
        self._calcrdot_(self.geodata.qdrdist[:, :, 0])
        #self.calcrdot(geo.dhdg)
        mask = np.ones(self.rdot.shape, dtype=bool)
        mask = np.triu(mask, 1)
        self.avgrdot = np.average(self.rdot[mask])
        self.timehist.append(self.sim.simt)
        self.hist.append(self.avgrdot)
        if self.swprint:
            print "Average rdot: " + str(int(self.avgrdot)) + " m/s"
        return self.avgrdot

class TrafficDensity(Metrics):
    """ METRIC: TRAFFIC DENSITY

    AC/sqkm

    """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        self.interval = 0
        if self.sim.rarea.surfacearea != 0:
            self.interval = self.traf.ntraf / self.sim.rarea.surfacearea * 1000000.0
            self.timehist.append(self.sim.simt)
            self.hist.append(self.interval)
            if self.swprint:
                print "Traffic density: " + str(self.interval) + " AC/km2"
        return self.interval

class RelativeVelocity(Metrics):
    """ METRIC: RELATIVE VELOCITY """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    def update(self):
        """ update metric """
        self.avgdV = sqrt(np.average(self.geodata.dVsqr))
        self.timehist.append(self.sim.simt)
        self.hist.append(self.avgdV)
        if self.swprint:
            print "Average dV: " + str(int(self.avgdV)) + " m/s"
        return self.avgdV

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
            self.histntraf.append(np.average(self.traf.ntraf))
            self.histrantraf.append(np.average(self.rarea.ntraf))
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

class AirspaceQuality(Metrics):
    """ METRIC: AirspaceQuality """
    def __init__(self, sim, geodata, swprint):
        Metrics.__init__(self, sim, geodata, swprint, self.__class__.__name__)

    @staticmethod
    def dcpa2todcpa(dcpa2):
        """ Convert DCPA2 to DCPA in meters, do not allow zero values"""
        dcpa = np.sqrt(dcpa2)
        return dcpa # in m
        #return np.sqrt(dcpa2)/1852. # in NM

    @staticmethod
    def purgezeros(array, replacement):
        """ Checks an array for zeros and replaces it with a small value """
        array[array == 0] = replacement
        return array
        
    def update(self, rdot):
        """ update metric """
        mask = np.ones(self.geodata.dhdg.shape, dtype=bool)
        mask = np.triu(mask, 1)
        np.average(np.abs(self.geodata.dhdg[mask]))
        tcpa = self.asas.tcpa
        dcpa = self.dcpa2todcpa(self.asas.dcpa2)
        
        self.purgezeros(dcpa, 0.01)
        self.purgezeros(tcpa, 0.1)
        # With this rdot 0 ac pairs are considered having a near zero diverging range
        self.purgezeros(rdot, 0.1)  
        if (tcpa[mask] < 0).all():
            print "THERE ARE NEGATIVE TIME VALUES"
        if (dcpa[mask] < 0).all():
            print "THERE ARE NEGATIVE RANGE VALUES"
            
        pairsafetylevel = np.multiply(rdot[mask], 1. / (dcpa[mask] * tcpa[mask]))

        self.airspacesafetylevel = np.sum(pairsafetylevel)/pairsafetylevel.size

        self.timehist.append(self.sim.simt)
        self.hist.append(self.airspacesafetylevel)
        if self.swprint:
            print "ASQ SL: %f" % self.airspacesafetylevel
        return self.airspacesafetylevel
