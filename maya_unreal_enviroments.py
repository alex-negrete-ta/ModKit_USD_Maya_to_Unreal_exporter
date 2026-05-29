import importlib
import logging
from pathlib import Path

import maya.cmds as cmds
import unreal_loader as ueload

importlib.reload(ueload)

# Set up logger
logger = logging.getLogger("EnvironmentExporter")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

TOOL_VERSION = "1.0"


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
        if not cmds.objExists(node):
            logger.warning(f'Warning: Node "{node}" does not exist.')
            return False
        return True

    @staticmethod
    def is_valid_for_export(node):
        """Checks if the mesh is ready to publish."""
        if cmds.lockNode(node, query=True, lock=True)[0]:
            return False
        if not cmds.listRelatives(node, children=True, type="mesh"):
            return False
        return True

    @staticmethod
    def prepare_mesh(node, centered=False):
        """Prepares the mesh by freezing transforms and deleting history."""
        if not MayaPipelineEngine.node_checker(node):
            return False

        try:
            cmds.delete(node, ch=True)
            cmds.makeIdentity(node, apply=True, translate=True, rotate=True, scale=True)
            if centered:
                cmds.xform(node, pivots=[0, 0, 0], worldSpace=True)
            return True

        except Exception as e:
            logger.warning(f"Preparation error on {node}: {e}")
            return False

    @staticmethod
    def export_selection_to_usd(export_path_str):
        """
        Exports the current Maya selection to a USD file optimized for Unreal Engine.
        """
        try:
            # Ensure the Maya USD plugin is loaded
            if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
                cmds.loadPlugin("mayaUsdPlugin")

            export_path = Path(export_path_str)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            # The native, powerful Maya USD export command
            cmds.mayaUSDExport(
                file=str(export_path),
                selection=True,
                mergeTransformAndShape=True,
                defaultMeshScheme="none",  # 'none' is best for real-time/games (no subdiv)
                exportUVs=True,
                exportColorSets=False,
            )

            logger.info(f"Data published to USD: {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export USD: {e}")
            return False


class EnvironmentExporterController:
    def __init__(self):
        pass

    def process_selection(self, target_folder, filename="LiveScene.usd"):
        """
        Grabs the selection in Maya, processes each mesh, and exports to a single USD file.
        """
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            logger.warning("No meshes selected. Aborting export.")
            return None

        try:
            target_path = Path(target_folder)

            # exist_ok=True allows the tool to create the folder if it doesn't exist
            target_path.mkdir(parents=True, exist_ok=True)
            usd_path = target_path / filename

            valid_nodes = []

            # 1. Prepare each mesh individually
            for node in selection:
                if not MayaPipelineEngine.is_valid_for_export(node):
                    logger.warning(f"Skipping {node}: Not valid for export.")
                    continue

                if MayaPipelineEngine.prepare_mesh(node):
                    valid_nodes.append(node)
                else:
                    logger.warning(f"Skipping {node}: Preparation failed.")

            # 2. Select all valid meshes and export them as one unified modular kit
            if valid_nodes:
                cmds.select(valid_nodes, replace=True)

                if MayaPipelineEngine.export_selection_to_usd(str(usd_path)):
                    MayaPipelineEngine.write_metadata(str(usd_path), valid_nodes)
                    launcher = ueload.UnrealBridge
                    exe_path = launcher.find_ue5()
                    script_dir = Path(__file__).parent.resolve()

                    if exe_path:
                        launcher.launch_unreal(
                            exe_path,
                            "D:/Projects/ChaewonEnv/UnrealEngine/Chaewoon/Chaewoon.uproject",
                            str(usd_path),
                            str(script_dir),  # Pass the script directory
                        )
                    logger.info(f"Successfully synced modular kit to UE: {usd_path}")
                    return str(usd_path)
            else:
                logger.warning("No valid meshes left to export after preparation.")
                return None

        except Exception as e:
            logger.error(f"Something went wrong during processing: {e}")
            return None
