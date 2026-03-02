"""Settings dialog for configuring AI and display preferences."""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from models.user_preferences import UserPreferences
from services.model_downloader import ModelDownloader
from services.initial_training_service import InitialTrainingService
from services.ai_categorization_service import AICategorizationService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SettingsDialog:
    """
    Settings dialog for configuring application preferences.

    Sections:
    - AI Categorization
    - Display Settings
    - Training & Data
    """

    def __init__(
        self,
        parent,
        db_session,
        project_id: int,
        on_save: Optional[Callable] = None
    ):
        """
        Initialize settings dialog.

        Args:
            parent: Parent window
            db_session: Database session
            project_id: Current project ID
            on_save: Optional callback when settings are saved
        """
        self.parent = parent
        self.db_session = db_session
        self.project_id = project_id
        self.on_save = on_save
        self._should_recategorize_after_save = False

        # Load preferences
        self.preferences = UserPreferences.get_or_create(db_session, project_id)

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("600x700")
        self.dialog.resizable(False, False)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Setup UI
        self.setup_ui()

        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def setup_ui(self):
        """Setup the settings dialog UI."""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.ai_frame = ttk.Frame(notebook, padding=10)
        self.display_frame = ttk.Frame(notebook, padding=10)
        self.training_frame = ttk.Frame(notebook, padding=10)

        notebook.add(self.ai_frame, text="AI Categorization")
        notebook.add(self.display_frame, text="Display")
        notebook.add(self.training_frame, text="Training & Data")

        # Setup each tab
        self.setup_ai_tab()
        self.setup_display_tab()
        self.setup_training_tab()

        # Bottom buttons
        self.setup_buttons()

    def setup_ai_tab(self):
        """Setup AI categorization settings tab."""
        # Enable/Disable AI
        self.ai_enabled_var = tk.BooleanVar(value=self.preferences.enable_ai_categorization)
        ai_check = ttk.Checkbutton(
            self.ai_frame,
            text="Enable AI-powered categorization",
            variable=self.ai_enabled_var,
            command=self.on_ai_toggle
        )
        ai_check.pack(anchor=tk.W, pady=(0, 10))

        # Model status
        status_frame = ttk.LabelFrame(self.ai_frame, text="Model Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        downloader = ModelDownloader()
        model_info = downloader.get_model_info()

        if model_info['downloaded']:
            status_text = f"✓ Model downloaded ({model_info.get('actual_size_mb', model_info['size_mb'])}MB)"
            status_color = "green"
        else:
            status_text = f"⚠ Model not downloaded (~{model_info['size_mb']}MB required)"
            status_color = "orange"

        status_label = ttk.Label(status_frame, text=status_text, foreground=status_color)
        status_label.pack(anchor=tk.W)

        if not model_info['downloaded']:
            download_btn = ttk.Button(
                status_frame,
                text="Download Model",
                command=self.download_model
            )
            download_btn.pack(anchor=tk.W, pady=(5, 0))

        # Confidence threshold
        threshold_frame = ttk.LabelFrame(self.ai_frame, text="Confidence Threshold", padding=10)
        threshold_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            threshold_frame,
            text="Minimum confidence for auto-categorization:"
        ).pack(anchor=tk.W)

        self.threshold_var = tk.IntVar(value=self.preferences.ai_confidence_threshold_percentage)
        threshold_slider = ttk.Scale(
            threshold_frame,
            from_=70,
            to=95,
            orient=tk.HORIZONTAL,
            variable=self.threshold_var,
            command=self.on_threshold_change
        )
        threshold_slider.pack(fill=tk.X, pady=(5, 0))

        self.threshold_label = ttk.Label(threshold_frame, text=f"{self.threshold_var.get()}%")
        self.threshold_label.pack(anchor=tk.W)

        # Auto-learn checkbox
        self.auto_learn_var = tk.BooleanVar(value=self.preferences.auto_learn_from_edits)
        auto_learn_check = ttk.Checkbutton(
            self.ai_frame,
            text="Automatically learn from manual category corrections",
            variable=self.auto_learn_var
        )
        auto_learn_check.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(
            self.ai_frame,
            text="(If disabled, you'll be prompted before AI learns from each correction)",
            font=('TkDefaultFont', 9, 'italic'),
            foreground='gray'
        ).pack(anchor=tk.W)

    def setup_display_tab(self):
        """Setup display settings tab."""
        # Confidence indicators
        self.show_confidence_var = tk.BooleanVar(value=self.preferences.show_confidence_indicators)
        confidence_check = ttk.Checkbutton(
            self.display_frame,
            text="Show confidence indicators (🟢🟡⚪)",
            variable=self.show_confidence_var
        )
        confidence_check.pack(anchor=tk.W, pady=(0, 10))

        # Color-coded amounts
        self.color_amounts_var = tk.BooleanVar(value=self.preferences.color_code_amounts)
        color_check = ttk.Checkbutton(
            self.display_frame,
            text="Color-code amounts (green for income, red for expenses)",
            variable=self.color_amounts_var
        )
        color_check.pack(anchor=tk.W, pady=(0, 10))

        # Preview
        preview_frame = ttk.LabelFrame(self.display_frame, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        ttk.Label(preview_frame, text="Example transactions:").pack(anchor=tk.W, pady=(0, 5))

        # Example income
        income_frame = ttk.Frame(preview_frame)
        income_frame.pack(fill=tk.X, pady=2)
        ttk.Label(income_frame, text="Income:", width=15).pack(side=tk.LEFT)
        income_label = ttk.Label(
            income_frame,
            text="+1,234.56€",
            foreground='#059669' if self.color_amounts_var.get() else 'black'
        )
        income_label.pack(side=tk.LEFT)
        if self.show_confidence_var.get():
            ttk.Label(income_frame, text="🟢").pack(side=tk.LEFT, padx=(10, 0))

        # Example expense
        expense_frame = ttk.Frame(preview_frame)
        expense_frame.pack(fill=tk.X, pady=2)
        ttk.Label(expense_frame, text="Expense:", width=15).pack(side=tk.LEFT)
        expense_label = ttk.Label(
            expense_frame,
            text="-567.89€",
            foreground='#DC2626' if self.color_amounts_var.get() else 'black'
        )
        expense_label.pack(side=tk.LEFT)
        if self.show_confidence_var.get():
            ttk.Label(expense_frame, text="🟡").pack(side=tk.LEFT, padx=(10, 0))

    def setup_training_tab(self):
        """Setup training and data management tab."""
        # Training statistics
        stats_frame = ttk.LabelFrame(self.training_frame, text="Training Statistics", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        try:
            ai_service = AICategorizationService(self.db_session, self.project_id)
            training_stats = ai_service.get_training_stats()

            stats_text = f"Total examples: {training_stats['total_examples']}\n"
            stats_text += f"Categories covered: {len(training_stats['categories'])}\n"
            stats_text += f"Average usage: {training_stats['avg_usage']:.1f}"

            ttk.Label(stats_frame, text=stats_text).pack(anchor=tk.W)

        except Exception as e:
            logger.error(f"Failed to load training stats: {e}")
            ttk.Label(stats_frame, text="Training statistics unavailable").pack(anchor=tk.W)

        # Training readiness
        readiness_frame = ttk.LabelFrame(self.training_frame, text="Readiness", padding=10)
        readiness_frame.pack(fill=tk.X, pady=(0, 10))

        try:
            initial_training = InitialTrainingService(self.db_session, self.project_id)
            readiness = initial_training.get_training_readiness()

            readiness_colors = {
                'excellent': 'green',
                'good': 'green',
                'fair': 'orange',
                'potential': 'orange',
                'none': 'red'
            }

            color = readiness_colors.get(readiness['readiness'], 'black')
            ttk.Label(
                readiness_frame,
                text=readiness['message'],
                foreground=color
            ).pack(anchor=tk.W)

            details = f"\nManual edits available: {readiness['manual_edits_available']}\n"
            details += f"Rules available: {readiness['rules_available']}\n"
            details += f"Current examples: {readiness['current_examples']}"

            ttk.Label(readiness_frame, text=details, font=('TkDefaultFont', 9)).pack(anchor=tk.W, pady=(5, 0))

        except Exception as e:
            logger.error(f"Failed to check readiness: {e}")
            ttk.Label(readiness_frame, text="Readiness check unavailable").pack(anchor=tk.W)

        # Actions
        actions_frame = ttk.LabelFrame(self.training_frame, text="Actions", padding=10)
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            actions_frame,
            text="Build Initial Training from Existing Data",
            command=self.build_initial_training
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            actions_frame,
            text="Clear All Training Data",
            command=self.clear_training_data
        ).pack(fill=tk.X, pady=2)

    def setup_buttons(self):
        """Setup bottom action buttons."""
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="Save",
            command=self.save_settings
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT)

    def on_ai_toggle(self):
        """Handle AI enable/disable toggle."""
        if not self.ai_enabled_var.get():
            response = messagebox.askyesno(
                "Disable AI",
                "Disabling AI will use only keyword-based categorization.\n\n"
                "Your training data will be preserved.\n\n"
                "Continue?",
                parent=self.dialog
            )
            if not response:
                self.ai_enabled_var.set(True)

    def on_threshold_change(self, value):
        """Handle threshold slider change."""
        self.threshold_label.config(text=f"{int(float(value))}%")

    def download_model(self):
        """Download the AI model."""
        downloader = ModelDownloader()

        # Create progress window
        progress_window = tk.Toplevel(self.dialog)
        progress_window.title("Downloading Model")
        progress_window.geometry("400x100")
        progress_window.transient(self.dialog)
        progress_window.grab_set()

        progress_label = ttk.Label(progress_window, text="Downloading...")
        progress_label.pack(pady=20)

        def update_progress(message):
            progress_label.config(text=message)
            progress_window.update()

        # Download in background
        success = downloader.download_model(progress_callback=update_progress)

        progress_window.destroy()

        if success:
            messagebox.showinfo(
                "Download Complete",
                "AI model downloaded successfully!\n\n"
                "You can now use AI-powered categorization.",
                parent=self.dialog
            )
            # Refresh dialog
            self.dialog.destroy()
            SettingsDialog(self.parent, self.db_session, self.project_id, self.on_save)
        else:
            messagebox.showerror(
                "Download Failed",
                "Failed to download AI model.\n\n"
                "Please check your internet connection and try again.",
                parent=self.dialog
            )

    def build_initial_training(self):
        """Build initial training from existing data and recategorize all transactions."""
        response = messagebox.askyesno(
            "Build Initial Training",
            "This will create AI training examples from:\n"
            "• Manually edited transactions\n"
            "• Existing categorization rules\n"
            "• Representative transactions\n\n"
            "After training, all transactions will be recategorized using the new training data.\n\n"
            "This may take several minutes.\n\n"
            "Continue?",
            parent=self.dialog
        )

        if not response:
            return

        # Create progress window
        progress_window = tk.Toplevel(self.dialog)
        progress_window.title("Building Training Data")
        progress_window.geometry("400x100")
        progress_window.transient(self.dialog)
        progress_window.grab_set()

        progress_label = ttk.Label(progress_window, text="Initializing...")
        progress_label.pack(pady=20)

        def update_progress(message, current, total):
            progress_label.config(text=f"{message} ({current}/{total})")
            progress_window.update()

        try:
            initial_training = InitialTrainingService(self.db_session, self.project_id)
            stats = initial_training.build_initial_training(progress_callback=update_progress)

            progress_window.destroy()

            messagebox.showinfo(
                "Training Complete",
                f"Successfully built initial training data!\n\n"
                f"Total examples: {stats['total_examples']}\n"
                f"• From manual edits: {stats['manual_edits']}\n"
                f"• From rules: {stats['category_rules']}\n"
                f"• Representatives: {stats['representatives']}\n\n"
                f"Categories covered: {stats['categories_covered']}\n\n"
                f"Now recategorizing all transactions...",
                parent=self.dialog
            )

            # Refresh training tab
            for widget in self.training_frame.winfo_children():
                widget.destroy()
            self.setup_training_tab()

            # Trigger recategorization via callback if available
            if self.on_save:
                # Mark that we should recategorize
                self._should_recategorize_after_save = True

        except Exception as e:
            progress_window.destroy()
            logger.error(f"Failed to build training: {e}", exc_info=True)
            messagebox.showerror(
                "Training Failed",
                f"Failed to build training data:\n\n{str(e)}",
                parent=self.dialog
            )

    def clear_training_data(self):
        """Clear all training data."""
        response = messagebox.askyesno(
            "Clear Training Data",
            "⚠ WARNING ⚠\n\n"
            "This will delete ALL AI training examples.\n"
            "This action cannot be undone.\n\n"
            "Continue?",
            parent=self.dialog,
            icon='warning'
        )

        if not response:
            return

        try:
            from models import CategoryTrainingExample, TransactionEmbedding

            # Delete all training examples
            self.db_session.query(CategoryTrainingExample).filter(
                CategoryTrainingExample.project_id == self.project_id
            ).delete()

            # Delete all embedding cache
            self.db_session.query(TransactionEmbedding).filter(
                TransactionEmbedding.project_id == self.project_id
            ).delete()

            self.db_session.commit()

            messagebox.showinfo(
                "Training Data Cleared",
                "All training data has been deleted.",
                parent=self.dialog
            )

            # Refresh training tab
            for widget in self.training_frame.winfo_children():
                widget.destroy()
            self.setup_training_tab()

        except Exception as e:
            logger.error(f"Failed to clear training data: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"Failed to clear training data:\n\n{str(e)}",
                parent=self.dialog
            )

    def save_settings(self):
        """Save settings and close dialog. Trigger recategorization if needed."""
        try:
            # Update preferences
            self.preferences.enable_ai_categorization = self.ai_enabled_var.get()
            self.preferences.ai_confidence_threshold = self.threshold_var.get() / 100.0
            self.preferences.auto_learn_from_edits = self.auto_learn_var.get()
            self.preferences.show_confidence_indicators = self.show_confidence_var.get()
            self.preferences.color_code_amounts = self.color_amounts_var.get()

            # Save to database
            self.db_session.commit()

            logger.info("Settings saved successfully")

            messagebox.showinfo(
                "Settings Saved",
                "Settings have been saved successfully!",
                parent=self.dialog
            )

            # Close dialog first
            self.dialog.destroy()

            # Call callback if provided
            if self.on_save:
                self.on_save()

            # Trigger recategorization if needed (after dialog is closed)
            if self._should_recategorize_after_save:
                self._should_recategorize_after_save = False
                # Call recategorization on parent if available
                if hasattr(self.parent, 'recategorize_all_transactions'):
                    self.parent.recategorize_all_transactions()
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"Error saving settings:\n\n{str(e)}",
                parent=self.dialog
            )

        except Exception as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"Failed to save settings:\n\n{str(e)}",
                parent=self.dialog
            )
