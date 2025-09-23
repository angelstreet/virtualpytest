"""
Campaign Service

Handles campaign management business logic that was previously in routes.
This service manages campaign CRUD operations and related functionality.
"""

from typing import Dict, Any, List, Optional
from shared.src.lib.supabase.campaign_executions_db import get_campaign_results
from shared.src.lib.utils.app_utils import check_supabase, get_team_id

class CampaignService:
    """Service for handling campaign management business logic"""
    
    def get_all_campaigns(self, team_id: str, user_agent: str = None, referer: str = None) -> Dict[str, Any]:
        """Get all campaigns for a team"""
        try:
            # Log caller information (moved from route)
            print(f"[CampaignService:get_all_campaigns] 🔍 CALLER INFO:")
            print(f"  - User-Agent: {user_agent or 'Unknown'}")
            print(f"  - Referer: {referer or 'Unknown'}")
            print(f"  - Team ID: {team_id}")
            
            if not team_id:
                return {
                    'success': False,
                    'error': 'team_id is required',
                    'status_code': 400
                }
            
            print(f"[CampaignService] Getting all campaigns for team: {team_id}")
            
            # Check if Supabase is available
            supabase_error = check_supabase()
            if supabase_error:
                return {
                    'success': False,
                    'error': f'Database not available: {supabase_error}',
                    'status_code': 503
                }
            
            # Business logic: Get campaigns from database
            # Note: This would need the actual campaign database function
            # For now, returning empty list as placeholder
            campaigns = []  # TODO: Replace with actual get_all_campaigns(team_id) call
            
            print(f"[CampaignService] Found {len(campaigns)} campaigns")
            
            return {
                'success': True,
                'campaigns': campaigns,
                'count': len(campaigns)
            }
            
        except Exception as e:
            print(f"[CampaignService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def get_campaign(self, campaign_id: str, team_id: str) -> Dict[str, Any]:
        """Get a specific campaign"""
        try:
            if not campaign_id or not team_id:
                return {
                    'success': False,
                    'error': 'campaign_id and team_id are required',
                    'status_code': 400
                }
            
            print(f"[CampaignService] Getting campaign: {campaign_id}")
            
            # Business logic: Get campaign from database
            # Note: This would need the actual campaign database function
            campaign = None  # TODO: Replace with actual get_campaign(campaign_id, team_id) call
            
            if campaign:
                return {
                    'success': True,
                    'campaign': campaign
                }
            else:
                return {
                    'success': False,
                    'error': 'Campaign not found',
                    'status_code': 404
                }
                
        except Exception as e:
            print(f"[CampaignService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def create_campaign(self, campaign_data: Dict[str, Any], team_id: str, user_id: str) -> Dict[str, Any]:
        """Create a new campaign"""
        try:
            if not campaign_data or not team_id or not user_id:
                return {
                    'success': False,
                    'error': 'campaign_data, team_id, and user_id are required',
                    'status_code': 400
                }
            
            campaign_name = campaign_data.get('name')
            if not campaign_name:
                return {
                    'success': False,
                    'error': 'Campaign name is required',
                    'status_code': 400
                }
            
            print(f"[CampaignService] Creating campaign: {campaign_name}")
            
            # Add metadata to campaign data
            campaign_data['team_id'] = team_id
            campaign_data['user_id'] = user_id
            
            # Business logic: Create campaign in database
            # Note: This would need the actual campaign database function
            created_campaign = None  # TODO: Replace with actual create_campaign(campaign_data) call
            
            if created_campaign:
                return {
                    'success': True,
                    'campaign': created_campaign,
                    'message': 'Campaign created successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create campaign',
                    'status_code': 500
                }
                
        except Exception as e:
            print(f"[CampaignService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def update_campaign(self, campaign_id: str, campaign_data: Dict[str, Any], team_id: str, user_id: str) -> Dict[str, Any]:
        """Update an existing campaign"""
        try:
            if not campaign_id or not campaign_data or not team_id or not user_id:
                return {
                    'success': False,
                    'error': 'campaign_id, campaign_data, team_id, and user_id are required',
                    'status_code': 400
                }
            
            print(f"[CampaignService] Updating campaign: {campaign_id}")
            
            # Add metadata to campaign data
            campaign_data['id'] = campaign_id
            campaign_data['team_id'] = team_id
            campaign_data['user_id'] = user_id
            
            # Business logic: Update campaign in database
            # Note: This would need the actual campaign database function
            updated_campaign = None  # TODO: Replace with actual update_campaign(campaign_data) call
            
            if updated_campaign:
                return {
                    'success': True,
                    'campaign': updated_campaign,
                    'message': 'Campaign updated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Campaign not found or failed to update',
                    'status_code': 404
                }
                
        except Exception as e:
            print(f"[CampaignService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def delete_campaign(self, campaign_id: str, team_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a campaign"""
        try:
            if not campaign_id or not team_id or not user_id:
                return {
                    'success': False,
                    'error': 'campaign_id, team_id, and user_id are required',
                    'status_code': 400
                }
            
            print(f"[CampaignService] Deleting campaign: {campaign_id}")
            
            # Business logic: Delete campaign from database
            # Note: This would need the actual campaign database function
            success = False  # TODO: Replace with actual delete_campaign(campaign_id, team_id) call
            
            if success:
                return {
                    'success': True,
                    'message': 'Campaign deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Campaign not found or failed to delete',
                    'status_code': 404
                }
                
        except Exception as e:
            print(f"[CampaignService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def get_campaign_results(self, campaign_id: str, team_id: str) -> Dict[str, Any]:
        """Get results for a campaign"""
        try:
            if not campaign_id or not team_id:
                return {
                    'success': False,
                    'error': 'campaign_id and team_id are required',
                    'status_code': 400
                }
            
            print(f"[CampaignService] Getting results for campaign: {campaign_id}")
            
            # Business logic: Get campaign results from database
            results = get_campaign_results(campaign_id)
            
            if results:
                return {
                    'success': True,
                    'results': results
                }
            else:
                return {
                    'success': False,
                    'error': 'No results found for campaign',
                    'status_code': 404
                }
                
        except Exception as e:
            print(f"[CampaignService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }

# Singleton instance
campaign_service = CampaignService()
