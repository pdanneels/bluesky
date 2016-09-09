""" Metrics plot class """

import numpy as np
import matplotlib.pyplot as plt
import os
from time import strftime, gmtime
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

# To ignore numpy errors:
#     pylint: disable=E1101

class MetricsPlot():
    """ Plots metrics """
    def __init__(self, sim):
        self.sim = sim
        self.figdd = None
        self.fighist = None
        self.figevo = None
        self.fig3d = None

    def saveplot(self):
        """ Save plot"""
        if self.figdd is not None:
            fname = os.path.dirname(__file__) + "/../../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSkyDD.png", gmtime())
            self.figdd.savefig(fname, transparent=True)
        if self.fighist is not None:
            fname = os.path.dirname(__file__) + "/../../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSkyHIST.png", gmtime())
            self.fighist.savefig(fname, transparent=True)
        if self.figevo is not None:
            fname = os.path.dirname(__file__) + "/../../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSkyEVO.png", gmtime())
            self.figevo.savefig(fname, transparent=True)
        if self.fig3d is not None:
            fname = os.path.dirname(__file__) + "/../../../data/output/" \
            + strftime("%Y-%m-%d-%H-%M-%S-BlueSky3D.png", gmtime())
            self.fig3d.savefig(fname, transparent=True)

    def plotddd(self, rdot):
        """ Plots 3D map """
        traf = self.sim.traf
        self.fig3d = plt.figure()
        axis = self.fig3d.add_subplot(111, projection='3d')
        dcpamasked, tcpamasked, rdotmasked = self._dddfilter_(traf.asas.dcpa2, \
                                                traf.asas.tcpa, rdot.rdot)
        colorvalue = rdotmasked/(dcpamasked*tcpamasked)
