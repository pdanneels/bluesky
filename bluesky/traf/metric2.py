import numpy as np
#import matplotlib.pyplot as plt
from math import sqrt
#from ..tools.aero import R
from ..tools.aero_np import qdrdist_vector
from ..tools.misc import degto180
    
""" 

    Metric class definition : traffic metrics
    
    Methods:
        Metric()                : constructor
        update()                : add a command to the command stack
        close()                 : close file
       
    Created by  : P. Danneels, spring 2016

"""
class geometric():
    """
    calculating geometric data for current traffic
    
    """
    def __init__(self,sim):
            self.sim = sim
            
    def calcgeo(self): # perform calculations on traf set in simulation object
            traf = self.sim.traf
            size = self.size
            self.vectV = np.zeros((self.size,1,3))
            self.vectdV = np.zeros((size,size,3))  
            self.qdrdist = np.zeros((size,size,2))
            self.dVsqr = np.zeros((size,size))
            self.dhdg = np.zeros((size,size))
            vectV = self.vectV
            vectdV = self.vectdV
            qdrdist = self.qdrdist
            dhdg = self.dhdg

            # speed vectors in Earth-Fixed reference frame meaning x points towards North, Z towards center of the Earth, right hand system
            # vectV[AC,1,[Vx,Vy,Vz]]
            vectV[:,:,0] = (traf.gs*np.sin(traf.ahdg*np.pi/180)).reshape((size,1))
            vectV[:,:,1] = (traf.gs*np.cos(traf.ahdg*np.pi/180)).reshape((size,1))
            vectV[:,:,2] = -traf.vs.reshape((size,1))
            
            # relative speed vectors
            vectdV[:,:,0] = np.subtract.outer(vectV[:,0,0],vectV[:,0,0])
            vectdV[:,:,1] = np.subtract.outer(vectV[:,0,1],vectV[:,0,1])
            vectdV[:,:,2] = np.subtract.outer(vectV[:,0,2],vectV[:,0,2])
            
            # relative speed squared
            dVsqr = np.sum(np.square(vectdV), axis=2)
            
            # realtive bearing and distance
            combslatA,combslatB = np.meshgrid(traf.lat,traf.lat)
            combslonA,combslonB = np.meshgrid(traf.lon,traf.lon)
            truebearing,distance = qdrdist_vector(combslatA.flatten(), combslonA.flatten(), combslatB.flatten(), combslonB.flatten())
            relativebearing = truebearing%360 - np.tile(traf.trk,size)%360   # get relative bearing (true bearing - heading)    
            qdrdist[:,:,0] = np.reshape(relativebearing,(size,size))
            qdrdist[:,:,1] = np.reshape(distance,(size,size))
            
            # delta heading
            dhdg = degto180(np.subtract.outer(traf.trk,traf.trk)) # in plane, no wgs
            
            # speed vector matrix in Fe [AC,1,[Vx,Vy,Vz]], 
            # distance matrix [AC,AC,[relativebearing,distance]] WATCH OUT: relative bearing on diagonal is -heading 
            # relative speed matrix
            return vectV, qdrdist, dVsqr, dhdg
    def update(self):
        self.size = self.sim.traf.gs.size
        self.vectV,self.qdrdist,self.dVsqr,self.dhdg = self.calcgeo()
          
class metric_TD():
    """
    METRIC TRAFFIC DENSITY
    
    """
    def __init__(self, sim):
        self.sim = sim
    
    def update(self,geo):
        return 0
    
class metric_CA():
    """
    METRIC CONFLICTS/AC
    
    """
    def __init__(self, sim):
        self.sim = sim
    
    def update(self,geo):
        traf = self.sim.traf
        ca = float(traf.dbconf.nconf)/traf.ntraf
        print "Conflicts per AC: " + str(ca)
        return ca
    
class metric_Cr():
    """
    METRIC 3: CONFLICT RATE
    
    Cr = avgVg * R * avgT / ( A * totT )
    with:   - avgVg is average ground velocity
            - R is speration mimimum
            - avgT is average time in research area
            - A is research area
            - totT is total observation time
        
    """
    def __init__(self, sim):
        self.sim = sim
    
    def update(self,geo):
        #traf = self.sim.traf
        #cr = np.average(traf.gs)*R*avgT/A/totT
        #print "Collision rate: " + str(cr)
        return 0
        
