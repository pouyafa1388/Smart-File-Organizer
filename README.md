Smart File Organizer

A desktop file organization tool built with Python and Tkinter.

Smart File Organizer helps users manage files in a selected directory through a simple graphical interface. It identifies file types, displays file information, and organizes files into category-based folders.

Features

- File Categorization: Automatically identifies images, videos, documents, music, archives, programs, and other files.
- Folder Selection: Select a directory to scan and organize.
- Search: Find files by name.
- Category Filtering: Display files based on their categories.
- File Sorting: Sort files using table columns.
- File Information: View file sizes and modification dates.
- Progress Bar: Monitor the organization process.
- Cancel Operation: Stop an ongoing operation.
- Undo: Restore files from the most recent organization operation when possible.
- Activity Logging: Keep operation records and error logs.
- Collision Protection: Avoid overwriting files with identical names.

Technologies

- Python
- Tkinter
- PyInstaller

Requirements

To run the source code:

- Windows
- Python 3.14 or a compatible Python version
- Tkinter

The application primarily uses Python's standard library.

Run the Application

Clone or download this repository.

Open a terminal in the project directory and run:

python main.py

Download the Executable

You can download the packaged Windows executable from the Releases section of this repository.

Python is not required to run the packaged executable.

Build the Executable

Install PyInstaller:

python -m pip install pyinstaller

Build a single-file executable:

python -m PyInstaller --noconfirm --clean --onefile --windowed --name SmartFileOrganizer main.py

The output will be generated inside:

dist/SmartFileOrganizer.exe

Important Notes

- The application processes files in the selected folder's top level.
- Files are moved into category folders; they are not copied.
- Subfolders are not recursively processed.
- Test the application with sample files before using it on important data.
- Keep backups of important files. The undo feature is not a replacement for a backup.

Future Improvements

- Custom file categories
- Optional recursive folder organization
- More detailed operation history
- Custom application icon
- Automated testing

Author

Developed as a Python desktop application project.