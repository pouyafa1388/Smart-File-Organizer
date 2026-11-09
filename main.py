from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_NAME = "Smart File Organizer"

CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"],
    "Documents": [
        ".pdf", ".docx", ".doc", ".txt", ".rtf", ".pptx", ".ppt",
        ".xlsx", ".xls", ".csv", ".odt", ".ods"
    ],
    "Music": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Programs": [".exe", ".msi", ".bat", ".cmd", ".py", ".js"],
}

selected_folder = None
all_file_records = []
operation_queue = []
operation_manifest = []
operation_total = 0
operation_done = 0
operation_failed = 0
operation_cancelled = False
operation_running = False
sort_state = {"column": "filename", "reverse": False}


# ---------------- FILE HELPERS ----------------

def detect_category(file_path):
    extension = file_path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return "Others"


def format_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    return f"{size / (1024 ** 3):.2f} GB"


def get_log_directory():
    return selected_folder / "_Organizer_Logs"


def write_log(message):
    if selected_folder is None:
        return
    try:
        log_directory = get_log_directory()
        log_directory.mkdir(parents=True, exist_ok=True)
        log_file = log_directory / "organizer.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_file.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def get_unique_path(destination):
    if not destination.exists():
        return destination

    counter = 1
    while True:
        candidate = destination.with_name(
            f"{destination.stem}_{counter}{destination.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1


def save_manifest(entries):
    if selected_folder is None:
        return
    try:
        log_directory = get_log_directory()
        log_directory.mkdir(parents=True, exist_ok=True)
        manifest_file = log_directory / "last_operation.json"
        payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "folder": str(selected_folder),
            "moves": entries,
        }
        manifest_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except OSError as error:
        write_log(f"Could not save undo data: {error}")


# ---------------- FILE LIST / FILTER / SORT ----------------

def scan_folder():
    global all_file_records

    if selected_folder is None:
        all_file_records = []
        return

    records = []
    try:
        for item in selected_folder.iterdir():
            # Only organize files directly inside the selected folder.
            # Subfolders, including category folders and the log folder, are ignored.
            if item.is_file():
                try:
                    stat = item.stat()
                    size = stat.st_size
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                except OSError:
                    size = 0
                    modified = "Unavailable"

                records.append({
                    "path": item,
                    "filename": item.name,
                    "category": detect_category(item),
                    "size": size,
                    "modified": modified,
                })

        all_file_records = records
    except OSError as error:
        messagebox.showerror("Folder Error", f"Could not read this folder:\n{error}")
        all_file_records = []


def get_filtered_records():
    search_text = search_var.get().strip().lower()
    chosen_category = category_var.get()

    records = []
    for record in all_file_records:
        if chosen_category != "All categories" and record["category"] != chosen_category:
            continue
        if search_text and search_text not in record["filename"].lower():
            continue
        records.append(record)

    column = sort_state["column"]
    reverse = sort_state["reverse"]

    if column == "size":
        records.sort(key=lambda record: record["size"], reverse=reverse)
    else:
        records.sort(
            key=lambda record: str(record[column]).lower(),
            reverse=reverse
        )
    return records


def refresh_table():
    for row in file_table.get_children():
        file_table.delete(row)

    records = get_filtered_records()
    for record in records:
        file_table.insert(
            "",
            "end",
            iid=str(record["path"]),
            values=(
                record["filename"],
                record["category"],
                format_size(record["size"]),
                record["modified"],
            )
        )

    total_size = sum(record["size"] for record in all_file_records)
    visible_count = len(records)
    count_label.config(
        text=(
            f"Files: {len(all_file_records)}   |   "
            f"Visible: {visible_count}   |   "
            f"Total size: {format_size(total_size)}"
        )
    )

    category_counts = {}
    for record in all_file_records:
        category_counts[record["category"]] = (
            category_counts.get(record["category"], 0) + 1
        )

    summary_parts = [
        f"{name}: {count}"
        for name, count in sorted(category_counts.items())
    ]
    summary_label.config(
        text="   •   ".join(summary_parts) if summary_parts else "No files found."
    )


def preview_files():
    if selected_folder is None:
        return
    scan_folder()
    refresh_table()
    status_var.set("Folder scan complete.")


def sort_by(column):
    if sort_state["column"] == column:
        sort_state["reverse"] = not sort_state["reverse"]
    else:
        sort_state["column"] = column
        sort_state["reverse"] = False
    refresh_table()


# ---------------- GUI ACTIONS ----------------

