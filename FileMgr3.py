import sys
import os
import shutil
import subprocess
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QLabel, QStyle, QDialog, QTreeView,
    QListWidget, QListWidgetItem, QPushButton, QInputDialog, QComboBox,
    QDialogButtonBox, QAbstractItemView, QMessageBox, QStackedWidget,
    QHeaderView
)
from PyQt6.QtGui import (
    QAction, QActionGroup, QUndoStack, QUndoCommand, QStandardItemModel,
    QStandardItem, QDrag, QIcon, QFileSystemModel
)
from PyQt6.QtCore import Qt, QSize, QMimeData, QDir, pyqtSignal, QThread, QObject, QUrl, QSettings

# --- Application Constants ---
APP_AUTHOR = "Mark Stout"
APP_NAMESHORT = "File Manager Vibe"

# --- Background Worker for Image Loading ---
class ImageLoader(QObject):
    """Worker object that loads images in a separate thread."""
    image_loaded = pyqtSignal(str, QIcon) # Signal to emit when an image is ready
    finished = pyqtSignal()

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
        self._is_running = True

    def run(self):
        """Load images from the specified path."""
        if os.path.exists(self.path):
            for file_name in os.listdir(self.path):
                if not self._is_running:
                    break
                if any(file_name.lower().endswith(ext) for ext in self.image_extensions):
                    full_path = os.path.join(self.path, file_name)
                    icon = QIcon(full_path)
                    if not icon.isNull():
                        self.image_loaded.emit(file_name, icon)
        self.finished.emit()

    def stop(self):
        self._is_running = False

# --- Custom Dialogs (Unchanged, collapsed for brevity) ---
class DragTextStandardItemModel(QStandardItemModel):
    def mimeData(self, indexes):
        mime_data = QMimeData()
        texts = [self.itemFromIndex(index).text() for index in indexes if self.itemFromIndex(index) and not self.itemFromIndex(index).hasChildren()]
        if texts: mime_data.setText(texts[0])
        return mime_data
class DropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
    def dragEnterEvent(self, event):
        if event.source() is not self and event.mimeData().hasText(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)
    def dragMoveEvent(self, event):
        if event.source() is not self and event.mimeData().hasText(): event.acceptProposedAction()
        else: super().dragMoveEvent(event)
    def dropEvent(self, event):
        if event.source() is not self and event.mimeData().hasText():
            field_name = event.mimeData().text()
            if not self.findItems(field_name, Qt.MatchFlag.MatchExactly): self.addItem(field_name)
            event.acceptProposedAction()
        else: super().dropEvent(event)
