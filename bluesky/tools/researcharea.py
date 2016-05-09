import numpy as np
from ..tools.aero_np import latlondist
""" 

    Research area
    
        This class is a set of standalone features to define an area and track the AC inside.
        It does not interfere with the regular Area function in ..traf.traffic
    
    Classes:
        area()             : define area, return ac in area

        
    Created by:     P. Danneels, spring 2016
                    inspired by oringinal area functions in ..traf.traffic

"""
class Rarea():
    
    def __init__(self,sim,scr):
        self.sim = sim
        self.scr = scr
        self.type = "Rectangle"
        self.description = "research area 1"
        self.northb = 0    
        self.eastb = 0
        self.southb = 0
        self.westb = 0
        self.atimeid = []
        self.entertime = []
        self.leavetime = []
        self.staytime = []
        self.gs = []
        self.a = 0
        self.ntraf = 0
    
    def create(self, lat0, lon0, lat1, lon1):
        scr = self.scr
        if lat0 == 0 and lat1 == 0 and lon0 == 0 and lon1 == 0 :
            lat0,lat1,lon0,lon1 = scr.getviewlatlon()
        self.northb = max(lat0, lat1)
        self.southb = min(lat0, lat1)
        self.eastb = max(lon0, lon1)
        self.westb = min(lon0, lon1)
        self.a = latlondist(self.southb, self.westb, self.southb, self.eastb) * \
                 latlondist(self.southb, self.eastb, self.northb, self.eastb)
        scr.objappend(1, "RAREA", [self.northb, self.westb, self.northb, self.eastb])
        scr.objappend(1, "RAREA", [self.northb, self.eastb, self.southb, self.eastb])
        scr.objappend(1, "RAREA", [self.southb, self.eastb, self.southb, self.westb])
        scr.objappend(1, "RAREA", [self.southb, self.westb, self.northb, self.westb])
        return True
            
    def ainarea(self):
        """
            Returns numpy array of AC inside RA. 
            It is the shape of the traffic arrays and sets a boolean value for every AC
        
        """
        traf = self.sim.traf
        i = 0
        self.inside = np.zeros(traf.gs.shape)
        while (i <= traf.ntraf-1):
            self.inside[i] = self.southb <= traf.lat[i] <= self.northb and \
                     self.westb <= traf.lon[i] <= self.eastb
            i += 1
        return self.inside
    
    def update(self):
        """
            update tracking DB
        
        """
        sim = self.sim
        traf = sim.traf

        i =0
        while (i <= traf.ntraf-1):
            # Is this AC in the tracking area?
            inside = self.southb <= traf.lat[i] <= self.northb and \
                     self.westb <= traf.lon[i] <= self.eastb
            
            if inside:                                      # AC is in
                if traf.id[i] in self.atimeid:                  # Are we tracking this AC in the area?
                    pass                                        # Already in tracking DB
                else:
                    self.atimeid.append(traf.id[i])             # Add the AC to the tracking DB
                    self.entertime.append(sim.simt) 
                    self.leavetime.append(0)
                    self.staytime.append(0)
                    self.gs.append(traf.gs[i])
            else:                                           # AC is not in area
                if traf.id[i] in self.atimeid:                  # Are we tracking this AC in the area?
                    aindex = self.atimeid.index(traf.id[i])     # Get the location in the tracking DB
                    if self.leavetime[aindex] == 0:              # Is leavetime already recorded?
                        print "AC leaving RA: " + str(traf.id[i])
                        self.leavetime[aindex] = sim.simt       # AC just left, set leavetime
            i += 1  # go check next AC
        self.ntraf = np.array(self.leavetime).size - np.count_nonzero(np.array(self.leavetime))
        return