"""Main entry point for SpendSight BBVA application."""
from models.database import DatabaseManager
from gui.project_selector import ProjectSelector
from gui.main_window import MainWindow
from utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Run the application."""
    # Initialize database
    db_manager = DatabaseManager()
    db_manager.create_tables()

    logger.info("Starting SpendSight BBVA")

    # Show project selector
    selector = ProjectSelector(db_manager)
    selected_project = selector.run()

    # If project selected, open main window
    if selected_project:
        logger.info(f"Opening project: {selected_project.name}")
        app = MainWindow(db_manager, selected_project)
        app.run()
    else:
        logger.info("No project selected, exiting")

if __name__ == "__main__":
    main()
