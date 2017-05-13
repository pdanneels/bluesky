"""
This module provides a connection to aircraft saved in a mongoDB database

    A thread is spawned which continuesly fetches data from a MongoDB server.
    On the interval set the update function will grab the dataset from the queue and process it.

"""
from .. import Toolsmodule
from ... import settings
import pymongo
import threading
import Queue
import time
from datetime import datetime
from .filterpipe import getfilter

# Ignores dynamically created settings in pylint:
# pylint: disable=no-member

class MongoDB(Toolsmodule):
    """ Class contains functions allowing to set up a connection with a MongoDB database """
    def __init__(self, sim, scr):
        Toolsmodule.__init__(self, sim, scr, self.__class__.__name__)
        cmddict = {"MONGODB": ["MONGODB ON/OFF,[LIVE/REPLAY]", "onoff,[txt]", \
                    lambda *args: sim.mdb.toggle(args)]}
        Toolsmodule.add_stack_commands(self, cmddict)

        host = settings.mdb_host
        port = settings.mdb_port
        username = settings.mdb_username
        password = settings.mdb_password
        usernamemetr = settings.mdb_username2
        passwordmetr = settings.mdb_password2
        self.database = settings.mdb_db
        self.databasemetr = settings.mdb_db2

        self.achandled = []
        self.swsupermdb = True
        self.skip = False
        self.timer0 = -9999
        self.intervaltime = 10          # Number of seconds simtime between data processing
        self.mpauzetime = 2             # Number of seconds to sleep between MongoDB fetches
        self.timechunk = 300            # Timeframe for aircraft records to grab in seconds
        self.lostsignaltimeout = 100    # Timeout for aircraft singal
        self.fetchstart = 0             # Start time fetching data from server
        self.fetchfin = 0               # Finish time fetching data from server

        self.mode = 'replay'          # Mode, can be 'live', 'replay' or 'metropolis'
        replaystart = '2017_01_10:13_00'  # Set to time you want to start replay "%Y_%m_%d:%H_%M"
        metropoliscollection = 'OFF_FULLMIX_SET1_SNAP_fm_morninghgh_cr_off_ii_1407112255'
        if self.mode == 'metropolis':
            self._buildconnectionstring_(host, port, usernamemetr, passwordmetr, \
                                        self.databasemetr, metropoliscollection)
        else:
            self._buildconnectionstring_(host, port, username, password, self.database, replaystart)

        self.mdbkill = threading.Event()
        self.mdbrun = threading.Event()
        if self.mode == 'replay':
            self.dataqueue = Queue.Queue(maxsize=5)
        else:
            self.dataqueue = Queue.LifoQueue(maxsize=0)

    def _buildconnectionstring_(self, host, port, username, password, database, extra):
        """ Build the connection string based on the mode """
        self.mconnectionstring = "mongodb://"+username+":"+password+"@"+host+":"+port+"/"+database
        if self.mode == 'replay':
            self.starttime = time.mktime(datetime.strptime(extra, "%Y_%m_%d:%H_%M").timetuple())
            if self.swsupermdb:
                self.coll = 'tempsuperset'
                self._createsuperset_(self.starttime, self.starttime+3600*5, 'EHAM_' + extra[:10])
            else:
                self.coll = 'EHAM_' + extra[:10]
            self.connectionoutput = "NOTICE: Connecting to collection: %s at %s" % \
                    (self.coll, str(datetime.fromtimestamp(self.starttime)))
        elif self.mode == 'metropolis':
            self.coll = extra
        elif self.mode == 'live':
            self.starttime = time.time()
            self.coll = 'EHAM_' + datetime.utcnow().strftime("%Y_%m_%d")
            self.connectionoutput = "NOTICE: Connecting to collection: %s at UTC now." % self.coll
        else:
            print "No MongoDB connection mode defined."

    @staticmethod
    def _connectmdb_(mconnectionstring, database, coll):
        """ This function returns a MongoDB connection """
        try: # Connection to Mongo DB
            mconn = pymongo.MongoClient(mconnectionstring)
            mdb = mconn[database]
            print "NOTICE: Connected successfully to MongoDB server."
            return mconn, mdb[coll]
        except pymongo.errors.ConnectionFailure, error:
            print "ERROR: Could not connect to MongoDB: %s" % error
            return None, None

    def _createsuperset_(self, mintime, maxtime, origin):
        """ This function creates a smaller filterd data collection to speed up datagathering """
        print "NOTICE: Running in super MDB mode"
        filterpipe = getfilter('createsuperset', mintime, maxtime, self.swsupermdb)
        mconn, mdbcoll = self._connectmdb_(self.mconnectionstring, self.database, origin)
        mdbcoll.aggregate(filterpipe)
        mconn.close()
        print "NOTICE: Created superset"

    def _getmdbdata_(self, mdbcoll):
        """ This function collects data from the mongoDB server """
        updatecycles = 0
        if self.mode == 'metropolis':
            self.starttime = mdbcoll.find_one(sort=[('ts', 1)])['ts']
        while True:
            if self.mdbkill.is_set():
                print "NOTICE: MongoDB connector thread killed"
                break
            if not self.mdbrun.is_set():
                print "NOTICE: MongoDB connector thread suspended"
            self.mdbrun.wait()
            if self.mode == 'replay':
                mintime = self.starttime + updatecycles * self.intervaltime - self.intervaltime
                maxtime = self.starttime + updatecycles * self.intervaltime
            elif self.mode == 'live':
                mintime = time.time() - self.timechunk
                maxtime = time.time()
            else:
                mintime = self.starttime
                maxtime = 0

            filterpipe = getfilter(self.mode, mintime, maxtime, self.swsupermdb)
            self.fetchstart = time.time()
            filtereddata = list(mdbcoll.aggregate(filterpipe))
            if len(filtereddata) > 0:
                datatuple = (updatecycles * self.intervaltime, filtereddata)
                self.dataqueue.put(datatuple)
            else:
                print 'WARNING: No aircraft found in timewindow: %s %s' % \
                    (str(datetime.fromtimestamp(mintime)), str(datetime.fromtimestamp(maxtime)))
                time.sleep(1)
            if self.mode == 'replay':
                updatecycles += 1
            else:
                self.fetchfin = time.time()
                if self.fetchfin - self.fetchstart > 10:
                    print "WARNING: Fetching dataset took more than 10 seconds: " + \
                        str(int(self.fetchfin - self.fetchstart)) + " seconds"
                time.sleep(self.mpauzetime)

    def _processqueue_(self):
        """ Simply processes the dataqueue, also empties it """
        print str(self.dataqueue.qsize()) + " dataset found in queue, processing...."
        _, dataset = self.dataqueue.get()
        self.dataqueue.task_done()
        while not self.dataqueue.empty():
            self.dataqueue.get()
        self._stackallcommands_(dataset)

    def _startmdbthread_(self):
        """ This function starts a background process for constant data fetching """
        _, mdbcoll = self._connectmdb_(self.mconnectionstring, self.database, self.coll)
        self.mdbkill.clear()
        self.mdbrun.set()
        thread = threading.Thread(target=self._getmdbdata_, args=(mdbcoll,))
        thread.daemon = True
        thread.start()
        if self.mode == 'replay':
            print "NOTICE: Throtteling active in replay mode"

    def _stackallcommands_(self, dataset):
        """ Create and stack command """
        createcount = 0
        delay = time.time() - self.fetchfin
        if not self.mode == 'replay':
            print "NOTICE: Dataset delay: " + str(delay) + " seconds"

        for pos in dataset:
            acid = str(pos['icao'])
            if  self.traf.id2idx(acid) < 0: # Check if AC exists
                if self.starttime + self.sim.simt - pos['ts'] - delay < 10 + self.intervaltime \
                or self.mode == 'replay':
                    cmdstr = 'CRE %s, %s, %f, %f, %f, %d, %d' % \
                            (acid, pos['mdl'], pos['loc']['lat'], \
                            pos['loc']['lng'], pos['hdg'], pos['alt'], pos['spd'])
                    self.stack.stack(cmdstr)
                    createcount = createcount + 1
                    self.achandled.append((acid, self.sim.simt))
            else:
                if self.starttime + self.sim.simt - pos['ts'] - delay > self.lostsignaltimeout:
                    print "Lost signal for %s %s seconds" % \
                            (pos['icao'], str(int(self.starttime + self.sim.simt - pos['ts'])))
                    self.stack.stack('DEL %s' % pos['icao'])
                else:
                    if self.starttime + self.sim.simt - pos['ts'] < self.intervaltime + delay + 10 \
                    or self.mode == 'replay':
                        cmdstr = 'MOVE %s, %f, %f, %d' % \
                            (acid, pos['loc']['lat'], pos['loc']['lng'], pos['alt'])
                        self.stack.stack(cmdstr)

                        cmdstr = 'HDG %s, %f' % (acid, pos['hdg'])
                        self.stack.stack(cmdstr)

                        cmdstr = 'SPD %s, %f' % (acid, pos['spd'])
                        self.stack.stack(cmdstr)
                        achandledidx = [x[0] for x in self.achandled].index(acid)
                        self.achandled[achandledidx] = acid, self.sim.simt
        dellist = []
        for acid, modtime in self.achandled:
            if self.sim.simt - modtime > self.lostsignaltimeout:
                print "Lost signal for %s" % acid
                self.stack.stack('DEL %s' % acid)
                dellist.append(acid)

        keepac = [x for x in self.achandled if x[0] not in dellist]
        self.achandled = keepac

        if createcount > 0:
            print "Created " + str(createcount) + " AC"
        return

    def _throttle_(self):
        """ Throttles the sim in case the mdb connection cannot keep up """
        if self.sim.simt < 10:
            return
        while self.dataqueue.qsize() == 0:
            self.sim.pause()
            print "NOTICE: mdb cannot keep up, throtteling sim"
            time.sleep(2)
        self.sim.start()
        if self.dataqueue.qsize == 5:
            print "NOTICE: Queue is full, mdb will be throttled"

    def toggle(self, flag):
        """ Turn the connector on or off """
        if flag:
            print "NOTICE: Starting %s mode." % self.mode
            print self.connectionoutput
            self._startmdbthread_()
            self.sim.reset()
        else:
            self.dataqueue.queue.clear()
            self.mdbkill.set() # stop thread loop
            # self.mdbrun.clear() # suspends thread

    def update(self, _):
        """ Update AC in traf database on scheduled interval """
        sim = self.sim
        # Only do something when module is started
        if not self.mdbrun.is_set():
            return
        # Only do something when time is there
        if abs(sim.simt - self.timer0) < self.intervaltime:
            return
        self.timer0 = sim.simt  # Update time for scheduler
        if self.mode == 'replay':
            self._throttle_()
            if self.skip:
                self.skip = False
                return
            timeofset, dataset = self.dataqueue.get()
            self.dataqueue.task_done()
            if timeofset > int(sim.simt):
                self.skip = True
            elif timeofset == int(sim.simt):
                self._stackallcommands_(dataset)
            else:
                print "WARNING: Simtime deviates %f seconds from fixed update interval" % \
                        (sim.simt - timeofset)
        else:
            if self.dataqueue.qsize() > 0:
                self._processqueue_()
