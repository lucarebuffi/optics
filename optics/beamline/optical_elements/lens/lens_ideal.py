"""
Represents an ideal lens.
"""
from optics.beamline.beamline_component import BeamlineComponent
from collections import OrderedDict


class LensIdeal(BeamlineComponent):
    def __init__(self, name, focal_x, focal_y):
        BeamlineComponent.__init__(self, name=name)
        self._focal_x = focal_x
        self._focal_y = focal_y

    def focalX(self): 
        return self._focal_x

    def focalY(self):
        return self._focal_y

    def to_dictionary(self):
        #returns a dictionary with the variable names as keys, and a tuple with value, unit and doc string
        mytuple = [ ("focal_x"   ,( self._focal_x ,"m",  "Ideal lens focal length (horizontal)" ) ),
                    ("focal_y"   ,( self._focal_y ,"m",  "Ideal lens focal length (vertical)"  ) )]
        return(OrderedDict(mytuple))