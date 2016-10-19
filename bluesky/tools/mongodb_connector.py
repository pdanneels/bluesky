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
from .. import settings

# Ignores dynamically created settings:
# pylint: disable=no-member

class MongoDB():
    """ Class contains functions allowing to set up a connection with a MongoDB database """
    def __init__(self, sim):
        self.sim = sim
        self.traf = sim.traf
        self.add_stack_commands(sim)

        host = settings.mdb_host
        port = settings.mdb_port
        username = settings.mdb_username
        password = settings.mdb_password
        usernamemetr = settings.mdb_username2
        passwordmetr = settings.mdb_password2
        self.database = settings.mdb_db
        self.databasemetr = settings.mdb_db2

        self.timer0 = -9999
        self.intervaltime = 10          # Number of seconds simtime between data processing
        self.mpauzetime = 2             # Number of seconds to sleep between MongoDB fetches
        self.timechunk = 200            # Timeframe for aircraft records to grab in seconds
        self.lostsignaltimeout = 100    # Timeout for aircraft singal
        self.fetchstart = 0             # Start time fetching data from server
        self.fetchfin = 0               # Finish time fetching data from server

        self.mode = 'live'          # Mode, can be 'live', 'replay' or 'metropolis'
        replaystart = '2016_08_21:10_30'  # Set to time you want to start replay "%Y_%m_%d:%H_%M"
        metropoliscollection = 'OFF_FULLMIX_SET1_SNAP_fm_morninghgh_cr_off_ii_1407112255'

        if self.mode == 'replay':
            self.mconnectionstring = \
                "mongodb://"+username+":"+password+"@"+host+":"+port+"/"+self.database
            self.starttime = time.mktime(datetime.strptime(replaystart, "%Y_%m_%d:%H_%M").timetuple())
            self.coll = 'EHAM_' + replaystart[:10]
            self.connectionoutput = "Connecting to collection: %s at %s" % \
                    (self.coll, str(datetime.fromtimestamp(self.starttime)))
        elif self.mode == 'metropolis':
            self.mconnectionstring = \
                "mongodb://"+usernamemetr+":"+passwordmetr+"@"+host+":"+port+"/"+self.databasemetr
            self.coll = metropoliscollection

        elif self.mode == 'live':
            self.mconnectionstring = \
                "mongodb://"+username+":"+password+"@"+host+":"+port+"/"+self.database
            self.starttime = time.time()
            self.coll = 'EHAM_' + datetime.utcnow().strftime("%Y_%m_%d")
            self.connectionoutput = "Connecting to collection: %s at UTC now." % self.coll
        else:
            print "No MongoDB connection mode defined."

        self.mdbkill = threading.Event()
        self.mdbrun = threading.Event()
        self.dataqueue = Queue.Queue(maxsize=0)

    @staticmethod
    def add_stack_commands(sim):
        """ Add mongodb command to stack """
        cmddict = {"MONGODB": [ \
                    "MONGODB ON/OFF", \
                    "onoff", \
                    lambda *args: sim.mdb.toggle(*args)]}
        stack.append_commands(cmddict)

    def toggle(self, flag):
        """ turn the connector on or off """
        if flag:
            print "Starting %s mode." % self.mode
            print self.connectionoutput
            self.mdbthread()
            self.sim.reset()
        else:
            self.dataqueue.queue.clear()
            self.mdbkill.set() # stop thread loop
            # self.mdbrun.clear() # suspends thread

    def mdbthread(self):
        """ This function starts a background process for constant data fetching """
        mdbcoll = self.connectmdb()
        self.mdbkill.clear()
        self.mdbrun.set()
        thread = threading.Thread(target=self.getmdbdata, args=(mdbcoll,))
        thread.daemon = True
        thread.start()

    def connectmdb(self):
        """ This function connects to a collection on a mongoDB server """
        try: # Connection to Mongo DB
            mconn = pymongo.MongoClient(self.mconnectionstring)
            mdb = mconn[self.database]
            print "Connected successfully to MongoDB server."
            return mdb[self.coll]
        except pymongo.errors.ConnectionFailure, error:
            print "Could not connect to MongoDB: %s" % error
            return None

    def getmdbdata(self, mdbcoll):
        """ This function collects data from the mongoDB server """
        if self.mode == 'metropolis':
            self.starttime = mdbcoll.find_one(sort=[('ts', 1)])['ts']
        while True:
            if self.mdbkill.is_set():
                print "MongoDB connector thread killed"
                break
            if not self.mdbrun.is_set():
                print "MongoDB connector thread suspended"
            self.mdbrun.wait()
            if self.mode == 'replay':
                mintime = self.starttime + self.sim.simt - self.timechunk
                maxtime = self.starttime + self.sim.simt
            elif self.mode == 'live':
                mintime = time.time() - 300
                maxtime = time.time()
            else:
                mintime = self.starttime
                maxtime = 0

            filterpipe = getfilter(self.mode, mintime, maxtime)

            self.fetchstart = time.time()
            filtereddata = list(mdbcoll.aggregate(filterpipe))
            if len(filtereddata) > 0:
                self.dataqueue.put(filtereddata)
            else:
                print 'No aircraft found in timewindow: %s %s' % \
                    (str(datetime.fromtimestamp(mintime)), str(datetime.fromtimestamp(maxtime)))
            self.fetchfin = time.time()
            if self.fetchfin - self.fetchstart > 10:
                print "Fetching dataset took more than 10 seconds: " + \
                        str(int(self.fetchfin - self.fetchstart)) + " seconds"
            time.sleep(self.mpauzetime)

    def stack_all_commands(self, dataset):
        """ Create and stack command """
        createcount = 0
        delay = time.time() - self.fetchfin
        print "Dataset delay: " + str(delay) + " seconds"
        for pos in dataset:
            acid = str(pos['icao'])
            if self.traf.id2idx(acid) < 0: # Check if AC exists
                if self.starttime + self.sim.simt - pos['ts'] - delay < 10 + self.intervaltime:
                    cmdstr = 'CRE %s, %s, %f, %f, %f, %d, %d' % \
                            (acid, pos['mdl'], pos['loc']['lat'], \
                            pos['loc']['lng'], pos['hdg'], pos['alt'], pos['spd'])
                    stack.stack(cmdstr)
                    createcount = createcount + 1
            else:
                if self.starttime + self.sim.simt - pos['ts'] - delay > self.lostsignaltimeout:
                    print "Lost signal for %s %s seconds" % \
                            (pos['icao'], str(int(self.starttime + self.sim.simt - pos['ts'])))
                    stack.stack('DEL %s' % pos['icao'])
                else:
                    if self.starttime + self.sim.simt - pos['ts'] < self.intervaltime + delay + 10:
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
        if abs(sim.simt - self.timer0) < self.intervaltime:
            return
        self.timer0 = sim.simt  # Update time for scheduler

        if self.dataqueue.qsize() > 0:
            start = time.time()
            print str(self.dataqueue.qsize()) + " dataset found in queue, processing...."
            dataset = self.dataqueue.get()
            self.dataqueue.task_done()
            self.dataqueue.queue.clear()
            self.stack_all_commands(dataset)
            print "Done, it took: %s seconds to process %i records" % \
                (str(time.time() - start), len(dataset))