class metric_Vrel():
    """
    METRIC 4: RELATIVE VELOCITY
    
    """ 
    def __init__(self,sim):
        self.sim = sim

    def update(self,geo):
        avgdV = sqrt(np.average(geo.dVsqr))
        print "Average dV: " + str(int(avgdV))
        return avgdV
            
class metric_dHDG():
    """
    METRIC 5: DELTA HEADING
    
    """ 
    def __init__(self,sim):
        self.sim = sim
    def update(self,geo):
        mask = np.ones(geo.dhdg.shape, dtype=bool)
        mask = np.triu(mask,1)
        avgdHDG = np.average(np.abs(geo.dhdg[mask]))
        print "Average dHDG: " + str(int(avgdHDG))
        return avgdHDG
    
class metric_rdot():
    """
    METRIC 6: RANGE RATE
    project vectV on dist to get rdot, requires qdrdist (from speed_vectors function)
    
    """ 
    def __init__(self,sim):
        self.sim = sim
        self.n = len(sim.traf.gs)
 
    def calcrdot(self, qdrdist):
        traf = self.sim.traf
        self.rdot = np.zeros((self.n,self.n))
        bearingcomponent = np.cos(np.radians(qdrdist[:,:,0])) # get cosine out of for-loop and do once with np
        np.fill_diagonal(bearingcomponent, 0) # set zero for own
        for i in range(self.n):
            for j in range(self.n):
                self.rdot[i,j] = traf.gs[i]*bearingcomponent[i][j]+traf.gs[j]*bearingcomponent[j][i]
        return self.rdot #range rate
        
    def update(self,geo):
        self.n = len(self.sim.traf.gs)
        rdot = self.calcrdot(geo.qdrdist)
        mask = np.ones(rdot.shape, dtype=bool)
        mask = np.triu(mask,1)
        avgrdot = np.average(rdot[mask])
        print "Average rdot: " + str(int(avgrdot))
        return avgrdot
    
class metric_severitytime():
    """
    METRIC 7: SEVERITY TIME
    
    """ 
    def __init__(self,sim):
        self.sim = sim
    def update(self):
        pass

class Metrics():
    """ 
    Metric class definition : traffic metrics

    Methods:
        Metric()                : constructor
        update()                : update the enabled metrics
    
    """
    
    def __init__(self,sim):
        self.sim = sim
        # Last time for which Metrics.update was called 
        self.swmetrics = True   # Toggle metrics module
        self.t0 = -9999   # force first time call, update
        self.t1 = -9999   # force first time call, plot  

        # Set time interval in seconds
        self.dt = 1  # [seconds]
        self.dtplot = 5 # [seconds]
        
        # Metrics instances (not geo, we want to recreate that each update)
        self.vrel = metric_Vrel(sim)    
        self.cr = metric_Cr(sim)
        self.td = metric_TD(sim)
        self.ca = metric_CA(sim)
        self.rdot = metric_rdot(sim)
        self.sevtime = metric_severitytime(sim)
        self.dhdg = metric_dHDG(sim)
        
        return
                
    def update(self):
        sim = self.sim
        log = self.sim.datalog
        # Check if configured and there is actual traffic
        if not self.swmetrics or sim.traf.ntraf < 1:
            return
        # Only do something when time is there 
        if abs(sim.simt-self.t0)<self.dt:
            return
        self.t0 = sim.simt  # Update time for scheduler
        
        if sim.simt >= 0: # Perform update
            geo = geometric(sim)        # first create new set of geometric data from traffic
            geo.update()
            log.updatem1("avgdV", str(self.vrel.update(geo)))       # average relative velocity
            log.updatem1("Cr", str(self.cr.update(geo)))            # collision rate
            log.updatem1("Td", str(self.td.update(geo)))            # traffic density
            log.updatem1("CA", str(self.ca.update(geo)))            # collisions devided by #AC
            log.updatem1("avgrdot", str(self.rdot.update(geo)))     # average range rate
            log.updatem1("avgdHDG", str(self.dhdg.update(geo)))     # average range rate  
        return
    
    def plot(self):
        sim = self.sim
        # Check if configured and there is actual traffic
        if np.sum(self.swmetrics) < 1 or sim.traf.ntraf < 1:
            return
        # Only do something when time is there 
        if abs(sim.simt-self.t1)<self.dtplot:
            return
        self.t1 = sim.simt

        sim.pause()
        
        if self.metric_number > 0: #no plot for CoCa metric
            self.metric[self.metric_number].plot(sim)
            
        sim.start()
        return