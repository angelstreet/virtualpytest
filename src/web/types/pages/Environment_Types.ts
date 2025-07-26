// Environment and configuration interfaces
export interface EnvironmentProfile {
  id: string;
  name: string;
  device_name: string;
  remote_controller_id?: string;
  av_controller_id?: string;
  verification_controller_id?: string;
  team_id: string;
  created_at?: string;
  updated_at?: string;
}

// Environment configuration interface
export interface EnvironmentConfig {
  id: string;
  name: string;
  description?: string;
  environment_type: 'prod' | 'preprod' | 'dev' | 'staging';
  default_settings: { [key: string]: any };
  team_id: string;
  created_at?: string;
  updated_at?: string;
}

// Environment validation result
export interface EnvironmentValidation {
  profile_id: string;
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  validated_at: string;
} 