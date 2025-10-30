"""
Execution Orchestrator
Unified coordinator for all execution types (navigation, actions, verifications, blocks)
Handles cross-cutting concerns: logging, screenshots, error handling
"""

from typing import Dict, Any, List, Optional
from .logging_manager import LoggingManager
from .screenshot_manager import ScreenshotManager


class ExecutionOrchestrator:
    """
    Unified orchestrator that coordinates all execution types.
    Handles cross-cutting concerns and delegates to domain executors.
    """
    
    @staticmethod
    def execute_navigation(
        device,
        tree_id: str,
        userinterface_name: str,
        target_node_id: str = None,
        target_node_label: str = None,
        navigation_path: List[Dict] = None,
        current_node_id: Optional[str] = None,
        frontend_sent_position: bool = False,
        image_source_url: Optional[str] = None,
        team_id: str = None,
        context=None
    ) -> Dict[str, Any]:
        """
        Execute navigation with logging
        
        Args:
            device: Device instance
            tree_id: Navigation tree ID
            userinterface_name: User interface name (REQUIRED)
            target_node_id: Target node ID (UUID)
            target_node_label: Target node label
            navigation_path: Optional pre-computed path
            current_node_id: Optional current position
            frontend_sent_position: Whether frontend explicitly sent position
            image_source_url: Optional image source URL
            team_id: Team ID for security
            context: Optional execution context
            
        Returns:
            Dict with success status, logs, and navigation details
        """
        print(f"[@ExecutionOrchestrator] Executing navigation to {target_node_label or target_node_id}")
        
        def execute():
            return device.navigation_executor.execute_navigation(
                tree_id=tree_id,
                userinterface_name=userinterface_name,
                target_node_id=target_node_id,
                target_node_label=target_node_label,
                navigation_path=navigation_path,
                current_node_id=current_node_id,
                frontend_sent_position=frontend_sent_position,
                image_source_url=image_source_url,
                team_id=team_id,
                context=context
            )
        
        return LoggingManager.execute_with_logging(execute)
    
    @staticmethod
    def execute_actions(
        device,
        actions: List[Dict[str, Any]],
        retry_actions: Optional[List[Dict[str, Any]]] = None,
        failure_actions: Optional[List[Dict[str, Any]]] = None,
        team_id: str = None,
        context=None
    ) -> Dict[str, Any]:
        """
        Execute actions with logging
        
        Args:
            device: Device instance
            actions: List of actions to execute
            retry_actions: Optional retry actions
            failure_actions: Optional failure actions
            team_id: Team ID for database recording
            context: Optional execution context
            
        Returns:
            Dict with success status, logs, and action results
        """
        print(f"[@ExecutionOrchestrator] Executing {len(actions)} action(s)")
        
        def execute():
            return device.action_executor.execute_actions(
                actions=actions,
                retry_actions=retry_actions,
                failure_actions=failure_actions,
                team_id=team_id,
                context=context
            )
        
        return LoggingManager.execute_with_logging(execute)
    
    @staticmethod
    def execute_verifications(
        device,
        verifications: List[Dict[str, Any]],
        userinterface_name: str,
        image_source_url: Optional[str] = None,
        team_id: str = None,
        context=None,
        tree_id: Optional[str] = None,
        node_id: Optional[str] = None,
        verification_pass_condition: str = 'all'
    ) -> Dict[str, Any]:
        """
        Execute verifications with logging
        
        Args:
            device: Device instance
            verifications: List of verifications to execute
            userinterface_name: User interface name (REQUIRED)
            image_source_url: Optional image source URL
            team_id: Team ID for database recording
            context: Optional execution context
            tree_id: Optional tree ID for navigation context
            node_id: Optional node ID for navigation context
            verification_pass_condition: 'all' or 'any'
            
        Returns:
            Dict with success status, logs, and verification results
        """
        print(f"[@ExecutionOrchestrator] Executing {len(verifications)} verification(s)")
        
        def execute():
            return device.verification_executor.execute_verifications(
                verifications=verifications,
                userinterface_name=userinterface_name,
                image_source_url=image_source_url,
                team_id=team_id,
                context=context,
                tree_id=tree_id,
                node_id=node_id,
                verification_pass_condition=verification_pass_condition
            )
        
        return LoggingManager.execute_with_logging(execute)
    
    @staticmethod
    def execute_blocks(
        device,
        blocks: List[Dict[str, Any]],
        context=None
    ) -> Dict[str, Any]:
        """
        Execute standard blocks with logging
        
        Args:
            device: Device instance
            blocks: List of standard blocks to execute
            context: Optional execution context
            
        Returns:
            Dict with success status, logs, and block results
        """
        print(f"[@ExecutionOrchestrator] Executing {len(blocks)} block(s)")
        
        def execute():
            return device.standard_block_executor.execute_blocks(
                blocks=blocks,
                context=context
            )
        
        return LoggingManager.execute_with_logging(execute)

