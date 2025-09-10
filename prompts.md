* Use PyQt so we can have drag and drop to another application
* Name it File Manager Vibe Again
* Resizable window
* File, Edit and View menus
* Starts in center of screen
* The option to have 1,2,3, or 4 windows
* Options for layout of the up to 4 windows and a 5th pane for bookmarks.
* For 4 windows : 2 top & bottom on left, 2 top and bottom for right
* For 4 windows, 4 vertical
* For 3 windows, 2 top & bottom left, one vertical on right
* For 3 windows 2 top and bottom right, one vertical on left
* for 3 windows, 3 vertical
* For 2 windows, 2 vertical panes
* also for 2 windows, 2 vertical with a properties pane between them.
* For 1 window, 1 vertical
* The application window must remain constant when changing number or layout of views
* Also under the View menu, Narrow (showing only filename), Detailed (showing filename, date modified and size), and Images (3 tiles per line in pane displaying the image if the file is a displayable image)
===============================================================================
* Undo/Redo
* Edit menu with undo/redo
* Add a menu item, Fields to View menu. Have a dialog box with a panel on left listing all the explorer fields grouped by type (general, image, audio, video).  Have a middle panel “Display” and a right hand one “Properties”  You can drag & drop from left to both middle and right.  Below panel 2 & 3, is a delete button.  Below that center, is a drop down labeled Profile. It is populated with “Default” and “Add New” Add new invokes a dialog box asking for the name of the Profile.
===============================================================================
* for now, hard code the files for each pane to "C:\Users\marks\OneDrive\Pictures" and display those file depending on what view is set.
===============================================================================
* Changing a view should only affect the active pane.
* Show some indicator which is the active pane.
* For Detail view, use the fields in the current Field Profile
===============================================================================
*Note : It created the fields dialog based on previous code.*

Left off here 2025-09-09 17:09:19 472 lines of code
===============================================================================
* Drag and drop between windows
* Drag and Drop to another application like Gmail
===============================================================================
* Set APP_NAMESHORT variable to "File Manager Vibe"
* implement a preferences file. Store the last screen size, screen location, pane configurations, and last directory for each pane and bookmarks.  Store it in appdata/local using the APP_NAMESHORT variable.
===============================================================================
* The bookmark panel should have a right click contact menu allowing edit, delete. An add button at bottom. And an Add bookmark choice in the File menu.
* Clicking a bookmark should cause the current pane to go to that path
* Save bookmarks and preferences to join file in same location as app
* Default bookmarks on startup without a preference file should be "Desktop, Documents, Downloads, Pictures, Videos, Music"
* If they exist default bookmarks should also be include "One Drive, Google Drive, Dropbox"
===============================================================================
**Left off here 2025-09-09 21:50:48 425 lines -- Need to test and refne Drag & Drop**
===============================================================================
* right click menu options for when clicking on file or folder : rename, copy path to clipboard, Edit in notepad.exe, delete
right click menu options for when clicking on file or folder : rename, copy path to clipboard, Edit in notepad.exe, delete
* Make a field showing path to current folder and make its path elements clickable for navigation.
* For example, if the path is C:\Program Files\Core Temp\Languages, clicking on Program Files should take me to the program Files folder.
   Make the drive from the last iteration a drop down box listing all the available drives
* if you click the right end of the field, it clears and you can type in a path of your own
===============================================================================
* Put a label at the top of each pane with just the folder name of the folder displayed in the pane
* if you drag that folder name atop one from a different pane, the second pane's contents should be set to the first panes
* regarding the breadcrumb, It isn't doing this : if you click the right end of the field, it clears and you can type in a path of your own



