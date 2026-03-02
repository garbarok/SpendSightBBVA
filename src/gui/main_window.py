"""Main window for the Bank Transaction Analyzer with database persistence."""
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
import os
import pandas as pd

from models.database import DatabaseManager
from models.project import Project
from models.transaction import Transaction
from services.project_manager import ProjectManager
from services.migration_service import MigrationService
from services import CategorizationService, RecurringDetector, SearchService
from utils.data_processor import DataProcessor, DataProcessingError
from utils.validators import FileValidationError
from utils.categories import get_all_categories
from charts.chart_manager import ChartManager
from utils.logger import setup_logger
from gui.widgets.editable_treeview import CategoryEditableTreeview
from gui.search_panel import SearchPanel
from gui.widgets.tag_input import TagSelectorDialog

logger = setup_logger(__name__)

class MainWindow:
    def __init__(self, db_manager: DatabaseManager, project: Project):
        """
        Initialize main window with database integration.

        Args:
            db_manager: Database manager instance
            project: Active project
        """
        self.db_manager = db_manager
        self.project = project
        self.project_manager = ProjectManager(db_manager)
        self.migration_service = MigrationService(db_manager)

        # Phase 2 services
        session = db_manager.get_session()
        self.categorization_service = CategorizationService(session, project.id)
        self.recurring_detector = RecurringDetector(session, project.id)
        self.search_service = SearchService(session, project.id)
        session.close()

        self.root = tk.Tk()
        self.setup_gui()
        self.df = None  # Pandas DataFrame for current view
        self.load_project_data()

    def setup_gui(self):
        self.root.title(f"Bank Transaction Analyzer - {self.project.name}")
        self.root.geometry("1200x800")

        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create controls frame
        self.controls_frame = ttk.Frame(self.main_frame)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)

        # Project info frame
        info_frame = ttk.LabelFrame(self.controls_frame, text="Project Info", padding="5")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        stats = self.project_manager.get_project_stats(self.project.id)
        info_text = f"Project: {self.project.name} | Transactions: {stats['transaction_count']}"
        if stats['earliest_date']:
            info_text += f" | Period: {stats['earliest_date'].strftime('%Y-%m-%d')} to {stats['latest_date'].strftime('%Y-%m-%d')}"

        ttk.Label(info_frame, text=info_text).pack()

        # Create buttons frame
        buttons_frame = ttk.Frame(self.controls_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        # Import file button
        ttk.Button(buttons_frame, text="Import Excel File", command=self.import_file).pack(side=tk.LEFT, padx=5)

        # Add month filter
        ttk.Label(buttons_frame, text="Filter by Month:").pack(side=tk.LEFT, padx=(20, 5))
        self.month_var = tk.StringVar(value="All Months")
        self.month_filter = ttk.Combobox(buttons_frame, textvariable=self.month_var, state="readonly")
        self.month_filter.pack(side=tk.LEFT, padx=5)
        self.month_filter.bind('<<ComboboxSelected>>', lambda e: self.update_filtered_view())

        # Download button
        ttk.Button(buttons_frame, text="Download Results", command=self.download_results).pack(side=tk.LEFT, padx=20)

        # Settings button (AI Configuration)
        ttk.Button(buttons_frame, text="⚙️ AI Settings", command=self.open_settings).pack(side=tk.RIGHT, padx=5)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create frames for each tab
        self.transactions_frame = ttk.Frame(self.notebook)
        self.grouped_frame = ttk.Frame(self.notebook)
        self.search_frame = ttk.Frame(self.notebook)
        self.recurring_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.transactions_frame, text="All Transactions")
        self.notebook.add(self.grouped_frame, text="Grouped by Category")
        self.notebook.add(self.search_frame, text="🔍 Search")
        self.notebook.add(self.recurring_frame, text="🔁 Recurring")

        # Setup transaction view with editable treeview
        self.setup_all_transactions_tab()
        self.setup_grouped_tab()
        self.setup_search_tab()
        self.setup_recurring_tab()

        # Create summary frame
        self.summary_frame = ttk.Frame(self.main_frame)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=5)

        self.summary_text = tk.Text(self.summary_frame, height=3, width=50)
        self.summary_text.pack(side=tk.LEFT, padx=5)

        # Initialize chart manager
        self.chart_manager = ChartManager(self.notebook)

    def setup_all_transactions_tab(self):
        """Setup the all transactions tab with editable category column."""
        # Create editable Treeview with confidence and method columns
        columns = ("Fecha", "Concepto", "Movimiento", "Importe", "Categoría", "Confianza", "Método", "Tags", "Source")
        self.tree = CategoryEditableTreeview(
            self.transactions_frame,
            categories=get_all_categories(),
            columns=columns,
            show="headings"
        )

        # Set edit callback
        self.tree.set_edit_callback(self.on_category_edited)

        # Add column headings (with edit hints)
        for col in columns:
            # Add pencil icon to editable columns
            display_text = col
            if col == "Categoría":
                display_text = f"✏️ {col} (doble clic para editar)"
            elif col == "Tags":
                display_text = f"✏️ {col} (doble clic para editar)"

            self.tree.heading(col, text=display_text, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=150)

        # Adjust column widths
        self.tree.column("Concepto", width=300)
        self.tree.column("Categoría", width=250)  # Make wider for edit hint
        self.tree.column("Confianza", width=80)  # Confidence indicator column
        self.tree.column("Método", width=80)  # Categorization method column
        self.tree.column("Tags", width=200)  # Make wider for edit hint
        self.tree.column("Importe", width=120)

        # Configure color tags for amounts
        self.tree.tag_configure('income', foreground='#059669')  # Green for income
        self.tree.tag_configure('expense', foreground='#DC2626')  # Red for expenses
        self.tree.tag_configure('uncertain', background='#FEF3C7')  # Yellow background for medium confidence

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.transactions_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack elements
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind custom event for Tags editing (generated by CategoryEditableTreeview)
        self.tree.bind('<<TagsEditRequested>>', self._on_tags_edit_requested)

        # Add legend for categorization methods
        legend_frame = ttk.Frame(self.transactions_frame)
        legend_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Label(legend_frame, text="Método:", font=('', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(legend_frame, text="🤖 AI", font=('', 9)).pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="📋 Regla", font=('', 9)).pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="🔑 Palabra clave", font=('', 9)).pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="✋ Manual", font=('', 9)).pack(side=tk.LEFT, padx=5)

        ttk.Label(legend_frame, text="  |  Confianza:", font=('', 9, 'bold')).pack(side=tk.LEFT, padx=(20, 10))
        ttk.Label(legend_frame, text="🟢 Alta (≥85%)", font=('', 9)).pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="🟡 Media (70-85%)", font=('', 9)).pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="⚪ Baja/Sin IA", font=('', 9)).pack(side=tk.LEFT, padx=5)

    def on_category_edited(self, item_id, column, old_value, new_value):
        """
        Handle category edit event.

        Args:
            item_id: Treeview item ID
            column: Column name
            old_value: Old category value
            new_value: New category value
        """
        if column != "Categoría" or old_value == new_value:
            return

        # Get transaction data from item
        values = self.tree.item(item_id)['values']
        fecha = pd.to_datetime(values[0])
        concepto = values[1]
        importe = float(values[3].replace("€", "").strip())

        logger.info(f"Category changed: {concepto} | {old_value} -> {new_value}")

        # Update in database
        session = self.db_manager.get_session()
        try:
            # Find transaction
            transaction = session.query(Transaction).filter_by(
                project_id=self.project.id,
                fecha=fecha,
                concepto=concepto,
                importe=importe
            ).first()

            if transaction:
                # Save original category if first edit
                if not transaction.is_manually_edited:
                    transaction.categoria_original = old_value

                # Update category with manual categorization metadata
                transaction.set_manual_categorization(new_value)
                session.commit()

                logger.info(f"Updated transaction {transaction.id} category to {new_value}")

                # 🤖 Phase 2: Ask if user wants to create a rule
                self.ask_create_rule(session, transaction, new_value)

                # 🤖 Phase 5: Ask if user wants AI to learn from this correction
                self.ask_ai_learning(session, transaction, new_value)

                # Auto-save indicator
                self.show_save_indicator()

                # Refresh views
                self.load_project_data()
            else:
                logger.warning(f"Transaction not found for update: {concepto}")

        except Exception as e:
            logger.error(f"Error updating category: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to save category change: {str(e)}")
            session.rollback()
        finally:
            session.close()

    def ask_create_rule(self, session, transaction, new_category):
        """
        Ask user if they want to create a categorization rule.

        Args:
            session: Database session
            transaction: Transaction object
            new_category: New category assigned
        """
        # Extract pattern from concept
        pattern = self.categorization_service._extract_pattern(transaction.concepto)

        if not pattern:
            return

        # Ask user
        response = messagebox.askyesno(
            "Crear regla de categorización",
            f"¿Quieres crear una regla para categorizar automáticamente "
            f"transacciones con '{pattern}' como '{new_category}'?\n\n"
            f"Las futuras transacciones similares se categorizarán automáticamente.",
            icon='question'
        )

        if response:
            # Reinitialize service with current session
            cat_service = CategorizationService(session, self.project.id)
            rule = cat_service.create_rule_from_edit(transaction, new_category)

            if rule:
                messagebox.showinfo(
                    "Regla creada",
                    f"✓ Regla creada: '{rule.pattern}' → '{rule.category}'\n\n"
                    f"Las transacciones futuras que contengan '{rule.pattern}' "
                    f"se categorizarán automáticamente."
                )
                logger.info(f"Created categorization rule: {rule.pattern} -> {rule.category}")

                # Auto-recategorize all transactions with the new rule
                self.recategorize_all_transactions()
            else:
                messagebox.showinfo(
                    "Regla existente",
                    f"Ya existe una regla para '{pattern}' → '{new_category}'"
                )

    def ask_ai_learning(self, session, transaction, new_category):
        """
        Ask user if AI should learn from this category correction.

        Args:
            session: Database session
            transaction: Transaction object
            new_category: New category assigned
        """
        try:
            # Check if AI service is available
            from services.ai_categorization_service import AICategorizationService

            # Ask user
            response = messagebox.askyesno(
                "Aprendizaje de IA",
                f"¿Quieres que el sistema de IA aprenda de esta corrección?\n\n"
                f"Transacción: {transaction.concepto[:50]}...\n"
                f"Nueva categoría: {new_category}\n\n"
                f"El sistema mejorará la precisión para transacciones similares.",
                icon='question'
            )

            if response:
                # Initialize AI service
                ai_service = AICategorizationService(session, self.project.id)

                # Learn from correction
                example = ai_service.learn_from_correction(
                    transaction,
                    new_category,
                    source='manual'
                )

                if example:
                    messagebox.showinfo(
                        "IA actualizada",
                        f"✓ Sistema de IA actualizado\n\n"
                        f"La IA ahora reconocerá transacciones similares a:\n"
                        f"'{transaction.concepto[:60]}...'\n\n"
                        f"como '{new_category}'"
                    )
                    logger.info(f"AI learned from correction: {transaction.concepto} -> {new_category}")

                    # Auto-recategorize all transactions with the new training
                    self.recategorize_all_transactions()
                else:
                    logger.debug("AI already has similar training example")

        except ImportError:
            logger.debug("AI categorization not available - dependencies not installed")
        except Exception as e:
            logger.error(f"Error in AI learning: {e}", exc_info=True)
            # Don't show error to user - learning is optional

    def _on_tags_edit_requested(self, event):
        """Handle custom event from CategoryEditableTreeview when Tags column is double-clicked."""
        # Get the tag edit request info
        if not hasattr(self.tree, '_tag_edit_request') or not self.tree._tag_edit_request:
            return

        request = self.tree._tag_edit_request
        item_id = request['item_id']

        # Get the values from the item
        values = self.tree.item(item_id)['values']

        # Get transaction data (adjusted for new column layout)
        fecha = pd.to_datetime(values[0])
        concepto = values[1]
        importe = float(values[3].replace("€", "").strip())

        # Get transaction from database
        session = self.db_manager.get_session()
        try:
            transaction = session.query(Transaction).filter_by(
                project_id=self.project.id,
                fecha=fecha,
                concepto=concepto,
                importe=importe
            ).first()

            if not transaction:
                logger.warning(f"Transaction not found: {concepto}")
                return

            # Get all available tags in project
            search_service = SearchService(session, self.project.id)
            available_tags = search_service.get_all_tags()

            # Show tag selector dialog
            dialog = TagSelectorDialog(
                self.root,
                title="Editar Tags",
                available_tags=available_tags,
                selected_tags=transaction.get_tags()
            )

            new_tags = dialog.show()

            if new_tags is not None:
                # Update tags
                transaction.set_tags(new_tags)
                session.commit()

                logger.info(f"Updated tags for {concepto}: {new_tags}")

                # Show confirmation
                self.show_save_indicator()

                # Refresh view
                self.load_project_data()

        except Exception as e:
            logger.error(f"Error updating tags: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error al actualizar tags: {str(e)}")
            session.rollback()
        finally:
            session.close()

    def show_save_indicator(self):
        """Show a brief 'Saved' indicator."""
        # Create temporary label
        indicator = ttk.Label(self.summary_frame, text="✓ Saved", foreground="green")
        indicator.pack(side=tk.RIGHT, padx=10)

        # Remove after 2 seconds
        self.root.after(2000, indicator.destroy)

    def recategorize_all_transactions(self):
        """
        Recategorize all transactions using current rules and AI training.

        Shows progress dialog during operation and refreshes UI when complete.
        Displays statistics about how many transactions were recategorized.
        """
        # Count total transactions
        session = self.db_manager.get_session()
        try:
            total_count = session.query(Transaction).filter_by(
                project_id=self.project.id
            ).count()

            if total_count == 0:
                session.close()
                messagebox.showinfo(
                    "No Data",
                    "No transactions to recategorize."
                )
                return

            # Create progress window
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Recategorizing Transactions")
            progress_window.geometry("450x120")
            progress_window.transient(self.root)
            progress_window.grab_set()

            progress_label = ttk.Label(progress_window, text="Initializing...", font=('', 10))
            progress_label.pack(pady=15)

            progress_bar = ttk.Progressbar(
                progress_window,
                length=400,
                mode='determinate',
                maximum=total_count
            )
            progress_bar.pack(pady=10, padx=25)

            status_label = ttk.Label(progress_window, text=f"0/{total_count}", font=('', 9))
            status_label.pack()

            # Get all transactions
            transactions = session.query(Transaction).filter_by(
                project_id=self.project.id
            ).order_by(Transaction.id).all()

            # Track statistics
            recategorized_count = 0
            unchanged_count = 0
            errors = []

            # Reinitialize categorization service for each batch
            cat_service = CategorizationService(session, self.project.id)

            # Process transactions in batches
            batch_size = 50
            for i, transaction in enumerate(transactions):
                try:
                    # Get old category
                    old_category = transaction.categoria
                    old_method = transaction.categorization_method
                    old_confidence = transaction.ai_confidence

                    # Recategorize
                    result = cat_service.categorize_transaction(
                        transaction.concepto,
                        transaction.movimiento
                    )

                    new_category = result['category']
                    new_method = result['method']
                    new_confidence = result['confidence']

                    # Update transaction
                    transaction.categoria = new_category
                    transaction.categorization_method = new_method
                    transaction.ai_confidence = new_confidence if new_confidence > 0 else None

                    # Count changes
                    if old_category != new_category or old_method != new_method:
                        recategorized_count += 1
                    else:
                        unchanged_count += 1

                    # Commit in batches
                    if (i + 1) % batch_size == 0:
                        try:
                            session.commit()
                            logger.debug(f"Committed batch: {i + 1}/{total_count}")
                        except Exception as e:
                            logger.error(f"Error committing batch: {e}")
                            session.rollback()
                            errors.append(f"Batch error at transaction {i + 1}: {str(e)}")
                            # Continue with next batch
                            continue

                    # Update progress
                    progress_bar['value'] = i + 1
                    status_label.config(text=f"{i + 1}/{total_count}")
                    progress_label.config(
                        text=f"Recategorizing transactions... ({recategorized_count} changed)"
                    )
                    progress_window.update()

                except Exception as e:
                    logger.error(f"Error recategorizing transaction {transaction.id}: {e}")
                    errors.append(f"Transaction {transaction.id}: {str(e)}")
                    unchanged_count += 1

            # Final commit
            try:
                session.commit()
                logger.info(f"Recategorization complete: {recategorized_count} changed, {unchanged_count} unchanged")
            except Exception as e:
                logger.error(f"Error in final commit: {e}")
                session.rollback()
                errors.append(f"Final commit error: {str(e)}")

            progress_window.destroy()

            # Show results
            if errors:
                error_msg = "\n".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    error_msg += f"\n... and {len(errors) - 5} more errors"
                messagebox.showwarning(
                    "Recategorization Complete (With Errors)",
                    f"Recategorization complete!\n\n"
                    f"Changed: {recategorized_count} transactions\n"
                    f"Unchanged: {unchanged_count} transactions\n\n"
                    f"Errors:\n{error_msg}",
                    icon='warning'
                )
            else:
                messagebox.showinfo(
                    "Recategorization Complete",
                    f"✓ Recategorization complete!\n\n"
                    f"Changed: {recategorized_count} transactions\n"
                    f"Unchanged: {unchanged_count} transactions\n\n"
                    f"The UI is being refreshed with updated categories and confidence indicators."
                )

            # Refresh UI
            self.load_project_data()

        except Exception as e:
            logger.error(f"Recategorization error: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"Recategorization failed: {str(e)}"
            )
        finally:
            session.close()

    def import_file(self):
        """Import Excel file into current project."""
        filenames = filedialog.askopenfilenames(
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not filenames:
            return

        try:
            logger.info(f"Importing {len(filenames)} file(s) to project {self.project.name}")

            # 🤖 AI CATEGORIZATION: Create service and pass to importer for immediate AI analysis
            session = self.db_manager.get_session()
            cat_service = CategorizationService(session, self.project.id)

            stats = self.migration_service.import_excel_to_project(
                project_id=self.project.id,
                file_paths=list(filenames),
                skip_duplicates=True,
                categorization_service=cat_service  # Pass service to enable AI during import
            )
            session.close()

            # 🤖 Phase 2: Collect categorization statistics from imported data
            categorization_stats = None
            if stats['imported'] > 0:
                session = self.db_manager.get_session()
                try:
                    # Get recently imported transactions (last minute)
                    from datetime import datetime, timedelta
                    recent_cutoff = datetime.now() - timedelta(minutes=1)

                    recent_transactions = session.query(Transaction).filter(
                        Transaction.project_id == self.project.id,
                        Transaction.created_at >= recent_cutoff
                    ).all()

                    # Count categorization methods used during import
                    categorization_stats = {
                        'rule': 0,
                        'ai': 0,
                        'keyword': 0,
                        'default': 0
                    }

                    for txn in recent_transactions:
                        method = txn.categorization_method
                        if method in categorization_stats:
                            categorization_stats[method] += 1

                    # Log results
                    total_categorized = (
                        categorization_stats.get('rule', 0) +
                        categorization_stats.get('ai', 0) +
                        categorization_stats.get('keyword', 0)
                    )
                    if total_categorized > 0:
                        logger.info(
                            f"Categorized {total_categorized} transactions during import: "
                            f"rule={categorization_stats.get('rule', 0)}, "
                            f"ai={categorization_stats.get('ai', 0)}, "
                            f"keyword={categorization_stats.get('keyword', 0)}"
                        )

                except Exception as e:
                    logger.error(f"Error collecting categorization stats: {e}", exc_info=True)
                    categorization_stats = None
                finally:
                    session.close()

            # Show results
            msg = f"Import complete!\n\n"
            msg += f"Imported: {stats['imported']} transactions\n"
            msg += f"Skipped (duplicates): {stats['skipped']}\n"

            # Show categorization breakdown if available
            if categorization_stats:
                total_cat = (
                    categorization_stats.get('rule', 0) +
                    categorization_stats.get('ai', 0) +
                    categorization_stats.get('keyword', 0)
                )
                if total_cat > 0:
                    msg += f"\nCategorization:\n"
                    if categorization_stats.get('rule', 0) > 0:
                        msg += f"  • Rules: {categorization_stats['rule']}\n"
                    if categorization_stats.get('ai', 0) > 0:
                        msg += f"  • AI: {categorization_stats['ai']}\n"
                    if categorization_stats.get('keyword', 0) > 0:
                        msg += f"  • Keywords: {categorization_stats['keyword']}\n"

            if stats['errors']:
                msg += f"\nErrors:\n" + "\n".join(stats['errors'])

            messagebox.showinfo("Import Complete", msg)

            # Reload data
            self.load_project_data()

        except Exception as e:
            logger.error(f"Import error: {e}", exc_info=True)
            messagebox.showerror("Error", f"Import failed: {str(e)}")

    def load_project_data(self):
        """Load project data from database into DataFrame."""
        session = self.db_manager.get_session()
        try:
            # Get all transactions for project
            transactions = session.query(Transaction).filter_by(
                project_id=self.project.id
            ).order_by(Transaction.fecha.desc()).all()

            if not transactions:
                self.df = pd.DataFrame()
                self.update_month_filter()
                self.update_filtered_view()
                return

            # Convert to DataFrame
            data = []
            for t in transactions:
                # Format tags for display
                tags = t.get_tags()
                tags_str = ", ".join(tags) if tags else ""

                data.append({
                    'Fecha': t.fecha,
                    'Concepto': t.concepto,
                    'Movimiento': t.movimiento,
                    'Importe': t.importe,
                    'Categoría': t.categoria,
                    'AI_Confidence': t.ai_confidence,  # Include AI confidence
                    'Categorization_Method': t.categorization_method,  # Include method
                    'Tags': tags_str,
                    'Source': t.source_file or ''
                })

            self.df = pd.DataFrame(data)
            logger.info(f"Loaded {len(self.df)} transactions from database")

            self.update_month_filter()
            self.update_filtered_view()

        finally:
            session.close()

    def download_results(self):
        """Download current view to Excel."""
        if self.df is None or self.df.empty:
            messagebox.showwarning("Warning", "No data to download")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"{self.project.name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        if filename:
            try:
                logger.info(f"Saving results to {filename}")
                filtered_df = self.filter_by_month(self.df)
                filtered_df.to_excel(filename, index=False)
                logger.info(f"Results saved successfully")
                messagebox.showinfo("Success", f"Results saved to {filename}")
            except PermissionError:
                logger.error(f"Permission denied writing to {filename}")
                messagebox.showerror(
                    "Permission Denied",
                    f"Cannot save to {filename}.\n\nPlease check permissions and try again."
                )
            except Exception as e:
                logger.error(f"Error saving file: {e}", exc_info=True)
                messagebox.showerror("Error", f"Error saving file: {str(e)}")

    def setup_grouped_tab(self):
        # Create Treeview for grouped results
        columns = ("Categoría", "Total", "Cantidad")
        self.grouped_tree = ttk.Treeview(self.grouped_frame, columns=columns, show="headings")

        # Add column headings
        for col in columns:
            self.grouped_tree.heading(col, text=col, command=lambda c=col: self.sort_grouped_treeview(c))
            self.grouped_tree.column(col, width=150)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.grouped_frame, orient=tk.VERTICAL, command=self.grouped_tree.yview)
        self.grouped_tree.configure(yscrollcommand=scrollbar.set)

        # Pack elements
        self.grouped_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click event
        self.grouped_tree.bind("<Double-1>", self.show_category_details)

    def sort_treeview(self, col):
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]

        # Convert amounts to float for proper sorting
        if col == "Importe":
            items = [(float(value.replace("€", "").replace(",", "").strip()), item) for value, item in items]

        # Convert dates for proper sorting
        elif col == "Fecha":
            items = [(datetime.strptime(value, "%Y-%m-%d"), item) for value, item in items]

        items.sort(reverse=getattr(self, "reverse_sort", False))

        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)

        self.reverse_sort = not getattr(self, "reverse_sort", False)

    def sort_grouped_treeview(self, col):
        items = [(self.grouped_tree.set(item, col), item) for item in self.grouped_tree.get_children("")]

        # Convert numeric values for proper sorting
        if col in ["Total", "Cantidad"]:
            items = [(float(value.replace("€", "").replace(",", "").strip()), item) for value, item in items]

        items.sort(reverse=getattr(self, "reverse_sort_grouped", False))

        for index, (_, item) in enumerate(items):
            self.grouped_tree.move(item, "", index)

        self.reverse_sort_grouped = not getattr(self, "reverse_sort_grouped", False)

    def show_category_details(self, event):
        item = self.grouped_tree.selection()[0]
        category = self.grouped_tree.item(item)["values"][0]

        # Create new window
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Transactions for {category}")
        details_window.geometry("800x600")

        # Create Treeview
        columns = ("Fecha", "Concepto", "Movimiento", "Importe")
        tree = ttk.Treeview(details_window, columns=columns, show="headings")

        # Add column headings
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(details_window, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Pack elements
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Filter and display data
        if self.df is not None:
            category_df = self.df[self.df["Categoría"] == category]
            for _, row in category_df.iterrows():
                values = (
                    row["Fecha"].strftime("%Y-%m-%d"),
                    row["Concepto"],
                    row["Movimiento"],
                    f"{row['Importe']:.2f}€"
                )
                tree.insert("", tk.END, values=values)

    def update_month_filter(self):
        if self.df is not None and not self.df.empty:
            months = ["All Months"] + sorted(self.df["Fecha"].dt.strftime("%Y-%m").unique().tolist())
            self.month_filter["values"] = months
            self.month_filter.set("All Months")

    def filter_by_month(self, df):
        if df.empty:
            return df

        selected_month = self.month_var.get()
        if selected_month != "All Months":
            return df[df["Fecha"].dt.strftime("%Y-%m") == selected_month]
        return df

    def update_grouped_view(self, df):
        # Clear previous items
        for item in self.grouped_tree.get_children():
            self.grouped_tree.delete(item)

        if df.empty:
            return

        # Group data
        grouped = df.groupby("Categoría").agg({
            "Importe": ["sum", "count"]
        }).reset_index()

        # Add items
        for _, row in grouped.iterrows():
            values = (
                row["Categoría"],
                f"{row[('Importe', 'sum')]:.2f}€",
                row[('Importe', 'count')]
            )
            self.grouped_tree.insert("", tk.END, values=values)

    def update_treeview(self, df):
        """Update treeview with enhanced amount display, confidence indicators, and method."""
        # Clear previous items
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df.empty:
            return

        # Add items with enhanced formatting
        for _, row in df.iterrows():
            # Format amount with +/- and thousands separator
            importe = row['Importe']
            if importe >= 0:
                amount_str = f"+{importe:,.2f}€"
                amount_tag = 'income'
            else:
                amount_str = f"{importe:,.2f}€"  # Negative sign already present
                amount_tag = 'expense'

            # Get confidence indicator
            ai_confidence = row.get('AI_Confidence')
            if ai_confidence is not None and ai_confidence > 0:
                if ai_confidence >= 0.85:
                    confidence_indicator = "🟢"  # High confidence
                elif ai_confidence >= 0.70:
                    confidence_indicator = "🟡"  # Medium confidence
                else:
                    confidence_indicator = "⚪"  # Low confidence
            else:
                confidence_indicator = "⚪"  # No AI (manual/keyword)

            # Get categorization method indicator
            method = row.get('Categorization_Method')
            method_icons = {
                'ai': '🤖',      # AI categorization
                'rule': '📋',    # Rule-based
                'keyword': '🔑', # Keyword matching
                'manual': '✋'   # Manual edit
            }
            method_indicator = method_icons.get(method, '')

            # Determine if uncertain (medium confidence) for background color
            tags = [amount_tag]
            if ai_confidence and 0.70 <= ai_confidence < 0.85:
                tags.append('uncertain')

            values = (
                row["Fecha"].strftime("%Y-%m-%d"),
                row["Concepto"],
                row["Movimiento"],
                amount_str,
                row["Categoría"],
                confidence_indicator,
                method_indicator,
                row.get("Tags", ""),
                row["Source"]
            )
            self.tree.insert("", tk.END, values=values, tags=tuple(tags))

    def update_summary(self, df):
        if df.empty:
            summary = "No transactions"
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(tk.END, summary)
            return

        total_income = df[df["Importe"] > 0]["Importe"].sum()
        total_expenses = df[df["Importe"] < 0]["Importe"].sum()
        balance = total_income + total_expenses

        summary = f"Total Income: {total_income:.2f}€\n"
        summary += f"Total Expenses: {total_expenses:.2f}€\n"
        summary += f"Balance: {balance:.2f}€"

        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary)

    def update_filtered_view(self):
        if self.df is not None:
            filtered_df = self.filter_by_month(self.df)
            self.update_treeview(filtered_df)
            self.update_grouped_view(filtered_df)
            self.update_summary(filtered_df)
            self.chart_manager.update_charts(filtered_df)

    def setup_search_tab(self):
        """Setup the search and filter tab."""
        # Create main container
        container = ttk.Frame(self.search_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create search panel on the left
        self.search_panel = SearchPanel(
            container,
            on_search=self.execute_search
        )
        self.search_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Create results area on the right
        results_frame = ttk.LabelFrame(container, text="Search Results", padding=10)
        results_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create Treeview for search results
        columns = ("Fecha", "Concepto", "Importe", "Categoría", "Tags")
        self.search_tree = ttk.Treeview(results_frame, columns=columns, show="headings")

        # Add column headings
        for col in columns:
            self.search_tree.heading(col, text=col)
            if col == "Concepto":
                self.search_tree.column(col, width=300)
            else:
                self.search_tree.column(col, width=120)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=scrollbar.set)

        # Pack elements
        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Results count label
        self.search_results_label = ttk.Label(results_frame, text="No search executed")
        self.search_results_label.pack(side=tk.BOTTOM, pady=5)

    def execute_search(self, filters):
        """
        Execute search with given filters.

        Args:
            filters: Dictionary with filter criteria
        """
        session = self.db_manager.get_session()
        try:
            # Create new search service instance
            search_service = SearchService(session, self.project.id)

            # Update available categories and tags in search panel
            self.search_panel.update_categories(search_service.get_all_categories())
            self.search_panel.update_tags(search_service.get_all_tags())

            # Execute search
            results = search_service.search(
                text=filters.get('text'),
                date_from=filters.get('date_from'),
                date_to=filters.get('date_to'),
                amount_min=filters.get('amount_min'),
                amount_max=filters.get('amount_max'),
                categories=filters.get('categories'),
                tags=filters.get('tags')
            )

            # Clear previous results
            for item in self.search_tree.get_children():
                self.search_tree.delete(item)

            # Display results
            for txn in results:
                tags_str = ", ".join(txn.get_tags()) if txn.get_tags() else ""
                values = (
                    txn.fecha.strftime("%Y-%m-%d"),
                    txn.concepto,
                    f"{txn.importe:.2f}€",
                    txn.categoria,
                    tags_str
                )
                self.search_tree.insert("", tk.END, values=values)

            # Update results count
            self.search_results_label.config(text=f"Found {len(results)} transactions")

            logger.info(f"Search executed: {len(results)} results")

        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            messagebox.showerror("Error", f"Search failed: {str(e)}")
        finally:
            session.close()

    def setup_recurring_tab(self):
        """Setup the recurring transactions tab."""
        # Create main container
        container = ttk.Frame(self.recurring_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Info label
        info_label = ttk.Label(
            container,
            text="Transacciones recurrentes detectadas automáticamente (suscripciones, facturas, etc.)",
            font=('', 10)
        )
        info_label.pack(pady=(0, 10))

        # Create Treeview for recurring patterns
        columns = ("Merchant", "Frequency", "Amount", "Count", "Last Date", "Next Expected", "Confidence", "Status")
        self.recurring_tree = ttk.Treeview(container, columns=columns, show="headings")

        # Add column headings
        headings = {
            "Merchant": "Comercio",
            "Frequency": "Frecuencia",
            "Amount": "Importe Medio",
            "Count": "Veces",
            "Last Date": "Última Fecha",
            "Next Expected": "Próxima Fecha",
            "Confidence": "Confianza",
            "Status": "Estado"
        }

        for col in columns:
            self.recurring_tree.heading(col, text=headings[col])
            if col == "Merchant":
                self.recurring_tree.column(col, width=200)
            else:
                self.recurring_tree.column(col, width=120)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.recurring_tree.yview)
        self.recurring_tree.configure(yscrollcommand=scrollbar.set)

        # Pack elements
        self.recurring_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons frame
        buttons_frame = ttk.Frame(container)
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        ttk.Button(
            buttons_frame,
            text="🔄 Refresh Patterns",
            command=self.refresh_recurring_patterns
        ).pack(side=tk.LEFT, padx=5)

        # Results count label
        self.recurring_results_label = ttk.Label(buttons_frame, text="")
        self.recurring_results_label.pack(side=tk.LEFT, padx=10)

        # Load patterns initially
        self.refresh_recurring_patterns()

    def refresh_recurring_patterns(self):
        """Detect and display recurring transaction patterns."""
        session = self.db_manager.get_session()
        try:
            # Create new detector instance
            detector = RecurringDetector(session, self.project.id)

            # Detect patterns
            patterns = detector.detect_recurring_patterns()

            # Clear previous results
            for item in self.recurring_tree.get_children():
                self.recurring_tree.delete(item)

            # Display patterns
            frequency_map = {
                "weekly": "Semanal",
                "monthly": "Mensual",
                "yearly": "Anual"
            }

            for pattern in patterns:
                next_date = pattern.next_expected_date.strftime("%Y-%m-%d") if pattern.next_expected_date else "N/A"
                status = "✓ Activo" if pattern.is_active else "⚠ Inactivo"

                values = (
                    pattern.merchant_name,
                    frequency_map.get(pattern.frequency, pattern.frequency),
                    f"€{pattern.average_amount:.2f}",
                    pattern.transaction_count,
                    pattern.last_date.strftime("%Y-%m-%d"),
                    next_date,
                    f"{pattern.confidence:.0%}",
                    status
                )
                self.recurring_tree.insert("", tk.END, values=values)

            # Update results count
            active_count = sum(1 for p in patterns if p.is_active)
            self.recurring_results_label.config(
                text=f"Found {len(patterns)} patterns ({active_count} active)"
            )

            logger.info(f"Detected {len(patterns)} recurring patterns")

        except Exception as e:
            logger.error(f"Recurring detection error: {e}", exc_info=True)
            messagebox.showerror("Error", f"Pattern detection failed: {str(e)}")
        finally:
            session.close()

    def open_settings(self):
        """Open AI settings dialog."""
        try:
            from gui.dialogs import SettingsDialog

            session = self.db_manager.get_session()
            SettingsDialog(
                self.root,
                session,
                self.project.id,
                on_save=self.on_settings_saved
            )
            session.close()
        except Exception as e:
            logger.error(f"Failed to open settings: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"Failed to open settings dialog:\n\n{str(e)}"
            )

    def on_settings_saved(self):
        """Called when settings are saved - reload data to apply changes."""
        logger.info("Settings saved - reloading data")
        self.load_project_data()

    def run(self):
        self.root.mainloop()
