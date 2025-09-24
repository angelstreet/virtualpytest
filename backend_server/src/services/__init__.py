"""
Heatmap Services

Background services for continuous heatmap generation.
"""

from .heatmap_processor import HeatmapProcessor

def start_heatmap_processor():
    """Start the heatmap processor as a daemon"""
    processor = HeatmapProcessor()
    processor.start()