class FieldsDialog(QDialog):
    def __init__(self, saved_profiles=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Field Profiles")
        self.setMinimumSize(1000, 700)
        self.saved_profiles = saved_profiles if saved_profiles is not None else {}
        self.last_selected_profile = ""
        main_layout = QVBoxLayout(self)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        available_widget = QWidget()
        available_layout = QVBoxLayout(available_widget)
        available_layout.addWidget(QLabel("<b>Available Fields</b>"))
        self.available_tree = QTreeView()
        self.available_tree.setDragEnabled(True)
        self.available_tree.setHeaderHidden(True)
        available_layout.addWidget(self.available_tree)
        self.populate_available_fields()
        right_container_widget = QWidget()
        right_container_layout = QVBoxLayout(right_container_widget)
        right_container_layout.setContentsMargins(0, 0, 0, 0)
        right_splitter = QSplitter(Qt.Orientation.Horizontal)
        display_widget = QWidget()
        display_layout = QVBoxLayout(display_widget)
        display_layout.addWidget(QLabel("<b>Display</b> (Columns in file pane)"))
        self.display_list = DropListWidget()
        display_layout.addWidget(self.display_list)
        self.delete_display_button = QPushButton("Delete")
        display_layout.addWidget(self.delete_display_button, 0, Qt.AlignmentFlag.AlignRight)
        properties_widget = QWidget()
        properties_layout = QVBoxLayout(properties_widget)
        properties_layout.addWidget(QLabel("<b>Properties</b> (Fields in details pane)"))
        self.properties_list = DropListWidget()
        properties_layout.addWidget(self.properties_list)
        self.delete_properties_button = QPushButton("Delete")
        properties_layout.addWidget(self.delete_properties_button, 0, Qt.AlignmentFlag.AlignRight)
        right_splitter.addWidget(display_widget)
        right_splitter.addWidget(properties_widget)
        profile_layout = QHBoxLayout()
        profile_layout.setContentsMargins(0, 10, 0, 5)
        self.profile_label = QLabel("Profile:")
        self.profile_combo = QComboBox()
        profile_layout.addStretch()
        profile_layout.addWidget(self.profile_label)
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addStretch()
        right_container_layout.addWidget(right_splitter)
        right_container_layout.addLayout(profile_layout)
        main_splitter.addWidget(available_widget)
        main_splitter.addWidget(right_container_widget)
        main_splitter.setSizes([300, 700])
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(main_splitter)
        main_layout.addWidget(self.button_box)
        self.delete_display_button.clicked.connect(self._delete_display_item)
        self.delete_properties_button.clicked.connect(self._delete_properties_item)
        self.display_list.itemSelectionChanged.connect(self._update_delete_button_states)
        self.properties_list.itemSelectionChanged.connect(self._update_delete_button_states)
        self.profile_combo.activated.connect(self._handle_profile_activation)
        self.setup_profiles()
        self._load_profile(self.profile_combo.currentText())
        self._update_delete_button_states()
    def _delete_display_item(self):
        item = self.display_list.currentItem()
        if item: self.display_list.takeItem(self.display_list.row(item))
    def _delete_properties_item(self):
        item = self.properties_list.currentItem()
        if item: self.properties_list.takeItem(self.properties_list.row(item))
    def _update_delete_button_states(self):
        self.delete_display_button.setEnabled(bool(self.display_list.selectedItems()))
        self.delete_properties_button.setEnabled(bool(self.properties_list.selectedItems()))
    def setup_profiles(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Default Files")
        self.profile_combo.addItems(sorted(self.saved_profiles.keys()))
        self.profile_combo.insertSeparator(self.profile_combo.count())
        self.profile_combo.addItem("Create New...")
        self.profile_combo.blockSignals(False)
    def _handle_profile_activation(self, index):
        self._save_current_profile_state()
        selected_text = self.profile_combo.itemText(index)
        if selected_text == "Create New...":
            new_profile_name = self._create_new_profile_from_dialog()
            if new_profile_name:
                self.setup_profiles()
                self.profile_combo.setCurrentText(new_profile_name)
                self._load_profile(new_profile_name)
                self.last_selected_profile = new_profile_name
            else:
                self.profile_combo.setCurrentText(self.last_selected_profile)
        else:
            self.last_selected_profile = selected_text
            self._load_profile(selected_text)
    def _load_profile(self, profile_name):
        if not profile_name or profile_name == "Create New...": return
        self.display_list.clear()
        self.properties_list.clear()
        if profile_name == "Default Files":
            default_fields = ["Name", "Size", "Type", "Date modified"]
            self.display_list.addItems(default_fields)
            self.properties_list.addItems(default_fields + ["Date created"])
        else:
            profile_data = self.saved_profiles.get(profile_name, {})
            self.display_list.addItems(profile_data.get("display", []))
            self.properties_list.addItems(profile_data.get("properties", []))
        self.last_selected_profile = profile_name
    def _create_new_profile_from_dialog(self):
        profile_name, ok = QInputDialog.getText(self, "Create New Profile", "Enter profile name:")
        if ok and profile_name:
            if profile_name in self.saved_profiles or profile_name in ["Default Files", "Create New..."]:
                QMessageBox.warning(self, "Profile Exists", f"A profile named '{profile_name}' already exists.")
                return None
            self.saved_profiles[profile_name] = {"display": [], "properties": []}
            return profile_name
        return None
    def _save_current_profile_state(self):
        current_profile_name = self.last_selected_profile
        if current_profile_name and current_profile_name not in ["Default Files", "Create New..."]:
            display_items = [self.display_list.item(i).text() for i in range(self.display_list.count())]
            properties_items = [self.properties_list.item(i).text() for i in range(self.properties_list.count())]
            self.saved_profiles[current_profile_name] = { "display": display_items, "properties": properties_items }
    def get_profiles_for_saving(self):
        self._save_current_profile_state()
        return self.saved_profiles
    def populate_available_fields(self):
        model = DragTextStandardItemModel()
        root_node = model.invisibleRootItem()
        def create_category_with_fields(category_name, fields):
            category_item = QStandardItem(category_name)
            category_item.setEditable(False); category_item.setDragEnabled(False)
            root_node.appendRow(category_item)
            for field in fields:
                field_item = QStandardItem(field)
                field_item.setEditable(False); field_item.setDragEnabled(True); field_item.setDropEnabled(False)
                category_item.appendRow(field_item)
        create_category_with_fields("General", ["Name", "Size", "Type", "Date modified", "Date created", "Date accessed", "Attributes"])
        create_category_with_fields("Images", ["Dimensions", "Date taken", "Camera model", "Resolution", "ISO speed", "F-stop"])
        create_category_with_fields("Audio/Music", ["Title", "Artist", "Album", "Genre", "Year", "Length", "Bit rate"])
        create_category_with_fields("Video", ["Frame width", "Frame height", "Frame rate", "Length", "Data rate", "Director"])
        self.available_tree.setModel(model)
        self.available_tree.expandAll()

# --- Focus-aware and Drag-and-Drop Enabled Widgets ---
class DnDTreeView(QTreeView):
    focus_gained = pyqtSignal()
    def __init__(self, parent_pane, parent=None):
        super().__init__(parent); self.parent_pane = parent_pane; self.setDragEnabled(True); self.setAcceptDrops(True)
        self.setDropIndicatorShown(True); self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    def focusInEvent(self, event): self.focus_gained.emit(); super().focusInEvent(event)
    def startDrag(self, supportedActions):
        indexes = self.selectedIndexes()
        if not indexes: return
        mime_data = QMimeData(); urls = [self.model().filePath(index) for index in indexes if index.column() == 0]
        mime_data.setUrls([QUrl.fromLocalFile(path) for path in set(urls)])
        drag = QDrag(self); drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            menu = QMenu(self); copy_action = menu.addAction("Copy Here"); move_action = menu.addAction("Move Here")
            menu.addSeparator(); cancel_action = menu.addAction("Cancel")
            selected_action = menu.exec(event.globalPosition().toPoint())
            if selected_action == copy_action: self.parent_pane._perform_file_operation(event.mimeData().urls(), "copy"); event.acceptProposedAction()
            elif selected_action == move_action: self.parent_pane._perform_file_operation(event.mimeData().urls(), "move"); event.acceptProposedAction()
            else: event.ignore()
        else: super().dropEvent(event)

class DnDListWidget(QListWidget):
    focus_gained = pyqtSignal()
    def __init__(self, parent_pane, parent=None):
        super().__init__(parent); self.parent_pane = parent_pane; self.setDragEnabled(True); self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    def focusInEvent(self, event): self.focus_gained.emit(); super().focusInEvent(event)
    def startDrag(self, supportedActions):
        items = self.selectedItems();
        if not items: return
        mime_data = QMimeData(); urls = [item.data(Qt.ItemDataRole.UserRole) for item in items if item.data(Qt.ItemDataRole.UserRole)]
        mime_data.setUrls([QUrl.fromLocalFile(path) for path in urls]); drag = QDrag(self); drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            menu = QMenu(self); copy_action = menu.addAction("Copy Here"); move_action = menu.addAction("Move Here")
            menu.addSeparator(); cancel_action = menu.addAction("Cancel")
            selected_action = menu.exec(event.globalPosition().toPoint())
            if selected_action == copy_action: self.parent_pane._perform_file_operation(event.mimeData().urls(), "copy"); event.acceptProposedAction()
            elif selected_action == move_action: self.parent_pane._perform_file_operation(event.mimeData().urls(), "move"); event.acceptProposedAction()
            else: event.ignore()
        else: super().dropEvent(event)

# --- Functional File Pane ---
class FilePane(QWidget):
    focus_gained = pyqtSignal(QWidget)
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.active_profile_name = "Default Files"
        self.setMinimumSize(200, 200)
        self.path = "" # Path will be set by navigate_to
        self.image_loader_thread = None
        self.image_loader = None
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 2, 5, 2)
        self.folder_label = QLabel()
        self.profile_combo = QComboBox()
        self.update_profiles()
        header_layout.addWidget(self.folder_label)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Profile:"))
        header_layout.addWidget(self.profile_combo)
        
        self.stacked_widget = QStackedWidget()
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.Files | QDir.Filter.AllDirs)

        self.tree_view = DnDTreeView(parent_pane=self)
        self.tree_view.setModel(self.model)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.image_view = DnDListWidget(parent_pane=self)
        self.image_view.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_view.setIconSize(QSize(128, 128))
        self.image_view.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_view.setGridSize(QSize(150, 150))
        
        self.stacked_widget.addWidget(self.tree_view)
        self.stacked_widget.addWidget(self.image_view)
        self.main_layout.addWidget(header_widget)
        self.main_layout.addWidget(self.stacked_widget)
        
        self.tree_view.focus_gained.connect(lambda: self.focus_gained.emit(self))
        self.image_view.focus_gained.connect(lambda: self.focus_gained.emit(self))
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)

    def navigate_to(self, path):
        self.path = path
        self.folder_label.setText(os.path.basename(path) if os.path.basename(path) else path)
        self.model.setRootPath(path)
        self.tree_view.setRootIndex(self.model.index(path))
        self._populate_image_view()

    def update_profiles(self):
        self.profile_combo.blockSignals(True); self.profile_combo.clear(); self.profile_combo.addItem("Default Files")
        self.profile_combo.addItems(sorted(self.main_window.field_profiles.keys())); self.profile_combo.blockSignals(False)
    
    def _on_profile_changed(self, profile_name):
        if not profile_name: return
        self.active_profile_name = profile_name
        if self.stacked_widget.currentWidget() == self.tree_view and not self.tree_view.isHeaderHidden():
            self.apply_view_mode("detailed")
            
    def _populate_image_view(self):
        # Stop previous loader if it's running
        if self.image_loader and self.image_loader_thread.isRunning():
            self.image_loader.stop()
            self.image_loader_thread.quit()
            self.image_loader_thread.wait()

        self.image_view.clear()
        self.image_loader_thread = QThread()
        self.image_loader = ImageLoader(self.path)
        self.image_loader.moveToThread(self.image_loader_thread)
        self.image_loader.image_loaded.connect(self._add_image_item)
        self.image_loader_thread.started.connect(self.image_loader.run)
        self.image_loader.finished.connect(self.image_loader_thread.quit)
        # The thread and worker will be cleaned up by Python's garbage collector
        self.image_loader_thread.start()

    def _add_image_item(self, name, icon):
        """Slot to add an item to the image view from the background thread."""
        item = QListWidgetItem(icon, name)
        full_path = os.path.join(self.path, name)
        item.setData(Qt.ItemDataRole.UserRole, full_path)
        self.image_view.addItem(item)
    
    def _perform_file_operation(self, urls, operation_type):
        for url in urls:
            source_path = url.toLocalFile()
            if source_path and os.path.exists(source_path):
                try:
                    if operation_type == "copy": shutil.copy(source_path, self.path)
                    elif operation_type == "move": shutil.move(source_path, self.path)
                except Exception as e:
                    QMessageBox.critical(self, f"{operation_type.capitalize()} Error", f"Could not {operation_type} item:\n{e}")
    
    def apply_view_mode(self, mode):
        header = self.tree_view.header()
        if mode == "narrow":
            self.stacked_widget.setCurrentWidget(self.tree_view); self.tree_view.setHeaderHidden(True)
            for i in range(1, self.model.columnCount()): header.hideSection(i)
        
        elif mode == "detailed":
            self.stacked_widget.setCurrentWidget(self.tree_view); self.tree_view.setHeaderHidden(False)
            if self.active_profile_name == "Default Files":
                display_fields = ["Name", "Size", "Type", "Date Modified"]
            else:
                profile_data = self.main_window.field_profiles.get(self.active_profile_name, {})
                display_fields = profile_data.get("display", [])
            
            if not display_fields: display_fields = ["Name"]

            column_map = {"Name": 0, "Size": 1, "Type": 2, "Date Modified": 3}
            for i in range(self.model.columnCount()): header.hideSection(i)
            for field in display_fields:
                if field in column_map: header.showSection(column_map[field])

        elif mode == "images":
            self.stacked_widget.setCurrentWidget(self.image_view)

