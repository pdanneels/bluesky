""" Output statistical info on metrics """

import numpy as np
import scipy.stats as stats

# To ignore numpy errors:
#     pylint: disable=E1101

class MetricsStats(object):
    """ Outpus statistical info on metrics """
    def __init__(self, sim):
        self.sim = sim
        return

    def printstats(self, geodata, rdot):
        """ retrieves data """
        mask = np.ones((geodata.size, geodata.size), dtype=bool)
        mask = np.fill_diagonal(mask, 0) # exclude diagonal from data

        velocity = np.squeeze(self.sim.traf.gs)
        dvelocity = np.sqrt(geodata.dVsqr[mask]).flatten()
        drange = geodata.qdrdist[:, :, 1][mask].flatten()
        dheading = geodata.dhdg[mask].flatten()
        rangedot = rdot.rdot[mask].flatten()

        print " -- VELOCITY --"
        self._stats(velocity)
        print " -- RELATIVE VELOCITY --"
        self._stats(dvelocity)
        print " -- RELATIVE RANGE --"
        self._stats(drange)
        print " -- RELATIVE HEADING --"
        self._stats(dheading)
        print " -- RANGE RATE --"
        self._stats(rangedot)

    def logstatsline(self, geodata, rdot):
        """ returns line to log """
        mask = np.ones((geodata.size, geodata.size), dtype=bool)
        mask = np.fill_diagonal(mask, 0) # exclude diagonal from data

        strvel = self._partlogline(np.squeeze(self.sim.traf.gs))
        strdvel = self._partlogline(np.sqrt(geodata.dVsqr[mask]).flatten())
        strdrange = self._partlogline(geodata.qdrdist[:, :, 1][mask].flatten())
        strdhdg = self._partlogline(geodata.dhdg[mask].flatten())
        strrdot = self._partlogline(rdot.rdot[mask].flatten())

        return "{0};{1};{2};{3};{4}".format(strvel, strdvel, \
                                                strdrange, strdhdg, strrdot)

    @staticmethod
    def _stats(datamatrix):
        """ print statistics """
        print "Average: %f" % np.average(datamatrix)
        print "Mean: %f" % np.mean(datamatrix)
        print "Skewness: %f" % stats.skew(datamatrix)
        print "Variation: %f" % stats.variation(datamatrix)
        print "STD: %f" % stats.tstd(datamatrix)
        print "SEM: %F" % stats.tsem(datamatrix)
        print ""

    @staticmethod
    def _partlogline(datamatrix):
        """ return statistical data for one metrics """
        return "{0};{1};{2};{3};{4};{5}".format(np.average(datamatrix), \
                        np.mean(datamatrix), stats.skew(datamatrix), stats.variation(datamatrix), \
                        stats.tstd(datamatrix), stats.tsem(datamatrix))
