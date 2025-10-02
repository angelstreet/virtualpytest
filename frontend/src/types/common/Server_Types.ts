/**
 * Server-related type definitions
 * 
 * Centralizes all server data structures used across the application
 */

import { Host } from './Host_Types';
import { SystemStats } from '../pages/Dashboard_Types';

/**
 * Server information returned from backend
 */
export interface ServerInfo {
  server_name: string;           // Server name from SERVER_NAME env (e.g., "RPI1-server")
  server_url: string;             // Full server URL for API calls (e.g., "https://dev.virtualpytest.com:443")
  server_url_display: string;     // Cleaned URL for display (e.g., "dev.virtualpytest.com")
  server_port: string;            // Server port (e.g., "443")
  system_stats?: SystemStats;     // Server's own system stats (CPU, RAM, Disk, etc.)
}

/**
 * Server data with hosts
 * Returned from /server/system/getAllHosts endpoint for each server
 */
export interface ServerHostData {
  server_info: ServerInfo;
  hosts: Host[];
}

/**
 * Server manager state
 */
export interface ServerManagerState {
  selectedServer: string;         // Currently selected server URL (full URL)
  availableServers: string[];     // List of all configured server URLs
  serverHostsData: ServerHostData[]; // Data from all servers
  isLoading: boolean;
  error: string | null;
}