def select_folder():
    global selected_folder

    folder = filedialog.askdirectory(title="Select a folder to organize")
    if not folder:
        return

    selected_folder = Path(folder)
    folder_label.config(text=f"Selected folder: {selected_folder}")
    preview_files()
    undo_button.config(state="normal" if get_manifest_moves() else "disabled")


def set_controls_enabled(enabled):
    state = "normal" if enabled else "disabled"
    select_button.config(state=state)
    organize_button.config(state=state)
    refresh_button.config(state=state)
    logs_button.config(state=state)
    undo_button.config(
        state=("normal" if enabled and get_manifest_moves() else "disabled")
    )
    search_entry.config(state=state)
    category_combo.config(state="readonly" if enabled else "disabled")


def organize_files():
    global operation_queue, operation_manifest
    global operation_total, operation_done, operation_failed
    global operation_cancelled, operation_running

    if selected_folder is None:
        messagebox.showwarning("No folder selected", "Select a folder first.")
        return

    # Organizing always processes every top-level file, not only filtered rows.
    try:
        files = [
            item for item in selected_folder.iterdir()
            if item.is_file()
        ]
    except OSError as error:
        messagebox.showerror("Folder Error", str(error))
        return

    if not files:
        messagebox.showinfo("Nothing to do", "There are no files in this folder.")
        return

    answer = messagebox.askyesno(
        "Confirm organization",
        f"{len(files)} files will be moved into category folders.\n\n"
        "Only files directly inside the selected folder are processed.\n"
        "Existing files will not be overwritten.\n\n"
        "Continue?"
    )
    if not answer:
        return

    operation_queue = list(files)
    operation_manifest = []
    operation_total = len(operation_queue)
    operation_done = 0
    operation_failed = 0
    operation_cancelled = False
    operation_running = True

    progress_bar["maximum"] = operation_total
    progress_bar["value"] = 0
    progress_label.config(text=f"0 / {operation_total}")
    cancel_button.config(state="normal")
    set_controls_enabled(False)
    status_var.set("Organizing files...")
    root.after(10, process_next_file)


def process_next_file():
    global operation_done, operation_failed, operation_running

    if operation_cancelled or not operation_queue:
        finish_organization()
        return

    source = operation_queue.pop(0)
    category = detect_category(source)
    destination_folder = selected_folder / category

    try:
        destination_folder.mkdir(parents=True, exist_ok=True)
        destination = get_unique_path(destination_folder / source.name)
        shutil.move(str(source), str(destination))

        operation_manifest.append({
            "source": str(source),
            "destination": str(destination),
        })
        write_log(f"MOVED | {source.name} | {category} | {destination}")
    except (OSError, shutil.Error) as error:
        operation_failed += 1
        write_log(f"FAILED | {source.name} | {error}")

    operation_done += 1
    progress_bar["value"] = operation_done
    progress_label.config(text=f"{operation_done} / {operation_total}")

    percent = int((operation_done / operation_total) * 100)
    status_var.set(f"Organizing... {percent}% complete")

    root.after(10, process_next_file)


def cancel_organization():
    global operation_cancelled
    if operation_running:
        operation_cancelled = True
        cancel_button.config(state="disabled")
        status_var.set("Cancellation requested...")


def finish_organization():
    global operation_running

    operation_running = False
    save_manifest(operation_manifest)
    cancel_button.config(state="disabled")
    set_controls_enabled(True)
    preview_files()

    moved = len(operation_manifest)
    if operation_cancelled:
        status_var.set("Organization cancelled. Completed moves were saved.")
        title_text = "Operation cancelled"
    else:
        status_var.set("Organization completed.")
        title_text = "Organization completed"

    undo_button.config(state="normal" if operation_manifest else "disabled")

    messagebox.showinfo(
        title_text,
        f"Moved: {moved}\nFailed: {operation_failed}\n"
        f"Not processed: {len(operation_queue)}"
    )


# ---------------- UNDO / LOGS ----------------

