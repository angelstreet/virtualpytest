#!/usr/bin/env python3
"""
Example showing how to use the dedicated AudioMenuAnalyzer

This demonstrates the correct architectural approach:
1. Normal navigation handles getting to nodes
2. Dedicated analyzer handles audio menu analysis when needed
3. Zap controller only handles zap-related analysis
"""

import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor, ScriptExecutionContext
from shared.lib.utils.audio_menu_analyzer import analyze_audio_menu, add_audio_menu_analysis_to_step
from shared.lib.utils.navigation_utils import goto_node


def example_audio_menu_analysis_during_navigation():
    """
    Example: Analyze audio menu as part of a navigation sequence
    
    This is the CORRECT architectural approach - analyze the menu when you navigate to it,
    not as a side effect of some other action.
    """
    
    # Setup (normally done by script framework)
    context = ScriptExecutionContext("audio_menu_example")
    # ... initialize context with host, device, etc.
    
    print("🎧 [Example] Navigating to live screen...")
    # Navigate to live screen first
    goto_result = goto_node(context.host, context.selected_device, "live_fullscreen", 
                          context.tree_id, context.team_id, context)
    
    if goto_result.get('success'):
        print("🎧 [Example] Now navigating to audio menu...")
        
        # Navigate to audio menu
        audio_menu_result = goto_node(context.host, context.selected_device, "live_fullscreen_audiomenu", 
                                    context.tree_id, context.team_id, context)
        
        if audio_menu_result.get('success'):
            print("🎧 [Example] Successfully reached audio menu - now analyzing...")
            
            # THIS IS WHERE THE AUDIO MENU ANALYSIS BELONGS
            # Right after navigating TO the audio menu node
            analysis_result = analyze_audio_menu(context, current_node="live_fullscreen")
            
            # Add the analysis to the navigation step that just completed
            add_audio_menu_analysis_to_step(context)
            
            print(f"🎧 [Example] Analysis complete: menu_detected = {analysis_result.get('menu_detected', False)}")
            
            if analysis_result.get('menu_detected'):
                audio_languages = analysis_result.get('audio_languages', [])
                subtitle_languages = analysis_result.get('subtitle_languages', [])
                print(f"🎧 [Example] Found audio languages: {audio_languages}")
                print(f"🎧 [Example] Found subtitle languages: {subtitle_languages}")
        else:
            print("❌ [Example] Failed to navigate to audio menu")
    else:
        print("❌ [Example] Failed to navigate to live screen")


def example_standalone_audio_menu_analysis():
    """
    Example: Use the audio menu analyzer as a standalone function
    
    This can be called from any script when you want to analyze audio menus
    without being tied to zap actions.
    """
    
    # Setup (normally done by script framework)
    context = ScriptExecutionContext("standalone_audio_analysis")
    # ... initialize context with host, device, etc.
    
    print("🎧 [Example] Performing standalone audio menu analysis...")
    
    # Call the analyzer directly - it will handle navigation internally
    analysis_result = analyze_audio_menu(context)
    
    print(f"🎧 [Example] Standalone analysis complete:")
    print(f"  - Success: {analysis_result.get('success', False)}")
    print(f"  - Menu detected: {analysis_result.get('menu_detected', False)}")
    print(f"  - Message: {analysis_result.get('message', 'No message')}")
    
    if analysis_result.get('menu_detected'):
        audio_languages = analysis_result.get('audio_languages', [])
        subtitle_languages = analysis_result.get('subtitle_languages', [])
        print(f"  - Audio languages: {audio_languages}")
        print(f"  - Subtitle languages: {subtitle_languages}")


def example_integration_with_script_framework():
    """
    Example: How to integrate audio menu analysis with the script framework
    
    This shows the proper way to add audio menu analysis to navigation steps
    in a larger script execution.
    """
    
    # Create script executor
    executor = ScriptExecutor()
    context = ScriptExecutionContext("audio_menu_integration_example")
    
    # Load navigation tree (normally done by script)
    # executor.load_navigation_tree(context, "horizon_android_mobile")
    
    # Define navigation path that includes audio menu
    navigation_path = [
        {
            'from': 'start',
            'to': 'live_fullscreen',
            'actions': [{'action': 'press_key', 'params': {'key': 'HOME'}}]
        },
        {
            'from': 'live_fullscreen', 
            'to': 'live_fullscreen_audiomenu',
            'actions': [{'action': 'press_key', 'params': {'key': 'MENU'}}],
            # THIS IS THE KEY - add audio menu analysis as a custom step handler
            'custom_analysis': 'audio_menu'
        }
    ]
    
    # Custom step handler that adds audio menu analysis
    def custom_step_handler(context, step_data, step_result):
        """Custom handler to add audio menu analysis to specific steps"""
        
        if step_data.get('custom_analysis') == 'audio_menu':
            print("🎧 [Example] Adding audio menu analysis to navigation step...")
            
            # Add audio menu analysis to this step
            success = add_audio_menu_analysis_to_step(context)
            
            if success:
                print("✅ [Example] Audio menu analysis added to navigation step")
            else:
                print("❌ [Example] Failed to add audio menu analysis")
        
        return step_result
    
    # Execute navigation with custom handler
    # executor.execute_navigation_sequence(context, navigation_path, custom_step_handler)
    
    print("🎧 [Example] Navigation complete with audio menu analysis integrated")


if __name__ == "__main__":
    print("🎧 Audio Menu Analyzer Examples")
    print("=" * 50)
    
    print("\n1. Audio menu analysis during navigation (RECOMMENDED):")
    print("-" * 50)
    # example_audio_menu_analysis_during_navigation()
    
    print("\n2. Standalone audio menu analysis:")
    print("-" * 50)
    # example_standalone_audio_menu_analysis()
    
    print("\n3. Integration with script framework:")
    print("-" * 50)
    # example_integration_with_script_framework()
    
    print("\n🎧 Examples complete!")
    print("\nKey architectural points:")
    print("- Audio menu analysis is separate from zap controller")
    print("- Analysis happens when navigating TO audio menu nodes")
    print("- Results are stored in the correct navigation step")
    print("- Clean separation of concerns")
