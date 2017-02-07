class Metrics(object):
    def __init__(self, metrictype):
        self.timehist = []
        self.hist = []
        self.metrictype = metrictype
        
        self.testvalue = 0        
        
    def testcalc(self):
        self.testvalue = 10
        
class DynamicDensity(Metrics):
    def __init__(self):
        Metrics.__init__(self, self.__class__.__name__)
        print self.metrictype

    def testout(self):
        print self.metrictype
        print mm.testvalue
        

class TD(Metrics):
    def __init__(self):
        Metrics.__init__(self, self.__class__.__name__)
        print self.metrictype

    def testout(self):
        print self.metrictype
        print mm.testvalue


dd = DynamicDensity()
td = TD()
mm = Metrics("GEODATA")
dd.testout()
mm.testcalc()
td.testout()
print "end"
