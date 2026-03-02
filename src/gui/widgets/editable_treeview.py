"""Editable Treeview widget for inline editing."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List

class EditableTreeview(ttk.Treeview):
    """
    Treeview with inline editing support for specific columns.

    Allows double-click editing of cells with dropdown or text entry.
    """

    @staticmethod
    def format_amount(amount: float) -> str:
        """
        Format amount with +/- sign and thousands separator.

        Args:
            amount: Amount value (positive for income, negative for expense)

        Returns:
            Formatted string (e.g., "+1,234.56€" or "-1,234.56€")
        """
        if amount >= 0:
            return f"+{amount:,.2f}€"
        else:
            return f"{amount:,.2f}€"  # Negative sign already present

    def __init__(self, parent, editable_columns: List[str] = None, **kwargs):
        """
        Initialize editable treeview.

        Args:
            parent: Parent widget
            editable_columns: List of column names that are editable
            **kwargs: Additional Treeview arguments
        """
        super().__init__(parent, **kwargs)
        self.editable_columns = editable_columns or []
        self.edit_callback = None
        self.entry_popup = None
        self.combobox_popup = None

        # Bind double-click for editing
        self.bind('<Double-Button-1>', self._on_double_click)

    def set_edit_callback(self, callback: Callable):
        """
        Set callback function for when cell is edited.

        Callback signature: callback(item_id, column, old_value, new_value)

        Args:
            callback: Function to call when cell is edited
        """
        self.edit_callback = callback

    def _on_double_click(self, event):
        """Handle double-click event for editing."""
        # Get clicked region
        region = self.identify_region(event.x, event.y)
        if region != 'cell':
            return

        # Get clicked column and item
        column = self.identify_column(event.x)
        item = self.identify_row(event.y)

        if not column or not item:
            return

        # Convert column ID to column name
        col_index = int(column.replace('#', '')) - 1
        columns = self['columns']
        if col_index < 0 or col_index >= len(columns):
            return

        col_name = columns[col_index]

        # Check if column is editable
        if col_name not in self.editable_columns:
            return

        # Get current value
        values = self.item(item)['values']
        if col_index >= len(values):
            return

        current_value = values[col_index]

        # Get cell bounding box
        x, y, width, height = self.bbox(item, column)

        # Show edit widget
        self._show_edit_widget(item, col_name, col_index, current_value, x, y, width, height)

    def _show_edit_widget(self, item_id, col_name, col_index, current_value, x, y, width, height):
        """
        Show edit widget (entry or combobox) for the cell.

        This is a basic text entry implementation. Override this method
        to provide custom edit widgets (e.g., dropdown for categories).
        """
        # Destroy existing edit widget if any
        if self.entry_popup:
            self.entry_popup.destroy()

        # Create entry widget
        self.entry_popup = tk.Entry(self, width=width // 7)
        self.entry_popup.insert(0, current_value)
        self.entry_popup.select_range(0, tk.END)
        self.entry_popup.focus()

        # Position the entry
        self.entry_popup.place(x=x, y=y, width=width, height=height)

        # Bind events
        self.entry_popup.bind('<Return>', lambda e: self._save_edit(item_id, col_name, col_index))
        self.entry_popup.bind('<Escape>', lambda e: self._cancel_edit())
        self.entry_popup.bind('<FocusOut>', lambda e: self._save_edit(item_id, col_name, col_index))

    def _save_edit(self, item_id, col_name, col_index):
        """Save the edited value."""
        if not self.entry_popup:
            return

        new_value = self.entry_popup.get()
        old_value = self.item(item_id)['values'][col_index]

        # Update treeview
        values = list(self.item(item_id)['values'])
        values[col_index] = new_value
        self.item(item_id, values=values)

        # Destroy edit widget
        self.entry_popup.destroy()
        self.entry_popup = None

        # Call callback if set and value changed
        if self.edit_callback and new_value != old_value:
            self.edit_callback(item_id, col_name, old_value, new_value)

    def _cancel_edit(self):
        """Cancel editing without saving."""
        if self.entry_popup:
            self.entry_popup.destroy()
            self.entry_popup = None

class CategoryEditableTreeview(EditableTreeview):
    """
    Specialized treeview for editing categories with dropdown.
    """

    def __init__(self, parent, categories: List[str], **kwargs):
        """
        Initialize category editable treeview.

        Args:
            parent: Parent widget
            categories: List of available categories
            **kwargs: Additional Treeview arguments
        """
        super().__init__(parent, editable_columns=['Categoría', 'Tags'], **kwargs)
        self.categories = categories
        self._tag_edit_request = None

    def set_categories(self, categories: List[str]):
        """Update the list of available categories."""
        self.categories = categories

    def _show_edit_widget(self, item_id, col_name, col_index, current_value, x, y, width, height):
        """Show dropdown for category selection or handle Tags editing."""
        # For Tags column, emit a custom event to let the parent window handle it
        if col_name == 'Tags':
            # Generate a custom event that the parent can catch
            self.event_generate('<<TagsEditRequested>>', when='tail')
            self._tag_edit_request = {
                'item_id': item_id,
                'col_name': col_name,
                'col_index': col_index
            }
            return

        # Destroy existing edit widget if any
        if self.combobox_popup:
            self.combobox_popup.destroy()

        # Create combobox widget
        self.combobox_popup = ttk.Combobox(
            self,
            values=self.categories,
            state='readonly',
            width=width // 7
        )
        self.combobox_popup.set(current_value)
        self.combobox_popup.focus()

        # Position the combobox
        self.combobox_popup.place(x=x, y=y, width=width, height=height)

        # Bind events
        self.combobox_popup.bind('<<ComboboxSelected>>', lambda e: self._save_combo_edit(item_id, col_name, col_index))
        self.combobox_popup.bind('<Escape>', lambda e: self._cancel_combo_edit())
        self.combobox_popup.bind('<FocusOut>', lambda e: self._cancel_combo_edit())

    def _save_combo_edit(self, item_id, col_name, col_index):
        """Save the combobox selection."""
        if not self.combobox_popup:
            return

        new_value = self.combobox_popup.get()
        old_value = self.item(item_id)['values'][col_index]

        # Update treeview
        values = list(self.item(item_id)['values'])
        values[col_index] = new_value
        self.item(item_id, values=values)

        # Destroy edit widget
        self.combobox_popup.destroy()
        self.combobox_popup = None

        # Call callback if set and value changed
        if self.edit_callback and new_value != old_value:
            self.edit_callback(item_id, col_name, old_value, new_value)

    def _cancel_combo_edit(self):
        """Cancel editing without saving."""
        if self.combobox_popup:
            self.combobox_popup.destroy()
            self.combobox_popup = None
