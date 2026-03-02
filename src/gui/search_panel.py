"""Search and filter panel for transactions."""
import tkinter as tk
from tkinter import ttk
from datetime import date
from typing import Optional, Callable, List, Dict, Any

# Try to import tkcalendar, fall back to simple picker if not available
try:
    from .widgets.date_range_picker import DateRangePicker
    HAS_CALENDAR = True
except ImportError:
    from .widgets.date_range_picker import SimpleDateRangePicker as DateRangePicker
    HAS_CALENDAR = False


class SearchPanel(ttk.LabelFrame):
    """
    Advanced search and filter panel for transactions.

    Provides filters for:
    - Text search (concept/description)
    - Date range (from/to)
    - Amount range (min/max)
    - Categories (multi-select)
    - Tags (multi-select)
    """

    def __init__(
        self,
        parent,
        on_search: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs
    ):
        """
        Initialize search panel.

        Args:
            parent: Parent widget
            on_search: Callback function called when search is executed
            **kwargs: Additional LabelFrame options
        """
        super().__init__(parent, text="Search & Filter", padding=10, **kwargs)

        self.on_search = on_search
        self.available_categories = []
        self.available_tags = []

        self._create_widgets()

    def _create_widgets(self):
        """Create the panel widgets."""
        # Text search
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.X, pady=5)

        text_label = ttk.Label(text_frame, text="Text:", width=12)
        text_label.pack(side=tk.LEFT)

        self.text_entry = ttk.Entry(text_frame)
        self.text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.text_entry.bind('<Return>', lambda e: self._execute_search())

        # Date range
        date_label = ttk.Label(self, text="Date Range:", font=('', 9, 'bold'))
        date_label.pack(anchor=tk.W, pady=(10, 5))

        self.date_picker = DateRangePicker(self)
        self.date_picker.pack(fill=tk.X)

        # Amount range
        amount_label = ttk.Label(self, text="Amount Range (€):", font=('', 9, 'bold'))
        amount_label.pack(anchor=tk.W, pady=(10, 5))

        amount_frame = ttk.Frame(self)
        amount_frame.pack(fill=tk.X, pady=5)

        min_label = ttk.Label(amount_frame, text="Min:", width=12)
        min_label.pack(side=tk.LEFT)

        self.amount_min_entry = ttk.Entry(amount_frame, width=10)
        self.amount_min_entry.pack(side=tk.LEFT, padx=(0, 10))

        max_label = ttk.Label(amount_frame, text="Max:", width=6)
        max_label.pack(side=tk.LEFT)

        self.amount_max_entry = ttk.Entry(amount_frame, width=10)
        self.amount_max_entry.pack(side=tk.LEFT)

        # Categories
        category_label = ttk.Label(self, text="Categories:", font=('', 9, 'bold'))
        category_label.pack(anchor=tk.W, pady=(10, 5))

        # Category listbox with scrollbar
        cat_frame = ttk.Frame(self)
        cat_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cat_scrollbar = ttk.Scrollbar(cat_frame)
        cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.category_listbox = tk.Listbox(
            cat_frame,
            selectmode=tk.MULTIPLE,
            height=6,
            yscrollcommand=cat_scrollbar.set
        )
        self.category_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_scrollbar.config(command=self.category_listbox.yview)

        # Tags
        tag_label = ttk.Label(self, text="Tags:", font=('', 9, 'bold'))
        tag_label.pack(anchor=tk.W, pady=(10, 5))

        # Tag listbox with scrollbar
        tag_frame = ttk.Frame(self)
        tag_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        tag_scrollbar = ttk.Scrollbar(tag_frame)
        tag_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tag_listbox = tk.Listbox(
            tag_frame,
            selectmode=tk.MULTIPLE,
            height=4,
            yscrollcommand=tag_scrollbar.set
        )
        self.tag_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tag_scrollbar.config(command=self.tag_listbox.yview)

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        self.search_button = ttk.Button(
            button_frame,
            text="Apply Filters",
            command=self._execute_search
        )
        self.search_button.pack(side=tk.LEFT, padx=(0, 5))

        self.clear_button = ttk.Button(
            button_frame,
            text="Clear All",
            command=self._clear_filters
        )
        self.clear_button.pack(side=tk.LEFT)

    def _execute_search(self):
        """Execute the search with current filter values."""
        if not self.on_search:
            return

        # Collect filter values
        filters = {
            'text': self.text_entry.get().strip() or None,
            'date_from': None,
            'date_to': None,
            'amount_min': None,
            'amount_max': None,
            'categories': [],
            'tags': []
        }

        # Get date range
        date_from, date_to = self.date_picker.get_range()
        filters['date_from'] = date_from
        filters['date_to'] = date_to

        # Get amount range
        try:
            min_str = self.amount_min_entry.get().strip()
            if min_str:
                filters['amount_min'] = float(min_str)
        except ValueError:
            pass

        try:
            max_str = self.amount_max_entry.get().strip()
            if max_str:
                filters['amount_max'] = float(max_str)
        except ValueError:
            pass

        # Get selected categories
        selected_indices = self.category_listbox.curselection()
        filters['categories'] = [
            self.category_listbox.get(i) for i in selected_indices
        ] if selected_indices else None

        # Get selected tags
        selected_indices = self.tag_listbox.curselection()
        filters['tags'] = [
            self.tag_listbox.get(i) for i in selected_indices
        ] if selected_indices else None

        # Execute callback
        self.on_search(filters)

    def _clear_filters(self):
        """Clear all filter values."""
        self.text_entry.delete(0, tk.END)
        self.date_picker.clear()
        self.amount_min_entry.delete(0, tk.END)
        self.amount_max_entry.delete(0, tk.END)
        self.category_listbox.selection_clear(0, tk.END)
        self.tag_listbox.selection_clear(0, tk.END)

        # Execute search with empty filters
        if self.on_search:
            self.on_search({})

    def update_categories(self, categories: List[str]):
        """
        Update the available categories list.

        Args:
            categories: List of category names
        """
        self.available_categories = categories

        # Update listbox
        self.category_listbox.delete(0, tk.END)
        for category in categories:
            self.category_listbox.insert(tk.END, category)

    def update_tags(self, tags: List[str]):
        """
        Update the available tags list.

        Args:
            tags: List of tag names
        """
        self.available_tags = tags

        # Update listbox
        self.tag_listbox.delete(0, tk.END)
        for tag in tags:
            self.tag_listbox.insert(tk.END, tag)

    def set_search_text(self, text: str):
        """
        Set the search text.

        Args:
            text: Search text
        """
        self.text_entry.delete(0, tk.END)
        self.text_entry.insert(0, text)

    def set_date_range(self, from_date: Optional[date], to_date: Optional[date]):
        """
        Set the date range.

        Args:
            from_date: From date
            to_date: To date
        """
        self.date_picker.set_range(from_date, to_date)

    def get_active_filter_count(self) -> int:
        """
        Get the number of active filters.

        Returns:
            Count of non-empty filters
        """
        count = 0

        if self.text_entry.get().strip():
            count += 1

        date_from, date_to = self.date_picker.get_range()
        if date_from or date_to:
            count += 1

        if self.amount_min_entry.get().strip() or self.amount_max_entry.get().strip():
            count += 1

        if self.category_listbox.curselection():
            count += 1

        if self.tag_listbox.curselection():
            count += 1

        return count
