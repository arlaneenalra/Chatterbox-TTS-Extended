#!/usr/bin/env python3
"""
Bulk TTS Client for Chatterbox-TTS-Extended

This script uses the Gradio API to batch process a directory of text files
into MP3 audio files using the Chatterbox TTS system.

Usage:
    python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --settings settings.json

Requirements:
    - Chatterbox Gradio app must be running (python Chatter.py)
    - gradio_client library (pip install gradio_client)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import time
import hashlib
from datetime import datetime
import signal
import threading
import queue

try:
    from gradio_client import Client, handle_file
except ImportError:
    print("Error: gradio_client library not found.")
    print("Please install it with: pip install gradio_client")
    sys.exit(1)

# Conditional imports for watch mode
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None


def load_settings(settings_path: str) -> Dict[str, Any]:
    """Load settings from JSON file."""
    if not os.path.exists(settings_path):
        print(f"Error: Settings file not found: {settings_path}")
        sys.exit(1)

    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    return settings


def get_default_settings() -> Dict[str, Any]:
    """Return default settings matching Chatterbox defaults."""
    return {
        "exaggeration_slider": 0.5,
        "temp_slider": 0.75,
        "seed_input": 0,
        "cfg_weight_slider": 1.0,
        "use_pyrnnoise_checkbox": False,
        "use_auto_editor_checkbox": False,
        "threshold_slider": 0.06,
        "margin_slider": 0.2,
        "export_format_checkboxes": ["mp3"],
        "enable_batching_checkbox": False,
        "to_lowercase_checkbox": True,
        "normalize_spacing_checkbox": True,
        "fix_dot_letters_checkbox": True,
        "remove_reference_numbers_checkbox": True,
        "keep_original_checkbox": False,
        "smart_batch_short_sentences_checkbox": True,
        "disable_watermark_checkbox": True,
        "num_generations_input": 1,
        "normalize_audio_checkbox": False,
        "normalize_method_dropdown": "ebu",
        "normalize_level_slider": -24,
        "normalize_tp_slider": -2,
        "normalize_lra_slider": 7,
        "num_candidates_slider": 3,
        "max_attempts_slider": 3,
        "bypass_whisper_checkbox": False,
        "whisper_model_dropdown": "medium (~5–8 GB OpenAI / ~2.5–4.5 GB faster-whisper)",
        "use_faster_whisper_checkbox": True,
        "enable_parallel_checkbox": True,
        "num_parallel_workers_slider": 4,
        "use_longest_transcript_on_fail_checkbox": True,
        "sound_words_field": "",
        "separate_files_checkbox": False,
    }


def is_file_stable(file_path: Path, stability_checks: int = 3,
                   check_interval: float = 1.0) -> bool:
    """
    Check if file has finished being written by monitoring size stability.
    Returns True if file size is unchanged for N consecutive checks.

    Args:
        file_path: Path to file to check
        stability_checks: Number of consecutive checks with same size
        check_interval: Seconds between size checks

    Returns:
        True if file appears stable and ready for processing
    """
    previous_size = -1
    stable_count = 0

    for _ in range(stability_checks * 2):  # Max attempts
        try:
            current_size = file_path.stat().st_size
            if current_size == previous_size and current_size > 0:
                stable_count += 1
                if stable_count >= stability_checks:
                    return True
            else:
                stable_count = 0
                previous_size = current_size
            time.sleep(check_interval)
        except (OSError, FileNotFoundError):
            return False

    return False


class ProcessedFilesTracker:
    """Track which files have been processed to avoid reprocessing."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {"version": "1.0", "processed_files": {}}

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def is_processed(self, file_path: Path) -> bool:
        return str(file_path.absolute()) in self.state["processed_files"]

    def mark_processed(self, file_path: Path, success: bool,
                       output_files: List[str], error: str = None):
        file_hash = self._compute_hash(file_path)
        self.state["processed_files"][str(file_path.absolute())] = {
            "hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "success": success,
            "output_files": output_files,
            "error_message": error
        }
        self._save_state()

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
        return f"sha256:{hasher.hexdigest()}"


