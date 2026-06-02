"""
Maya to UE5 Environment Exporter — UI (PySide6)
------------------------------------------------
Drop this file in the same folder as your other scripts.

Run from Maya's Script Editor:
    import exporter_ui
    exporter_ui.launch()

Or standalone (for design/testing without Maya):
    python exporter_ui.py
"""

import importlib
import logging
import sys
from pathlib import Path

from PySide6 import QtGui
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ── Constants (inline fallback if Constants.py not on path) ──────────────────

try:
    import Constants as cons

    importlib.reload(cons)
    TOOL_VERSION = cons.TOOL_VERSION
    FILENAME = cons.FILENAME
    TEMP_PRO_PATH = cons.TEMP_PRO_PATH
except ImportError:
    TOOL_VERSION = "1.0"
    FILENAME = "Unnamed_Enviroment.usd"
    TEMP_PRO_PATH = ""

# ── Stylesheet ────────────────────────────────────────────────────────────────

STYLE = """
QDialog, QWidget {
    background-color: #18181c;
    color: #ccc8be;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}

/* ─ Labels ─ */
QLabel#title {
    color: #e8e0cc;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 1px;
}
QLabel#subtitle {
    color: #3e3c38;
    font-size: 9px;
    letter-spacing: 4px;
}
QLabel#version {
    color: #4a4840;
    font-size: 10px;
    letter-spacing: 2px;
}
QLabel#section {
    color: #5a5550;
    font-size: 9px;
    letter-spacing: 3px;
}
QLabel#status_ok  { color: #7a9a6a; font-size: 10px; }
QLabel#status_err { color: #9a5a5a; font-size: 10px; }

/* ─ Inputs ─ */
QLineEdit {
    background-color: #101014;
    border: 1px solid #28262a;
    border-radius: 3px;
    padding: 7px 10px;
    color: #c8c4b8;
    selection-background-color: #c8a96e;
    selection-color: #18181c;
}
QLineEdit:focus { border-color: #c8a96e; }
QLineEdit:hover { border-color: #3a3838; }
QLineEdit[readOnly="true"] {
    color: #5a5850;
    background-color: #0e0e12;
}

/* ─ Browse buttons ─ */
QPushButton#browse {
    background-color: #1c1c22;
    border: 1px solid #28262a;
    border-radius: 3px;
    color: #6a6860;
    padding: 7px 16px;
    min-width: 64px;
}
QPushButton#browse:hover  { background-color: #242430; color: #c8a96e; border-color: #c8a96e; }
QPushButton#browse:pressed { background-color: #101018; }

/* ─ Clear button ─ */
QPushButton#clear {
    background-color: transparent;
    border: 1px solid #28262a;
    border-radius: 3px;
    color: #4a4840;
    padding: 4px 12px;
    font-size: 10px;
    letter-spacing: 1px;
}
QPushButton#clear:hover  { color: #9a7050; border-color: #5a4030; }
QPushButton#clear:pressed { background-color: #1a1210; }

/* ─ Publish ─ */
QPushButton#publish {
    background-color: #c8a96e;
    border: none;
    border-radius: 3px;
    color: #18181c;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 14px 0;
    margin-top: 4px;
}
QPushButton#publish:hover    { background-color: #d4b87a; }
QPushButton#publish:pressed  { background-color: #b89858; }
QPushButton#publish:disabled {
    background-color: #252525;
    color: #3a3a3a;
}

/* ─ Divider ─ */
QFrame#divider {
    background-color: #242228;
    border: none;
    max-height: 1px;
    min-height: 1px;
}

/* ─ Log ─ */
QTextEdit#log {
    background-color: #0c0c10;
    border: 1px solid #242228;
    border-radius: 3px;
    color: #5a6a4a;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    padding: 8px;
}

/* ─ Checkbox ─ */
QCheckBox {
    color: #6a6860;
    spacing: 8px;
    font-size: 11px;
}
QCheckBox::indicator {
    width: 13px; height: 13px;
    border: 1px solid #2e2c2a;
    border-radius: 2px;
    background: #101014;
}
QCheckBox::indicator:checked {
    background-color: #c8a96e;
    border-color: #c8a96e;
}
QCheckBox:hover { color: #c8a96e; }

/* ─ Scrollbar ─ */
QScrollBar:vertical {
    background: #0c0c10; width: 5px; border-radius: 2px;
}
QScrollBar::handle:vertical {
    background: #2e2c28; border-radius: 2px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #c8a96e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


# ── Coloured log handler ──────────────────────────────────────────────────────


class QTextEditHandler(logging.Handler):
    """Routes Python logger records into a QTextEdit with colour per level."""

    COLOURS = {
        logging.DEBUG: "#4a5a7a",
        logging.INFO: "#6a8a5a",
        logging.WARNING: "#c8a96e",
        logging.ERROR: "#9a5050",
        logging.CRITICAL: "#cc3030",
    }

    def __init__(self, widget: QTextEdit):
        super().__init__()
        self._widget = widget

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            color = self.COLOURS.get(record.levelno, "#6a8a5a")
            self._widget.append(f'<span style="color:{color};">{msg}</span>')
            sb = self._widget.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception:
            pass


# ── Main dialog ───────────────────────────────────────────────────────────────


class EnvironmentExporterUI(QDialog):
    """
    Maya → UE5 Environment Exporter
    Single-file PySide6 UI.  Works both inside Maya and standalone.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Enviroment Exporter")
        self.setMinimumWidth(500)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint
        )

        self._controller = None  # set lazily when Maya is available
        self._log_handler = None
        self._maya_mode = self._detect_maya()

        self._build_ui()
        self._attach_logger()

        if self._maya_mode:
            self._init_controller()

    # ── Maya detection ────────────────────────────────────────────────────────

    @staticmethod
    def _detect_maya() -> bool:
        try:
            import maya.cmds  # noqa

            return True
        except ImportError:
            return False

    def _init_controller(self):
        try:
            import maya_unreal_enviroments as mue

            importlib.reload(mue)
            self._controller = mue.EnvironmentExporterController()
        except Exception as e:
            self._log_direct(f"WARNING: Could not load pipeline modules: {e}")

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(0)

        # Header
        root.addLayout(self._header())
        root.addSpacing(18)
        root.addWidget(self._divider())
        root.addSpacing(18)

        # ── Export folder ──
        root.addLayout(
            self._field_row(
                "USD EXPORT FOLDER",
                "le_export",
                placeholder="C:/Exports/MyEnvironment",
                browse_slot=self._browse_export,
            )
        )
        root.addSpacing(12)

        # ── USD filename ──
        root.addLayout(
            self._field_row(
                "USD FILENAME",
                "le_filename",
                placeholder=FILENAME,
                default=FILENAME,
            )
        )
        root.addSpacing(12)

        # ── Unreal project ──
        root.addLayout(
            self._field_row(
                "UNREAL PROJECT",
                "le_project",
                placeholder="D:/Projects/.../MyProject.uproject",
                default=TEMP_PRO_PATH,
                browse_slot=self._browse_project,
            )
        )
        root.addSpacing(12)

        # ── NEW: UE destination folder ──
        root.addLayout(
            self._field_row(
                "UE5 ASSET DESTINATION",
                "le_ue_destination",
                placeholder="/Game/Environments/ModularKit",
                default="/Game",
                browse_slot=self._browse_ue_destination,  # <-- Map the slot here
            )
        )
        root.addSpacing(18)

        root.addWidget(self._divider())
        root.addSpacing(14)

        # ── NEW: Center meshes checkbox ──
        self.cb_centered = QCheckBox("Center meshes  —  move pivot to world origin")
        self.cb_centered.setChecked(False)
        self.cb_centered.setToolTip(
            "Moves each mesh's pivot to the world origin before export.\n"
            "Useful for modular kit pieces that need a consistent pivot."
        )
        root.addWidget(self.cb_centered)
        root.addSpacing(18)

        # ── Publish button ──
        self.btn_publish = QPushButton("PUBLISH TO UNREAL")
        self.btn_publish.setObjectName("publish")
        self.btn_publish.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        self.btn_publish.clicked.connect(self._on_publish)
        root.addWidget(self.btn_publish)
        root.addSpacing(20)

        # ── Log ──
        lbl_log = QLabel("OUTPUT LOG")
        lbl_log.setObjectName("section")
        root.addWidget(lbl_log)
        root.addSpacing(6)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("log")
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        self.log_output.setMaximumHeight(220)
        root.addWidget(self.log_output)
        root.addSpacing(6)

        # Clear log row
        btn_clear = QPushButton("CLEAR LOG")
        btn_clear.setObjectName("clear")
        btn_clear.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        btn_clear.clicked.connect(self.log_output.clear)
        clear_row = QHBoxLayout()
        clear_row.addStretch()
        clear_row.addWidget(btn_clear)
        root.addLayout(clear_row)

        # Status bar (bottom)
        root.addSpacing(10)
        root.addWidget(self._divider())
        root.addSpacing(6)
        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setObjectName("section")
        root.addWidget(self.lbl_status)

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _header(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(3)

        title = QLabel("MAYA  →  UE5")
        title.setObjectName("title")

        sub = QLabel("ENVIRONMENT EXPORTER")
        sub.setObjectName("subtitle")

        ver = QLabel(f"v{TOOL_VERSION}")
        ver.setObjectName("version")
        ver.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch()
        top.addWidget(ver)

        layout.addLayout(top)
        layout.addWidget(sub)
        return layout

    def _field_row(
        self,
        label_text: str,
        attr: str,
        placeholder: str = "",
        default: str = "",
        browse_slot=None,
    ) -> QVBoxLayout:
        """Creates a labelled input row and stores the QLineEdit as self.<attr>."""
        col = QVBoxLayout()
        col.setSpacing(5)

        lbl = QLabel(label_text)
        lbl.setObjectName("section")
        col.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(6)

        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        if default:
            le.setText(default)
        setattr(self, attr, le)
        row.addWidget(le)

        if browse_slot:
            btn = QPushButton("Browse")
            btn.setObjectName("browse")
            btn.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(browse_slot)
            row.addWidget(btn)

        col.addLayout(row)
        return col

    @staticmethod
    def _divider() -> QFrame:
        f = QFrame()
        f.setObjectName("divider")
        f.setFrameShape(QFrame.Shape.HLine)
        return f

    # ── Logger ────────────────────────────────────────────────────────────────

    def _attach_logger(self):
        try:
            from logger import get_logger

            log = get_logger()
        except ImportError:
            log = logging.getLogger("EnvironmentExporter")

        self._log_handler = QTextEditHandler(self.log_output)
        self._log_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        log.addHandler(self._log_handler)
        self._logger = log

    def _detach_logger(self):
        if self._log_handler and self._logger:
            self._logger.removeHandler(self._log_handler)
            self._log_handler = None

    def _log_direct(self, msg: str):
        """Write a plain message to the log widget without going through the logger."""
        self.log_output.append(f'<span style="color:#5a5a6a;">{msg}</span>')

    # ── Browse slots ──────────────────────────────────────────────────────────

    def _browse_export(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Export Folder", str(Path.home())
        )
        if folder:
            self.le_export.setText(folder)

    def _browse_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Unreal Project",
            str(Path(TEMP_PRO_PATH).parent) if TEMP_PRO_PATH else "D:/",
            "Unreal Project (*.uproject)",
        )
        if path:
            self.le_project.setText(path)

    def _browse_ue_destination(self):
        # Look for the selected Unreal Project to default the browser to its Content folder
        project_path = self.le_project.text().strip()
        start_dir = str(Path.home())

        if project_path and Path(project_path).exists():
            content_dir = Path(project_path).parent / "Content"
            if content_dir.exists():
                start_dir = str(content_dir)

        folder = QFileDialog.getExistingDirectory(
            self, "Select UE5 Destination (Inside Content Folder)", start_dir
        )

        if folder:
            folder_path = Path(folder)
            # Parse the physical folder path and translate it into a virtual /Game/ path
            if "Content" in folder_path.parts:
                idx = folder_path.parts.index("Content")
                sub_parts = folder_path.parts[idx + 1 :]
                ue_path = "/Game/" + "/".join(sub_parts) if sub_parts else "/Game"
                self.le_ue_destination.setText(ue_path)
            else:
                QMessageBox.warning(
                    self,
                    "Path Warning",
                    "The folder you selected is not inside a 'Content' directory.\n\nThe absolute path has been inserted, but this will likely fail during the Unreal Engine import.",
                )
                self.le_ue_destination.setText(str(folder_path).replace("\\", "/"))

    # ── Publish ───────────────────────────────────────────────────────────────

    def _on_publish(self):
        if not self._maya_mode:
            QMessageBox.information(
                self,
                "Standalone Mode",
                "UI is running outside Maya.\nConnect to Maya to publish.",
            )
            return

        if self._controller is None:
            self._init_controller()
            if self._controller is None:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Pipeline modules failed to load.\nCheck the Output Log.",
                )
                return

        # ── Gather & validate inputs ──
        export_folder = self.le_export.text().strip()
        filename = self.le_filename.text().strip() or FILENAME
        project = self.le_project.text().strip() or TEMP_PRO_PATH
        ue_destination = self.le_ue_destination.text().strip() or "/Game"  # NEW
        centered = self.cb_centered.isChecked()  # NEW

        if not export_folder:
            QMessageBox.warning(self, "Missing Field", "Please set an Export Folder.")
            return

        if not filename.lower().endswith(".usd"):
            filename += ".usd"

        if not Path(project).exists():
            QMessageBox.warning(self, "Project Not Found", f"Cannot find:\n{project}")
            return

        # ── Patch import_materials based on checkbox ──
        first_import = self.cb_first_import.isChecked()
        self._patch_import_materials(first_import)

        # ── Lock UI ──
        self.btn_publish.setEnabled(False)
        self.btn_publish.setText("PUBLISHING...")
        self.lbl_status.setText("Publishing…")
        self.lbl_status.setObjectName("section")
        QApplication.processEvents()

        try:
            result = self._controller.process_selection(
                target_folder=export_folder,
                filename=filename,
                project_path=project,
                centered=centered,  # NEW: wired through
                ue_destination=ue_destination,  # NEW: wired through
            )
            if result:
                self.btn_publish.setText("✓  PUBLISHED")
                self.lbl_status.setText(f"Published → {result}")
                QTimer.singleShot(
                    3000, lambda: self.btn_publish.setText("PUBLISH TO UNREAL")
                )
            else:
                self.btn_publish.setText("PUBLISH TO UNREAL")
                self.lbl_status.setText("Publish failed — see log above.")

        except Exception as exc:
            self._logger.error(f"Publish error: {exc}")
            self.btn_publish.setText("PUBLISH TO UNREAL")
            self.lbl_status.setText("Error — see log.")
        finally:
            self._restore_import_materials()
            self.btn_publish.setEnabled(True)

    # ── import_materials patch / restore ─────────────────────────────────────

    def _patch_import_materials(self, enabled: bool):
        """Temporarily patches UE5Importer._build_import_task to honour the checkbox."""
        try:
            import usd_importer_ue5

            importlib.reload(usd_importer_ue5)
            original = usd_importer_ue5.UE5Importer._build_import_task
            self._original_build = original

            def _patched(inner_self):
                task = original(inner_self)
                if task:
                    task.options.import_materials = enabled
                return task

            usd_importer_ue5.UE5Importer._build_import_task = _patched
        except ImportError:
            self._original_build = None

    def _restore_import_materials(self):
        try:
            if self._original_build is not None:
                import usd_importer_ue5

                usd_importer_ue5.UE5Importer._build_import_task = self._original_build
                self._original_build = None
        except Exception:
            pass

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event: QtGui.QCloseEvent):
        self._detach_logger()
        super().closeEvent(event)


# ── Launch helper (Maya) ──────────────────────────────────────────────────────

_instance: EnvironmentExporterUI | None = None


def launch() -> EnvironmentExporterUI:
    """
    Launch or re-open the exporter window.
    Call from Maya's Script Editor:

        import exporter_ui
        exporter_ui.launch()
    """
    global _instance

    # Resolve Maya main window as parent
    maya_parent = None
    try:
        from maya import OpenMayaUI as omui
        from shiboken6 import wrapInstance

        ptr = omui.MQtUtil.mainWindow()
        maya_parent = wrapInstance(int(ptr), QWidget)
    except Exception:
        pass

    if _instance is not None:
        try:
            _instance.close()
            _instance.deleteLater()
        except Exception:
            pass

    _instance = EnvironmentExporterUI(parent=maya_parent)
    _instance.show()
    _instance.raise_()
    _instance.activateWindow()
    return _instance


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    win = EnvironmentExporterUI()
    win.show()
    sys.exit(app.exec())
