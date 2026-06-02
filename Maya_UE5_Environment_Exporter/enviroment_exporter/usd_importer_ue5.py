import json
import os
import traceback
from datetime import datetime

import unreal


class UE5Importer:
    """
    Handles importing a USD modular kit into Unreal Engine 5.

    Methods:
        .run(usd_file, destination_folder): Full import pipeline entry point.
        ._log_metadata(json_path): Reads and logs sidecar JSON publish info.
        ._build_import_task(usd_file, destination_folder): Creates and configures the AssetImportTask.
        ._update_metadata(json_path, imported, destination_folder): Writes UE results back to sidecar JSON.

    attributes:
        usd_file(str): Path to the location of the USD file.
        destination_folder(str): Path to the location in UE5 to dump meshes.
    """

    def __init__(self, usd_file, destination_folder):
        # Initializes the variables.
        self.usd_file = usd_file
        self.destination_folder = destination_folder
        self.usd_dir = os.path.dirname(usd_file)
        self.log_file = os.path.join(self.usd_dir, "UE_Import_Log.txt")
        self.json_path = os.path.splitext(usd_file)[0] + ".json"

        # Reset log on each run
        with open(self.log_file, "w") as f:
            f.write("--- START ---\n")

    def _log(self, msg):
        """
        Description:
        It logs the information happening in the information.

        Input:
        msg(str): The message logging.

        Output:
        msg(str): The message logged.
        """
        # Creates a function that will log in Unreal engine and in the document.
        unreal.log(msg)
        with open(self.log_file, "a") as f:
            f.write(msg + "\n")
        return msg

    def _log_metadata(self):
        """
        Description:
        Reads and logs sidecar JSON if present.
        Input:
        None
        Output:
        meta(dict): Stores the meta data information.
        """
        # Verifies the json path exists.
        if not os.path.exists(self.json_path):
            return False
        # It opens and loads the json file and metadata.
        with open(self.json_path, "r") as f:
            meta = json.load(f)
        # It logs the information from the JSON.
        self._log("--- PUBLISH METADATA ---")
        self._log(
            f"  Tool:        {meta.get('tool', 'N/A')} v{meta.get('version', 'N/A')}"
        )
        self._log(f"  Artist:      {meta.get('artist', 'N/A')}")
        self._log(f"  Scene:       {meta.get('maya_scene', 'N/A')}")
        self._log(f"  Exported:    {meta.get('export_date', 'N/A')}")
        self._log(f"  Asset count: {meta.get('asset_count', 'N/A')}")
        self._log("------------------------")
        return meta

    def _build_import_task(self):
        """
        Description:
        Creates and configures the AssetImportTask.
        Input:
        None
        Output:
        task(instance): Is an instance of the method of the class AssetImportTask()
        """
        try:
            # It assigns the method import task to an object to work on it.
            task = unreal.AssetImportTask()
            # It grabs the USD file.
            task.filename = self.usd_file
            # Sets the destination path inside unreal.
            task.destination_path = f"{self.destination_folder}/Modular_Kit_Imports"
            # It automates the process so no window appears.
            task.automated = True
            # It replaces the meshes inside the destination folders.
            task.replace_existing = True
            # It saves after it finishes.
            task.save = True

            # It sets the parameters for the USD import.
            options = unreal.UsdStageImportOptions()
            # Imports the geometry but ignores the materials.
            options.import_geometry = True
            options.import_materials = False
            # Sets the import options from the options above.
            task.options = options
            # Imports the assets.
            task.factory = unreal.UsdStageImportFactory()
            return task

        except Exception as e:
            self._log(f"ERROR: {e}")
            return False

    def _update_metadata(self, imported):
        """
        Desription:
        Writes UE import results back into the sidecar JSON.
        Input:
        Imported(list): List of assets imported into UE5.
        Output:
        True/False(bool): If the function was as success.
        """
        # Verifies the json path exists.
        if not os.path.exists(self.json_path):
            return False
        # It opens the json file.
        try:
            with open(self.json_path, "r") as f:
                meta = json.load(f)
            # It updates the json file with time, list of assets, and fodler.
            meta["ue_import_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            meta["ue_imported_assets"] = imported
            meta["ue_destination"] = f"{self.destination_folder}/Modular_Kit_Imports"
            # It writes the adjustments into the JSON file.
            with open(self.json_path, "w") as f:
                json.dump(meta, f, indent=4)
            self._log("Sidecar JSON updated with UE import results.")

            return True

        except Exception as e:
            self._log(f"ERROR: {e}")
            return False

    def run(self):
        """
        Description:
        Full import pipeline entry point.
        Input:
        Output:
        """
        try:
            # It verifies the USD file path exists.
            self._log("1. Checking USD file exists...")
            if not os.path.exists(self.usd_file):
                self._log(f"ERROR: File not found: {self.usd_file}")
                return

            # Runs the log metadata method.
            self._log_metadata()

            # Builds the Instance and options for the USD import.
            self._log("2. Building import task...")
            task = self._build_import_task()

            # It runs the import.
            self._log("3. Running import...")
            # Saving this method into a variable.
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            # Reads the file path and executes the import with thre tasks preferences.
            asset_tools.import_asset_tasks([task])

            # Makes a list of the imported objects from USD.
            # BUG FIX: imported_object_paths returns an Unreal Array, not a Python list.
            # json.dump can't serialize it — cast to list first.
            imported = list(task.imported_object_paths)
            if imported:
                self._log(f"SUCCESS: {len(imported)} asset(s) imported:")
                for p in imported:
                    self._log(f"  {p}")
                self._update_metadata(imported)
            else:
                self._log("WARNING: Import ran but no assets were created.")

        except Exception:
            self._log(f"FATAL ERROR:\n{traceback.format_exc()}")


def import_usd_modular_kit(usd_file, destination_folder):
    """
    Entry point called by the bootstrap script.

    Inputs:
        usd_file (str): Path to the USD file.
        destination_folder (str): Target folder inside UE content browser.
    """
    UE5Importer(usd_file, destination_folder).run()