class GracefulShutdown:
    """Handle graceful shutdown on SIGINT/SIGTERM."""

    def __init__(self, observer):
        self.observer = observer
        self.shutdown = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        if self.shutdown:
            print("\n\nForce quit!")
            sys.exit(1)
        print("\n\nShutdown requested, stopping observer...")
        print("(Press Ctrl+C again to force quit)")
        self.shutdown = True
        self.observer.stop()


class TTSProcessingQueue:
    """Thread-safe queue for sequential TTS file processing."""

    def __init__(self, max_size: int = 0):
        """
        Initialize the processing queue.

        Args:
            max_size: Maximum queue size (0 = unlimited)
        """
        self.queue = queue.Queue(maxsize=max_size)
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        self.current_file = None
        self.lock = threading.Lock()

    def start_worker(self, process_callback):
        """
        Start the worker thread.

        Args:
            process_callback: Function to call for each file (receives Path object)
        """
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(process_callback,),
            daemon=False  # NOT daemon - want to finish processing
        )
        self.worker_thread.start()

    def _worker_loop(self, process_callback):
        """Main worker loop - processes files from queue sequentially."""
        while not self.shutdown_event.is_set():
            try:
                # Block for 1 second to allow checking shutdown
                file_path = self.queue.get(timeout=1.0)

                with self.lock:
                    self.current_file = file_path

                try:
                    process_callback(file_path)
                except Exception as e:
                    print(f"[QUEUE ERROR] {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    self.queue.task_done()
                    with self.lock:
                        self.current_file = None

            except queue.Empty:
                continue  # Timeout, check shutdown and continue

    def enqueue(self, file_path: Path) -> bool:
        """
        Add file to processing queue.

        Args:
            file_path: Path to file to process

        Returns:
            True if enqueued successfully, False if queue is full
        """
        try:
            self.queue.put(file_path, block=False)
            size = self.queue.qsize()
            print(f"[QUEUED] {file_path.name} (queue size: {size})")
            return True
        except queue.Full:
            print(f"[QUEUE FULL] Cannot enqueue: {file_path.name}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Dictionary with queue_size and current_file
        """
        with self.lock:
            return {
                'queue_size': self.queue.qsize(),
                'current_file': self.current_file.name if self.current_file else None
            }

    def shutdown(self, timeout: int = 300):
        """
        Shutdown worker, waiting for queue to drain.

        Args:
            timeout: Max seconds to wait for queue drain
        """
        print(f"[QUEUE] Draining queue (up to {timeout}s timeout)...")
        self.shutdown_event.set()

        # Wait for current processing to complete
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)

        if self.worker_thread and self.worker_thread.is_alive():
            print(f"[QUEUE] Warning: Worker thread still running after {timeout}s timeout")


class TTSFileEventHandler(FileSystemEventHandler):
    """Handle file system events for TTS processing."""

    def __init__(self, client, output_dir, pattern, settings, tracker,
                 watch_args, processing_queue, reference_audio=None, api_name=None, fn_index=None):
        self.client = client
        self.output_dir = output_dir
        self.pattern = pattern
        self.settings = settings
        self.tracker = tracker
        self.watch_args = watch_args
        self.processing_queue = processing_queue
        self.reference_audio = reference_audio
        self.api_name = api_name
        self.fn_index = fn_index

        import fnmatch
        self.pattern_regex = fnmatch.translate(pattern)

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if not self._matches_pattern(file_path):
            return

        print(f"\n[DETECTED] New file: {file_path.name}")

        # Enqueue file for processing
        self._enqueue_file(file_path)

    def on_modified(self, event):
        """Handle file modification events (if --reprocess-modified)."""
        if not self.watch_args.get('reprocess_modified', False):
            return

        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if not self._matches_pattern(file_path):
            return

        # Check if file hash changed
        if self.tracker.is_processed(file_path):
            try:
                current_hash = ProcessedFilesTracker._compute_hash(file_path)
                stored_info = self.tracker.state["processed_files"][str(file_path.absolute())]

                if current_hash != stored_info["hash"]:
                    print(f"\n[MODIFIED] File changed: {file_path.name}")
                    # Enqueue file for processing
                    self._enqueue_file(file_path)
            except (KeyError, OSError, FileNotFoundError):
                pass  # Skip if can't compute hash or file not found

    def _matches_pattern(self, file_path: Path) -> bool:
        """Check if file matches the specified pattern."""
        import re
        return re.match(self.pattern_regex, file_path.name) is not None

    def _enqueue_file(self, file_path: Path):
        """Enqueue file for processing with pre-checks."""
        # Pre-check: Already processed?
        if self.tracker.is_processed(file_path) and \
           not self.watch_args.get('reprocess_modified', False):
            print(f"[SKIP] Already processed: {file_path.name}")
            return

        # Enqueue the file
        self.processing_queue.enqueue(file_path)

    def _process_file_safe(self, file_path: Path):
        """Safely process a file with error handling and stability checks."""
        try:
            # Check if already processed (in case file was queued twice)
            if self.tracker.is_processed(file_path) and \
               not self.watch_args.get('reprocess_modified', False):
                print(f"[SKIP] Already processed: {file_path.name}")
                return

            # Initial delay
            delay = self.watch_args['delay']
            print(f"[WAITING] {delay}s initial delay...")
            time.sleep(delay)

            # Check file still exists
            if not file_path.exists():
                print(f"[ERROR] File disappeared: {file_path.name}")
                return

            # Wait for file stability
            print(f"[CHECKING] File stability...")
            if not is_file_stable(
                file_path,
                stability_checks=self.watch_args['stability_checks'],
                check_interval=self.watch_args['stability_interval']
            ):
                print(f"[ERROR] File not stable after timeout: {file_path.name}")
                self.tracker.mark_processed(file_path, False, [], "File stability timeout")
                return

            # Process the file
            print(f"[PROCESSING] Starting TTS generation...")
            output_files = process_text_file(
                client=self.client,
                text_file_path=str(file_path),
                output_dir=self.output_dir,
                settings=self.settings,
                audio_prompt_path=self.reference_audio,
                api_name=self.api_name,
                fn_index=self.fn_index
            )

            if output_files:
                print(f"[SUCCESS] Generated {len(output_files)} file(s)")
                self.tracker.mark_processed(file_path, True, output_files)
            else:
                print(f"[FAILED] No output generated")
                self.tracker.mark_processed(file_path, False, [], "No output files generated")

        except Exception as e:
            print(f"[ERROR] Processing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.tracker.mark_processed(file_path, False, [], str(e))

        finally:
            print(f"\n[READY] Watching for new files...")


def process_text_file(
    client: Client,
    text_file_path: str,
    output_dir: str,
    settings: Dict[str, Any],
    audio_prompt_path: str = None,
    api_name: str = None,
    fn_index: int = None,
) -> List[str]:
    """
    Process a single text file using the Gradio API.

    Args:
        client: Gradio client instance
        text_file_path: Path to input text file
        output_dir: Directory to save output files
        settings: Settings dictionary
        audio_prompt_path: Optional path to reference audio file

    Returns:
        List of generated audio file paths
    """
    # Read the text content
    with open(text_file_path, 'r', encoding='utf-8') as f:
        text_content = f.read().strip()

    if not text_content:
        print(f"Warning: Empty file skipped: {text_file_path}")
        return []

    print(f"\nProcessing: {text_file_path}")
    print(f"Text length: {len(text_content)} characters")

    # Prepare API call parameters for the /lambda endpoint
    # Based on actual endpoint signature from gradio client inspection
    api_params = [
        text_content,                                           # 0: param_0 - Text Input (str)
        [],                                                     # 1: param_1 - Text File(s) (.txt) - empty list for no files
        handle_file(audio_prompt_path) if audio_prompt_path else None,  # 2: param_2 - Reference Audio (Optional)
        settings.get("exaggeration_slider", 0.5),              # 3: param_3 - Emotion Exaggeration
        settings.get("temp_slider", 0.75),                     # 4: param_4 - Temperature
        settings.get("seed_input", 0),                         # 5: param_5 - Random Seed
        settings.get("cfg_weight_slider", 1.0),                # 6: param_6 - CFG Weight/Pace
        settings.get("use_pyrnnoise_checkbox", False),         # 7: param_7 - Denoise with RNNoise
        settings.get("use_auto_editor_checkbox", False),       # 8: param_8 - Post-process with Auto-Editor
        settings.get("threshold_slider", 0.06),                # 9: param_9 - Auto-Editor Volume Threshold
        settings.get("margin_slider", 0.2),                    # 10: param_10 - Auto-Editor Margin
        settings.get("export_format_checkboxes", ["mp3"]),     # 11: param_11 - Export Format(s)
        settings.get("enable_batching_checkbox", False),       # 12: param_12 - Enable Sentence Batching
        settings.get("to_lowercase_checkbox", True),           # 13: param_13 - Convert to lowercase
        settings.get("normalize_spacing_checkbox", True),      # 14: param_14 - Normalize spacing
        settings.get("fix_dot_letters_checkbox", True),        # 15: param_15 - Convert 'J.R.R.'
        settings.get("remove_reference_numbers_checkbox", True),  # 16: param_16 - Remove reference numbers
        settings.get("keep_original_checkbox", False),         # 17: param_17 - Keep original WAV
        settings.get("smart_batch_short_sentences_checkbox", True),  # 18: param_18 - Smart-append short sentences
        settings.get("disable_watermark_checkbox", True),      # 19: param_19 - Disable Perth Watermark
        settings.get("num_generations_input", 1),              # 20: param_20 - Number of Generations
        settings.get("normalize_audio_checkbox", False),       # 21: param_21 - Normalize with ffmpeg
        settings.get("normalize_method_dropdown", "ebu"),      # 22: param_22 - Normalization Method
        settings.get("normalize_level_slider", -24),           # 23: param_23 - EBU Target Integrated Loudness
        settings.get("normalize_tp_slider", -2),               # 24: param_24 - EBU True Peak
        settings.get("normalize_lra_slider", 7),               # 25: param_25 - EBU Loudness Range
        settings.get("num_candidates_slider", 3),              # 26: param_26 - Number of Candidates
        settings.get("max_attempts_slider", 3),                # 27: param_27 - Max Attempts
        settings.get("bypass_whisper_checkbox", False),        # 28: param_28 - Bypass Whisper Checking
        settings.get("whisper_model_dropdown", "medium (~5–8 GB OpenAI / ~2.5–4.5 GB faster-whisper)"),  # 29: param_29 - Whisper Model
        settings.get("enable_parallel_checkbox", True),        # 30: param_30 - Enable Parallel Chunk Processing
        settings.get("num_parallel_workers_slider", 4),        # 31: param_31 - Parallel Workers
        settings.get("use_longest_transcript_on_fail_checkbox", True),  # 32: param_32 - Use longest transcript on fail
        settings.get("sound_words_field", ""),                 # 33: param_33 - Remove/Replace Words/Sounds
        settings.get("use_faster_whisper_checkbox", True),     # 34: param_34 - Use faster-whisper
        settings.get("separate_files_checkbox", False),        # 35: param_35 - Generate separate audio files
    ]

    try:
        # Call the Gradio API
        print("Sending request to Gradio API...")
        start_time = time.time()

        # Determine which endpoint to use
        if api_name:
            # Use named endpoint if specified
            result = client.predict(*api_params, api_name=api_name)
        elif fn_index is not None:
            # Use function index if specified
            result = client.predict(*api_params, fn_index=fn_index)
        else:
            # Default to api_name="/lambda" (the TTS generation endpoint)
            result = client.predict(*api_params, api_name="/lambda")

        elapsed = time.time() - start_time
        print(f"Generation completed in {elapsed:.1f} seconds")

        # The result should be a tuple: (output_paths, dropdown_update, dropdown_value)
        # We need the first element which is the list of output file paths
        if isinstance(result, tuple) and len(result) > 0:
            output_files = result[0]
        else:
            output_files = result

        if not output_files:
            print(f"Warning: No output files generated for {text_file_path}")
            return []

        # Copy/move files to output directory with appropriate naming
        output_basename = Path(text_file_path).stem
        saved_files = []

        os.makedirs(output_dir, exist_ok=True)

        for i, file_path in enumerate(output_files):
            if not os.path.exists(file_path):
                print(f"Warning: Generated file not found: {file_path}")
                continue

            # Get the file extension
            ext = Path(file_path).suffix

            # Create output filename
            if len(output_files) == 1:
                output_filename = f"{output_basename}{ext}"
            else:
                output_filename = f"{output_basename}_{i+1}{ext}"

            output_path = os.path.join(output_dir, output_filename)

            # Copy the file
            import shutil
            shutil.copy2(file_path, output_path)
            saved_files.append(output_path)
            print(f"Saved: {output_path}")

        return saved_files

    except Exception as e:
        print(f"Error processing {text_file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def run_batch_mode(client: Client, input_dir: str, output_dir: str, pattern: str,
                   settings: Dict[str, Any], reference_audio: str = None,
                   api_name: str = None, fn_index: int = None) -> Dict[str, Any]:
    """
    Run one-time batch processing (original behavior).
    Extracted from existing main() loop.

    Args:
        client: Gradio client instance
        input_dir: Input directory path
        output_dir: Output directory path
        pattern: File pattern to match
        settings: Settings dictionary
        reference_audio: Optional reference audio path
        api_name: Optional API endpoint name
        fn_index: Optional function index

    Returns:
        Dictionary with statistics (total, successful, failed)
    """
    input_path = Path(input_dir)

    # Find all matching text files
    text_files = sorted(input_path.glob(pattern))

    if not text_files:
        print(f"\nNo files matching pattern '{pattern}' found in {input_dir}")
        return {"total": 0, "successful": 0, "failed": 0}

    print(f"\nFound {len(text_files)} file(s) to process")
    print(f"{'='*70}\n")

    successful = 0
    failed = 0

    for i, text_file in enumerate(text_files, 1):
        print(f"Processing file {i}/{len(text_files)}: {text_file.name}")
        print(f"{'-'*70}")

        try:
            output_files = process_text_file(
                client=client,
                text_file_path=str(text_file),
                output_dir=output_dir,
                settings=settings,
                audio_prompt_path=reference_audio,
                api_name=api_name,
                fn_index=fn_index
            )

            if output_files:
                successful += 1
                print(f"✓ Success: Generated {len(output_files)} file(s)")
            else:
                failed += 1
                print(f"✗ Failed: No output generated")

        except Exception as e:
            failed += 1
            print(f"✗ Error: {str(e)}")

        print(f"{'='*70}\n")

    # Print summary
    print(f"\nProcessing complete!")
    print(f"Total files: {len(text_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    return {"total": len(text_files), "successful": successful, "failed": failed}


def run_watch_mode(client: Client, input_dir: str, output_dir: str, pattern: str,
                   settings: Dict[str, Any], watch_args: Dict[str, Any],
                   reference_audio: str = None, api_name: str = None, fn_index: int = None):
    """
    Run continuous file watching mode.

    Args:
        client: Gradio client instance
        input_dir: Input directory path to watch
        output_dir: Output directory path
        pattern: File pattern to match
        settings: Settings dictionary
        watch_args: Watch-specific arguments (delay, stability_checks, etc.)
        reference_audio: Optional reference audio path
        api_name: Optional API endpoint name
        fn_index: Optional function index
    """
    # Initialize state tracker
    state_file = Path(watch_args.get('state_file') or
                      os.path.join(output_dir, 'watch_state.json'))
    tracker = ProcessedFilesTracker(state_file)

    # Create processing queue
    max_queue_size = watch_args.get('max_queue_size', 0)
    processing_queue = TTSProcessingQueue(max_size=max_queue_size)

    # Create event handler
    handler = TTSFileEventHandler(
        client=client,
        output_dir=output_dir,
        pattern=pattern,
        settings=settings,
        tracker=tracker,
        watch_args=watch_args,
        processing_queue=processing_queue,
        reference_audio=reference_audio,
        api_name=api_name,
        fn_index=fn_index
    )

    # Start queue worker thread
    processing_queue.start_worker(process_callback=handler._process_file_safe)

    # Start observer FIRST so it catches new files during initial scan
    observer = Observer()
    observer.schedule(handler, input_dir, recursive=watch_args.get('recursive', False))
    observer.start()

    print(f"\n{'='*70}")
    print("WATCH MODE ACTIVE")
    print(f"{'='*70}")
    print(f"Watching: {input_dir}")
    print(f"Pattern: {pattern}")
    print(f"Output: {output_dir}")
    print(f"State file: {state_file}")
    print(f"Watch delay: {watch_args['delay']} seconds")
    print(f"Stability checks: {watch_args['stability_checks']} (interval: {watch_args['stability_interval']}s)")
    print(f"{'='*70}\n")

    # Now process existing files (observer is already running)
    print(f"{'='*70}")
    print("INITIAL SCAN - Enqueueing existing files")
    print(f"{'='*70}")

    input_path = Path(input_dir)
    existing_files = sorted(input_path.glob(pattern))

    if existing_files:
        unprocessed_files = [f for f in existing_files if not tracker.is_processed(f)]

        if unprocessed_files:
            print(f"Found {len(unprocessed_files)} unprocessed file(s)\n")

            for file_path in unprocessed_files:
                processing_queue.enqueue(file_path)

            print(f"\n{'='*70}")
            print("Initial scan complete")
            print(f"{'='*70}\n")
        else:
            print(f"All {len(existing_files)} existing file(s) already processed\n")
            print(f"{'='*70}\n")
    else:
        print(f"No existing files found\n")
        print(f"{'='*70}\n")

    print("Now monitoring for new files...")
    print(f"Press Ctrl+C to stop...\n")

    shutdown_handler = GracefulShutdown(observer)

    # Track last status time for periodic updates
    last_status_time = time.time()
    status_interval = 10  # seconds

    try:
        while not shutdown_handler.shutdown:
            time.sleep(1)

            # Periodic status updates
            current_time = time.time()
            if current_time - last_status_time >= status_interval:
                status = processing_queue.get_status()
                if status['queue_size'] > 0 or status['current_file']:
                    msg = f"[STATUS] Queue: {status['queue_size']} pending"
                    if status['current_file']:
                        msg += f", processing: {status['current_file']}"
                    print(msg)
                last_status_time = current_time

    except KeyboardInterrupt:
        pass  # Handled by signal handler
    finally:
        # Shutdown queue and wait for completion
        queue_timeout = watch_args.get('shutdown_timeout', 300)
        processing_queue.shutdown(timeout=queue_timeout)

        observer.join(timeout=5)
        print("Watch mode stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Bulk TTS processing client for Chatterbox-TTS-Extended",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all .txt files in 'texts' directory using default settings
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs

  # Use custom settings file
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --settings my_settings.json

  # Connect to remote Gradio instance
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --url http://192.168.1.100:7860

  # Use a reference audio for voice cloning
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --reference-audio voice.wav
        """
    )

    parser.add_argument(
        '--input-dir',
        type=str,
        required=False,
        help='Directory containing input text files (.txt)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        required=False,
        help='Directory to save output audio files'
    )

    parser.add_argument(
        '--settings',
        type=str,
        default=None,
        help='Path to settings.json file (optional, uses defaults if not provided)'
    )

    parser.add_argument(
        '--reference-audio',
        type=str,
        default=None,
        help='Path to reference audio file for voice cloning (optional)'
    )

    parser.add_argument(
        '--url',
        type=str,
        default='http://localhost:7860',
        help='Gradio server URL (default: http://localhost:7860)'
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default='*.txt',
        help='File pattern to match (default: *.txt)'
    )

    parser.add_argument(
        '--api-name',
        type=str,
        default=None,
        help='Gradio API endpoint name (optional, e.g., "/predict")'
    )

    parser.add_argument(
        '--fn-index',
        type=int,
        default=None,
        help='Gradio endpoint function index (default: 0 for first endpoint)'
    )

    parser.add_argument(
        '--list-endpoints',
        action='store_true',
        help='List available API endpoints and exit'
    )

    # Watch mode arguments
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Enable watch mode - continuously monitor directory for new files'
    )

    parser.add_argument(
        '--watch-delay',
        type=float,
        default=2.0,
        help='Initial delay (seconds) after file creation before processing (default: 2.0)'
    )

    parser.add_argument(
        '--stability-checks',
        type=int,
        default=3,
        help='Number of consecutive file size checks for stability (default: 3)'
    )

    parser.add_argument(
        '--stability-interval',
        type=float,
        default=1.0,
        help='Interval (seconds) between stability checks (default: 1.0)'
    )

    parser.add_argument(
        '--watch-state-file',
        type=str,
        default=None,
        help='Path to state file for tracking processed files (default: <output-dir>/watch_state.json)'
    )

    parser.add_argument(
        '--reprocess-modified',
        action='store_true',
        help='Reprocess files if modified (checks file hash)'
    )

    parser.add_argument(
        '--watch-recursive',
        action='store_true',
        help='Watch subdirectories recursively (default: false)'
    )

    parser.add_argument(
        '--max-queue-size',
        type=int,
        default=0,
        help='Maximum queue size (0 = unlimited, default: 0)'
    )

    parser.add_argument(
        '--shutdown-timeout',
        type=int,
        default=300,
        help='Max seconds to wait for queue drain on shutdown (default: 300)'
    )

    args = parser.parse_args()

    # If --list-endpoints is specified, we don't need input/output dirs
    # Otherwise, validate required arguments
    if not args.list_endpoints:
        if not args.input_dir:
            parser.error("--input-dir is required (unless using --list-endpoints)")
        if not args.output_dir:
            parser.error("--output-dir is required (unless using --list-endpoints)")

        # Validate input directory
        if not os.path.isdir(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}")
            sys.exit(1)

    # Load settings (skip if just listing endpoints)
    if not args.list_endpoints:
        if args.settings:
            print(f"Loading settings from: {args.settings}")
            settings = load_settings(args.settings)
        else:
            print("Using default settings")
            settings = get_default_settings()

        # Validate reference audio if provided
        if args.reference_audio and not os.path.exists(args.reference_audio):
            print(f"Error: Reference audio file not found: {args.reference_audio}")
            sys.exit(1)

        print(f"\nOutput directory: {args.output_dir}")
        print(f"Gradio URL: {args.url}")

    # Connect to Gradio API
    print(f"\nConnecting to Gradio server at {args.url}...")
    try:
        client = Client(args.url)
        print("Successfully connected to Gradio API")
    except Exception as e:
        print(f"Error connecting to Gradio server: {str(e)}")
        print("\nMake sure the Chatterbox Gradio app is running:")
        print("  python Chatter.py")
        sys.exit(1)

    # Handle --list-endpoints
    if args.list_endpoints:
        print("\n" + "="*70)
        print("AVAILABLE API ENDPOINTS")
        print("="*70)
        try:
            api_info = client.view_api(all_endpoints=True)
            print(api_info)
        except Exception as e:
            print(f"Could not retrieve API info: {e}")
            print("\nTry accessing the API docs at: {}/docs".format(args.url))
        sys.exit(0)

    # If we're not just listing endpoints, proceed with processing
    if not args.list_endpoints:
        # Check watchdog availability if watch mode requested
        if args.watch and not WATCHDOG_AVAILABLE:
            print("\n" + "="*70)
            print("ERROR: Watch mode requires the 'watchdog' library")
            print("="*70)
            print("\nInstall it with:")
            print("  uv sync")
            print("\nOr manually:")
            print("  uv add watchdog")
            sys.exit(1)

        # Set up endpoint parameters
        api_name = args.api_name if args.api_name else "/lambda"
        fn_index = args.fn_index

        if args.api_name:
            print(f"\nUsing API endpoint: {api_name}")
        elif fn_index is not None:
            print(f"\nUsing function index: {fn_index}")
            api_name = None  # Clear api_name when using fn_index
        else:
            print(f"\nUsing API endpoint: {api_name} (default)")

        # Branch on watch vs batch mode
        if args.watch:
            # Prepare watch-specific arguments
            watch_args = {
                'delay': args.watch_delay,
                'stability_checks': args.stability_checks,
                'stability_interval': args.stability_interval,
                'state_file': args.watch_state_file,
                'reprocess_modified': args.reprocess_modified,
                'recursive': args.watch_recursive,
                'max_queue_size': args.max_queue_size,
                'shutdown_timeout': args.shutdown_timeout
            }

            # Run watch mode
            run_watch_mode(
                client=client,
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                pattern=args.pattern,
                settings=settings,
                watch_args=watch_args,
                reference_audio=args.reference_audio,
                api_name=api_name,
                fn_index=fn_index
            )
        else:
            # Run batch mode (existing behavior)
            run_batch_mode(
                client=client,
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                pattern=args.pattern,
                settings=settings,
                reference_audio=args.reference_audio,
                api_name=api_name,
                fn_index=fn_index
            )


if __name__ == "__main__":
    main()
