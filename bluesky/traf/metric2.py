#import os
#from time import time,gmtime,strftime
import numpy as np
#import matplotlib.pyplot as plt
#from math import degrees
#import collections
#from collections import defaultdict
#import itertools as IT
#from ..tools.misc import tim2txt
from ..tools.aero import R
from ..tools.aero_np import qdrdist_vector
    
""" 

    Metric class definition : traffic metrics
    
    Methods:
        Metric()                : constructor
        update()                : add a command to the command stack
        close()                 : close file
       
    Created by  : P. Danneels
    Based on and expanded upon original version of J. Hoekstra and D. Michon


"""

class metric_TD():
    """
    METRIC TRAFFIC DENSITY
    
    """
    def __init__(self, sim):
        pass
    
    def update(self):
        pass

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
    def cr(self):
        # TODO: A, totT, avgT: So tie this to the research area
        # cr = np.average(sim.traf.gs)*R*avgT/A/totT
        #cr = np.arverage(sim.traf.gs)*R/A
        #return cr
        pass
    
    def update(self):
        pass
        
class metric_Vrel():
    """
    METRIC 4: RELATIVE VELOCITY
    
    """ 
    def __init__(self,sim):
            self.sim = sim
    def speed_vectors(self): # perform calculations on traf set in simulation object
            # speed vectors in Earth-Fixed reference frame meaning x points towards North, Z towards center of the Earth, right hand system
            # vectV[AC,1,[Vx,Vy,Vz]]
            size = self.sim.traf.gs.size
            vectV = np.zeros((size,1,3))
            vectV[:,:,0] = (self.sim.traf.gs*np.sin(self.sim.traf.ahdg*np.pi/180)).reshape((size,1))
            vectV[:,:,1] = (self.sim.traf.gs*np.cos(self.sim.traf.ahdg*np.pi/180)).reshape((size,1))
            vectV[:,:,2] = -self.sim.traf.vs.reshape((size,1))
            
            # relative speed vectors
            vectdV = np.zeros((size,size,3))                        
            vectdV[:,:,0] = np.subtract.outer(vectV[:,0,0],vectV[:,0,0])
            vectdV[:,:,1] = np.subtract.outer(vectV[:,0,1],vectV[:,0,1])
            vectdV[:,:,2] = np.subtract.outer(vectV[:,0,2],vectV[:,0,2])
            
            # relative speed squared
            dVsqr = np.sum(np.square(vectdV), axis=2)
                        
            # dist = [ac][ac][bearing,distance]
            n = len(self.sim.traf.lat)
            qdrdist = np.zeros((n,n,2))            
            for i in range(n):   
                for j in range(n):
                    qdrdist[i][j][0], qdrdist[i][j][1] = qdrdist_vector(self.sim.traf.lat[i], self.sim.traf.lon[i], self.sim.traf.lat[j], self.sim.traf.lon[j])
            
            return vectV, qdrdist, dVsqr # speed vector matrix in Fe [AC,1,[Vx,Vy,Vz]], distance matrix [AC,AC,[bearing,distance]], relative speed matrix
            
    def update(self):
        pass
            
class metric_dHDG():
    """
    METRIC 5: DELTA HEADING
    
    """ 
    def __init__(self,sim):
        self.sim = sim
    def update(self):
        pass
    
class metric_rdot():
    """
    METRIC 6: RANGE RATE
    project vectV on dist to get rdot, requires qdrdist (from speed_vectors function)
    
    """ 
    def __init__(self,sim):
        self.n = len(sim.traf.lat)
        self.rdot = np.zeros((self.n,self.n))
 
    def rdot(self, qdrdist):
        bearingcomponent = np.cos(qdrdist[:][:][0]) # get cosine out of for-loop and do once with np
        for i in range(self.n):
            for j in range(self.n):
                self.rdot[i,j] = self.sim.traf.gs[i]*bearingcomponent[i][j]+self.sim.traf.gs[j]*bearingcomponent[j][i]
        return self.rdot #range rate
        
    def update(self,speedvect,logmetric):
        _,qrdist,_ = speedvect()
        _,avgrdot = self.rdot(qrdist)
        logmetric("avgrdot" + str(avgrdot))
    
class metric_severitytime():
    """
    METRIC 7: SEVERITY TIME
    
    """ 
    def __init__(self,sim):
        self.sim = sim
    def update(self):
        pass

class Metric():
    """ 
    Metric class definition : traffic metrics

    Methods:
        Metric()                : constructor
        update()                : update the enabled metrics
    
    """
    
    def __init__(self,sim):   
        # Last time for which Metrics.update was called 
        self.t0 = -9999   # force first time call, update
        self.t1 = -9999   # force first time call, plot  

        # Set time interval in seconds
        self.dt = 1  # [seconds]
        self.dtplot = 5 # [seconds]
        
        self.name = ("TD-Metric","Cr-Metric","Vrel-Metric","dHDG-Metric","rdot-Metric","severity-Metric")
        self.metric = np.vectorize(metric_TD(sim), metric_Cr(sim), metric_Vrel(sim), metric_dHDG(sim), metric_rdot(sim), metric_severitytime(sim))
        self.swmetric = [0,0,0,0,0,0]
        
        return
                
    def update(self,sim):
        # Check if configured and there is actual traffic
        if np.sum(self.swmetric) < 1 or sim.traf.ntraf < 1:
            return
        # Only do something when time is there 
        if abs(sim.simt-self.t0)<self.dt:
            return
        self.t0 = sim.simt  # Update time for scheduler
        
        if sim.simt >= 0: # Perform update
            for i in range(self.metric):
                if self.swmetric[i]: # If enabled, update
                    self.metric[i].update()
            
    def plot(self,sim):
        # Check if configured and there is actual traffic
        if np.sum(self.swmetric) < 1 or sim.traf.ntraf < 1:
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