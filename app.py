import customtkinter as ctk
from database import initialize_database, add_book, get_all_books, update_status, delete_book

# global appearance settings — do this before building the window
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ShelschApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Shelsch")
        self.geometry("900x600")
        self.minsize(700, 450)

        initialize_database()  # creates the table if it doesn't exist yet
        self.setup_ui()
        self.load_books()      # populate the list on startup

    # UI SETUP

    def setup_ui(self):
        # split the window into two columns: sidebar (left) + main panel (right)
        self.grid_columnconfigure(1, weight=1)  # right column stretches
        self.grid_rowconfigure(0, weight=1)     # row stretches vertically

        self.build_sidebar()
        self.build_main_panel()

    def build_sidebar(self):
        # the left column — holds the add-book form
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)       # keeps it from shrinking
        self.sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="My Library",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(24, 4), sticky="w")

        ctk.CTkLabel(
            self.sidebar,
            text="Add a book",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        # --- title field ---
        ctk.CTkLabel(self.sidebar, text="Title", anchor="w").grid(
            row=2, column=0, padx=20, sticky="w"
        )
        self.title_entry = ctk.CTkEntry(
            self.sidebar, placeholder_text="e.g. Dune"
        )
        self.title_entry.grid(row=3, column=0, padx=20, pady=(4, 12), sticky="ew")

        # --- author field ---
        ctk.CTkLabel(self.sidebar, text="Author", anchor="w").grid(
            row=4, column=0, padx=20, sticky="w"
        )
        self.author_entry = ctk.CTkEntry(
            self.sidebar, placeholder_text="e.g. Frank Herbert"
        )
        self.author_entry.grid(row=5, column=0, padx=20, pady=(4, 12), sticky="ew")

        # --- status dropdown ---
        ctk.CTkLabel(self.sidebar, text="Status", anchor="w").grid(
            row=6, column=0, padx=20, sticky="w"
        )
        self.status_var = ctk.StringVar(value="Archived")
        self.status_menu = ctk.CTkOptionMenu(
            self.sidebar,
            variable=self.status_var,
            values=["Archived", "Finished", "Out For Borrow", "Dropped", "Reading"]
        )
        self.status_menu.grid(row=7, column=0, padx=20, pady=(4, 20), sticky="ew")

        # --- add button ---
        self.add_button = ctk.CTkButton(
            self.sidebar,
            text="Add Book",
            command=self.handle_add_book
        )
        self.add_button.grid(row=8, column=0, padx=20, pady=(0, 12), sticky="ew")

        # --- feedback label (shows success/error messages) ---
        self.feedback_label = ctk.CTkLabel(
            self.sidebar, text="", text_color="gray", wraplength=200
        )
        self.feedback_label.grid(row=9, column=0, padx=20, sticky="w")

    def build_main_panel(self):
        # the right column — holds the scrollable book list
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.main_panel,
            text="Your Collection",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # scrollable frame — this is the list container
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_panel, fg_color="transparent"
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    # LOGIC

    def handle_add_book(self):
        title = self.title_entry.get().strip()
        author = self.author_entry.get().strip()
        status = self.status_var.get()

        # basic validation — don't let blank fields through
        if not title or not author:
            self.show_feedback("Title and author are required.", error=True)
            return

        add_book(title, author, status)

        # clear the inputs after adding
        self.title_entry.delete(0, "end")
        self.author_entry.delete(0, "end")
        self.status_var.set("Reading")

        self.show_feedback(f'"{title}" added.')
        self.load_books()  # refresh the list

    def load_books(self):
        # clear existing cards
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        books = get_all_books()

        if not books:
            ctk.CTkLabel(
                self.scroll_frame,
                text="No books yet. Add one to get started.",
                text_color="gray"
            ).grid(row=0, column=0, pady=40)
            return

        for i, book in enumerate(books):
            self.build_book_card(book, i)

    def build_book_card(self, book, index):
        # one card per book
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        card.grid(row=index, column=0, sticky="ew", pady=5)
        card.grid_columnconfigure(1, weight=1)

        # status color dot
        color = self.status_color(book["status"])
        ctk.CTkLabel(card, text="●", text_color=color, width=20).grid(
            row=0, column=0, padx=(12, 8), pady=14
        )

        # title and author
        ctk.CTkLabel(
            card,
            text=book["title"],
            font=ctk.CTkFont(weight="bold"),
            anchor="w"
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            card,
            text=f'{book["author"]}  ·  {book["date_added"]}',
            text_color="gray",
            font=ctk.CTkFont(size=11),
            anchor="w"
        ).grid(row=1, column=1, sticky="w", pady=(0, 10))

        # status dropdown on the card itself
        status_var = ctk.StringVar(value=book["status"])
        ctk.CTkOptionMenu(
            card,
            variable=status_var,
            values=["Archived", "Finished", "Out For Borrow", "Dropped", "Reading"],
            width=160,
            command=lambda val, bid=book["id"]: self.handle_status_change(bid, val)
        ).grid(row=0, column=2, rowspan=2, padx=10)

        # delete button
        ctk.CTkButton(
            card,
            text="✕",
            width=32,
            height=32,
            fg_color="transparent",
            hover_color="#3a1a1a",
            command=lambda bid=book["id"]: self.handle_delete(bid)
        ).grid(row=0, column=3, rowspan=2, padx=(0, 8))

    def handle_status_change(self, book_id, new_status):
        update_status(book_id, new_status)
        self.load_books()

    def handle_delete(self, book_id):
        delete_book(book_id)
        self.load_books()

    def show_feedback(self, message, error=False):
        color = "#e05555" if error else "gray"
        self.feedback_label.configure(text=message, text_color=color)
        # clear the message after 3 seconds
        self.after(3000, lambda: self.feedback_label.configure(text=""))

    def status_color(self, status):
        return {
            "Reading":        "#5B8DB8",
            "Finished":       "#5BA87A",
            "Out For Borrow": "#C8973A",
            "Dropped":        "#888888"
        }.get(status, "white")




if __name__ == "__main__":
    app = ShelschApp()
    app.mainloop()