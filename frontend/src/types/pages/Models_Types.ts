// Simple model interface matching database
export interface Model {
  id: string;
  name: string;
  types: string[];
  version: string;
  description: string;
  controllers?: { [key: string]: string }; // Controller type -> value mapping
  created_at?: string;
  updated_at?: string;
}

// Create payload type
export interface ModelCreatePayload {
  name: string;
  types: string[];
  version: string;
  description: string;
  controllers?: { [key: string]: string };
}
