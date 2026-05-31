import importlib
import json
import os
from datetime import datetime
from pathlib import Path

import Constants as cons
import maya.cmds as cmds
import unreal_loader as ueload
from logger import get_logger
from pxr import Usd

importlib.reload(cons)
importlib.reload(ueload)

# Set up logger
logger = get_logger()


class MayaPipelineEngine:
    """
    Description: It processes the maya scene nodes and meshes before exporting.

    Modules:
    .node_checker(node): It checks there is something to export.
    .is_valid_for_export(node): Verifies that it is a mesh and that it isnt locked.
    .prepare_mesh(node,centered = True): It prepares the mesh to be as a modular kit.
    .export_selection to usd(export_path_str): Grabs the selection and exports it as usd.
    """

    @staticmethod
    def node_checker(node):
        """
        Description: Verifies there is something to export in the selection.

        Input:
        node(object): The list or object form maya that holds the information.

        Output:
        True/false(bool): Success or failure in the operation.
        """
        # Checks if the object inside node exists in maya, if so returns true.
        if not cmds.objExists(node):
            logger.warning(f'Warning: Node "{node}" does not exist.')
            return False
        return True

    @staticmethod
    def is_valid_for_export(node):
        """
        Description: Verifies the mesh locked and relative properties to publish.
        Input:
        node(object): The list or object form maya that holds the information.
        Output:
        True/false(bool): Success or failure in the operation.
        """
        # Checks if the root of the selected node is locked, if locked its fasle.
        if cmds.lockNode(node, query=True, lock=True)[0]:
            return False
        # Verifies the selection is a mesh.
        if not cmds.listRelatives(node, children=True, type="mesh"):
            return False
        return True

    @staticmethod
    def prepare_mesh(node, centered=False):
        """
        Desccription: Prepares the mesh by freezing transforms and deleting history.
        Input:
        node(object): The list or object form maya that holds the information.
        centered(bool): User option to select if you want to center objects.
        True/false(bool): Success or failure in the operation.
        """
        # checks there is something to work on.
        if not MayaPipelineEngine.node_checker(node):
            return False

        try:
            # Deletes the objects history.
            cmds.delete(node, ch=True)
            # It freezes the transformations of the objects.
            cmds.makeIdentity(node, apply=True, translate=True, rotate=True, scale=True)
            # Centers the selection of the nodes.
            if centered:
                cmds.xform(node, pivots=[0, 0, 0], worldSpace=True)
            return True

        except Exception as e:
            logger.warning(f"Preparation error on {node}: {e}")
            return False

    @staticmethod
    def export_selection_to_usd(export_path_str):
        """
        Description:
        Exports the current Maya selection to a USD file optimized for Unreal Engine.
        Input:
        export_path_str(str): The folder directory to export the USD file.
        Output:
        export_path(str): The agnostic path directory of the USD file location.
        """
        try:
            # Ensure the Maya USD plugin is loaded
            if not cmds.pluginInfo(cons.PLUGININFO_MAYA, query=True, loaded=True):
                cmds.loadPlugin(cons.PLUGININFO_MAYA)

            # It ensures the directory exists and creates one if not.
            export_path = Path(export_path_str)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            # Exports the selection into an USD file.
            cmds.mayaUSDExport(
                file=str(export_path),
                selection=True,
                mergeTransformAndShape=True,
                defaultMeshScheme="none",
                exportUVs=True,
                exportColorSets=False,
            )

            # Logs the information.
            logger.info(f"Data published to USD: {export_path}")
            return True, export_path

        except Exception as e:
            logger.error(f"Failed to export USD: {e}")
            return False

    @staticmethod
    def write_metadata(usd_path, valid_nodes):
        """
        Description:
        Writes a sidecar JSON and embeds a comment into the USD file.
        Input:
        usd_path(str): The location the USD file lives in.
        valid_nodes(objects): The selected object or list in maya.
        """
        # Gets the meta data of the path, scene, artist machine, and time.
        usd_path = Path(usd_path)
        scene_path = cmds.file(query=True, sceneName=True) or "Unsaved Scene"
        artist = os.getenv("USERNAME", "Unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Creates a dictionary with the meta data of the object.
        metadata = {
            "tool": "Maya to UE5 Environment Exporter",
            "version": cons.TOOL_VERSION,
            "artist": artist,
            "export_date": timestamp,
            "maya_scene": scene_path,
            "usd_file": usd_path.name,
            "asset_count": len(valid_nodes),
            "assets": [Path(n).name for n in valid_nodes],
        }

        # It creates a jason path to dump the meta data.
        json_path = usd_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Metadata written to: {json_path}")

        # Embeds the meta data inside the usd file.
        try:
            # Opens the stage(file) to write in it.
            stage = Usd.Stage.Open(str(usd_path))

            # Sets the metadata into a variable.
            comment = (
                f"Exported by Maya to UE5 Pipeline v{cons.TOOL_VERSION} | "
                f"Artist: {artist} | "
                f"Scene: {Path(scene_path).name} | "
                f"Date: {timestamp} | "
                f"Assets: {len(valid_nodes)}"
            )

            # It writes the metadata as a comment into the stage and saves it.
            stage.SetMetadata("comment", comment)
            stage.Save()
            logger.info("USD comment metadata embedded.")

        except Exception as e:
            logger.warning(f"Could not embed USD metadata (pxr not available): {e}")


class EnvironmentExporterController:
    """
    Handles the exporting logic of the enviroment adn selection.
    """

    def __init__(self):
        pass

    def process_selection(
        self, target_folder, filename=cons.FILENAME, project_path=cons.TEMP_PRO_PATH
    ):
        """
        Description:
        Grabs the selection in Maya, processes each mesh, and exports to a single USD file.
        Input:
        target_folder(str): The destination folder you want your USD file.
        filename(str): The name of the USD file you want.
        project_path (str): Unreal Engine 5 project path file.

        """
        # Grabs and verifies there are selected meshes.
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            logger.warning("No meshes selected. Aborting export.")
            return None

        try:
            # Converts the path to agnostic object.
            target_path = Path(target_folder)

            # Makes a directory if it doesn´t exists.
            target_path.mkdir(parents=True, exist_ok=True)
            # MAkes an usd path based on the folder and filename.
            usd_path = target_path / filename

            # Initializes and empty list.
            valid_nodes = []

            # Prepares each mesh individually.
            for node in selection:
                # Verifies they are meshes and that they are not locked.
                if not MayaPipelineEngine.is_valid_for_export(node):
                    logger.warning(f"Skipping {node}: Not valid for export.")
                    continue

                # It prepares each mesh history, center and transformations.
                if MayaPipelineEngine.prepare_mesh(node):
                    valid_nodes.append(node)
                else:
                    logger.warning(f"Skipping {node}: Preparation failed.")

            # Select all valid meshes and export them as one unified modular kit
            if valid_nodes:
                cmds.select(valid_nodes, replace=True)

                # If it runs the method write it to disk.
                if MayaPipelineEngine.export_selection_to_usd(str(usd_path)):
                    # Write the metadata to the usd and json.
                    MayaPipelineEngine.write_metadata(str(usd_path), valid_nodes)
                    # Loads the unreal engine laoder bridge.
                    launcher = ueload.UnrealBridge
                    # Finds the unreal engine 5 engine path.
                    exe_path = launcher.find_ue5()
                    # Finds the absolute path to this script.
                    script_dir = Path(__file__).parent.resolve()

                    # If it finds the Unreal engine path.
                    if exe_path:
                        if Path(project_path).exists():
                            launcher.launch_unreal(
                                exe_path,
                                project_path,
                                str(usd_path),
                                str(script_dir),
                            )
                        else:
                            logger.warning(f"No UE5 project selected: {project_path}")
                            return False
                    logger.info(f"Successfully synced modular kit to UE: {usd_path}")
                    return str(usd_path)
            else:
                logger.warning("No valid meshes left to export after preparation.")
                return None

        except Exception as e:
            logger.error(f"Something went wrong during processing: {e}")
            return None