def get_manifest_moves():
    if selected_folder is None:
        return []
    manifest_file = get_log_directory() / "last_operation.json"
    if not manifest_file.exists():
        return []
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        return data.get("moves", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return []


def undo_last_operation():
    if selected_folder is None:
        return

    moves = get_manifest_moves()
    if not moves:
        messagebox.showinfo("Undo", "There is no saved operation to undo.")
        undo_button.config(state="disabled")
        return

    answer = messagebox.askyesno(
        "Undo last operation",
        f"This will try to restore {len(moves)} moved files to the selected folder.\n\n"
        "If a filename already exists, the restored file will receive a new name.\n"
        "Continue?"
    )
    if not answer:
        return

    restored = 0
    failed = 0

    for move in reversed(moves):
        destination = Path(move.get("destination", ""))
        original = Path(move.get("source", ""))

        try:
            if not destination.exists():
                failed += 1
                continue

            original.parent.mkdir(parents=True, exist_ok=True)
            restore_path = get_unique_path(original)
            shutil.move(str(destination), str(restore_path))
            restored += 1
            write_log(f"UNDO | {destination.name} | restored to {restore_path}")
        except (OSError, shutil.Error) as error:
            failed += 1
            write_log(f"UNDO FAILED | {destination} | {error}")

    # Clear the undo record after attempting the undo, preventing accidental repeats.
    save_manifest([])
    preview_files()
    undo_button.config(state="disabled")
    messagebox.showinfo(
        "Undo completed",
        f"Restored: {restored}\nFailed: {failed}"
    )


def open_logs():
    if selected_folder is None:
        messagebox.showwarning("No folder selected", "Select a folder first.")
        return

    log_file = get_log_directory() / "organizer.log"
    if not log_file.exists():
        messagebox.showinfo("Logs", "No logs available yet.")
        return

    try:
        os.startfile(str(log_file))
    except OSError as error:
        messagebox.showerror("Could not open logs", str(error))


# ---------------- APPLICATION WINDOW ----------------

root = tk.Tk()
root.title(APP_NAME)
root.geometry("1050x700")
root.minsize(820, 580)
root.configure(bg="#171b24")

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure(
    "Treeview",
    background="#222936",
    foreground="#edf2f7",
    fieldbackground="#222936",
    rowheight=29,
    borderwidth=0,
    font=("Segoe UI", 10),
)
style.configure(
    "Treeview.Heading",
    background="#303a4b",
    foreground="white",
    font=("Segoe UI", 10, "bold"),
    padding=8,
)
style.map(
    "Treeview",
    background=[("selected", "#315b83")],
    foreground=[("selected", "white")],
)
style.configure(
    "Horizontal.TProgressbar",
    troughcolor="#303a4b",
    background="#61afef",
    thickness=13,
)

header = tk.Frame(root, bg="#171b24")
header.pack(fill="x", padx=24, pady=(20, 10))

title = tk.Label(
    header,
    text="SMART FILE ORGANIZER",
    font=("Segoe UI", 22, "bold"),
    bg="#171b24",
    fg="#f4f7fb",
)
title.pack(anchor="w")

subtitle = tk.Label(
    header,
    text="Scan, search, preview and safely organize your files.",
    font=("Segoe UI", 10),
    bg="#171b24",
    fg="#aab6c5",
)
subtitle.pack(anchor="w", pady=(3, 0))

toolbar = tk.Frame(root, bg="#171b24")
toolbar.pack(fill="x", padx=24, pady=10)

select_button = tk.Button(
    toolbar, text="SELECT FOLDER", command=select_folder,
    bg="#61afef", fg="#101820", activebackground="#7bc0f5",
    font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=9,
)
select_button.pack(side="left")

folder_label = tk.Label(
    root, text="No folder selected",
    bg="#171b24", fg="#d7e0ea",
    font=("Segoe UI", 9), anchor="w", wraplength=980,
)
folder_label.pack(fill="x", padx=26, pady=(3, 10))

filters = tk.Frame(root, bg="#202735", padx=12, pady=10)
filters.pack(fill="x", padx=24, pady=(0, 10))

tk.Label(
    filters, text="Search files:",
    bg="#202735", fg="#edf2f7", font=("Segoe UI", 9, "bold")
).pack(side="left", padx=(0, 8))

search_var = tk.StringVar()
search_entry = ttk.Entry(filters, textvariable=search_var, width=32)
search_entry.pack(side="left", padx=(0, 18))

tk.Label(
    filters, text="Category:",
    bg="#202735", fg="#edf2f7", font=("Segoe UI", 9, "bold")
).pack(side="left", padx=(0, 8))

category_var = tk.StringVar(value="All categories")
category_combo = ttk.Combobox(
    filters,
    textvariable=category_var,
    values=["All categories"] + sorted(list(CATEGORIES.keys()) + ["Others"]),
    state="readonly",
    width=19,
)
category_combo.pack(side="left")

table_frame = tk.Frame(root, bg="#171b24")
table_frame.pack(fill="both", expand=True, padx=24, pady=5)

columns = ("filename", "category", "size", "modified")
file_table = ttk.Treeview(
    table_frame,
    columns=columns,
    show="headings",
    selectmode="extended",
)

file_table.heading("filename", text="File Name", command=lambda: sort_by("filename"))
file_table.heading("category", text="Category", command=lambda: sort_by("category"))
file_table.heading("size", text="File Size", command=lambda: sort_by("size"))
file_table.heading("modified", text="Modified", command=lambda: sort_by("modified"))

file_table.column("filename", width=470, minwidth=220, anchor="w")
file_table.column("category", width=150, minwidth=100, anchor="center")
file_table.column("size", width=120, minwidth=90, anchor="center")
file_table.column("modified", width=160, minwidth=130, anchor="center")

vertical_scroll = ttk.Scrollbar(
    table_frame, orient="vertical", command=file_table.yview
)
horizontal_scroll = ttk.Scrollbar(
    table_frame, orient="horizontal", command=file_table.xview
)
file_table.configure(
    yscrollcommand=vertical_scroll.set,
    xscrollcommand=horizontal_scroll.set,
)
file_table.grid(row=0, column=0, sticky="nsew")
vertical_scroll.grid(row=0, column=1, sticky="ns")
horizontal_scroll.grid(row=1, column=0, sticky="ew")
table_frame.grid_rowconfigure(0, weight=1)
table_frame.grid_columnconfigure(0, weight=1)

count_label = tk.Label(
    root, text="Files: 0   |   Visible: 0   |   Total size: 0 B",
    bg="#171b24", fg="#edf2f7", font=("Segoe UI", 9, "bold"), anchor="w",
)
count_label.pack(fill="x", padx=26, pady=(8, 2))

summary_label = tk.Label(
    root, text="No files found.",
    bg="#171b24", fg="#aab6c5", font=("Segoe UI", 8), anchor="w",
    wraplength=980,
)
summary_label.pack(fill="x", padx=26, pady=(0, 8))

progress_frame = tk.Frame(root, bg="#171b24")
progress_frame.pack(fill="x", padx=24, pady=(4, 8))

progress_bar = ttk.Progressbar(
    progress_frame, mode="determinate", style="Horizontal.TProgressbar"
)
progress_bar.pack(side="left", fill="x", expand=True)

progress_label = tk.Label(
    progress_frame, text="0 / 0", width=10,
    bg="#171b24", fg="#edf2f7", font=("Segoe UI", 9),
)
progress_label.pack(side="left", padx=(10, 0))

buttons_frame = tk.Frame(root, bg="#171b24")
buttons_frame.pack(pady=(5, 8))

organize_button = tk.Button(
    buttons_frame, text="ORGANIZE FILES", command=organize_files,
    bg="#98c379", fg="#101820", activebackground="#acd98d",
    font=("Segoe UI", 10, "bold"), relief="flat", padx=17, pady=9,
)
organize_button.grid(row=0, column=0, padx=5)

refresh_button = tk.Button(
    buttons_frame, text="REFRESH", command=preview_files,
    bg="#d5dce5", fg="#17202b", relief="flat",
    font=("Segoe UI", 9, "bold"), padx=15, pady=9,
)
refresh_button.grid(row=0, column=1, padx=5)

undo_button = tk.Button(
    buttons_frame, text="UNDO LAST", command=undo_last_operation,
    bg="#e5b567", fg="#17202b", relief="flat",
    font=("Segoe UI", 9, "bold"), padx=15, pady=9, state="disabled",
)
undo_button.grid(row=0, column=2, padx=5)

logs_button = tk.Button(
    buttons_frame, text="VIEW LOGS", command=open_logs,
    bg="#a9b8cc", fg="#17202b", relief="flat",
    font=("Segoe UI", 9, "bold"), padx=15, pady=9,
)
logs_button.grid(row=0, column=3, padx=5)

cancel_button = tk.Button(
    buttons_frame, text="CANCEL", command=cancel_organization,
    bg="#e06c75", fg="white", relief="flat",
    font=("Segoe UI", 9, "bold"), padx=15, pady=9, state="disabled",
)
cancel_button.grid(row=0, column=4, padx=5)

status_var = tk.StringVar(value="Ready.")
status_label = tk.Label(
    root, textvariable=status_var,
    bg="#202735", fg="#c7d2df", font=("Segoe UI", 9),
    anchor="w", padx=12, pady=8,
)
status_label.pack(fill="x", side="bottom")

search_var.trace_add("write", lambda *_: refresh_table())
category_var.trace_add("write", lambda *_: refresh_table())

root.mainloop()
