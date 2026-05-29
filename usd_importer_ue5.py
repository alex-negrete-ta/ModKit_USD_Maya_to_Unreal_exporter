import json
import os
import traceback
from datetime import datetime

import unreal

TOOL_VERSION = "1.0"


def import_usd_modular_kit(usd_file, destination_folder):
    usd_dir = os.path.dirname(usd_file)
    log_file = os.path.join(usd_dir, "UE_Import_Log.txt")

    def _log(msg):
        unreal.log(msg)
        with open(log_file, "a") as f:
            f.write(msg + "\n")

    with open(log_file, "w") as f:
        f.write("--- START ---\n")

    try:
        _log("1. Checking USD file exists...")
        if not os.path.exists(usd_file):
            _log(f"ERROR: File not found: {usd_file}")
            return

        # Read and log sidecar metadata if present
        json_path = os.path.splitext(usd_file)[0] + ".json"
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                meta = json.load(f)
            _log("--- PUBLISH METADATA ---")
            _log(
                f"  Tool:        {meta.get('tool', 'N/A')} v{meta.get('version', 'N/A')}"
            )
            _log(f"  Artist:      {meta.get('artist', 'N/A')}")
            _log(f"  Scene:       {meta.get('maya_scene', 'N/A')}")
            _log(f"  Exported:    {meta.get('export_date', 'N/A')}")
            _log(f"  Asset count: {meta.get('asset_count', 'N/A')}")
            _log("------------------------")

        _log("2. Creating import task...")
        task = unreal.AssetImportTask()
        task.filename = usd_file
        task.destination_path = f"{destination_folder}/Modular_Kit_Imports"
        task.automated = True
        task.replace_existing = True
        task.save = True

        _log("3. Setting USD options...")
        options = unreal.UsdStageImportOptions()
        options.import_geometry = True
        options.import_materials = False
        task.options = options
        task.factory = unreal.UsdStageImportFactory()

        _log("4. Running import...")
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        asset_tools.import_asset_tasks([task])

        imported = task.imported_object_paths
        if imported:
            _log(f"SUCCESS: {len(imported)} asset(s) imported:")
            for p in imported:
                _log(f"  {p}")

            # Write UE-side completion metadata into the sidecar JSON
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    meta = json.load(f)
                meta["ue_import_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                meta["ue_imported_assets"] = imported
                meta["ue_destination"] = f"{destination_folder}/Modular_Kit_Imports"
                with open(json_path, "w") as f:
                    json.dump(meta, f, indent=4)
                _log("Sidecar JSON updated with UE import results.")
        else:
            _log("WARNING: Import ran but no assets were created.")

    except Exception:
        _log(f"FATAL ERROR:\n{traceback.format_exc()}")
