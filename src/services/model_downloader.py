"""Model downloader for sentence-transformers."""
from pathlib import Path
import os
from typing import Optional, Callable
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ModelDownloader:
    """
    Handles downloading and managing sentence-transformers models.

    Models are stored locally in data/models/sentence-transformers/
    """

    # Model configuration
    MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
    MODEL_SIZE_MB = 80  # Approximate size in MB

    def __init__(self):
        """Initialize model downloader."""
        self.model_dir = self._get_model_directory()

    def _get_model_directory(self) -> Path:
        """
        Get the directory for storing models.

        Returns:
            Path object for model storage directory
        """
        # Store in data/models directory (three levels up from this file)
        model_dir = Path(__file__).parent.parent.parent / 'data' / 'models' / 'sentence-transformers'
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir

    def is_model_downloaded(self) -> bool:
        """
        Check if the model is already downloaded.

        Returns:
            True if model exists locally, False otherwise
        """
        model_path = self.model_dir / 'all-MiniLM-L6-v2'
        return model_path.exists() and (model_path / 'config.json').exists()

    def get_model_path(self) -> str:
        """
        Get the local path to the model.

        Returns:
            String path to model directory
        """
        return str(self.model_dir / 'all-MiniLM-L6-v2')

    def download_model(
        self,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Download the sentence-transformers model.

        Args:
            progress_callback: Optional callback for progress updates
                               Receives status messages as string

        Returns:
            True if successful, False otherwise
        """
        try:
            from sentence_transformers import SentenceTransformer

            if self.is_model_downloaded():
                logger.info("Model already downloaded")
                if progress_callback:
                    progress_callback("Model already available")
                return True

            logger.info(f"Downloading model {self.MODEL_NAME}...")
            if progress_callback:
                progress_callback(f"Downloading model (~{self.MODEL_SIZE_MB}MB)...")

            # Download model
            model = SentenceTransformer(self.MODEL_NAME)

            # Save to local directory
            model_path = self.get_model_path()
            model.save(model_path)

            logger.info(f"Model saved to {model_path}")
            if progress_callback:
                progress_callback("Download complete!")

            return True

        except ImportError as e:
            logger.error(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            if progress_callback:
                progress_callback("Error: sentence-transformers not installed")
            return False

        except Exception as e:
            logger.error(f"Failed to download model: {e}", exc_info=True)
            if progress_callback:
                progress_callback(f"Error: {str(e)}")
            return False

    def delete_model(self) -> bool:
        """
        Delete the downloaded model to free up space.

        Returns:
            True if successful, False otherwise
        """
        try:
            import shutil

            model_path = self.model_dir / 'all-MiniLM-L6-v2'

            if not model_path.exists():
                logger.warning("Model not found - nothing to delete")
                return False

            shutil.rmtree(model_path)
            logger.info(f"Deleted model from {model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete model: {e}", exc_info=True)
            return False

    def get_model_info(self) -> dict:
        """
        Get information about the model.

        Returns:
            Dictionary with model information
        """
        model_path = self.model_dir / 'all-MiniLM-L6-v2'

        info = {
            'name': self.MODEL_NAME,
            'size_mb': self.MODEL_SIZE_MB,
            'downloaded': self.is_model_downloaded(),
            'path': str(model_path)
        }

        if self.is_model_downloaded():
            try:
                # Get actual size on disk
                total_size = sum(
                    f.stat().st_size
                    for f in model_path.rglob('*')
                    if f.is_file()
                )
                info['actual_size_mb'] = round(total_size / (1024 * 1024), 2)
            except Exception as e:
                logger.warning(f"Could not calculate model size: {e}")

        return info
