import importlib
import json
import os
from datetime import datetime
from pathlib import Path

import maya.cmds as cmds
from pxr import Usd

from . import Constants as cons
from . import unreal_loader as ueload
from .logger import get_logger

importlib.reload(cons)
importlib.reload(ueload)

# Set up logger
logger = get_logger()


class MayaPipelineEngine:
    """
    Description: It processes the maya scene nodes and meshes before exporting.
    """

    @staticmethod
    def node_checker(node):
        if not cmds.objExists(node):
            logger.warning(f'Warning: Node "{node}" does not exist.')
            return False
        return True

    @staticmethod
    def is_valid_for_export(node):
        if cmds.lockNode(node, query=True, lock=True)[0]:
            return False
        if not cmds.listRelatives(node, children=True, type="mesh"):
            return False
        return True

    @staticmethod
    def export_with_clean_duplicates(valid_nodes, usd_path_str, centered=False):
        """
        Duplicates the selection, centers it based on custom pivots, cleans history,
        exports via the native Maya USD plugin, and deletes the duplicates to leave
        the user's scene completely untouched.
        """
        duplicates_to_export = []
        original_renames = {}

        try:
            for node in valid_nodes:
                short_name = node.split("|")[-1]

                # 1. Duplicate safely
                dup_list = cmds.duplicate(node, returnRootsOnly=True)
                if not dup_list:
                    continue
                dup = dup_list[0]

                # 2. Unparent to world to avoid group transformations
                if cmds.listRelatives(dup, parent=True):
                    dup = cmds.parent(dup, world=True)[0]

                # 3. Center to origin using the custom Maya pivot
                if centered:
                    cmds.move(0, 0, 0, dup, rotatePivotRelative=True)

                # 4. Clean history (removes phantom shapes) and freeze transforms
                cmds.delete(dup, ch=True)
                cmds.makeIdentity(
                    dup, apply=True, translate=True, rotate=True, scale=True
                )

                # 5. Swap names so USD gets the exact original mesh name
                temp_orig = cmds.rename(node, short_name + "_TEMP_ORIG")
                final_dup = cmds.rename(dup, short_name)

                original_renames[temp_orig] = short_name
                duplicates_to_export.append(final_dup)

            # Export using native Maya USD plugin
            cmds.select(duplicates_to_export, replace=True)

            if not cmds.pluginInfo(cons.PLUGININFO_MAYA, query=True, loaded=True):
                cmds.loadPlugin(cons.PLUGININFO_MAYA)

            export_path = Path(usd_path_str)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            cmds.mayaUSDExport(
                file=str(export_path),
                selection=True,
                mergeTransformAndShape=True,
                defaultMeshScheme="none",
                exportUVs=True,
                exportColorSets=False,
            )

            logger.info(f"Data published to USD: {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export USD: {e}")
            return False

        finally:
            # 6. Silent cleanup - delete duplicates and restore names
            if duplicates_to_export:
                cmds.delete(duplicates_to_export)

            for temp_orig, original_short_name in original_renames.items():
                if cmds.objExists(temp_orig):
                    cmds.rename(temp_orig, original_short_name)

    @staticmethod
    def write_metadata(usd_path, valid_nodes):
        usd_path = Path(usd_path)
        scene_path = cmds.file(query=True, sceneName=True) or "Unsaved Scene"
        artist = os.getenv("USERNAME", "Unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

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

        json_path = usd_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Metadata written to: {json_path}")

        try:
            stage = Usd.Stage.Open(str(usd_path))
            comment = (
                f"Exported by Maya to UE5 Pipeline v{cons.TOOL_VERSION} | "
                f"Artist: {artist} | "
                f"Scene: {Path(scene_path).name} | "
                f"Date: {timestamp} | "
                f"Assets: {len(valid_nodes)}"
            )

            stage.SetMetadata("comment", comment)
            stage.Save()
            logger.info("USD comment metadata embedded.")

        except Exception as e:
            logger.warning(f"Could not embed USD metadata (pxr not available): {e}")


class EnvironmentExporterController:
    """
    Handles the exporting logic of the enviroment and selection.
    """

    def __init__(self):
        pass

    def process_selection(
        self,
        target_folder,
        filename=cons.FILENAME,
        project_path=cons.TEMP_PRO_PATH,
        centered=False,  # Received from UI
        ue_destination="/Game",  # Received from UI
    ):
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            logger.warning("No meshes selected. Aborting export.")
            return None

        try:
            target_path = Path(target_folder)
            target_path.mkdir(parents=True, exist_ok=True)
            usd_path = target_path / filename

            valid_nodes = []

            for node in selection:
                if not MayaPipelineEngine.is_valid_for_export(node):
                    logger.warning(f"Skipping {node}: Not valid for export.")
                    continue
                valid_nodes.append(node)

            if valid_nodes:
                # Trigger the clean duplicate export method
                if MayaPipelineEngine.export_with_clean_duplicates(
                    valid_nodes, str(usd_path), centered
                ):
                    MayaPipelineEngine.write_metadata(str(usd_path), valid_nodes)

                    launcher = ueload.UnrealBridge
                    exe_path = launcher.find_ue5()
                    script_dir = Path(__file__).parent.resolve()

                    if exe_path:
                        if Path(project_path).exists():
                            launcher.launch_unreal(
                                exe_path,
                                project_path,
                                str(usd_path),
                                str(script_dir),
                                ue_destination=ue_destination,
                            )
                        else:
                            logger.warning(f"No UE5 project selected: {project_path}")
                            return False
                    logger.info(f"Successfully synced modular kit to UE: {usd_path}")
                    return str(usd_path)
                else:
                    logger.warning("Export failed during plugin execution.")
                    return None
            else:
                logger.warning("No valid meshes left to export.")
                return None

        except Exception as e:
            logger.error(f"Something went wrong during processing: {e}")
            return None
