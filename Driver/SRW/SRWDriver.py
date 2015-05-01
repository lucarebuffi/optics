"""
Minimal implementation of a SRW driver.
"""
from srwlib import *

from Driver.AbstractDriver import AbstractDriver
from Driver.SRW.SRWSourceSetting import SRWSourceSetting
from Driver.SRW.SRWBeamlineComponentSetting import SRWBeamlineComponentSetting

from Source.Undulator import Undulator
from Lens.LensIdeal import LensIdeal


class SRWDriver(AbstractDriver):

    def _SRWElectronBeam(self, electron_beam):
        """
        Private helper function to translate generic electron beam to srw "electron beam".
        Should/could go to another file.
        """

        srw_electron_beam = SRWLPartBeam()
        srw_electron_beam.Iavg = electron_beam.averageCurrent()
        srw_electron_beam.partStatMom1.x = electron_beam.x()
        srw_electron_beam.partStatMom1.y = electron_beam.y()

        srw_electron_beam.partStatMom1.z = 0
        srw_electron_beam.partStatMom1.xp = 0
        srw_electron_beam.partStatMom1.yp = 0
        srw_electron_beam.partStatMom1.gamma = electron_beam.gamma()

        return srw_electron_beam

    def _SRWUndulator(self, undulator):
        """
        Private helper function to translate generic undulator to srw "undulator".
        Should/could go to another file.
        """

        magnetic_fields = []

        if undulator.K_vertical() > 0.0:
            vertical_field = SRWLMagFldH(1, 'v', undulator.B_vertical(), 0, 1, 1)
            magnetic_fields.append(vertical_field)

        if undulator.K_horizontal() > 0.0:
            horizontal_field = SRWLMagFldH(1, 'h', undulator.B_horizontal(), 0, -1, 1)
            magnetic_fields.append(horizontal_field)

        srw_undulator = SRWLMagFldU(magnetic_fields,
                                    undulator.periodLength(),
                                    undulator.periodNumber())

        return srw_undulator

    def _magnetFieldFromUndulator(self, undulator):
        """
        Private helper function to generate srw magnetic fields.
        Should/could go to another file.
        """

        srw_undulator = self._SRWUndulator(undulator)

        magnetic_fields = SRWLMagFldC([srw_undulator],
                                      array('d', [0]), array('d', [0]), array('d', [0]))

        return magnetic_fields

    def _createQuadraticSRWWavefrontSingleEnergy(self, grid_size, grid_length, z_start, srw_electron_beam, energy):
        """
        Private helper function to translate a srw wavefront.
        """

        srw_wavefront = SRWLWfr()
        srw_wavefront.allocate(1, grid_size, grid_size)
        srw_wavefront.mesh.zStart = float(z_start)
        srw_wavefront.mesh.eStart = energy
        srw_wavefront.mesh.eFin   = energy
        srw_wavefront.mesh.xStart = -grid_length
        srw_wavefront.mesh.xFin   =  grid_length
        srw_wavefront.mesh.yStart = -grid_length
        srw_wavefront.mesh.yFin   =  grid_length

        srw_wavefront.partBeam = srw_electron_beam

        return srw_wavefront

    def calculateRadiation(self,electron_beam, radiation_source, beamline):
        """
        Calculates radiation.

        :param electron_beam: ElectronBeam object
        :param radiation_source: Source object
        :param beamline: Beamline object
        :return: SRW wavefront.
        """

        # Get position of the first component. We need this to know where to calculate the source radiation.
        first_component = beamline.componentByIndex(0)
        position_first_component = beamline.positionOf(first_component)

        # Create srw electron beam from generic electron beam.
        srw_electron_beam = self._SRWElectronBeam(electron_beam)

        # Calculate the source radiation depending on the chosen source.
        # Only undulator here.
        # In the real driver this should be refactored to separate functions.
        if isinstance(radiation_source, Undulator):
            undulator = radiation_source

            magFldCnt = self._magnetFieldFromUndulator(undulator)
            max_theta = undulator.gaussianCentralConeDivergence(electron_beam.gamma()) * 2.5

            z_start = undulator.length()+position_first_component.z()
            grid_length = max_theta * z_start / sqrt(2.0)

            wavefront = self._createQuadraticSRWWavefrontSingleEnergy(grid_size=1000,
                                                                      grid_length=grid_length,
                                                                      z_start=z_start,
                                                                      srw_electron_beam=srw_electron_beam,
                                                                      energy=int(undulator.resonanceEnergy(electron_beam.gamma(),0.0,0.0)))

            # Use custom settings if present. Otherwise use default SRW settings.
            if undulator.hasSettings(self):
                # Mind the self in the next line.
                # It tells the DriverSettingsManager to use SRW settings.
                undulator_settings = undulator.settings(self)
            else:
                undulator_settings = SRWSourceSetting()

            srwl.CalcElecFieldSR(wavefront, 0, magFldCnt, undulator_settings.toList())
        else:
            raise NotImplementedError

        # Create the srw beamline.
        srw_optical_element = list()
        srw_preferences = list()

        # Iterate over all beamline components and translate them.
        # Translate free space between two components to drift space.
        # Only lenses implemented.
        # In the real driver this should be refactored to separate functions.
        current_z_position = position_first_component.z()
        for component in beamline:
            position = beamline.positionOf(component)

            # Add drift space between two components.
            if position.z() > current_z_position:
                distance = position.z()-current_z_position
                srw_optical_element.append(SRWLOptD(distance))
                srw_preferences.append(SRWBeamlineComponentSetting().toList())
                current_z_position = position.z()

            if isinstance(component, LensIdeal):
                srw_component= SRWLOptL(component.focalX(),
                                        component.focalY())
                srw_optical_element.append(srw_component)
            else:
                raise NotImplementedError

            # Use custom settings if present. Otherwise use default SRW settings.
            if component.hasSettings(self):
                # Mind the self in the next line.
                # It tells the DriverSettingsManager to use SRW settings.
                component_settings = component.settings(self)
            else:
                component_settings = SRWBeamlineComponentSetting()

            srw_preferences.append(component_settings.toList())


        # Create the srw beamline object.
        srw_beamline = SRWLOptC(srw_optical_element,
                                srw_preferences)

        # Call SRW to perform propagation.
        srwl.PropagElecField(wavefront, srw_beamline)

        return wavefront

    def calculateIntensity(self, radiation):
        """
        Calculates intensity of the radiation.
        :param radiation: Object received from self.calculateRadiation
        :return: Intensity.
        """
        wavefront = radiation
        mesh = deepcopy(wavefront.mesh)
        intensity = array('f', [0]*mesh.nx*mesh.ny)
        srwl.CalcIntFromElecField(intensity, wavefront, 6, 0, 3, mesh.eStart, 0, 0)
        plot_mesh_x = [1e+06*mesh.xStart, 1e+06*mesh.xFin, mesh.nx]
        plot_mesh_y = [1e+06*mesh.yStart, 1e+06*mesh.yFin, mesh.ny]
        return [intensity, plot_mesh_x, plot_mesh_y]

    def calculatePhase(self, radiation):
        """
        Calculates intensity of the radiation.
        :param radiation: Object received from self.calculateRadiation
        :return: Phases.
        """
        wavefront = radiation
        mesh = deepcopy(wavefront.mesh)

        phase = array('d', [0]*mesh.nx*mesh.ny)
        srwl.CalcIntFromElecField(phase, wavefront, 0, 4, 3, mesh.eStart, 0, 0)
        plot_mesh_x = [1e+06*mesh.xStart, 1e+06*mesh.xFin, mesh.nx]
        plot_mesh_y = [1e+06*mesh.yStart, 1e+06*mesh.yFin, mesh.ny]

        return [phase, plot_mesh_x, plot_mesh_y]