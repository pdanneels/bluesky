"""
Metrics module
Created by  : P. Danneels, 2016

"""
# To ignore numpy errors in pylint static code analyser:
#     pylint: disable=E1101

import numpy as np
from bluesky.tools import Toolsmodule
from bluesky.tools.metrics.metrics import Metrics, RelativeVelocity, \
    ConflictRate, TrafficDensity, ConflictsPerAc, RangeDot, RelativeHeading, \
    Other, AirspaceQuality
from bluesky.tools.metrics.plot import MetricsPlot
from bluesky.tools.metrics.stats import MetricsStats
from bluesky.tools.metrics.log import MetricsLog

class MetricsModule(Toolsmodule):
    """ Handles metrics module """
    def __init__(self, sim, scr):
        Toolsmodule.__init__(self, sim, scr, self.__class__.__name__)
        cmddict = {"METRICS": ["METRICS ON/OFF", "onoff", \
                    lambda *args: sim.metrics.toggle(*args)]}
        Toolsmodule.add_stack_commands(self, cmddict)
        self.swmetrics = False      # Initial value

        # Toggle calculations and output
        self.swsingleshot = False   # Toggle single shot operation
        self.swplotinitial = False   # Toggle initial geodata plots
        self.swplot = True          # Toggle plot
        self.swprint = False         # Toggle print
        self.swmetricslog = True    # Toggle metrics log
        self.swstats = False        # Toggle stats output

        # Time
        self.timer0 = -9999         # Force first time call, update
        self.timer1 = -9999         # Force first time call, plot
        self.intervalmetrics = 1    # [seconds]
        self.intervalplot = 15      # [seconds]

        self.init_instances()

    def init_instances(self):
        """ Initiate instances for metrics and plot/log/stats modules"""
        self.geodata = Metrics(self.sim, None, self.swprint, "geodata")
        self.vrel = RelativeVelocity(self.sim, self.geodata, self.swprint)
        self.conflictrate = ConflictRate(self.sim, self.geodata, self.swprint)
        self.trafficdensity = TrafficDensity(self.sim, self.geodata, self.swprint)
        self.confperac = ConflictsPerAc(self.sim, self.geodata, self.swprint)
        self.rdot = RangeDot(self.sim, self.geodata, self.swprint)
        self.dhdg = RelativeHeading(self.sim, self.geodata, self.swprint)
        self.other = Other(self.sim, self.geodata, self.sim.rarea, self.swprint)
        self.asq = AirspaceQuality(self.sim, self.geodata, self.swprint)

        self.plot = MetricsPlot(self.sim)
        self.log = MetricsLog(self.sim)
        self.stats = MetricsStats(self.sim)

    def toggle(self, flag):
        """ Toggle metrics module """
        if self.swmetrics:
            self.swmetrics = False
        else:
            self.swmetrics = True

    def update(self):
        """ Update all the metrics with the current set of traffic data """
        sim = self.sim
        log = self.log
        plot = self.plot
        stats = self.stats
        rarea = sim.rarea

        # Check if metrics is actually switched on and there is traffic
        # Check if the simulation is running
        # Check if there is actual traffic
        if not self.swmetrics or self.sim.simt < 0 or self.traf.ntraf < 1:
            return

        # Only do something when time is there
        if abs(self.sim.simt-self.timer0) < self.intervalmetrics:
            return
        self.timer0 = self.sim.simt  # Update time for scheduler

        if rarea is not None:  # Update tracking DB for research area
            if self.sim.rarea.surfacearea <= 0:
                print "Defining default research area"
                self.stack.stack("RAREA %f,%f,%f,%f" % (51, 3, 53.5, 7))
            rarea.update()

        self.sim.pause() # "Lost time is never found again" - Benjamin Franklin -

        self.geodata.updategeodata()
        if self.swprint:
            print "------------------------"
        if self.swmetricslog:
            log.update("Conf/AC", str(self.confperac.update()))     # collisions devided by #AC
            log.update("Cr", str(self.conflictrate.update()))       # collision rate
            log.update("avgdHDG", str(self.dhdg.update()))          # average range rate
            log.update("avgrdot", str(self.rdot.update()))          # average range rate
            log.update("Td", str(self.trafficdensity.update()))     # traffic density
            log.update("avgdV", str(self.vrel.update()))            # average relative velocity
            log.update("avgV", str(np.average(sim.traf.gs)))        # average groundspeed
            log.update("ASQ", str(self.asq.update(self.rdot.rdot)))
        else:
            self.confperac.update()
            self.conflictrate.update()
            self.dhdg.update()
            self.rdot.update()
            self.trafficdensity.update()
            self.vrel.update()
            self.asq.update(self.rdot.rdot)
        self.other.update()
        if self.swprint:
            print "------------------------"

        if self.swplot: # Plot
            if abs(self.sim.simt-self.timer1) < self.intervalplot:
                self.sim.start() # "The show must go on" - Freddie Mercury, Queen -
                return
            if self.swsingleshot:
                self.sim.mdb.mdbkill.set() # free up resources

            if self.swplotinitial:
                plot.plothistograms(self.geodata, self.rdot)
                plot.plotdynamicdensity(self.geodata, self.rdot)
                plot.plot3d(self.rdot)
                self.swplotinitial = False

            plot.plotevolution(self.rdot, self.other, self.confperac, self.conflictrate, \
                                self.vrel, self.dhdg, self.trafficdensity)
            self.timer1 = self.sim.simt

        if self.swstats: # Stats
            stats.printstats(self.geodata, self.rdot)

        if not self.swsingleshot:
            sim.start() # "The show must go on" - Freddie Mercury, Queen -
        else:
            log.update("Number of AC: " + str(sim.traf.ntraf), \
                "Number of conflicts: " + str(sim.traf.asas.nconf / 2))
            log.update("------------------------------------------------", "")
            log.update("Velocity;;;;;;Relative Veolocity;;;;;;Relative Range;;;;;;Relative Heading;;;;;Range Rate", "")
            line = "Average;Mean;Skewness;Variation;STD;SEM;"
            log.update(line + line + line + line + line, "")
            log.update(stats.logstatsline(self.geodata, self.rdot), "")
            log.save()
            plot.saveplot()
            print ""
            print " -- Finished single shot operation -- "
            print ""
        return
