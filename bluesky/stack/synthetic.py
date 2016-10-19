""" Module to create traffic according to different patterns """

import random
import numpy as np
from .. import stack
from ..tools.aero import ft, nm, eas2tas
from ..tools import geo
from ..tools.misc import txt2alt, txt2spd

# To ignore numpy errors:
#     pylint: disable=E1101

SAVESCENARIOS = False #whether to save a scenario as .scn file after generation via commands

class Synthetic():
    """ Class contains functions to generate synthetic scenarios """
    def __init__(self, sim, scr):
        self.sim = sim
        self.traf = sim.traf
        self.scr = scr

        stackcmd = {"SYN": [ \
                " SYN: Possible subcommands: HELP, SIMPLE, SIMPLED, DIFG, SUPER,\n" + \
                "MATRIX, FLOOR, TAKEOVER, WALL, ROW, COLUMN, DISP", "txt,[...]", \
                lambda *args: sim.syn.process(args[0], len(args) - 1, args, sim)\
                ]}
        stack.append_commands(stackcmd)

    def process(self, command, numargs, cmdargs, sim):
        """ Process the synthetic commands """
        callsign = 'SYN '
        traf = sim.traf
        scr = self.scr

        # change display settings and delete AC to generate own FF scenarios
        if command == "START":
            scr.swgeo = False         # don't draw coastlines and borders
            scr.swsat = False         # don't draw the satellite image
            scr.apsw = 0              # don't draw airports
            #scr.swlabel = 0          # don't draw aircraft labels      # BROKEN
            scr.wpsw = 0              # don't draw waypoints
            scr.swfir = False         # don't show FIRs
            scr.swgrid = True         # do show a grid
            stack.stack("PAN 0,0")    # focus the map at the prime meridian and equator
            scr.redrawradbg = True    # draw the background again
            scr.swsep = True          # show circles of seperation between ac
            scr.swspd = True          # show speed vectors of aircraft
            # scr.zoom(0.4, True)     # set zoom level to the standard distance
            # cmd.scenlines=[]        # skip the rest of the scenario
            # cmd.scencmd=[]          # skip the rest of the scenario
            # cmd.scentime=[]         # skip the rest of the scenario
            # cmd.scenlines.append("00:00:00.00>"+callsign+"TESTCIRCLE")
            # cmd.scenlines.append("00:00:00.00>DT 1")
            # cmd.scenlines.append("00:00:00.00>FIXDT ON")
            sim.reset()

        elif command == "HELP":
            return True, ("This is the synthetic traffic scenario module\n" \
                "Possible subcommands: HELP, SIMPLE, SIMPLED, DIFG, SUPER, SPHERE, " \
                "MATRIX, FLOOR, TAKEOVER, WALL, ROW, COLUMN, DISP")

        #create a perpendicular conflict between two aircraft
        elif command == "SIMPLE":
            scr.isoalt = 0
            stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                ("OWNSHIP", "GENERIC", -.5, 0, 0, 5000 * ft, 200))
            stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                ("INTRUDER", "GENERIC", 0, .5, 270, 5000 * ft, 200))
            return True

        #create a perpendicular conflict with slight deviations to aircraft speeds and places
        elif command == "SIMPLED":
            scr.isoalt = 0
            ds = random.uniform(0.92, 1.08)
            dd = random.uniform(0.92, 1.08)
            stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                ("OWNSHIP", "GENERIC", -.5 * dd, 0, 0, 20000 * ft, 200 * ds))
            stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                ("INTRUDER", "GENERIC", 0, .5 / dd, 270, 20000 * ft, 200 / ds))
            return True

        # used for testing the differential game resolution method
        elif command == "DIFG":
            if numargs < 5:
                return False, "5 ARGUMENTS REQUIRED"
            else:
                scr.isoalt = 0

                x = traf.dbconf.xw[int(float(cmdargs[1]))]/111319.
                y = traf.dbconf.yw[int(float(cmdargs[2]))]/111319.
                v_o = traf.dbconf.v_o[int(float(cmdargs[3]))]
                v_w = traf.dbconf.v_w[int(float(cmdargs[4]))]
                phi = np.degrees(traf.dbconf.phi[int(float(cmdargs[5]))])
                stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                    ("OWN", "GENERIC", 0, 0, 0, 5000*ft, v_o))
                stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                    ("WRN", "GENERIC", y, x, phi, 5000*ft, v_w))
                return True

        # create a superconflict of x aircraft in a circle towards the center
        elif command == "SUPER":
            if numargs == 0:
                return True, callsign + "SUPER <NUMBER OF A/C>"
            else:
                scr.isoalt = 0
                numac = int(float(cmdargs[1]))
                distance = 0.50 #this is in degrees lat/lon, for now
                alt = 20000*ft #ft
                spd = 200 #kts
                for i in range(numac):
                    angle = 2*np.pi/numac*i
                    acid = "SUP" + str(i)
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acid, 'SUPER', distance*-np.cos(angle), distance*np.sin(angle), \
                        360-360/numac*i, alt, spd))

                if SAVESCENARIOS:
                    fname = "super"+str(numac)
                    stack.stack("SAVEIC %s" % fname)
                return True

        # create a sphereconflict of 3 layers of superconflicts
        elif command == "SPHERE":
            if numargs == 0:
                return True, callsign + "SPHERE <NUMBER OF A/C PER LAYER>"
            else:
                scr.isoalt = 1. / 200

                numac = int(float(cmdargs[1]))
                distance = 0.5 #this is in degrees lat/lon, for now
                distancenm = distance * 111319. / nm
                alt = 20000 #ft
                spd = 150 #kts
                vs = 4 #m/s
                timetoimpact = distancenm / spd * 3600 #seconds
                altdifference = vs * timetoimpact # m
                midalt = alt
                lowalt = alt - altdifference
                highalt = alt + altdifference
                hispd = eas2tas(spd, highalt)
                mispd = eas2tas(spd, midalt)
                lospd = eas2tas(spd, lowalt)
                hispd = spd
                mispd = spd
                lospd = spd
                for i in range(numac):
                    angle = np.pi * (2. / numac * i)
                    lat = distance * -np.cos(angle)
                    lon = distance * np.sin(angle)
                    track = np.degrees(-angle)

                    acidl = "SPH" + str(i) + "LOW"
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acidl, "SUPER", lat, lon, track, lowalt*ft, lospd))
                    acidm = "SPH" + str(i) + "MID"
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acidm, "SUPER", lat, lon, track, midalt*ft, mispd))
                    acidh = "SPH" + str(i) + "HIG"
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acidh, "SUPER", lat, lon, track, highalt*ft, hispd))

                    idxl = traf.id.index(acidl)
                    idxh = traf.id.index(acidh)

                    traf.vs[idxl] = vs
                    traf.vs[idxh] = -vs

                    traf.avs[idxl] = vs
                    traf.avs[idxh] = -vs

                    traf.aalt[idxl] = highalt
                    traf.aalt[idxh] = lowalt

                if SAVESCENARIOS:
                    fname = "sphere" + str(numac)
                    stack.stack("SAVEIC %s" % fname)
                return True

        elif command == "FUNNEL":
            if numargs == 0:
                scr.echo(callsign + "FUNNEL <FUNNELSIZE IN NUMBER OF A/C>")
            else:
                scr.isoalt = 0
                traf.deleteall()
                # TODO:
                #traf.asas = CASASfunnel.Dbconf(traf, 300., 5.*nm, 1000.*ft)
                size = float(cmdargs[1])
                mperdeg = 111319.
                distance = 0.90 #this is in degrees lat/lon, for now
                alt = 20000 #meters
                spd = 200 #kts
                numac = 8 #number of aircraft
                for i in range(numac):
                    angle = np.pi/2/numac*i+np.pi/4
                    acid = "SUP"+str(i)
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acid, "SUPER", distance*-np.cos(angle), distance*-np.sin(angle), \
                        90, alt, spd))

                separation = traf.asas.R*1.01
                #[m] the factor 1.01 is so that the funnel doesn't collide with itself
                sepdeg = separation/np.sqrt(2.)/mperdeg #[deg]

                for row in range(1):
                    for col in range(15):
                        opening = (size+1)/2.*separation/mperdeg
                        coldeg = sepdeg*col  #[deg]
                        rowdeg = sepdeg*row  #[deg]
                        acid1 = "FUNN"+str(row)+"-"+str(col)
                        acid2 = "FUNL"+str(row)+"-"+str(col)
                        stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                            (acid1, "FUNNEL", coldeg+rowdeg+opening, -coldeg+rowdeg+0.5, \
                            0, alt, 0))
                        stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                            (acid2, "FUNNEL", -coldeg-rowdeg-opening, -coldeg+rowdeg+0.5, \
                            0, alt, 0))

                if SAVESCENARIOS:
                    fname = "funnel"+str(size)
                    stack.stack("SAVEIC %s" % fname)

        # create a conflict with several aircraft flying in a matrix formation
        elif command == "MATRIX":
            if numargs == 0:
                return True, callsign + "MATRIX <SIZE>"
            else:
                size = int(float(cmdargs[1]))
                scr.isoalt = 0

                mperdeg = 111319.
                hsep = traf.asas.R # [m] horizontal separation minimum
                hseplat = hsep/mperdeg
                matsep = 1.1 #factor of extra space in the matrix
                hseplat = hseplat*matsep
                vel = 200 #m/s
                extradist = (vel*1.1)*5*60/mperdeg #degrees latlon flown in 5 minutes

                for i in range(size):
                    acidn = "NORTH"+str(i)
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acidn, "MATRIX", hseplat*(size-1.)/2+extradist, (i-(size-1.)/2)*hseplat, \
                        180, 20000*ft, vel))
                    acids = "SOUTH"+str(i)
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acids, "MATRIX", -hseplat*(size-1.)/2-extradist, (i-(size-1.)/2)*hseplat, \
                        0, 20000*ft, vel))
                    acide = "EAST"+str(i)
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acide, "MATRIX", (i-(size-1.)/2)*hseplat, hseplat*(size-1.)/2+extradist, \
                        270, 20000*ft, vel))
                    acidw = "WEST"+str(i)
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acidw, "MATRIX", (i-(size-1.)/2)*hseplat, -hseplat*(size-1.)/2-extradist, \
                        90, 20000*ft, vel))

                if SAVESCENARIOS:
                    fname = "matrix"+str(size)
                    stack.stack("SAVEIC %s" % fname)
                return True

        # create a conflict with several aircraft flying in a floor formation
        elif command == "FLOOR":
            scr.isoalt = 1./50

            mperdeg = 111319.
            altdif = 3000 # ft
            hsep = traf.asas.R # [m] horizontal separation minimum
            floorsep = 1.1 #factor of extra spacing in the floor
            hseplat = hsep/mperdeg*floorsep
            stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                ("OWNSHIP", "FLOOR", -1, 0, 90, (20000+altdif)*ft, 200))
            idx = traf.id.index("OWNSHIP")
            traf.avs[idx] = -10
            traf.aalt[idx] = 20000-altdif
            for i in range(20):
                acid = "OTH"+str(i)
                stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                    (acid, "FLOOR", -1, (i-10)*hseplat, 90, 20000*ft, 200))
            if SAVESCENARIOS:
                fname = "floor"
                stack.stack("SAVEIC %s" % fname)
            return True

        # create a conflict with several aircraft overtaking eachother
        elif command == "OVERTAKE":
            if numargs == 0:
                return True, callsign + "OVERTAKE <NUMBER OF A/C>"
            else:
                numac = int(float(cmdargs[1]))
                scr.isoalt = 0

                mperdeg = 111319.
                vsteps = 50 #[m/s]
                for v in range(vsteps, vsteps*(numac+1), vsteps): #m/s
                    acid = "OT"+str(v)
                    distancetofly = v*5*60 #m
                    degtofly = distancetofly/mperdeg
                    stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                        (acid, "OT", 0, -degtofly, 90, 20000*ft, v))
                if SAVESCENARIOS:
                    fname = "overtake"+str(numac)
                    stack.stack("SAVEIC %s" % fname)
                return True

        # create a conflict with several aircraft flying in a wall formation
        elif command == "WALL":
            scr.isoalt = 0

            mperdeg = 111319.
            distance = 0.6 # in degrees lat/lon, for now
            hsep = traf.asas.R # [m] horizontal separation minimum
            hseplat = hsep/mperdeg
            wallsep = 1.1 #factor of extra space in the wall
            stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                ("OWNSHIP", "WALL", 0, -distance, 90, 20000*ft, 200))
            for i in range(20):
                acid = "OTHER"+str(i)
                stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                    (acid, "WALL", (i-10)*hseplat*wallsep, distance, 270, 20000*ft, 200))
            if SAVESCENARIOS:
                fname = "wall"
                stack.stack("SAVEIC %s" % fname)
            return True

        # create a conflict with several aircraft flying in two rows angled towards each other
        elif command == "ROW":
            commandhelp = "SYN ROW n angle " \
                "[-r=radius in NM] [-a=alt in ft] [-s=speed EAS in kts] [-t=actype]"
            if numargs == 0:
                return True, commandhelp
            else:
                try:
                     # start fresh
                    synerror, acalt, acspd, actype, startdistance, ang = self.__arguments__(numargs, cmdargs[1:])
                    if synerror:
                        raise Exception()

                    mperdeg = 111319.
                    hsep = traf.asas.R # [m] horizontal separation minimum
                    hseplat = hsep/mperdeg
                    matsep = 1.1 #factor of extra space in the formation
                    hseplat = hseplat*matsep

                    aclat = startdistance * np.cos(np.deg2rad(ang)) #[deg]
                    aclon = startdistance * np.sin(np.deg2rad(ang))
                    latsep = abs(hseplat * np.cos(np.deg2rad(90-ang))) #[deg]
                    lonsep = abs(hseplat * np.sin(np.deg2rad(90-ang)))

                    alternate = 1
                    for i in range(int(cmdargs[1])): # Create a/c
                        aclat = aclat+i*latsep*alternate
                        aclon = aclon-i*lonsep*alternate
                        stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                            ("ANG"+str(i*2), actype, aclat, aclon, 180+ang, acalt*ft, acspd))
                        stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                            ("ANG"+str(i*2+1), actype, aclat, -aclon, 180-ang, acalt*ft, acspd))
                        alternate = alternate * -1

                    stack.stack("PAN 0,0")
                    return True
                except Exception:
                    return False, 'unknown argument flag'
                except:
                    return False, commandhelp

        # create a conflict with several aircraft flying in two columns angled towards each other
        elif command == "COLUMN":
            commandhelp = "SYN COLUMN n angle " \
                "[-r=radius in NM] [-a=alt in ft] [-s=speed EAS in kts] [-t=actype]"
            if numargs == 0:
                return True, commandhelp
            else:
                try:
                     # start fresh
                    synerror, acalt, acspd, actype, startdistance, ang = self.__arguments__(numargs, cmdargs[1:])
                    if synerror:
                        raise Exception()

                    mperdeg = 111319.
                    hsep = traf.asas.R # [m] horizontal separation minimum
                    hseplat = hsep/mperdeg
                    matsep = 1.1 #factor of extra space in the formation
                    hseplat = hseplat*matsep

                    aclat = startdistance * np.cos(np.deg2rad(ang)) #[deg]
                    aclon = startdistance * np.sin(np.deg2rad(ang))
                    latsep = abs(hseplat * np.cos(np.deg2rad(ang))) #[deg]
                    lonsep = abs(hseplat * np.sin(np.deg2rad(ang)))

                    traf.create("ANG0", actype, aclat, aclon, 180+ang, acalt*ft, acspd)
                    traf.create("ANG1", actype, aclat, -aclon, 180-ang, acalt*ft, acspd)

                    for i in range(1, int(cmdargs[1])): # Create a/c
                        aclat = aclat+latsep
                        aclon = aclon+lonsep
                        stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                            ("ANG"+str(i*2), actype, aclat, aclon, 180+ang, acalt*ft, acspd))
                        stack.stack('CRE %s, %s, %f, %f, %f, %d, %d' % \
                            ("ANG"+str(i*2+1), actype, aclat, -aclon, 180-ang, acalt*ft, acspd))

                    stack.stack("PAN 0,0")
                    return True
                except Exception:
                    return False, 'unknown argument flag'
                except:
                    return False, commandhelp

        #give up
        else:
            return False, "Unknown command: " + callsign + command

    @staticmethod
    def __arguments__(numargs, cmdargs):
        """ processes arguments """
        syntaxerror = False
        # tunables:
        acalt = float(10000) # default
        acspd = float(300) # default
        actype = "B747" # default
        startdistance = 1 # default

        ang = float(cmdargs[1])/2

        if numargs > 2:   #process optional arguments
            for i in range(2, numargs): # loop over arguments (TODO: put arguments in np array)
                if cmdargs[i].upper().startswith("-R"): #radius
                    startdistance = geo.qdrpos(0, 0, 90, float(cmdargs[i][3:]))[2] #input in nm
                elif cmdargs[i].upper().startswith("-A"): #altitude
                    acalt = txt2alt(cmdargs[i][3:])*ft
                elif cmdargs[i].upper().startswith("-S"): #speed
                    acspd = txt2spd(cmdargs[i][3:], acalt)
                elif cmdargs[i].upper().startswith("-T"): #ac type
                    actype = cmdargs[i][3:].upper()
                else:
                    syntaxerror = True
        return syntaxerror, acalt, acspd, actype, startdistance, ang
