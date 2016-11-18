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
                    lambda *args: sim.metrics.toggle(args)], \
                    "SAVEPLOTS": ["SAVEPLOTS", "", \
                    lambda *args: sim.metrics.saveplots()], \
                    "SHOWPLOT": ["SHOWPLOT EVOLUTION/CR/DENSITY/3D/HISTORGRAMS", "txt", \
                    lambda *args: sim.metrics.showplot(args[0])]}
        Toolsmodule.add_stack_commands(self, cmddict)
        self.swmetrics = False      # Initial value

        # Toggle calculations and output
        self.swsingleshot = False       # Toggle single shot operation
        self.swplotinitial = False      # Toggle initial geodata plots
        self.swprint = False            # Toggle print
        self.swmetricslog = False       # Toggle metrics log
        self.swstats = False            # Toggle stats output

        self.swplotevolution = False

        # Time
        self.timer0 = -9999         # Force first time call, update
        self.timer1 = -9999         # Force first time call, plot
        self.intervalmetrics = 1    # [seconds]
        self.intervalplot = 15      # [seconds]

        self.init_instances()

    def init_instances(self):
        """ Initiate instances for metrics and plot/log/stats modules"""
        self.geodata = Metrics(self.sim, None, self.swprint, "geodata")
        self.conflictrate = ConflictRate(self.sim, self.geodata, self.swprint)
        self.vrel = None #RelativeVelocity(self.sim, self.geodata, self.swprint)
        self.trafficdensity = None #TrafficDensity(self.sim, self.geodata, self.swprint)
        self.confperac = None #ConflictsPerAc(self.sim, self.geodata, self.swprint)
        self.rdot = None #RangeDot(self.sim, self.geodata, self.swprint)
        self.dhdg = None #RelativeHeading(self.sim, self.geodata, self.swprint)
        self.other = None #Other(self.sim, self.geodata, self.sim.rarea, self.swprint)
        self.asq = None #AirspaceQuality(self.sim, self.geodata, self.swprint)

        self.plot = MetricsPlot(self.sim)
        self.log = MetricsLog(self.sim)
        self.stats = MetricsStats(self.sim)

    def saveplots(self):
        """ Save plots """
        self.plot.saveplot()

    def showplot(self, plottoshow):
        """ Show plots """

        if plottoshow == "CR" and len(self.conflictrate.conflictrates) != 0:
            # Plot conflictrates
            self.plot.plotcrdistribution(np.array(self.conflictrate.conflictrates) / \
                (self.sim.simt - self.sim.rarea.passedthrough[0][1]))
            print "TOTALTIME is %f" % (self.sim.simt - self.sim.rarea.passedthrough[0][1])
            return

        if not self.rdot:
            #needed for below plots
            return

        if plottoshow == "3D":
            # 3D plot of aircraft pairs
            self.plot.plot3d(self.rdot)
            return

        if plottoshow == "DENSITY":
            # Density plots of aircraft pairs
            self.plot.plotdynamicdensity(self.geodata, self.rdot)
            return

        if plottoshow == "HISTOGRAMS":
            # Show distribution of
            self.plot.plothistograms(self.geodata, self.rdot)
            return

        if plottoshow == "EVOLUTION":
            # Plot evolution if all metrics are available
            if self.other and self.confperac and self.conflictrate \
                and self.vrel and self.dhdg and self.trafficdensity:
                self.swplotevolution = True
                self.plot.plotevolution(self.rdot, self.other, self.confperac, \
                    self.conflictrate, self.vrel, self.dhdg, self.trafficdensity)
                return
        return

    def toggle(self, flag):
        """ Toggle metrics module """
        if self.swmetrics:
            self.swmetrics = False
        else:
            self.swmetrics = True

    def _updatemetrics_(self):
        """ Check if metric exists, if so: call update function """
        if self.asq:
            self.asq.update()
        if self.conflictrate:
            self.conflictrate.update()
        if self.confperac:
            self.confperac.update()
        if self.dhdg:
            self.dhdg.update()
        if self.other:
            self.other.update()
        if self.rdot:
            self.rdot.update()
        if self.trafficdensity:
            self.trafficdensity.update()
        if self.vrel:
            self.vrel.update()

    def update(self):
        """ Update all the metrics with the current set of traffic data """
        sim = self.sim
        log = self.log
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

        # Pause simulation, update metrics
        self.sim.pause() # "Lost time is never found again" - Benjamin Franklin -
        if self.swsingleshot:
            self.sim.mdb.mdbkill.set() # free up resources, kill mdb connection
            
        self.geodata = None
        self.geodata = Metrics(self.sim, None, self.swprint, "geodata")
        
        self.geodata.updategeodata()
        if self.swprint: print "------------------------"
        self._updatemetrics_()
        if self.swprint: print "------------------------"

        if abs(self.sim.simt-self.timer1) >= self.intervalplot:
            # You can add plot functions here that need updates on self.intervalplot
            if self.swplotevolution:
                self.stack.stack("SHOWPLOT EVOLUTION")
        self.timer1 = self.sim.simt
        if self.swstats: # Stats
            stats.printstats(self.geodata, self.rdot)

        # Finish up or unpause
        if self.swsingleshot:
            log.update("Number of AC: " + str(sim.traf.ntraf), \
                "Number of conflicts: " + str(sim.traf.asas.nconf / 2))
            log.update("------------------------------------------------", "")
            log.update("Velocity;;;;;;Relative Veolocity;;;;;;Relative Range;;;;;;Relative Heading;;;;;Range Rate", "")
            line = "Average;Mean;Skewness;Variation;STD;SEM;"
            log.update(line + line + line + line + line, "")
            log.update(stats.logstatsline(self.geodata, self.rdot), "")
            log.save()
            self.stack.stack("SAVEPLOTS")
            print "\n -- Finished single shot operation -- \n"
        else:
            sim.start() # "The show must go on" - Freddie Mercury, Queen -
        return
