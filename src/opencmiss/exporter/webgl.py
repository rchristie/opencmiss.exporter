"""
Geometric fit model adding visualisations to github.com/ABI-Software/scaffoldfitter
"""
import os
import json

from opencmiss.argon.argondocument import ArgonDocument
from opencmiss.argon.argonlogger import ArgonLogger
from opencmiss.argon.argonerror import ArgonError


class ArgonSceneExporter(object):
    """
    Export a visualisation described by an Argon document to webGL.
    """

    def __init__(self, input_argon_doc_file, output_target=None, output_prefix=None):
        """
        :param input_argon_doc_file: The argon document to export.
        :param output_target: The target directory to export the visualisation to.
        """
        self._output_target = output_target
        self._document = ArgonDocument()
        self._document.initialiseVisualisationContents()
        self._prefix = "ArgonSceneExporter"
        if output_prefix is not None:
            self._prefix = output_prefix
        self._numberOfTimeSteps = 10
        self._initialTime = 0.0
        self._finishTime = 1.0
        self.load(input_argon_doc_file)

    def load(self, filename):
        """
        Loads the named Argon file and on success sets filename as the current location.
        Emits documentChange separately if new document loaded, including if existing document cleared due to load failure.
        :return  True on success, otherwise False.
        """
        try:
            with open(filename, 'r') as f:
                state = f.read()

            current_wd = os.getcwd()
            # set current directory to path from file, to support scripts and FieldML with external resources
            path = os.path.dirname(filename)
            os.chdir(path)
            self._document.deserialize(state)
            os.chdir(current_wd)
            return True
        except (ArgonError, IOError, ValueError) as e:
            ArgonLogger.getLogger().error("Failed to load Argon visualisation " + filename + ": " + str(e))
        except Exception as e:
            ArgonLogger.getLogger().error("Failed to load Argon visualisation " + filename + ": Unknown error " + str(e))

        return False

    def set_parameters(self, parameters):
        self._numberOfTimeSteps = parameters["numberOfTimeSteps"]
        self._initialTime = parameters["initialTime"]
        self._finishTime = parameters["finishTime"]
        self._prefix = parameters["prefix"]

    def _form_full_filename(self, filename):
        return filename if self._output_target is None else os.path.join(self._output_target, filename)

    def export(self, output_target=None):
        if output_target is not None:
            self._output_target = output_target
        self.export_view()
        self.export_webgl()

    def export_view(self):
        """Export sceneviewer parameters to JSON format"""
        sceneviewer = self._document.getSceneviewer()
        viewData = {'farPlane': sceneviewer._far_clipping_plane, 'nearPlane': sceneviewer._near_clipping_plane, 'eyePosition': sceneviewer._eye_position,
                    'targetPosition': sceneviewer._lookat_position, 'upVector': sceneviewer._up_vector}

        view_file = self._form_full_filename(self._prefix + '_view.json')
        with open(view_file, 'w') as f:
            json.dump(viewData, f)

    def export_webgl(self):
        """
        Export graphics into JSON format, one json export represents one
        surface graphics.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        sceneSR = scene.createStreaminformationScene()
        sceneSR.setIOFormat(sceneSR.IO_FORMAT_THREEJS)
        """
        Output frames of the deforming heart between time 0 to 1,
        this matches the number of frame we have read in previously
        """
        sceneSR.setNumberOfTimeSteps(self._numberOfTimeSteps)
        sceneSR.setInitialTime(self._initialTime)
        sceneSR.setFinishTime(self._finishTime)
        """ We want the geometries and colours change overtime """
        sceneSR.setOutputTimeDependentVertices(1)
        sceneSR.setOutputTimeDependentColours(1)
        number = sceneSR.getNumberOfResourcesRequired()
        resources = []
        """Write out each graphics into a json file which can be rendered with ZincJS"""
        for i in range(number):
            resources.append(sceneSR.createStreamresourceMemory())
        scene.write(sceneSR)
        """Write out each resource into their own file"""
        for i in range(number):
            buffer = resources[i].getBuffer()[1].decode()

            if i == 0:
                for j in range(number - 1):
                    """
                    IMPORTANT: the replace name here is relative to your html page, so adjust it
                    accordingly.
                    """
                    replaceName = '' + self._prefix + '_' + str(j + 1) + '.json'
                    old_name = 'memory_resource' + '_' + str(j + 2)
                    buffer = buffer.replace(old_name, replaceName)
                viewObj = {
                    "Type": "View",
                    "URL": self._prefix + '_view' + '.json'
                }
                obj = json.loads(buffer)
                obj.append(viewObj)
                buffer = json.dumps(obj)

            if i == 0:
                current_file = self._form_full_filename(self._prefix + '_metadata.json')
            else:
                current_file = self._form_full_filename(self._prefix + '_' + str(i) + '.json')

            with open(current_file, 'w') as f:
                f.write(buffer)
