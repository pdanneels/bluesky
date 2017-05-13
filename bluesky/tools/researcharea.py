"""
    Research area

        This module is a set of standalone features to define an area and track the AC inside.
        It does not interfere with the regular Area function in ..traf.traffic

"""
# To ignore numpy errors:
#     pylint: disable=E1101

import numpy as np
from collections import Counter
from ..tools import geo
from . import Toolsmodule

class ResearchArea(Toolsmodule):
    """
        Resarch area class.
        Generic functions to define area and track aircraft inside area

    """
    def __init__(self, sim, scr):
        Toolsmodule.__init__(self, sim, scr, self.__class__.__name__)
        cmddict = {"RAREA": ["AREA OFF, or\nlat0,lon0,lat1,lon1", \
                             "float/txt,float,[float,float,float]", \
                             lambda *args: sim.rarea.create(*args)]}
        Toolsmodule.add_stack_commands(self, cmddict)

        self.type = "Rectangle"
        self.description = "research area 1"
        self.northb = 0                         # Northern boundary latitude
        self.eastb = 0                          # Eastern boundary longitude
        self.southb = 0                         # Southern boundary latitude
        self.westb = 0                          # Western boundary longitude
        self.trackingids = []                   # IDs of tracked AC
        self.entrytime = []                     # Time AC entered RA
        self.groundspeeds = []                  # Groundspeeds
        self.surfacearea = 0                    # Surface area of RA
        self.ntraf = 0                          # Number of AC in RA
        self.passedthrough = []                 # AC that passed through RA

        self.conflicts = []                     # Conflicts: timestamp, (ac1, ac2)
        self.cd = []                            # Conlficts detected
        self.oldcd = []                         # Conflicts detected in previous update cycle
        self.conflictdist = []
        self.confperac = []

    def create(self, lat0, lon0, lat1, lon1):
        """ Create new research rectangular research area defined by lat/lon """
        if lat0 == 0 and lat1 == 0 and lon0 == 0 and lon1 == 0:
            lat0, lat1, lon0, lon1 = self.scr.getviewlatlon()
        self.northb = max(lat0, lat1)
        self.southb = min(lat0, lat1)
        self.eastb = max(lon0, lon1)
        self.westb = min(lon0, lon1)
        self.surfacearea = geo.latlondist(self.southb, self.westb, self.southb, self.eastb) * \
                            geo.latlondist(self.southb, self.eastb, self.northb, self.eastb)
        self.drawarea(self.northb, self.eastb, self.southb, self.westb)
        return True

    def drawarea(self, northb, eastb, southb, westb):
        """ Draw research area on screen """
        self.scr.objappend("LINE", "RAREA", [northb, westb, northb, eastb])
        self.scr.objappend("LINE", "RAREA", [northb, eastb, southb, eastb])
        self.scr.objappend("LINE", "RAREA", [southb, eastb, southb, westb])
        self.scr.objappend("LINE", "RAREA", [southb, westb, northb, westb])

    def acinarea(self):
        """ Returns numpy array of AC inside RA """
        traf = self.sim.traf
        i = 0
        self.inside = np.zeros(traf.gs.shape)
        while i <= traf.ntraf-1:
            self.inside[i] = self.southb <= traf.lat[i] <= self.northb and \
                     self.westb <= traf.lon[i] <= self.eastb
            i += 1
        return self.inside

    def _addpassedthrough_(self, trackedacid, entrytime, leavetime, avggroundspeed, trackingid):
        """ List of AC who entered and left the RA """

        if self.entrytime[trackingid] == self.entrytime[0]:
            # AC spawned inside the RA are not tracked
            return

        print "AC leaving RA: " + str(trackedacid)
        self.passedthrough.append((trackedacid, entrytime, leavetime, avggroundspeed))

        # Delete AC from trackingDB
        del self.trackingids[trackingid]
        del self.entrytime[trackingid]
        del self.groundspeeds[trackingid]

    def update(self):
        """ Update tracking DB """
        sim = self.sim
        traf = self.sim.traf

        self.oldcd = self.cd
        self.cd = []

        i = 0
        ntrafcounter = 0
        while i <= traf.ntraf-1:
            # Is this AC in the tracking area?
            inside = self.southb <= traf.lat[i] <= self.northb and \
                     self.westb <= traf.lon[i] <= self.eastb

            if inside:
                ntrafcounter += 1
                # Already tracking?
                if traf.id[i] in self.trackingids:
                    trackingid = self.trackingids.index(traf.id[i])
                    # Append groundspeed datapoint
                    self.groundspeeds[trackingid].append(traf.gs[i])
                else:
                    # Add the AC to the tracking DB
                    self.trackingids.append(traf.id[i])
                    #print "ADDED AN AC to TRACKINGDB"
                    self.entrytime.append(sim.simt)
                    self.groundspeeds.append([traf.gs[i]])
                # CD
                cdwithownship = [item for item in traf.asas.confpairs if item[0] == traf.id[i]]
                #cdinarea = [item for item in traf.asas.confpairs if traf.id[i] in item]
                if cdwithownship:
                    for j in range(len(cdwithownship)):
                        _, othership = cdwithownship[j]
                        if othership in self.trackingids:
                            self.cd.append(cdwithownship[j])
            else:
                # AC is not in RA
                # Were we tracking this AC in the area?
                if traf.id[i] in self.trackingids:
                    trackingid = self.trackingids.index(traf.id[i])
                    self._addpassedthrough_(self.trackingids[trackingid], \
                        self.entrytime[trackingid], sim.simt, \
                        np.average(np.array(self.groundspeeds[trackingid])), trackingid)

            i += 1  # go check next AC
        self.ntraf = ntrafcounter
        #print "Number of AC in RA: %i" % int(self.ntraf)

        newcd = list(set(self.cd) - set(self.oldcd))
        #print newcd
        if newcd:
            for i in range(len(newcd)):
                self.conflicts.append((sim.simt, newcd[i]))
                #print "ADDED NEW UNIQUE CONFLICT: "
                #print newcd[i]
        #print "Number of unique conflicts in RA: %i" % (len(self.conflictid)/2)

        self.confperac = []
        for j in range(len(traf.asas.iconf)):
            self.confperac.append(len(traf.asas.iconf[j]))
        self.conflictdist.append((sim.simt, Counter(self.confperac)))
        return
