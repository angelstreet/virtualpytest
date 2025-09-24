#!/usr/bin/env python3
"""
Main entry point for heatmap processor service
"""

if __name__ == "__main__":
    from .heatmap_processor import HeatmapProcessor
    
    print("🔥 Starting Heatmap Processor Service...")
    processor = HeatmapProcessor()
    processor.start()