#        colormapping = np.ones(colorvalue.shape)
#        for i in colorvalue:
#            if colorvalue[i] < -8. or colorvalue[i] > 0.:
#                colormapping[i] = 'g'
#            else:
#                colormapping[i] = 'r'
        
        axis.scatter(dcpamasked, tcpamasked, rdotmasked, cmap='RdYlGn', c=colorvalue)
        axis.set_xlim3d(0, 100)
        axis.set_ylim3d(0, 900)
        axis.set_zlim3d(-1000, 1000)
        axis.set_xlabel('dcpa')
        axis.set_ylabel('tcpa')
        axis.set_zlabel('rdot')
        
        plt.hold(True)
        x_surf=np.arange(0, 100, 10)
        y_surf=np.arange(0, 900, 90)
        x_surf, y_surf = np.meshgrid(x_surf, y_surf)
        z_surf = np.zeros(x_surf.shape)
        axis.plot_surface(x_surf, y_surf, z_surf, cmap=cm.hot, alpha=0.2);
        
        figmanager = plt.get_current_fig_manager()
        figmanager.window.showMaximized()
        plt.show()

    @staticmethod
    def _dddfilter_(dcpa2, tcpa, rdot):
        """ Filters irrelevant data before 3D plot """
        mask = np.ones(dcpa2.shape, dtype=bool)
        # mask = np.greater(tcpa, 0) & np.less(tcpa, 1800)
        dcpa = np.sqrt(dcpa2)/1852.
        mask = np.greater(dcpa, 0) & np.less(dcpa, 100) & np.greater(tcpa, 0) & np.less(tcpa, 900)
        np.fill_diagonal(mask, 0)
        return dcpa[mask], tcpa[mask], rdot[mask]

    def plotdynamicdensity(self, geo, rdot):
        """ Plot Dynamic Density Map """
        sim = self.sim

        self.figdd = plt.figure()
        distance = geo.qdrdist[:, :, 1]
        self.figdd.add_subplot(221)
        size, _ = distance.shape
        mask = np.triu_indices(size, 1)
        plt.scatter(sim.traf.asas.tcpa[mask], distance[mask])
        plt.ylim(-1, 150)
        plt.xlim(-1, 1800)
        plt.xlabel(r'$t [s]$')
        plt.ylabel(r'$R [NM]$')
        plt.title("Range vs time to CPA")

        self.figdd.add_subplot(222)
        plt.scatter(sim.traf.asas.tcpa[mask], np.square(distance[mask]))
        plt.ylim(-1, 22500)
        plt.xlim(-1, 1800)
        plt.xlabel(r'$t [s]$')
        plt.ylabel(r'$R^2 [NM^2]$')
        plt.title("Range squared vs time to CPA")

        self.figdd.add_subplot(223)
        plt.scatter(sim.traf.asas.tcpa[mask], rdot.rdot[mask])
        plt.ylim(-1000, 1000)
        plt.xlim(-1, 10000)
        plt.xlabel(r'$t [s]$')
        plt.ylabel(r'$\.r [m/s]$')
        plt.title("Range rate vs time to CPA")

        self.figdd.add_subplot(224)
        plt.scatter(sim.traf.asas.tcpa[mask], \
                    np.sqrt(sim.traf.asas.dcpa2[mask])/1852.)
        plt.ylim(-1, 800)
        plt.xlim(-1, 20000)
        plt.xlabel(r'$t [s]$')
        plt.ylabel(r'$R [NM]$')
        plt.title("Range at CPA vs time to CPA")

        figmanager = plt.get_current_fig_manager()
        figmanager.window.showMaximized()
        plt.show()

    def plothistograms(self, geo, rdot):
        """ Plot Histograms """

        sim = self.sim
        if self.fighist is None:
            self.fighist = plt.figure()
        plt.clf() # Fresh plots
        mask = np.ones((geo.size, geo.size), dtype=bool)
        #mask = np.triu(mask,1) # this is problematic for traf.ntraf<=2
        mask = np.fill_diagonal(mask, 0) # exclude diagonal from data
        self.fighist.add_subplot(231)
        velocity = np.squeeze(sim.traf.gs)
        plt.hist(velocity, bins=50)
        plt.xlim(50, 450)
        plt.title("Velocity")

        self.fighist.add_subplot(232)
        dvelocity = np.sqrt(geo.dVsqr[mask]).flatten()
        plt.hist(dvelocity, bins=50)
        plt.xlim(-1, 800)
        plt.title("Relative velocity")

        self.fighist.add_subplot(233)
        drange = geo.qdrdist[:, :, 1][mask].flatten()
        plt.hist(drange, bins=50)
        plt.xlim(-1, 600)
        plt.title("Relative distance")

        self.fighist.add_subplot(234)
        dheading = geo.dhdg[mask].flatten()
        plt.hist(dheading, bins=50)
        plt.xlim(-180, 180)
        plt.title("Relative bearing")

        self.fighist.add_subplot(235)
        rangedot = rdot.rdot[mask].flatten()
        plt.hist(rangedot, bins=50)
        plt.xlim(-700, 700)
        plt.title("Range rate")

        figmanager = plt.get_current_fig_manager()
        figmanager.window.showMaximized()

        plt.draw()
        plt.show()

    def plotevolution(self, rdot, other, confperac, conflictrate, vrel, dhdg, trafficdensity):
        """ Evolution of averages over time """
        sim = self.sim
        if self.figevo is None:
            self.figevo = plt.figure()
        plt.clf() # Fresh plots
        if sim.rarea.surfacearea <= 0:
            return
        histgs, histntraf, histrantraf = other.gethist()

        self.figevo.add_subplot(331)
        plt.plot(histntraf[0, :], histntraf[1, :])
        plt.ylabel(r'$#AC [-]$')
        plt.title("#AC evolution")

        self.figevo.add_subplot(332)
        plt.plot(histrantraf[0, :], histrantraf[1, :])
        plt.title("#AC in RA evolution")
        plt.ylabel(r'$#AC [-]$')

        self.figevo.add_subplot(333)
        hist = confperac.gethist()
        plt.plot(hist[0, :], hist[1, :])
        plt.ylabel(r'$#conf/AC [-]$')
        plt.title("Conflicts per AC evolution")

        self.figevo.add_subplot(334)
        hist = conflictrate.gethist()
        plt.plot(hist[0, :], hist[1, :])
        plt.ylabel(r'$Cr [-]$')
        plt.title("Cr evolution")

        self.figevo.add_subplot(335)
        plt.plot(histgs[0, :], histgs[1, :])
        plt.ylabel(r'$V [m/s]$')
        plt.title("Average V evolution")

        self.figevo.add_subplot(336)
        hist = vrel.gethist()
        plt.plot(hist[0, :], hist[1, :])
        plt.ylabel(r'$V [m/s]$')
        plt.title("Average relative V evolution")

        self.figevo.add_subplot(337)
        hist = dhdg.gethist()
        plt.plot(hist[0, :], hist[1, :])
        plt.ylabel(r'$HDG [^\circ]$')
        plt.title("Average relative HDG evolution")

        self.figevo.add_subplot(338)
        hist = trafficdensity.gethist()
        plt.plot(hist[0, :], hist[1, :])
        plt.ylabel(r'$#AC/km^2$')
        plt.title("Traffic density evolution")

        self.figevo.add_subplot(339)
        hist = rdot.gethist()
        plt.plot(hist[0, :], hist[1, :])
        plt.ylabel(r'$\.r [m/s]$')
        plt.title("Average range rate evolution")

        figmanager = plt.get_current_fig_manager()
        figmanager.window.showMaximized()

        plt.draw()
        plt.show()
