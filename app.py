import customtkinter as ctk
from tkinter import filedialog
from database import (
    initialize_database, add_book, get_all_books, delete_book, update_book,
    export_library, import_library,
)

# optional drag-and-drop support — only available if tkinterdnd2 is installed
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_AVAILABLE = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    _DND_AVAILABLE = False

# global appearance settings — do this before building the window
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
# use Helvetica everywhere — sets the default family for every widget/CTkFont
ctk.ThemeManager.theme["CTkFont"]["family"] = "Helvetica"


class ShelkrApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # load the tkdnd Tcl package so widgets can register as drop targets;
        # if anything goes wrong we just fall back to click-to-browse
        self._dnd_ready = False
        if _DND_AVAILABLE:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self._dnd_ready = True
            except Exception:
                self._dnd_ready = False

        self.title("Shelkr")
        self.geometry("900x600")
        self.minsize(700, 450)

        initialize_database()  # creates the table if it doesn't exist yet

        # sort state — default to newest first (matches the old DB ordering)
        self.sort_key = "date_added"
        self.sort_reverse = True

        self.setup_ui()
        self.load_books()      # populate the list on startup

    # UI SETUP

    def setup_ui(self):
        # single full-width page for the collection
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.build_main_panel()

    def build_main_panel(self):
        # one whole page — header row + scrollable table
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        self.main_panel.grid_columnconfigure(0, weight=1)

        # --- header: title on the left, Add Entry button on the right ---
        header = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Your Collection.",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="+  Add Entry",
            width=120,
            command=self.open_add_dialog
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            header,
            text="Import / Export",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=self.open_import_export_dialog
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        # --- table header row ---
        table_header = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        table_header.grid(row=1, column=0, sticky="ew", padx=4)
        self._configure_row_columns(table_header)

        # columns: display text, sort key (None = not sortable)
        columns = [
            ("Title", "title"),
            ("Author", "author"),
            ("Added", "date_added"),
            ("Status", None),
        ]
        self.header_labels = {}  # sort key -> label, so we can show the arrow
        for col, (text, key) in enumerate(columns):
            label = ctk.CTkLabel(
                table_header,
                text=text.upper(),
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="gray",
                anchor="w"
            )
            label.grid(row=0, column=col, sticky="w",
                       padx=(12 if col == 0 else 8, 8), pady=(0, 6))

            # only Title / Author / Added are sortable
            if key is not None:
                self.header_labels[key] = label
                label.bind("<Button-1>", lambda _e, k=key: self.sort_by(k))
                try:
                    label.configure(cursor="hand2")
                except Exception:
                    pass

        # thin divider under the header
        ctk.CTkFrame(self.main_panel, height=1, fg_color="#333333").grid(
            row=2, column=0, sticky="new", padx=4
        )

        # --- scrollable table body ---
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_panel, fg_color="transparent"
        )
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", pady=(4, 0))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(3, weight=1)

    def _configure_row_columns(self, frame):
        # shared column widths so the header and every row line up like a table
        frame.grid_columnconfigure(0, weight=3, uniform="col")  # title
        frame.grid_columnconfigure(1, weight=3, uniform="col")  # author
        frame.grid_columnconfigure(2, weight=2, uniform="col")  # date added
        frame.grid_columnconfigure(3, weight=2, uniform="col")  # status
        frame.grid_columnconfigure(4, weight=0)                 # delete button

    # LOGIC

    def sort_by(self, key):
        # clicking the active column flips direction; a new column starts ascending
        if self.sort_key == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_key = key
            self.sort_reverse = False
        self.load_books()

    def _sorted_books(self, books):
        def key_fn(book):
            value = book[self.sort_key]
            # title/author sort case-insensitively; dates (ISO strings) sort fine as-is
            return value.lower() if self.sort_key in ("title", "author") else value
        return sorted(books, key=key_fn, reverse=self.sort_reverse)

    def _refresh_header_arrows(self):
        for key, label in self.header_labels.items():
            base = label.cget("text").split("  ")[0]  # strip any existing arrow
            if key == self.sort_key:
                arrow = "  ↓" if self.sort_reverse else "  ↑"
                label.configure(text=base + arrow, text_color="#cccccc")
            else:
                label.configure(text=base, text_color="gray")

    def load_books(self):
        # clear existing rows
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self._refresh_header_arrows()

        books = self._sorted_books(get_all_books())

        if not books:
            ctk.CTkLabel(
                self.scroll_frame,
                text="No entries yet. Click \"Add Entry\" to get started.",
                text_color="gray"
            ).grid(row=0, column=0, pady=40)
            return

        for i, book in enumerate(books):
            self.build_book_row(book, i)

    def build_book_row(self, book, index):
        # one uniform table row per book
        row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", corner_radius=6)
        row.grid(row=index, column=0, sticky="ew", pady=1)
        self._configure_row_columns(row)

        title_lbl = ctk.CTkLabel(
            row, text=book["title"], anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        title_lbl.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=10)

        author_lbl = ctk.CTkLabel(
            row, text=book["author"], anchor="w", text_color="#cccccc"
        )
        author_lbl.grid(row=0, column=1, sticky="w", padx=8, pady=10)

        date_lbl = ctk.CTkLabel(
            row, text=book["date_added"], anchor="w", text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        date_lbl.grid(row=0, column=2, sticky="w", padx=8, pady=10)

        # status shown as a small colored dot + label — blank when "None"
        status_cell = ctk.CTkFrame(row, fg_color="transparent")
        status_cell.grid(row=0, column=3, sticky="w", padx=8, pady=10)
        status_widgets = []  # included in the row's clickable area
        has_status = book["status"] and book["status"] != self.STATUS_NONE
        if has_status:
            dot_lbl = ctk.CTkLabel(
                status_cell, text="●", width=14,
                text_color=self.status_color(book["status"])
            )
            dot_lbl.grid(row=0, column=0, padx=(0, 6))
            status_widgets.append(dot_lbl)
        # always keep a label (blank when no status) so the empty cell doesn't
        # fall back to the frame's default height and inflate the row
        status_lbl = ctk.CTkLabel(
            status_cell, text=book["status"] if has_status else "", anchor="w"
        )
        status_lbl.grid(row=0, column=1, sticky="w")
        status_widgets.append(status_lbl)

        # subtle delete button (keeps its own click target — not editable)
        ctk.CTkButton(
            row, text="✕", width=28, height=28,
            fg_color="transparent", hover_color="#3a1a1a", text_color="gray",
            command=lambda bid=book["id"]: self.handle_delete(bid)
        ).grid(row=0, column=4, padx=(8, 4))

        # hover highlight + click-to-edit across the whole row (except delete)
        clickable = [row, title_lbl, author_lbl, date_lbl,
                     status_cell] + status_widgets
        self._make_row_interactive(row, clickable, book)

    def _make_row_interactive(self, row, widgets, book):
        # subtle highlight on hover, open the edit popup on click
        HIGHLIGHT = "#262626"

        def on_enter(_=None):
            row.configure(fg_color=HIGHLIGHT)

        def on_leave(_=None):
            # only clear the highlight once the pointer truly leaves the row —
            # moving between the row's child labels would otherwise flicker
            x, y = self.winfo_pointerxy()
            widget = self.winfo_containing(x, y)
            while widget is not None:
                if widget == row:
                    return
                widget = widget.master
            row.configure(fg_color="transparent")

        def on_click(_=None):
            self.open_edit_dialog(book)

        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass

    STATUSES = ["Finished", "Out For Borrow", "Dropped", "Reading"]
    STATUS_NONE = "None"  # stored value that renders as a blank Status column
    STATUS_OPTIONS = [STATUS_NONE] + STATUSES  # dropdown choices incl. "None"

    def open_import_export_dialog(self):
        # native popup with two tabs: Import and Export
        win = ctk.CTkToplevel(self)
        win.title("Import / Export")
        win.geometry("440x360")
        win.resizable(False, False)
        win.transient(self)
        win.after(100, win.grab_set)

        tabview = ctk.CTkTabview(win)
        tabview.pack(fill="both", expand=True, padx=16, pady=16)
        tabview.add("Import")
        tabview.add("Export")

        self._build_import_tab(tabview.tab("Import"))
        self._build_export_tab(tabview.tab("Export"))

    # --- Export tab ---

    def _build_export_tab(self, tab):
        ctk.CTkLabel(
            tab,
            text="Save your entire library to a .json file.",
            wraplength=360, text_color="gray"
        ).pack(padx=20, pady=(24, 18))

        ctk.CTkButton(
            tab, text="Export Library", command=self._do_export
        ).pack()

        self.export_feedback = ctk.CTkLabel(
            tab, text="", text_color="gray", wraplength=360
        )
        self.export_feedback.pack(padx=20, pady=(16, 0))

    def _do_export(self):
        path = filedialog.asksaveasfilename(
            title="Export Library",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="shelkr_library.json",
        )
        if not path:
            return
        try:
            count = export_library(path)
            self.export_feedback.configure(
                text=f"Exported {count} book(s).", text_color="#5BA87A"
            )
        except Exception as e:
            self.export_feedback.configure(
                text=f"Export failed: {e}", text_color="#e05555"
            )

    # --- Import tab ---

    def _build_import_tab(self, tab):
        ctk.CTkLabel(
            tab,
            text="Add books from a .json file into your library.",
            wraplength=360, text_color="gray"
        ).pack(padx=20, pady=(18, 12))

        # drop zone — accepts a dragged .json file when tkinterdnd2 is available
        drop = ctk.CTkFrame(
            tab, fg_color="#1c1c1c", border_width=2,
            border_color="#333333", corner_radius=10, height=80
        )
        drop.pack(fill="x", padx=20, pady=(0, 14))
        drop.pack_propagate(False)

        hint = ("Drag & drop a .json file here"
                if self._dnd_ready
                else "Tip: install 'tkinterdnd2' to drag & drop files here")
        ctk.CTkLabel(drop, text=hint, text_color="gray").pack(expand=True)

        if self._dnd_ready:
            try:
                drop.drop_target_register(DND_FILES)
                drop.dnd_bind("<<Drop>>", self._handle_drop)
            except Exception:
                pass

        ctk.CTkButton(
            tab, text="Import Library", command=self._do_import
        ).pack()

        self.import_feedback = ctk.CTkLabel(
            tab, text="", text_color="gray", wraplength=360
        )
        self.import_feedback.pack(padx=20, pady=(14, 0))

    def _do_import(self):
        path = filedialog.askopenfilename(
            title="Import Library",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._import_path(path)

    def _handle_drop(self, event):
        # tkdnd hands back a brace-wrapped, possibly multi-file string
        files = self.tk.splitlist(event.data)
        if not files:
            return
        path = files[0]
        if not path.lower().endswith(".json"):
            self.import_feedback.configure(
                text="Please drop a .json file.", text_color="#e05555"
            )
            return
        self._import_path(path)

    def _import_path(self, path):
        try:
            count = import_library(path)
            self.import_feedback.configure(
                text=f"Imported {count} book(s).", text_color="#5BA87A"
            )
            self.load_books()  # refresh the main table with the new entries
        except Exception as e:
            self.import_feedback.configure(
                text=f"Import failed: {e}", text_color="#e05555"
            )

    # --- shared book-form helpers (used by both add & edit dialogs) ---

    def _build_book_fields(self, parent, *, title="", author="", status=None):
        """Build the Title / Author / Status fields + feedback label.

        Fields occupy grid rows 1-7; the caller owns row 0 (heading) and
        row 8 (buttons). Returns (title_entry, author_entry, status_var,
        feedback_label).
        """
        ctk.CTkLabel(parent, text="Title", anchor="w").grid(
            row=1, column=0, padx=28, sticky="w"
        )
        title_entry = ctk.CTkEntry(parent, placeholder_text="e.g. Dune")
        title_entry.grid(row=2, column=0, padx=28, pady=(4, 12), sticky="ew")
        if title:
            title_entry.insert(0, title)

        ctk.CTkLabel(parent, text="Author", anchor="w").grid(
            row=3, column=0, padx=28, sticky="w"
        )
        author_entry = ctk.CTkEntry(parent, placeholder_text="e.g. Frank Herbert")
        author_entry.grid(row=4, column=0, padx=28, pady=(4, 12), sticky="ew")
        if author:
            author_entry.insert(0, author)

        ctk.CTkLabel(parent, text="Status", anchor="w").grid(
            row=5, column=0, padx=28, sticky="w"
        )
        status_var = ctk.StringVar(value=status or self.STATUS_NONE)
        ctk.CTkOptionMenu(
            parent, variable=status_var, values=self.STATUS_OPTIONS
        ).grid(row=6, column=0, padx=28, pady=(4, 20), sticky="ew")

        feedback = ctk.CTkLabel(parent, text="", text_color="gray", wraplength=280)
        feedback.grid(row=7, column=0, padx=28, sticky="w")

        return title_entry, author_entry, status_var, feedback

    def _build_dialog_buttons(self, parent, *, save_text, on_save, on_cancel):
        # Cancel / save button pair on row 8, matching the form layout above
        buttons = ctk.CTkFrame(parent, fg_color="transparent")
        buttons.grid(row=8, column=0, padx=28, pady=(8, 24), sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            buttons, text="Cancel", fg_color="transparent", border_width=1,
            command=on_cancel
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            buttons, text=save_text, command=on_save
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _read_book_fields(self, title_entry, author_entry, feedback):
        # validate the shared form; returns (title, author) or None if invalid
        title = title_entry.get().strip()
        author = author_entry.get().strip()
        if not title or not author:
            feedback.configure(
                text="Title and author are required.", text_color="#e05555"
            )
            return None
        return title, author

    def open_add_dialog(self):
        # dim backdrop covering the whole window (acts as a modal layer)
        backdrop = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=0)
        backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)

        # centered "add entry" card — mirrors the old sidebar form
        card = ctk.CTkFrame(backdrop, corner_radius=12, border_width=1, width=320)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Add a book",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=28, pady=(24, 16), sticky="w")

        title_entry, author_entry, status_var, feedback = self._build_book_fields(card)

        def close():
            backdrop.destroy()

        def save():
            fields = self._read_book_fields(title_entry, author_entry, feedback)
            if fields is None:
                return
            self.handle_add_book(*fields, status_var.get())
            close()

        self._build_dialog_buttons(
            card, save_text="Add Book", on_save=save, on_cancel=close
        )
        title_entry.focus()

    def handle_add_book(self, title, author, status):
        add_book(title, author, status)
        self.load_books()  # refresh the table

    def open_edit_dialog(self, book):
        # a real (native) popup window for editing a single entry
        win = ctk.CTkToplevel(self)
        win.title("Edit entry")
        win.geometry("360x430")
        win.resizable(False, False)
        win.transient(self)             # stay above the main window
        win.after(100, win.grab_set)    # make it modal once it's drawn
        win.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            win, text="Edit book",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=28, pady=(24, 16), sticky="w")

        title_entry, author_entry, status_var, feedback = self._build_book_fields(
            win, title=book["title"], author=book["author"], status=book["status"]
        )

        def close():
            win.grab_release()
            win.destroy()

        def save():
            fields = self._read_book_fields(title_entry, author_entry, feedback)
            if fields is None:
                return
            update_book(book["id"], *fields, status_var.get())
            close()
            self.load_books()  # refresh the table

        self._build_dialog_buttons(
            win, save_text="Save", on_save=save, on_cancel=close
        )
        win.protocol("WM_DELETE_WINDOW", close)
        title_entry.focus()

    def handle_delete(self, book_id):
        # confirm before removing — shown as an in-window overlay
        self.show_confirm(
            message="Are you sure you want to remove this entry?",
            on_confirm=lambda: self._delete_confirmed(book_id)
        )

    def _delete_confirmed(self, book_id):
        delete_book(book_id)
        self.load_books()

    def show_confirm(self, message, on_confirm):
        # dim backdrop covering the whole window (acts as a modal layer)
        backdrop = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=0)
        backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)

        # centered confirmation card
        card = ctk.CTkFrame(backdrop, corner_radius=12, border_width=1)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card, text=message, wraplength=280,
            font=ctk.CTkFont(size=14)
        ).grid(row=0, column=0, columnspan=2, padx=28, pady=(24, 18))

        def close():
            backdrop.destroy()

        def confirm():
            close()
            on_confirm()

        ctk.CTkButton(
            card, text="Cancel", width=110,
            fg_color="transparent", border_width=1,
            command=close
        ).grid(row=1, column=0, padx=(28, 8), pady=(0, 24))

        ctk.CTkButton(
            card, text="Remove", width=110,
            fg_color="#b03a3a", hover_color="#8f2e2e",
            command=confirm
        ).grid(row=1, column=1, padx=(8, 28), pady=(0, 24))

    def status_color(self, status):
        return {
            "Reading":        "#5B8DB8",
            "Finished":       "#5BA87A",
            "Out For Borrow": "#C8973A",
            "Dropped":        "#888888",
        }.get(status, "white")


if __name__ == "__main__":
    app = ShelkrApp()
    app.mainloop()
