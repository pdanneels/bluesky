"""
This module provides a connection to aircraft saved in a mongoDB database

    A thread is spawned which continuesly fetches data from a MongoDB server.
    On the interval set the update function will grab the dataset from the queue and process it.

"""

import pymongo
import threading
import Queue
import time
from datetime import datetime
from ..tools.mongodb_filterpipe import getfilter
from .. import stack

class MongoDB():
    def __init__(self, sim):
        self.sim = sim
        self.traf = sim.traf
        self.add_stack_commands(sim)

        HOST = 'danneels.nl'
        PORT = '27018'
        USERNAME = 'fr24ro'
        PASSWORD = 'TVewF3HCS52U'
        USERNAMEMETR = 'metropolisrw'
        PASSWORDMETR = 'Mq2vUNuXAwz8'
        self.DB = 'fr24'
        self.DBMETR = 'metropolis'
        
        self.timer0 = -9999
        self.INTERVALTIME = 10      # Number of seconds simtime between data processing
        self.MPAUZETIME = 2         # Number of seconds to sleep between MongoDB fetches
        self.TIMECHUNK = 200        # Timeframe for aircraft records to grab in seconds
        self.LOSTSIGNALTIMOUT = 100 # Timeout for aircraft singal
        self.fetchstart = 0         # Start time fetching data from server
        self.fetchfin = 0           # Finish time fetching data from server

        self.MODE = 'live'          # Mode, can be 'live', 'replay' or 'metropolis'
        replaystart = '2016_08_21:10_30'  # Set to time you want to start replay "%Y_%m_%d:%H_%M"
        metropoliscollection = 'OFF_FULLMIX_SET1_SNAP_fm_morninghgh_cr_off_ii_1407112255'

        if self.MODE == 'replay':
            self.MCONNECTIONSTRING = "mongodb://"+USERNAME+":"+PASSWORD+"@"+HOST+":"+PORT+"/"+self.DB
            self.STARTTIME = time.mktime(datetime.strptime(replaystart, "%Y_%m_%d:%H_%M").timetuple())
            self.COLL = 'EHAM_' + replaystart[:10]
            self.connectionoutput = "Connecting to collection: %s at %s" % \
                    (self.COLL, str(datetime.fromtimestamp(self.STARTTIME)))
        elif self.MODE == 'metropolis':
            self.MCONNECTIONSTRING = "mongodb://"+USERNAMEMETR+":"+PASSWORDMETR+"@"+HOST+":"+PORT+"/"+self.DBMETR
            self.COLL = metropoliscollection

        elif self.MODE == 'live':
            self.MCONNECTIONSTRING = "mongodb://"+USERNAME+":"+PASSWORD+"@"+HOST+":"+PORT+"/"+self.DB
            self.STARTTIME = time.time()
            self.COLL = 'EHAM_' + datetime.utcnow().strftime("%Y_%m_%d")
            self.connectionoutput = "Connecting to collection: %s at UTC now." % self.COLL
        else:
            print "No MongoDB connection mode defined."
        
        self.MDBrun = threading.Event()
        self.dataqueue = Queue.Queue(maxsize=0)
    
    def add_stack_commands(self, sim):
        cmddict = {"MONGODB": [
                    "MONGODB ON/OFF",
                    "onoff",
                    lambda *args: sim.mdb.toggle(*args)]}
        stack.append_commands(cmddict)

    def toggle(self, flag):
        if flag:
            print "Starting %s mode." % self.MODE
            print self.connectionoutput
            self.mdbthread()
            self.sim.reset()
        else:
            self.MDBrun.clear()

    def mdbthread(self):
        """ This function starts a background process for constant data fetching """
        MCOLL = self.connectmdb()
        self.MDBrun.set()
        thread = threading.Thread(target=self.getmdbdata, args=(MCOLL,))
        thread.daemon = True
        thread.start()

    def connectmdb(self):
        """ This function connects to a collection on a mongoDB server """
        try: # Connection to Mongo DB
            MCONN = pymongo.MongoClient(self.MCONNECTIONSTRING)
            MDB = MCONN[self.DB]
            print "Connected successfully to MongoDB server."
            return MDB[self.COLL]
        except pymongo.errors.ConnectionFailure, error:
            print "Could not connect to MongoDB: %s" % error
            return None

    def getmdbdata(self, MCOLL):
        """ This function collects data from the mongoDB server """
        if self.MODE == 'metropolis':
            self.STARTTIME = MCOLL.find_one(sort=[('ts', 1)])['ts']
        while True:
            if not self.MDBrun.is_set():
                print "MongoDB connector thread suspended"
            self.MDBrun.wait()
            if self.MODE == 'replay':
                mintime = self.STARTTIME + self.sim.simt - self.TIMECHUNK
                maxtime = self.STARTTIME + self.sim.simt
            elif self.MODE == 'live':
                mintime = time.time() - 300
                maxtime = time.time()
            else:
                mintime = self.STARTTIME
                maxtime = 0

            filterpipe = getfilter(self.MODE, mintime, maxtime)

            self.fetchstart = time.time()
            filtereddata = list(MCOLL.aggregate(filterpipe))
            if len(filtereddata) > 0:
                self.dataqueue.put(filtereddata)
            else:
                print "No aircraft found in timewindow: " + str(datetime.fromtimestamp(mintime)) + " " + str(datetime.fromtimestamp(maxtime))
            self.fetchfin = time.time()
            if self.fetchfin - self.fetchstart > 10:
                print "Fetching dataset took more than 10 seconds: " + \
                        str(int(self.fetchfin - self.fetchstart)) + " seconds"
            time.sleep(self.MPAUZETIME)

    def stack_all_commands(self, dataset):
        """ Create and stack command """
        createcount = 0
        delay = time.time() - self.fetchfin
        print "Dataset delay: " + str(delay) + " seconds"
        for pos in dataset:
            acid = str(pos['icao'])
            if self.traf.id2idx(acid) < 0: # Check if AC exists
                if self.STARTTIME + self.sim.simt - pos['ts'] - delay < 10 + self.INTERVALTIME:
                    cmdstr = 'CRE %s, %s, %f, %f, %f, %d, %d' % \
                            (acid, pos['mdl'], pos['loc']['lat'], \
                            pos['loc']['lng'], pos['hdg'], pos['alt'], pos['spd'])
                    stack.stack(cmdstr)
                    createcount = createcount + 1
            else:
                if self.STARTTIME + self.sim.simt - pos['ts'] - delay > self.LOSTSIGNALTIMOUT:
                    print "Lost signal for %s %s seconds" % \
                            (pos['icao'], str(int(self.STARTTIME + self.sim.simt - pos['ts'])))
                    stack.stack('DEL %s' % pos['icao'])
                else:
                    if self.STARTTIME + self.sim.simt - pos['ts'] < self.INTERVALTIME + delay + 10:
                        cmdstr = 'MOVE %s, %f, %f, %d' % \
                            (acid, pos['loc']['lat'], pos['loc']['lng'], pos['alt'])
                        stack.stack(cmdstr)

                        cmdstr = 'HDG %s, %f' % (acid, pos['hdg'])
                        stack.stack(cmdstr)

                        cmdstr = 'SPD %s, %f' % (acid, pos['spd'])
                        stack.stack(cmdstr)
        if createcount > 0:
            print "Created " + str(createcount) + " AC"
        return

    def update(self):
        """ Update AC in traf database on scheduled interval """
        sim = self.sim
        # Only do something when time is there
        if abs(sim.simt - self.timer0) < self.INTERVALTIME:
            return
        self.timer0 = sim.simt  # Update time for scheduler

        if self.dataqueue.qsize() > 0:
            start = time.time()
            print str(self.dataqueue.qsize()) + " dataset found in queue, processing...."
            dataset = self.dataqueue.get()
            self.dataqueue.task_done()
            self.dataqueue.queue.clear()
            self.stack_all_commands(dataset)
            print "Done, it took: %s seconds to process %i records" % (str(time.time() - start), len(dataset))
