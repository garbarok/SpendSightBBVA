"""Project selector startup screen."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional
from models.database import DatabaseManager
from models.project import Project
from services.project_manager import ProjectManager
from services.migration_service import MigrationService
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ProjectSelector:
    """Startup screen for selecting or creating projects."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize project selector.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.project_manager = ProjectManager(db_manager)
        self.migration_service = MigrationService(db_manager)
        self.selected_project = None

        # Create window
        self.root = tk.Tk()
        self.root.title("SpendSight BBVA - Select Project")
        self.root.geometry("600x400")

        self.setup_gui()
        self.refresh_project_list()

    def setup_gui(self):
        """Setup the GUI components."""
        # Title
        title = ttk.Label(
            self.root,
            text="Welcome to SpendSight BBVA",
            font=("TkDefaultFont", 16, "bold")
        )
        title.pack(pady=20)

        # Project list frame
        list_frame = ttk.LabelFrame(self.root, text="Recent Projects", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Project listbox with scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.project_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("TkDefaultFont", 10)
        )
        scrollbar.config(command=self.project_listbox.yview)

        self.project_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to open
        self.project_listbox.bind('<Double-Button-1>', lambda e: self.open_selected_project())

        # Buttons frame
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(
            buttons_frame,
            text="Open Project",
            command=self.open_selected_project
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_frame,
            text="New Project",
            command=self.create_new_project
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_frame,
            text="Import from Excel",
            command=self.import_from_excel
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_frame,
            text="Delete Project",
            command=self.delete_project
        ).pack(side=tk.LEFT, padx=5)

    def refresh_project_list(self):
        """Refresh the list of projects."""
        self.project_listbox.delete(0, tk.END)
        self.projects = self.project_manager.list_projects()

        for project in self.projects:
            stats = self.project_manager.get_project_stats(project.id)
            display_text = f"{project.name} ({stats['transaction_count']} transactions)"
            self.project_listbox.insert(tk.END, display_text)

        if not self.projects:
            self.project_listbox.insert(tk.END, "No projects yet. Create one or import from Excel!")

    def open_selected_project(self):
        """Open the selected project."""
        selection = self.project_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a project first")
            return

        if not self.projects:
            return

        self.selected_project = self.projects[selection[0]]
        logger.info(f"Opening project: {self.selected_project.name}")
        self.root.destroy()

    def create_new_project(self):
        """Create a new project."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Project")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Name field
        ttk.Label(dialog, text="Project Name:").pack(pady=10)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        name_entry.focus()

        # Description field
        ttk.Label(dialog, text="Description (optional):").pack(pady=10)
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(dialog, textvariable=desc_var, width=40)
        desc_entry.pack(pady=5)

        def create():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please enter a project name")
                return

            try:
                project = self.project_manager.create_project(
                    name=name,
                    description=desc_var.get().strip() or None
                )
                logger.info(f"Created project: {project.name}")
                messagebox.showinfo("Success", f"Project '{name}' created!")
                dialog.destroy()
                self.refresh_project_list()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Create", command=create).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Enter key creates project
        dialog.bind('<Return>', lambda e: create())

    def import_from_excel(self):
        """Import Excel files into a new project."""
        # Select Excel files
        file_paths = filedialog.askopenfilenames(
            title="Select BBVA Excel Files",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not file_paths:
            return

        # Ask for project name
        dialog = tk.Toplevel(self.root)
        dialog.title("Import to New Project")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Importing {len(file_paths)} file(s)").pack(pady=10)
        ttk.Label(dialog, text="Project Name:").pack(pady=5)

        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        name_entry.focus()

        def do_import():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please enter a project name")
                return

            try:
                # Create project
                project = self.project_manager.create_project(name=name)

                # Import files
                logger.info(f"Importing {len(file_paths)} files to project {project.name}")
                stats = self.migration_service.import_excel_to_project(
                    project_id=project.id,
                    file_paths=list(file_paths),
                    skip_duplicates=True
                )

                dialog.destroy()

                # Show results
                msg = f"Import complete!\n\n"
                msg += f"Imported: {stats['imported']} transactions\n"
                msg += f"Skipped (duplicates): {stats['skipped']}\n"
                if stats['errors']:
                    msg += f"\nErrors:\n" + "\n".join(stats['errors'])

                messagebox.showinfo("Import Complete", msg)
                self.refresh_project_list()

            except ValueError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                logger.error(f"Import error: {e}", exc_info=True)
                messagebox.showerror("Error", f"Import failed: {str(e)}")

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Import", command=do_import).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        dialog.bind('<Return>', lambda e: do_import())

    def delete_project(self):
        """Delete the selected project."""
        selection = self.project_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a project to delete")
            return

        if not self.projects:
            return

        project = self.projects[selection[0]]

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete project '{project.name}'?\n\n"
            "This will delete all transactions and cannot be undone."
        )

        if confirm:
            self.project_manager.delete_project(project.id)
            logger.info(f"Deleted project: {project.name}")
            messagebox.showinfo("Success", f"Project '{project.name}' deleted")
            self.refresh_project_list()

    def run(self) -> Optional[Project]:
        """
        Run the project selector and return selected project.

        Returns:
            Selected project or None if cancelled
        """
        self.root.mainloop()
        return self.selected_project
