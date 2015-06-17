"""
Implement a vertical undulator.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from optics.magnetic_structures.undulator import Undulator


class UndulatorVertical(Undulator):
    def __init__(self,K , period_length, periods_number):

        Undulator.__init__(self,
                           K_vertical=K,
                           K_horizontal=0.0,
                           period_length=period_length,
                           periods_number=periods_number)

    def K(self):
            K = self.K_vertical()

    def B(self):
        return self._magneticFieldStrengthFromK(self.K())