# --- Other Panes and Main Window ---
class PropertiesPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setMinimumSize(150, 200); self.setMaximumWidth(400)
        layout = QVBoxLayout(self); label = QLabel("Properties Pane"); label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("border: 1px solid #555; background-color: #2A2A2A;"); layout.addWidget(label)
class BookmarkPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setMinimumSize(150, 200); self.setMaximumWidth(350)
        layout = QVBoxLayout(self); label = QLabel("Bookmarks"); label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("border: 1px solid #555; background-color: #252525;"); layout.addWidget(label)
class FileManagerVibeAgain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAMESHORT)
        self.undo_stack = QUndoStack(self); self.field_profiles = {}; self.current_layout_widget = None
        self.panes = []; self.active_pane = None; self.current_view_mode = "detailed"; self.current_layout_id = 1
        self.layout_actions = {}
        self._create_menus(); self._setup_main_ui(); self._load_settings()
    def closeEvent(self, event):
        self._save_settings(); event.accept()
    def _save_settings(self):
        settings = QSettings(APP_AUTHOR, APP_NAMESHORT)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("layout_id", self.current_layout_id)
        settings.setValue("pane_paths", [pane.path for pane in self.panes])
        settings.setValue("bookmarks", {}) # Placeholder for bookmarks
    def _load_settings(self):
        settings = QSettings(APP_AUTHOR, APP_NAMESHORT)
        geometry = settings.value("geometry")
        if geometry: self.restoreGeometry(geometry)
        else: self.setGeometry(0, 0, 1400, 800); self.center_window()
        layout_id = settings.value("layout_id", 1, type=int)
        pane_paths = settings.value("pane_paths", [], type=list)
        self.set_layout(layout_id, initial_paths=pane_paths) # Creates panes and navigates them
    def center_window(self):
        screen_geometry = self.screen().availableGeometry(); center_point = screen_geometry.center()
        self.move(center_point.x() - self.width() // 2, center_point.y() - self.height() // 2)
    def _setup_main_ui(self):
        self.main_container = QWidget()
        self.container_layout = QVBoxLayout(self.main_container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.main_container)
        main_splitter.addWidget(BookmarkPane())
        main_splitter.setSizes([1100, 300]) 
        self.setCentralWidget(main_splitter)
    def _create_menus(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        edit_menu = menu_bar.addMenu("&Edit")
        undo_action = self.undo_stack.createUndoAction(self, "Undo"); redo_action = self.undo_stack.createRedoAction(self, "Redo")
        undo_action.setShortcut("Ctrl+Z"); redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(undo_action); edit_menu.addAction(redo_action)
        view_menu = menu_bar.addMenu("&View")
        self.view_mode_group = QActionGroup(self)
        self.view_mode_group.setExclusive(True)
        actions = {"Narrow": "narrow", "Detailed": "detailed", "Images": "images"}
        for text, mode in actions.items():
            action = QAction(text, self, checkable=True)
            if mode == "detailed": action.setChecked(True)
            action.triggered.connect(lambda checked, m=mode: self._set_view_mode(m))
            self.view_mode_group.addAction(action); view_menu.addAction(action)
        view_menu.addSeparator()
        fields_action = QAction("Field Profiles...", self)
        fields_action.triggered.connect(self._open_fields_dialog)
        view_menu.addAction(fields_action)
        view_menu.addSeparator()
        self.layout_action_group = QActionGroup(self)
        self.layout_action_group.setExclusive(True)
        layouts = {"1 Vertical Pane": 1, "2 Vertical Panes": 2, "3 Vertical Panes": 3, "2 Vertical with Properties Pane": 21, "3 Panes (1 Left, 2 Right)": 31, "3 Panes (2 Left, 1 Right)": 32, "4 Vertical Panes": 41, "4 Panes (2x2 Grid)": 42}
        for text, layout_id in layouts.items():
            action = QAction(text, self, checkable=True)
            action.triggered.connect(lambda checked, lid=layout_id: self.change_layout(lid))
            self.layout_action_group.addAction(action)
            self.layout_actions[layout_id] = action
            view_menu.addAction(action)
    def _set_active_pane(self, pane):
        if self.active_pane: self.active_pane.setStyleSheet("")
        self.active_pane = pane
        if self.active_pane: self.active_pane.setStyleSheet("border: 2px solid #4a8dff;")
    def _set_view_mode(self, mode):
        self.current_view_mode = mode
        if self.active_pane:
            self.active_pane.apply_view_mode(mode)
            for action in self.view_mode_group.actions():
                if action.text().lower() == mode: action.setChecked(True)
    def _open_fields_dialog(self):
        dialog = FieldsDialog(self.field_profiles.copy(), self)
        if dialog.exec():
            self.field_profiles = dialog.get_profiles_for_saving()
            for pane in self.panes: pane.update_profiles()
    def change_layout(self, layout_id):
        current_geometry = self.geometry()
        self.set_layout(layout_id)
        self.setGeometry(current_geometry)
    def set_layout(self, layout_id, initial_paths=None):
        self.current_layout_id = layout_id
        if self.layout_actions.get(layout_id): self.layout_actions[layout_id].setChecked(True)
        if self.current_layout_widget: self.current_layout_widget.deleteLater()
        self.panes.clear(); self.active_pane = None
        
        def create_pane():
            pane = FilePane(main_window=self)
            self.panes.append(pane)
            pane.focus_gained.connect(self._set_active_pane)
            return pane
        if layout_id == 1: self.current_layout_widget = create_pane()
        elif layout_id == 2: splitter = QSplitter(Qt.Orientation.Horizontal); splitter.addWidget(create_pane()); splitter.addWidget(create_pane()); self.current_layout_widget = splitter
        elif layout_id == 3: splitter = QSplitter(Qt.Orientation.Horizontal); splitter.addWidget(create_pane()); splitter.addWidget(create_pane()); splitter.addWidget(create_pane()); self.current_layout_widget = splitter
        elif layout_id == 21: splitter = QSplitter(Qt.Orientation.Horizontal); splitter.addWidget(create_pane()); splitter.addWidget(PropertiesPane()); splitter.addWidget(create_pane()); splitter.setSizes([500, 300, 500]); self.current_layout_widget = splitter
        elif layout_id == 31: main_splitter, right_splitter = QSplitter(Qt.Orientation.Horizontal), QSplitter(Qt.Orientation.Vertical); right_splitter.addWidget(create_pane()); right_splitter.addWidget(create_pane()); main_splitter.addWidget(create_pane()); main_splitter.addWidget(right_splitter); self.current_layout_widget = main_splitter
        elif layout_id == 32: main_splitter, left_splitter = QSplitter(Qt.Orientation.Horizontal), QSplitter(Qt.Orientation.Vertical); left_splitter.addWidget(create_pane()); left_splitter.addWidget(create_pane()); main_splitter.addWidget(left_splitter); main_splitter.addWidget(create_pane()); self.current_layout_widget = main_splitter
        elif layout_id == 41: splitter = QSplitter(Qt.Orientation.Horizontal); splitter.addWidget(create_pane()); splitter.addWidget(create_pane()); splitter.addWidget(create_pane()); splitter.addWidget(create_pane()); self.current_layout_widget = splitter
        elif layout_id == 42: main_splitter, left_splitter, right_splitter = QSplitter(Qt.Orientation.Horizontal), QSplitter(Qt.Orientation.Vertical), QSplitter(Qt.Orientation.Vertical); left_splitter.addWidget(create_pane()); left_splitter.addWidget(create_pane()); right_splitter.addWidget(create_pane()); right_splitter.addWidget(create_pane()); main_splitter.addWidget(left_splitter); main_splitter.addWidget(right_splitter); self.current_layout_widget = main_splitter
        
        self.main_container.layout().addWidget(self.current_layout_widget)
        
        paths = initial_paths if initial_paths else []
        for i, pane in enumerate(self.panes):
            path = paths[i] if i < len(paths) and os.path.exists(paths[i]) else "C:/"
            pane.navigate_to(path)

        if self.panes: self._set_active_pane(self.panes[0])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dark_stylesheet = """
        QWidget { color: #eff0f1; background-color: #31363b; selection-background-color: #4a8dff; selection-color: #eff0f1; }
        QMainWindow { background-color: #232629; }
        QMenuBar { background-color: #31363b; } QMenuBar::item:selected { background-color: #4a8dff; }
        QMenu { background-color: #31363b; border: 1px solid #555; } QMenu::item:selected { background-color: #4a8dff; }
        QSplitter::handle { background-color: #555; } QSplitter::handle:hover { background-color: #4a8dff; }
        QSplitter::handle:horizontal { width: 4px; } QSplitter::handle:vertical { height: 4px; }
        QDialog { background-color: #31363b; }
        QPushButton { background-color: #4a4a4a; padding: 4px 8px; border: 1px solid #555; } QPushButton:hover { background-color: #5a5a5a; }
        QPushButton:flat { border: none; background-color: transparent; }
        QTreeView, QListWidget { border: 1px solid #555; }
        QHeaderView::section { background-color: #3a3a3a; padding: 4px; border: 1px solid #2b2b2b; }
        QComboBox { background-color: #4a4a4a; padding: 2px; } QComboBox::drop-down { border: none; }
    """
    app.setStyleSheet(dark_stylesheet)
    window = FileManagerVibeAgain()
    window.show()
    sys.exit(app.exec())
