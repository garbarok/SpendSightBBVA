"""Tag input widget for transaction tagging."""
import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional


class TagInputWidget(ttk.Frame):
    """
    Widget for displaying and editing transaction tags.

    Displays tags as removable chips and provides an input field
    for adding new tags.
    """

    def __init__(
        self,
        parent,
        tags: List[str] = None,
        on_change: Optional[Callable[[List[str]], None]] = None,
        **kwargs
    ):
        """
        Initialize tag input widget.

        Args:
            parent: Parent widget
            tags: Initial list of tags
            on_change: Callback function called when tags change
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.tags = tags or []
        self.on_change = on_change

        self._create_widgets()
        self._refresh_tags()

    def _create_widgets(self):
        """Create the widget components."""
        # Tags display frame (with scrolling support)
        self.tags_frame = ttk.Frame(self)
        self.tags_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Input frame
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X)

        # Tag input entry
        self.tag_entry = ttk.Entry(input_frame)
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.tag_entry.bind('<Return>', self._on_add_tag)

        # Add button
        self.add_button = ttk.Button(
            input_frame,
            text="+ Add Tag",
            command=self._on_add_tag,
            width=10
        )
        self.add_button.pack(side=tk.LEFT)

    def _refresh_tags(self):
        """Refresh the tag chips display."""
        # Clear existing chips
        for widget in self.tags_frame.winfo_children():
            widget.destroy()

        # Create a chip for each tag
        for tag in self.tags:
            self._create_tag_chip(tag)

    def _create_tag_chip(self, tag: str):
        """
        Create a single tag chip with remove button.

        Args:
            tag: Tag text
        """
        chip_frame = ttk.Frame(self.tags_frame, relief=tk.RAISED, borderwidth=1)
        chip_frame.pack(side=tk.LEFT, padx=2, pady=2)

        # Tag label
        label = ttk.Label(chip_frame, text=tag, padding=(8, 2))
        label.pack(side=tk.LEFT)

        # Remove button
        remove_btn = ttk.Button(
            chip_frame,
            text="×",
            width=3,
            command=lambda: self._remove_tag(tag)
        )
        remove_btn.pack(side=tk.LEFT, padx=(2, 4))

    def _on_add_tag(self, event=None):
        """Handle adding a new tag."""
        tag = self.tag_entry.get().strip()

        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.tag_entry.delete(0, tk.END)
            self._refresh_tags()

            if self.on_change:
                self.on_change(self.tags)

    def _remove_tag(self, tag: str):
        """
        Handle removing a tag.

        Args:
            tag: Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self._refresh_tags()

            if self.on_change:
                self.on_change(self.tags)

    def get_tags(self) -> List[str]:
        """
        Get current list of tags.

        Returns:
            List of tag strings
        """
        return self.tags.copy()

    def set_tags(self, tags: List[str]):
        """
        Set the tags list.

        Args:
            tags: New list of tags
        """
        self.tags = tags.copy()
        self._refresh_tags()

    def clear(self):
        """Clear all tags."""
        self.tags = []
        self.tag_entry.delete(0, tk.END)
        self._refresh_tags()

        if self.on_change:
            self.on_change(self.tags)


class TagSelectorDialog(tk.Toplevel):
    """
    Dialog for selecting tags from existing tags and adding new ones.

    Provides checkboxes for existing tags and an input for new tags.
    """

    def __init__(
        self,
        parent,
        title: str = "Select Tags",
        available_tags: List[str] = None,
        selected_tags: List[str] = None
    ):
        """
        Initialize tag selector dialog.

        Args:
            parent: Parent window
            title: Dialog title
            available_tags: List of existing tags to show as options
            selected_tags: List of currently selected tags
        """
        super().__init__(parent)
        self.title(title)
        self.geometry("400x500")

        self.available_tags = available_tags or []
        self.selected_tags = set(selected_tags or [])
        self.result = None

        self._create_widgets()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center dialog on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create the dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Existing tags section
        if self.available_tags:
            label = ttk.Label(main_frame, text="Select from existing tags:", font=('', 10, 'bold'))
            label.pack(anchor=tk.W, pady=(0, 5))

            # Container for checkboxes with fixed height
            checkbox_container = ttk.Frame(main_frame)
            checkbox_container.pack(fill=tk.X, pady=(0, 10))

            # Scrollable frame for checkboxes with fixed height
            canvas = tk.Canvas(checkbox_container, height=200)
            scrollbar = ttk.Scrollbar(checkbox_container, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Create checkboxes
            self.tag_vars = {}
            for tag in sorted(self.available_tags):
                var = tk.BooleanVar(value=tag in self.selected_tags)
                self.tag_vars[tag] = var

                cb = ttk.Checkbutton(
                    scrollable_frame,
                    text=tag,
                    variable=var
                )
                cb.pack(anchor=tk.W, padx=5, pady=2)

        # New tag section
        separator = ttk.Separator(main_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)

        new_tag_label = ttk.Label(main_frame, text="Add new tag:", font=('', 10, 'bold'))
        new_tag_label.pack(anchor=tk.W, pady=(0, 5))

        self.new_tag_entry = ttk.Entry(main_frame)
        self.new_tag_entry.pack(fill=tk.X, pady=(0, 10))
        self.new_tag_entry.bind('<Return>', lambda e: self._on_ok())

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ok_button = ttk.Button(button_frame, text="OK", command=self._on_ok)
        ok_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_button.pack(side=tk.RIGHT)

    def _on_ok(self):
        """Handle OK button click."""
        # Collect selected tags
        selected = set()

        if hasattr(self, 'tag_vars'):
            for tag, var in self.tag_vars.items():
                if var.get():
                    selected.add(tag)

        # Add new tag if provided
        new_tag = self.new_tag_entry.get().strip()
        if new_tag:
            selected.add(new_tag)

        self.result = sorted(selected)
        self.destroy()

    def _on_cancel(self):
        """Handle Cancel button click."""
        self.result = None
        self.destroy()

    def show(self) -> Optional[List[str]]:
        """
        Show the dialog and wait for result.

        Returns:
            List of selected tags or None if cancelled
        """
        self.wait_window()
        return self.result
