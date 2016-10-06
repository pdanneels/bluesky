""" Metrics plot class """

import numpy as np
import matplotlib.pyplot as plt
import os
from time import strftime, gmtime
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from scipy.stats import gaussian_kde

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

    def plot3d(self, rdot):
        """ Plots 3D map """
        traf = self.sim.traf
        self.fig3d = plt.figure()
        axis = self.fig3d.add_subplot(111, projection='3d')
        dcpa = self.dcpa2todcpa(traf.asas.dcpa2)
        self._boxquantities_(dcpa, traf.asas.tcpa, rdot.rdot)
        dcpamasked, tcpamasked, rdotmasked, colorarray = \
                        self._3dfilter_(dcpa, traf.asas.tcpa, rdot.rdot)

        axis.scatter(dcpamasked, tcpamasked, rdotmasked, c=colorarray.flatten().tolist())
        axis.set_xlim3d(0, 50)
        axis.set_ylim3d(0, 300)
        axis.set_zlim3d(-1000, 1000)
        axis.set_xlabel('dcpa')
        axis.set_ylabel('tcpa')
        axis.set_zlabel('rdot')

        plt.hold(True)
        x_surf = np.arange(0, 50, 5)
        y_surf = np.arange(0, 300, 30)
        x_surf, y_surf = np.meshgrid(x_surf, y_surf)
        z_surf = np.zeros(x_surf.shape)
        axis.plot_surface(x_surf, y_surf, z_surf, cmap=cm.hot, alpha=0.2)

        figmanager = plt.get_current_fig_manager()
        figmanager.window.showMaximized()
        plt.show()

    def _boxquantities_(self, dcpa, tcpa, rdot):
        """ Print the number of AC in each box """
        traf = self.sim.traf
        ntrafsq = traf.ntraf*traf.ntraf
        ntrafsqvalid = ntrafsq / 2 - traf.ntraf
        mask = np.ones(dcpa.shape, dtype=bool)
        print "Unfiltered datapoints: %i / %i" % (np.count_nonzero(mask), ntrafsqvalid)
        mask = np.greater(dcpa, 0) & np.greater(tcpa, 0)
        print "Future collisions: %i / %i" % (np.count_nonzero(mask), ntrafsqvalid)
        mask = np.greater(dcpa, 0) & np.greater(tcpa, 0) & np.less(tcpa, 300)
        print "TCPA less than 5min: %i / %i)" % (np.count_nonzero(mask), ntrafsqvalid)
        mask = np.greater(dcpa, 0) & np.less(dcpa, 50) & np.greater(tcpa, 0)
        print "DCPA less than 50NM: %i / %i)" % (np.count_nonzero(mask), ntrafsqvalid)
        mask = np.greater(dcpa, 0) & np.less(dcpa, 20) & np.greater(tcpa, 0) & np.less(tcpa, 300)
        print "Combine max DCPA and TCPA: %i / %i)" % (np.count_nonzero(mask), ntrafsqvalid)

    @staticmethod
    def dcpa2todcpa(dcpa2):
        """ Convert DCPA2 to DCPA """
        return np.sqrt(dcpa2)/1852.

    @staticmethod
    def _colorboxes_(dcpa, tcpa, rdot):
        """ Return array with colors for data points """
        colorarray = np.chararray(rdot.shape)
        colorarray[:] = 'b'
        mask = np.greater(rdot, 0)
        colorarray[mask] = 'g'
        mask = np.less(rdot, 0) & np.less(dcpa, 15) & np.less(tcpa, 300)
        colorarray[mask] = 'y'
        mask = np.greater(dcpa, 0) & np.less(dcpa, 10) & \
                np.greater(tcpa, 0) & np.less(tcpa, 60) & np.less(rdot, -25)
        colorarray[mask] = 'r'
        return colorarray
    
    def _3dfilter_(self, dcpa, tcpa, rdot):
        """ Filters irrelevant data before 3D plot """
        mask = np.ones(dcpa.shape, dtype=bool)
        # mask = np.greater(tcpa, 0) & np.less(tcpa, 1800)
        mask = np.greater(dcpa, 0) & np.less(dcpa, 50) & np.greater(tcpa, 0) & np.less(tcpa, 300)
        np.fill_diagonal(mask, 0)
        colorarray = self._colorboxes_(dcpa, tcpa, rdot)
        return dcpa[mask], tcpa[mask], rdot[mask], colorarray[mask]
    
    @staticmethod
    def _densitymap_(x, y):
        """ Input x, y of data points. Returns x, y ,z sorted by z(density) """
        xy = np.vstack([x,y])
        z = gaussian_kde(xy)(xy)
        idx = z.argsort()
        return x[idx], y[idx], z[idx]
    
    @staticmethod
    def _2dfilter_(x, xlow, xhigh, y, ylow, yhigh):
        mask = np.ones(x.shape, dtype=bool)
        mask = np.greater(x, xlow) & np.less(x, xhigh) & np.greater(y, ylow) & np.less(y, yhigh)
        np.triu(mask, 1)
        return x[mask].flatten(), y[mask].flatten()

    def plotdynamicdensity(self, geo, rdot):
        """ Plot Dynamic Density Map """
        sim = self.sim

        self.figdd = plt.figure()
        distance = geo.qdrdist[:, :, 1]

        #size, _ = distance.shape
        #mask = np.triu_indices(size, 1)
        xlow = -1; xhigh = 150; ylow = -1; yhigh = 300
        xrnge = (xhigh - xlow)*.1; yrnge = (yhigh - ylow)*.1
        axis = self.figdd.add_subplot(221)
        xmasked, ymasked = self._2dfilter_(sim.traf.asas.tcpa, xlow-xrnge, xhigh+xrnge, distance, ylow-yrnge, yhigh+yrnge)
        x, y, z = self._densitymap_(xmasked, ymasked)
        axis.scatter(x, y, c=z, s=50, edgecolor='')
        axis.set_xlim(xlow, xhigh)
        axis.set_ylim(ylow, yhigh)
        axis.set_xlabel(r'$t [s]$')
        axis.set_ylabel(r'$R [NM]$')
        axis.set_title("Range vs time to CPA")

        xlow = -1; xhigh = 300; ylow = -1; yhigh = 22500
        xrnge = (xhigh - xlow)*.1; yrnge = (yhigh - ylow)*.1
        axis = self.figdd.add_subplot(222)
        xmasked, ymasked = self._2dfilter_(sim.traf.asas.tcpa, xlow-xrnge, xhigh+xrnge, np.square(distance), ylow-yrnge, yhigh+yrnge)
        x, y, z = self._densitymap_(xmasked, ymasked)
        axis.scatter(x, y, c=z, s=50, edgecolor='')
        axis.set_xlim(xlow, xhigh)
        axis.set_ylim(ylow, yhigh)
        axis.set_xlabel(r'$t [s]$')
        axis.set_ylabel(r'$R^2 [NM^2]$')
        axis.set_title("Range squared vs time to CPA")

        xlow = -1; xhigh = 300; ylow = -1000; yhigh = 1000
        xrnge = (xhigh - xlow)*.1; yrnge = (yhigh - ylow)*.1
        axis = self.figdd.add_subplot(223)
        xmasked, ymasked = self._2dfilter_(sim.traf.asas.tcpa, xlow-xrnge, xhigh+xrnge, rdot.rdot, ylow-yrnge, yhigh+yrnge)
        x, y, z = self._densitymap_(xmasked, ymasked)
        axis.scatter(x, y, c=z, s=50, edgecolor='')
        axis.set_xlim(xlow, xhigh)
        axis.set_ylim(ylow, yhigh)
        axis.set_xlabel(r'$t [s]$')
        axis.set_ylabel(r'$\.r [m/s]$')
        axis.set_title("Range rate vs time to CPA")

        xlow = -1; xhigh = 1800; ylow = -1; yhigh = 300
        xrnge = (xhigh - xlow)*.1; yrnge = (yhigh - ylow)*.1
        axis = self.figdd.add_subplot(224)
        xmasked, ymasked = self._2dfilter_(sim.traf.asas.tcpa, xlow-xrnge, xhigh+xrnge, self.dcpa2todcpa(sim.traf.asas.dcpa2), ylow-yrnge, yhigh+yrnge)
        x, y, z = self._densitymap_(xmasked, ymasked)
        axis.scatter(x, y, c=z, s=50, edgecolor='')
        axis.set_xlim(xlow, xhigh)
        axis.set_ylim(ylow, yhigh)
        axis.set_xlabel(r'$t [s]$')
        axis.set_ylabel(r'$R [NM]$')
        axis.set_title("Range at CPA vs time to CPA")

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
