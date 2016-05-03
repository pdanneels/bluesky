""" 
Datalog class definition : Data logging class

Methods:
    Datalog(filename)  : constructor

    write(txt)         : add a line to the datalogging buffer
    save()             : save data to file
   
Created by  : Jacco M. Hoekstra (TU Delft)
Date        : October 2013

Modifation  :   - added start method including command processing
                - added CSV-style saving
By          : P. Danneels
Date        : April 2016

"""
import os
import numpy as np
from misc import tim2txt
from time import strftime, gmtime

#-----------------------------------------------------------------


class Datalog():
    def __init__(self, sim):
        self.sim = sim
        # Create a buffer and save filename
        self.fname = os.path.dirname(__file__) + "/../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSky.txt", gmtime())
        self.fnamem1 = os.path.dirname(__file__) + "/../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSky-metrics1.txt", gmtime())
        self.fnamem2 = os.path.dirname(__file__) + "/../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSky-metrics2.txt", gmtime())
        self.buffer = ["time;acid;gs;vs;track;lat;long\n"]        # Log data
        self.m1buffer = ["time;metric;value\n"]   
        self.aclist = np.zeros(1)                                 # AC list to log
        self.dt = 1.                                              # Default logging interval
        self.t0 = -9999                                           # Timers
        self.t1 = -9999
        self.swlog = False                                        # Logging started
        return

    def start(self, acbatch, dt):
        traf = self.sim.traf
        if len(traf.id) == 0:
            return False, "LOG: No traffic present, log not started."
        self.id2idx = np.vectorize(traf.id2idx)  # vectorize function
        if acbatch is None:  # No batch defined, log all
            self.aclist = self.id2idx(traf.id)
        elif acbatch == 'AREA':
            if traf.swarea:
                self.aclist = self.id2idx(traf.id)
            else:
                return False, "LOG: AREA DISABLED, LOG NOT STARTED"
        else:
            idx = self.id2idx(acbatch)
            if idx < 0:  # not an acid or ac does not exist
                return False, "LOG: ACID " + acbatch + " NOT FOUND"
            else:
                self.aclist = idx
        self.dt = dt
        if self.aclist.any():
            self.swlog = True
        return True, "LOG started."

    def update(self):
        sim = self.sim
        if not self.swlog:                     # Only update when logging started an traffic is selected
            return
        if abs(sim.simt - self.t0) < self.dt:  # Only do something when time is there
            return
        self.t0 = sim.simt                     # Update time for scheduler

        t = tim2txt(sim.simt)                  # Nicely formated time

        if self.aclist.ndim < 1:               # Write to buffer for one AC
            self.writebuffer(t, self.aclist)
        else:                                  # Write to buffer for multiple AC
            for i in self.aclist:
                self.writebuffer(t, self.aclist[i])
        return
        
    def writebuffer(self, t, idx):
        traf = self.sim.traf
        self.buffer.append(t + ";" +
                           str(traf.id[idx]) + ";" +
                           str(traf.gs[idx]) + ";" +
                           str(traf.vs[idx]) + ";" +
                           str(traf.trk[idx]) + ";" +
                           str(traf.lat[idx]) + ";" +
                           str(traf.lon[idx]) + "\n")
        return
    
    ############################
    #   General save funtion   #
    ############################
    def save(self):  # Write buffer to file
        if self.swlog:                  # save log if logging enabled
            f = open(self.fname, "w")
            f.writelines(self.buffer)
            f.close()
        self.savem1()                   # save metrics log 1
        return
        
    ###############
    #   METRICS   #
    ###############
    def updatem1(self, var, val):
        sim = self.sim
        t = tim2txt(sim.simt)                   # Nicely formated time
        self.writem1(t, var, val)
        return
    
    def writem1(self,t,var,val):
        self.m1buffer.append(t + ";" + var + ";" + val + "\n")
        return

    def savem1(self):  # Write buffer to file
        f = open(self.fnamem1, "w")
        f.writelines(self.m1buffer)
        f.close()
        return
