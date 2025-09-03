"""API routes for VirtualPyTest Backend Server."""

# Import all server route modules - using relative imports within package
from . import server_system_routes
from . import server_web_routes  
from . import server_rec_routes
from . import common_core_routes
from . import server_control_routes
from . import server_actions_routes
from . import server_device_routes
from . import server_navigation_routes
from . import server_navigation_trees_routes
from . import server_pathfinding_routes
from . import server_alerts_routes
from . import server_verification_common_routes
from . import server_heatmap_routes
from . import server_navigation_execution_routes
from . import server_devicemodel_routes
from . import server_remote_routes
from . import server_aiagent_routes
from . import server_aitestcase_routes
from . import server_desktop_bash_routes
from . import server_power_routes
from . import server_desktop_pyautogui_routes
from . import server_stream_proxy_routes
from . import server_validation_routes
from . import server_campaign_routes
from . import server_testcase_routes
from . import server_userinterface_routes
from . import server_mcp_routes
from . import server_av_routes
from . import server_execution_results_routes
from . import server_script_routes
from . import server_script_results_routes
from . import server_metrics_routes
from . import server_campaign_results_routes
from . import server_frontend_routes 