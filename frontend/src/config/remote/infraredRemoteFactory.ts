import { InfraredRemoteConfig, InfraredRemoteType } from './infraredRemoteBase';
import { samsungRemoteConfig } from './samsungRemote';
import { eosRemoteConfig } from './eosRemote';
import { firetvRemoteConfig } from './firetvRemote';
import { appleTvRemoteConfig } from './appleTvRemote';

/**
 * Factory function to get the appropriate infrared remote configuration
 * based on the IR type from environment variables
 */
export function getInfraredRemoteConfig(irType: string): InfraredRemoteConfig {
  // Map IR type to specific config
  const irTypeKey = irType.toLowerCase() as InfraredRemoteType;
  
  switch (irTypeKey) {
    case 'samsung':
      console.log(`[@config:infraredRemoteFactory] Loading Samsung remote config`);
      return samsungRemoteConfig;
    
    case 'eos':
      console.log(`[@config:infraredRemoteFactory] Loading EOS remote config`);
      return eosRemoteConfig;
    
    case 'firetv':
      console.log(`[@config:infraredRemoteFactory] Loading FireTV remote config`);
      return firetvRemoteConfig;
    
    case 'appletv':
      console.log(`[@config:infraredRemoteFactory] Loading Apple TV remote config`);
      return appleTvRemoteConfig;
    
    default:
      console.warn(`[@config:infraredRemoteFactory] Unknown IR type: ${irType}, falling back to Samsung`);
      return samsungRemoteConfig; // Default fallback
  }
}

/**
 * Get all available infrared remote types
 */
export function getAvailableInfraredRemoteTypes(): InfraredRemoteType[] {
  return ['samsung', 'eos', 'firetv', 'appletv'];
}

/**
 * Check if an IR type is supported
 */
export function isInfraredRemoteTypeSupported(irType: string): boolean {
  const supportedTypes = getAvailableInfraredRemoteTypes();
  return supportedTypes.includes(irType.toLowerCase() as InfraredRemoteType);
}
