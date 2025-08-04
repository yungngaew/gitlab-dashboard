"""Progress tracking utilities for GitLab tools."""

import logging
from typing import Optional, Iterator, Any
from contextlib import contextmanager

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    
try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


logger = logging.getLogger(__name__)


class ProgressTracker:
    """Wrapper for progress tracking that falls back gracefully."""
    
    def __init__(
        self, 
        items: Iterator[Any],
        total: Optional[int] = None,
        description: str = "Processing",
        unit: str = "items",
        disable: bool = False,
        use_rich: bool = False
    ):
        """Initialize progress tracker.
        
        Args:
            items: Iterator to track
            total: Total number of items
            description: Progress bar description
            unit: Unit name for items
            disable: Disable progress tracking
            use_rich: Use rich progress bars if available
        """
        self.items = items
        self.total = total
        self.description = description
        self.unit = unit
        self.disable = disable
        self.use_rich = use_rich and RICH_AVAILABLE
        self._progress_bar = None
    
    def __iter__(self):
        """Iterate with progress tracking."""
        if self.disable:
            # No progress tracking
            yield from self.items
        elif self.use_rich and RICH_AVAILABLE:
            # Use rich progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task(self.description, total=self.total)
                for item in self.items:
                    yield item
                    progress.update(task, advance=1)
        elif TQDM_AVAILABLE:
            # Use tqdm
            with tqdm(
                self.items,
                total=self.total,
                desc=self.description,
                unit=self.unit,
                leave=True
            ) as pbar:
                for item in pbar:
                    yield item
        else:
            # Fallback to simple counter
            count = 0
            for item in self.items:
                count += 1
                if self.total:
                    print(f"\r{self.description}: {count}/{self.total} {self.unit}", end="", flush=True)
                else:
                    print(f"\r{self.description}: {count} {self.unit}", end="", flush=True)
                yield item
            print()  # New line after completion


@contextmanager
def progress_context(description: str = "Working", disable: bool = False):
    """Context manager for showing a spinner during long operations.
    
    Args:
        description: Description to show
        disable: Disable progress display
    """
    if disable:
        yield
        return
    
    if RICH_AVAILABLE:
        console = Console()
        with console.status(description):
            yield
    elif TQDM_AVAILABLE:
        # Use tqdm spinner
        import itertools
        import threading
        import time
        
        stop_spinner = threading.Event()
        
        def spinner():
            with tqdm(
                itertools.cycle(['|', '/', '-', '\\']),
                desc=description,
                bar_format='{desc} {postfix}',
                leave=False
            ) as pbar:
                while not stop_spinner.is_set():
                    pbar.set_postfix_str(next(pbar))
                    time.sleep(0.1)
        
        spinner_thread = threading.Thread(target=spinner)
        spinner_thread.start()
        
        try:
            yield
        finally:
            stop_spinner.set()
            spinner_thread.join()
            print(f"\r{description} Done", flush=True)
    else:
        # Simple message
        print(f"{description}...", end="", flush=True)
        yield
        print(" Done")


def create_progress_bar(
    total: int,
    description: str = "Processing",
    unit: str = "items",
    disable: bool = False
) -> Optional[Any]:
    """Create a progress bar for manual updates.
    
    Args:
        total: Total number of items
        description: Progress bar description
        unit: Unit name for items
        disable: Disable progress bar
        
    Returns:
        Progress bar object or None
    """
    if disable:
        return None
    
    if TQDM_AVAILABLE:
        return tqdm(
            total=total,
            desc=description,
            unit=unit,
            leave=True
        )
    
    # Return a simple progress tracker
    class SimpleProgress:
        def __init__(self, total, description, unit):
            self.total = total
            self.description = description
            self.unit = unit
            self.current = 0
        
        def update(self, n=1):
            self.current += n
            print(f"\r{self.description}: {self.current}/{self.total} {self.unit}", end="", flush=True)
        
        def close(self):
            print()  # New line
    
    return SimpleProgress(total, description, unit)


def update_progress(progress_bar: Optional[Any], n: int = 1):
    """Update progress bar.
    
    Args:
        progress_bar: Progress bar object
        n: Number of items to advance
    """
    if progress_bar is None:
        return
    
    if hasattr(progress_bar, 'update'):
        progress_bar.update(n)


def close_progress(progress_bar: Optional[Any]):
    """Close progress bar.
    
    Args:
        progress_bar: Progress bar object
    """
    if progress_bar is None:
        return
    
    if hasattr(progress_bar, 'close'):
        progress_bar.close()