"""
Report Generation Utilities - Main Entry Point

This module provides the main entry point for report generation functionality.
The actual implementation has been split into focused modules for better maintainability.
"""

# Import from the new split modules
from .report_generation import (
    capture_and_upload_screenshot,
    generate_validation_report,
    generate_and_upload_script_report,
    format_timestamp,
    format_execution_time
)

from .report_formatting import (
    create_compact_step_results_section,
    get_video_thumbnail_html,
    format_console_summary_for_html,
    create_error_section,
    get_thumbnail_screenshot_html,
    update_step_results_with_r2_urls,
    create_verification_image_modal_data,
    create_error_report
)

# All functions are now imported from the split modules above
# This file serves as the main entry point to maintain backward compatibility