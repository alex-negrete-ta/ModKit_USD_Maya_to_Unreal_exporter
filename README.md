# ModKit_USD_Maya_to_Unreal_exporter
### Onedirectional USD Pipeline exporter for enviroment artists exporting modular kits.
This tool, will grab your maya modular kits selection and automatically export as a single USD file and reimport the meshes as individual SM in Unreal. The goal was to implement asset transfer between Maya and Unreal, and starting to dive into USD as a topic. For these modular kit workflow, I publish a compact single USD package optimized for automated Unreal import.

# Demo Videos:
Click to see the Demo:

[![Watch the project demo](docs/UI_screenshot.png)](https://vimeo.com/1198864885?share=copy&fl=sv&fe=ci)

# Current Features (V.1.0.0):
## Modular Kit Exporter from Maya
* Exports the selection in a single USD file for optimized for automated import.
* Directory selection for Unreal, USD file destination folder, and Output folder.
* Write metadata on artist, time and dump into a JSON sidecar file.
  
# How to install:
## Download and install:
## How to install:

### Method 1: Standard Installation (Recommended for Artists)

**1. Download the Package**
* Click the green **Code** button and select **Download ZIP**.
* Extract the contents of the ZIP file to a location on your computer.

**2. Copy to your Maya Scripts Folder**
* Open your local Maya scripts directory. By default, this is located at:
  * **Windows:** `C:\Users\<YourUsername>\Documents\maya\<maya_version>\scripts`
  * **Mac:** `~/Library/Preferences/Autodesk/maya/<maya_version>/scripts`
  * **Linux:** `~/maya/<maya_version>/scripts`
* Copy the `environment_exporter` folder from the extracted ZIP and paste it directly into your Maya `scripts` folder.
  
**3. Launch the Tool in Maya**
* Open Autodesk Maya.
* Open the **Script Editor** (`Windows > General Editors > Script Editor`).
* Create a new **Python** tab and paste the following execution code:

  ```python
  import enviroment_exporter
  environment_exporter.launch()

### Method 2: Command line installation.

***1. Download the Package**
* Open your terminal and write
  ```
  git clone [https://github.com/alex-negrete-ta/ModKit_USD_Maya_to_Unreal_exporter.git](https://github.com/alex-negrete-ta/ModKit_USD_Maya_to_Unreal_exporter.git)

***2. Install the package into Maya**
* Navigate to the root folder of the tool in your terminal and execute>
  ```
  "C:\Program Files\Autodesk\Maya<version>\bin\mayapy.exe" -m pip install .

**3. Launch the Tool in Maya**
* Open Autodesk Maya.
* Open the **Script Editor** (`Windows > General Editors > Script Editor`).
* Create a new **Python** tab and paste the following execution code:

  ```python
  import enviroment_exporter
  environment_exporter.launch()

# Quick Start:
# File Structure:
# Current Limitations:
# File Reference:
# Development Timeline:
# Requirements:

## Maya:
* Maya 2022+

## Unreal
* USD importer
* Python Editor Script Plugin


