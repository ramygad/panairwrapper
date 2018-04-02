"""This module provides a Python wrapper for the Panair program.

The primary purpose of this module is to provide a programmatic
interface) for Panair. This is done through the Panair interface available to
us, the input and output files. Thus, this module handles all of the formatting
details of generating a Panair inputfile and extracting data from the
outputfiles.

Additionaly, this module seeks to provide sane defaults for the many settings
available in Panair. This allows a user to start out simple and then dig into
the Panair settings as necessary for special cases.

By providing a programmatic interface to running Panair cases, this module
facilitates the creation of interfaces between Panair and other codes. For
example, another code can be used for generating/specifying a geometry
description or for postprocessing or visualizing results.

Example
-------
# generate and run Panair case
import panairwrapper.panairwrapper as panair

axie_case = panair.Case("NASA25D AXIE",
                        "Ted Giblette, USU AEROLAB")

axie_case.set_aero_state(mach=1.6, alpha=0., beta=0.)

axie_case.add_network("front", network_points_0)
axie_case.add_network("front_mid", network_points_1)
axie_case.add_network("back_mid", network_points_2)
axie_case.add_network("back", network_points_3)

axie_case.add_offbody_points(off_body_points)

results = axie_case.run()

offbody_data = results.get_offbody_data()

Notes
-----
Although simplifying to some degree the use of Panair, this module does
not remove the need of the user to understand the proper use of the Panair
program. Original documentation for Panair can be found at
http://www.pdas.com/panairrefs.html
It should also be noted that this is a work in progress so not all of the
functionaltity of Panair has been built into this interface. Feel free to
request or contribute any desired additions!

The use of this module is obviously based on Panair already being
installed on your system. Source code can be found at
http://www.pdas.com/panair.html
and is simple to install. Once installed the...
TODO: Move usage explanation to README.md

"""
from collections import OrderedDict
import panairwrapper.filehandling as fh
import os
import subprocess
import shutil


class Case:
    """The primary access point for specifying and running a case.

    Parameters
    ----------
    title : str
        This becomes the identifier for the case. All the files generated
        for the case will be stored in a folder under this name.

    description : str
        Option for including any additional description about the case. This
        description should be brief and will be included in the Panair input
        file when it is generated.

    Notes
    -----

    Examples
    --------

    """
    def __init__(self, title, description=""):
        self._title = title
        self._description = description
        self._aero_state = None
        self._symmetry = [True, False]
        self._networks = []
        self._results = None
        self._offbody_points = None

    def _generate_inputfile(self):

        # Build inputfile, specifying defaults when necessary
        inputfile = fh.InputFile()
        inputfile.title(self._title, self._description)
        inputfile.datacheck(0)
        inputfile.symmetric(int(self._symmetry[0]), int(self._symmetry[1]))

        # aerodynamic state inputs
        if self._aero_state:
            mach_number, alpha, beta = self._aero_state
            inputfile.mach(mach_number)
            inputfile.cases(1)
            inputfile.anglesofattack(alpha, [alpha])
            inputfile.yawangle(beta, [beta])
        else:
            raise RuntimeError("Aero state inputs must be provided.")

        inputfile.printout(0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0)

        # network inputs
        if self._networks:
            network_list = list(self._networks)

            # add networks to inputfile, grouping them by network type
            while network_list:
                # remove first network from list
                sub_list = [network_list.pop(0)]

                # determine all networks that are of the same type as this network
                matching_networks = [n for n in network_list if n[2] == sub_list[0][2]]
                sub_list.extend(matching_networks)

                # remove all networks of this type from network list
                network_list[:] = [n for n in network_list if not n[2] == sub_list[0][2]]

                # format network data for adding to inpufile
                count = len(sub_list)
                n_type = sub_list[0][2]
                net_names = [n[0] for n in sub_list]
                net_data = [n[1] for n in sub_list]

                inputfile.points(count, n_type, net_names, net_data)

        else:
            raise RuntimeError("Network inputs must be provided.")

        # offbody inputs
        if self._offbody_points is not None:
            inputfile.flowfieldproperties(1., 0.)
            inputfile.xyzcoordinatesofoffbodypoints(len(self._offbody_points),
                                                    self._offbody_points)

        # write inputfile
        self._filename = self._title.replace(" ", "_")+".INP"
        inputfile.write_inputfile(self._directory+self._filename)

    def set_aero_state(self, mach=0, alpha=0, beta=0):
        self._aero_state = [mach, alpha, beta]

    def add_network(self, network_name, network_data, network_type=1):
        self._networks.append([network_name, network_data, network_type])

    def add_offbody_points(self, offbody_points):
        self._offbody_points = offbody_points

    def run(self):
        """Generates Panair inputfile and runs case.

        Returns
        -------
        results : ?

        Examples
        --------

        """
        self._generate_dir()
        self._generate_inputfile()
        self._call_panair()
        self._results = Results(self._directory)
        return self._results
        # if self._check_if_successful():
        #     self._gather_results()
        #     return self._results
        # else:
        #     raise RuntimeError("Run not successful. Check panair.out for cause")

    def _generate_dir(self):
        # create directory for case if it doesn't exist
        self._directory = "./"+self._title.replace(" ", "_")+"/"
        if not os.path.exists(self._directory):
            os.makedirs(self._directory)
        else:
            # remove old files
            files = os.listdir(self._directory)
            for f in files:
                if f.startswith('rwms'):
                    os.remove(os.path.join(self._directory, f))

        # copy in panair.exec
        shutil.copy2('./panair', self._directory)


    def _call_panair(self):
        p = subprocess.Popen('./panair', stdin=subprocess.PIPE,
                             cwd=self._directory)
        p.communicate(self._filename.encode('ascii'))


class Results:
    """Handles the parsing of Panair output files for data retrieval"""
    def __init__(self, directory):
        self._output_file = fh.OutputFile(directory)

    def get_offbody_data(self):
        return self._output_file.get_offbody_data()