from ..settings import prefer_compiled
if prefer_compiled:
    try:
        import cgeo as geo
    except ImportError:
        import geo
else:
    import geo

class Toolsmodule(object):
    """ Super class for tools modules """
    def __init__(self, sim, scr, moduletype):
        from .. import stack
        self.sim = sim
        self.traf = sim.traf
        self.scr = scr
        self.stack = stack
        self.moduletype = moduletype

    def add_stack_commands(self, cmddict):
        """ Add command to stack """
        self.stack.append_commands(cmddict)
