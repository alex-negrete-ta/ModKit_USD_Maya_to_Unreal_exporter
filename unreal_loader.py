import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("EnvironmentExporter")


class UnrealBridge:
    @staticmethod
    def launch_unreal(editor_path, project_path, usd_path, script_directory):
        """
        Description:
        Launches Unreal Engine 5 and triggers the custom USD importer script.
        Input:
        editor_path(str): The path where ue5 lives in the system.
        project_path(str): UE5 project location.
        usd_path(str): Path to the modular kit from maya.
        script_directory(str): Path to the python script locations.

        Output:
        True/False(bool): Success if the launch in unreal worked.

        """
        try:
            # Sets the paths as agnostic objects using PATH.
            editor = Path(editor_path)
            project = Path(project_path)
            usd_file = Path(usd_path)

            # Checks The project and UE5 are installed.
            if not editor.exists() or not project.exists():
                logger.error("Editor or Project path is invalid.")
                return False

            # Force forward slashes to prevent escape character crashes.
            safe_usd_file = str(usd_file).replace("\\", "/")
            safe_script_dir = str(script_directory).replace("\\", "/")

            # Creates a temp fodler for the python script to live in.
            python_dir = project.parent / "Content" / "Python"
            python_dir.mkdir(parents=True, exist_ok=True)

            # It sets the temp path for the init python script to execute in Unreal.
            startup_script_path = python_dir / "init_unreal.py"
            safe_startup_path = str(startup_script_path).replace("\\", "/")
            # IMPORTANT: Do not add spaces/tabs before these lines!
            ue_python_code = f"""import sys
import os
sys.path.append("{safe_script_dir}")
import usd_importer_ue5
usd_importer_ue5.import_usd_modular_kit("{safe_usd_file}", "/Game")
os.remove("{safe_startup_path}")
"""

            # It initialzied the python scripts and writes the script.
            with open(startup_script_path, "w") as f:
                f.write(ue_python_code)

            logger.info("Launching Unreal Engine 5... This may take a moment.")

            # Makes a list of the commands to subproccess to execute.
            cmd = [
                str(editor),
                str(project),
                "-log",
                "-stdout",
            ]

            # Executes Subprocess.
            proc = subprocess.Popen(cmd)
            logger.info(f"UE5 launched with PID {proc.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to open unreal: {e}")
            return None

    @staticmethod
    def find_ue5():
        """
        Description:
        Reads the Epic Games Launcher manifest to find the latest UE5 executable.
        Returns the string path to UnrealEditor.exe, or None if not found.
        """
        # The standard location for Epic's installation manifest on Windows
        program_data = os.environ.get("PROGRAMDATA", "C:\\ProgramData")

        # Makes a full path to the .dat file for unreal.
        manifest_path = (
            Path(program_data)
            / "Epic"
            / "UnrealEngineLauncher"
            / "LauncherInstalled.dat"
        )

        #  Checks there is a manifest or .dat file in the system.
        if not manifest_path.exists():
            logger.error(
                "Epic Games manifest not found. Is UE installed via the Launcher?"
            )
            return None

        try:
            with open(manifest_path, "r") as file:
                data = json.load(file)

            # Dictionary to store { "UE_5.3": "C:/Path/To/Engine" }
            ue_installs = {}

            for item in data.get("InstallationList", []):
                app_name = item.get("AppName", "")
                # We only want Unreal Engine 5.x
                if app_name.startswith("UE_5"):
                    ue_installs[app_name] = item.get("InstallLocation")

            if not ue_installs:
                logger.error(
                    "Could not find any Unreal Engine 5 installations on this system."
                )
                return None

            # Sort the versions (e.g., UE_5.4 > UE_5.3) and grab the newest one
            latest_version = sorted(ue_installs.keys(), reverse=True)[0]
            latest_install_path = Path(ue_installs[latest_version])

            # Construct the path to the executable
            editor_exe = (
                latest_install_path
                / "Engine"
                / "Binaries"
                / "Win64"
                / "UnrealEditor.exe"
            )

            if editor_exe.exists():
                logger.info(
                    f"Auto-detected Unreal Editor ({latest_version}): {editor_exe}"
                )
                return str(editor_exe)
            else:
                logger.error(f"Executable missing at expected location: {editor_exe}")
                return None

        except Exception as e:
            logger.error(f"Failed to parse Unreal manifest: {e}")
            return None
