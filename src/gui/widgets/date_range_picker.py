"""Date range picker widget for filtering transactions."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date
from typing import Optional, Callable, Tuple
from tkcalendar import DateEntry


class DateRangePicker(ttk.Frame):
    """
    Widget for selecting a date range (from/to dates).

    Provides two calendar date pickers with clear functionality.
    """

    def __init__(
        self,
        parent,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        on_change: Optional[Callable[[Optional[date], Optional[date]], None]] = None,
        **kwargs
    ):
        """
        Initialize date range picker.

        Args:
            parent: Parent widget
            from_date: Initial from date
            to_date: Initial to date
            on_change: Callback function called when dates change
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.on_change = on_change

        self._create_widgets()

        if from_date:
            self.from_picker.set_date(from_date)
        if to_date:
            self.to_picker.set_date(to_date)

    def _create_widgets(self):
        """Create the widget components."""
        # From date section
        from_frame = ttk.Frame(self)
        from_frame.pack(fill=tk.X, pady=5)

        from_label = ttk.Label(from_frame, text="From:", width=8)
        from_label.pack(side=tk.LEFT)

        self.from_picker = DateEntry(
            from_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.from_picker.pack(side=tk.LEFT, padx=(0, 5))
        self.from_picker.bind('<<DateEntrySelected>>', self._on_date_changed)

        from_clear = ttk.Button(
            from_frame,
            text="Clear",
            command=self._clear_from,
            width=6
        )
        from_clear.pack(side=tk.LEFT)

        # To date section
        to_frame = ttk.Frame(self)
        to_frame.pack(fill=tk.X, pady=5)

        to_label = ttk.Label(to_frame, text="To:", width=8)
        to_label.pack(side=tk.LEFT)

        self.to_picker = DateEntry(
            to_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.to_picker.pack(side=tk.LEFT, padx=(0, 5))
        self.to_picker.bind('<<DateEntrySelected>>', self._on_date_changed)

        to_clear = ttk.Button(
            to_frame,
            text="Clear",
            command=self._clear_to,
            width=6
        )
        to_clear.pack(side=tk.LEFT)

        # State tracking
        self.from_enabled = True
        self.to_enabled = True

    def _on_date_changed(self, event=None):
        """Handle date selection change."""
        if self.on_change:
            from_date, to_date = self.get_range()
            self.on_change(from_date, to_date)

    def _clear_from(self):
        """Clear the from date."""
        self.from_enabled = False
        self.from_picker.set_date(datetime.now().date())
        self._on_date_changed()

    def _clear_to(self):
        """Clear the to date."""
        self.to_enabled = False
        self.to_picker.set_date(datetime.now().date())
        self._on_date_changed()

    def get_range(self) -> Tuple[Optional[date], Optional[date]]:
        """
        Get the selected date range.

        Returns:
            Tuple of (from_date, to_date) where either can be None if cleared
        """
        from_date = self.from_picker.get_date() if self.from_enabled else None
        to_date = self.to_picker.get_date() if self.to_enabled else None

        return from_date, to_date

    def set_range(self, from_date: Optional[date], to_date: Optional[date]):
        """
        Set the date range.

        Args:
            from_date: From date or None
            to_date: To date or None
        """
        if from_date:
            self.from_picker.set_date(from_date)
            self.from_enabled = True
        else:
            self.from_enabled = False

        if to_date:
            self.to_picker.set_date(to_date)
            self.to_enabled = True
        else:
            self.to_enabled = False

    def clear(self):
        """Clear both dates."""
        self.from_enabled = False
        self.to_enabled = False
        self.from_picker.set_date(datetime.now().date())
        self.to_picker.set_date(datetime.now().date())

        if self.on_change:
            self.on_change(None, None)


class SimpleDateRangePicker(ttk.Frame):
    """
    Simplified date range picker using Entry widgets instead of calendar.

    Falls back to this if tkcalendar is not available.
    """

    def __init__(
        self,
        parent,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        on_change: Optional[Callable[[Optional[date], Optional[date]], None]] = None,
        **kwargs
    ):
        """
        Initialize simple date range picker.

        Args:
            parent: Parent widget
            from_date: Initial from date
            to_date: Initial to date
            on_change: Callback function called when dates change
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.on_change = on_change

        self._create_widgets()

        if from_date:
            self.from_entry.insert(0, from_date.strftime('%Y-%m-%d'))
        if to_date:
            self.to_entry.insert(0, to_date.strftime('%Y-%m-%d'))

    def _create_widgets(self):
        """Create the widget components."""
        # From date section
        from_frame = ttk.Frame(self)
        from_frame.pack(fill=tk.X, pady=5)

        from_label = ttk.Label(from_frame, text="From:", width=8)
        from_label.pack(side=tk.LEFT)

        self.from_entry = ttk.Entry(from_frame, width=15)
        self.from_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.from_entry.insert(0, "YYYY-MM-DD")

        from_clear = ttk.Button(
            from_frame,
            text="Clear",
            command=lambda: self.from_entry.delete(0, tk.END),
            width=6
        )
        from_clear.pack(side=tk.LEFT)

        # To date section
        to_frame = ttk.Frame(self)
        to_frame.pack(fill=tk.X, pady=5)

        to_label = ttk.Label(to_frame, text="To:", width=8)
        to_label.pack(side=tk.LEFT)

        self.to_entry = ttk.Entry(to_frame, width=15)
        self.to_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.to_entry.insert(0, "YYYY-MM-DD")

        to_clear = ttk.Button(
            to_frame,
            text="Clear",
            command=lambda: self.to_entry.delete(0, tk.END),
            width=6
        )
        to_clear.pack(side=tk.LEFT)

    def get_range(self) -> Tuple[Optional[date], Optional[date]]:
        """
        Get the selected date range.

        Returns:
            Tuple of (from_date, to_date) where either can be None if invalid
        """
        from_date = None
        to_date = None

        try:
            from_str = self.from_entry.get().strip()
            if from_str and from_str != "YYYY-MM-DD":
                from_date = datetime.strptime(from_str, '%Y-%m-%d').date()
        except ValueError:
            pass

        try:
            to_str = self.to_entry.get().strip()
            if to_str and to_str != "YYYY-MM-DD":
                to_date = datetime.strptime(to_str, '%Y-%m-%d').date()
        except ValueError:
            pass

        return from_date, to_date

    def clear(self):
        """Clear both dates."""
        self.from_entry.delete(0, tk.END)
        self.to_entry.delete(0, tk.END)

        if self.on_change:
            self.on_change(None, None)
