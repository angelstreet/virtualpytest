/**
 * User Interface Hook
 *
 * This hook handles all user interface management functionality.
 */

import { useMemo } from 'react';

import { UserInterface, UserInterfaceCreatePayload } from '../../types/pages/UserInterface_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';

// 24-hour cache for userinterfaces
const userInterfaceCache = new Map<string, {data: Promise<UserInterface>, timestamp: number}>();
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

function getCachedInterface(name: string) {
  const cached = userInterfaceCache.get(name);
  if (cached && (Date.now() - cached.timestamp) < CACHE_TTL) {
    return cached.data;
  }
  if (cached) {
    userInterfaceCache.delete(name); // Remove expired
  }
  return null;
}

function setCachedInterface(name: string, data: Promise<UserInterface>) {
  userInterfaceCache.set(name, {data, timestamp: Date.now()});
}

export const useUserInterface = () => {
  /**
   * Get all user interfaces
   */
  const getAllUserInterfaces = useMemo(
    () => async (): Promise<UserInterface[]> => {
      try {
        console.log(
          '[@hook:useUserInterface:getAllUserInterfaces] Fetching all user interfaces from server',
        );

        const response = await fetch(buildServerUrl('/server/userinterface/getAllUserInterfaces'));

        console.log(
          '[@hook:useUserInterface:getAllUserInterfaces] Response status:',
          response.status,
        );
        console.log(
          '[@hook:useUserInterface:getAllUserInterfaces] Response headers:',
          response.headers.get('content-type'),
        );

        if (!response.ok) {
          // Try to get error message from response
          let errorMessage = `Failed to fetch user interfaces: ${response.status} ${response.statusText}`;
          try {
            const errorData = await response.text();
            console.log(
              '[@hook:useUserInterface:getAllUserInterfaces] Error response body:',
              errorData,
            );

            // Check if it's JSON
            if (response.headers.get('content-type')?.includes('application/json')) {
              const jsonError = JSON.parse(errorData);
              errorMessage = jsonError.error || errorMessage;
            } else {
              // It's HTML or other content, likely a proxy/server issue
              if (errorData.includes('<!doctype') || errorData.includes('<html')) {
                errorMessage =
                  'Server endpoint not available. Make sure the Flask server is running on the correct port and the proxy is configured properly.';
              }
            }
          } catch {
            console.log(
              '[@hook:useUserInterface:getAllUserInterfaces] Could not parse error response',
            );
          }

          throw new Error(errorMessage);
        }

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error(
            `Expected JSON response but got ${contentType}. This usually means the Flask server is not running or the proxy is misconfigured.`,
          );
        }

        const userInterfaces = await response.json();
        console.log(
          `[@hook:useUserInterface:getAllUserInterfaces] Successfully loaded ${userInterfaces?.length || 0} user interfaces`,
        );
        return userInterfaces || [];
      } catch (error) {
        console.error(
          '[@hook:useUserInterface:getAllUserInterfaces] Error fetching user interfaces:',
          error,
        );
        throw error;
      }
    },
    [],
  );

  /**
   * Get a specific user interface by ID
   */
  const getUserInterface = useMemo(
    () =>
      async (id: string): Promise<UserInterface> => {
        try {
          console.log(
            `[@hook:useUserInterface:getUserInterface] Fetching user interface ${id} from server`,
          );

          const response = await fetch(buildServerUrl(`/server/userinterface/getUserInterface/${id}`));
          if (!response.ok) {
            if (response.status === 404) {
              throw new Error('User interface not found');
            }
            throw new Error(
              `Failed to fetch user interface: ${response.status} ${response.statusText}`,
            );
          }

          const userInterface = await response.json();
          console.log(
            `[@hook:useUserInterface:getUserInterface] Successfully loaded user interface: ${userInterface.name}`,
          );
          return userInterface;
        } catch (error) {
          console.error(
            `[@hook:useUserInterface:getUserInterface] Error fetching user interface ${id}:`,
            error,
          );
          throw error;
        }
      },
    [],
  );

  /**
   * Get a specific user interface by name
   */
  const getUserInterfaceByName = useMemo(
    () =>
      async (name: string): Promise<UserInterface> => {
        // Check 24-hour cache first
        const cached = getCachedInterface(name);
        if (cached) {
          console.log(
            `[@hook:useUserInterface:getUserInterfaceByName] Using 24h cached user interface for name: ${name}`,
          );
          return cached;
        }

        // Create and cache the promise
        const fetchPromise = (async () => {
          try {
            console.log(
              `[@hook:useUserInterface:getUserInterfaceByName] Fetching user interface by name: ${name}`,
            );

            const response = await fetch(buildServerUrl(`/server/userinterface/getUserInterfaceByName/${name}`));
            if (!response.ok) {
              if (response.status === 404) {
                throw new Error('User interface not found');
              }
              throw new Error(
                `Failed to fetch user interface: ${response.status} ${response.statusText}`,
              );
            }

            const userInterface = await response.json();
            console.log(
              `[@hook:useUserInterface:getUserInterfaceByName] Successfully loaded user interface: ${userInterface.name} (ID: ${userInterface.id})`,
            );
            return userInterface;
          } catch (error) {
            console.error(
              `[@hook:useUserInterface:getUserInterfaceByName] Error fetching user interface by name ${name}:`,
              error,
            );
            throw error;
          }
        })();

        // Cache for 24 hours
        setCachedInterface(name, fetchPromise);
        return fetchPromise;
      },
    [],
  );

  /**
   * Create a new user interface
   */
  const createUserInterface = useMemo(
    () =>
      async (payload: UserInterfaceCreatePayload): Promise<UserInterface> => {
        try {
          console.log(
            '[@hook:useUserInterface:createUserInterface] Creating user interface:',
            payload,
          );

          const response = await fetch(buildServerUrl('/server/userinterface/createUserInterface'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
          });

          const result = await response.json();

          if (!response.ok) {
            throw new Error(
              result.error ||
                `Failed to create user interface: ${response.status} ${response.statusText}`,
            );
          }

          if (result.status === 'success' && result.userinterface) {
            console.log(
              `[@hook:useUserInterface:createUserInterface] Successfully created user interface: ${result.userinterface.name}`,
            );
            return result.userinterface;
          } else {
            throw new Error(result.error || 'Failed to create user interface');
          }
        } catch (error) {
          console.error(
            '[@hook:useUserInterface:createUserInterface] Error creating user interface:',
            error,
          );
          throw error;
        }
      },
    [],
  );

  /**
   * Update an existing user interface
   */
  const updateUserInterface = useMemo(
    () =>
      async (id: string, payload: UserInterfaceCreatePayload): Promise<UserInterface> => {
        try {
          console.log(
            `[@hook:useUserInterface:updateUserInterface] Updating user interface ${id}:`,
            payload,
          );

          const response = await fetch(buildServerUrl(`/server/userinterface/updateUserInterface/${id}`), {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
          });

          const result = await response.json();

          if (!response.ok) {
            throw new Error(
              result.error ||
                `Failed to update user interface: ${response.status} ${response.statusText}`,
            );
          }

          if (result.status === 'success' && result.userinterface) {
            console.log(
              `[@hook:useUserInterface:updateUserInterface] Successfully updated user interface: ${result.userinterface.name}`,
            );
            return result.userinterface;
          } else {
            throw new Error(result.error || 'Failed to update user interface');
          }
        } catch (error) {
          console.error(
            `[@hook:useUserInterface:updateUserInterface] Error updating user interface ${id}:`,
            error,
          );
          throw error;
        }
      },
    [],
  );

  /**
   * Delete a user interface
   */
  const deleteUserInterface = useMemo(
    () =>
      async (id: string): Promise<void> => {
        try {
          console.log(`[@hook:useUserInterface:deleteUserInterface] Deleting user interface ${id}`);

          const response = await fetch(buildServerUrl(`/server/userinterface/deleteUserInterface/${id}`), {
            method: 'DELETE',
          });

          const result = await response.json();

          if (!response.ok) {
            throw new Error(
              result.error ||
                `Failed to delete user interface: ${response.status} ${response.statusText}`,
            );
          }

          if (result.status === 'success') {
            console.log(
              `[@hook:useUserInterface:deleteUserInterface] Successfully deleted user interface ${id}`,
            );
          } else {
            throw new Error(result.error || 'Failed to delete user interface');
          }
        } catch (error) {
          console.error(
            `[@hook:useUserInterface:deleteUserInterface] Error deleting user interface ${id}:`,
            error,
          );
          throw error;
        }
      },
    [],
  );

  /**
   * Create empty navigation config for a user interface
   */
  const createEmptyNavigationConfig = useMemo(
    () =>
      async (userInterface: UserInterface): Promise<void> => {
        try {
          console.log(
            `[@hook:useUserInterface:createEmptyNavigationConfig] Creating empty navigation config for: ${userInterface.name}`,
          );

          const response = await fetch(
            buildServerUrl(`/server/navigation/config/createEmpty/${encodeURIComponent(userInterface.name)}`),
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                userinterface_data: {
                  id: userInterface.id,
                  name: userInterface.name,
                  models: userInterface.models,
                  min_version: userInterface.min_version,
                  max_version: userInterface.max_version,
                },
                commit_message: `Create empty navigation config: ${userInterface.name}`,
              }),
            },
          );

          const result = await response.json();

          if (!response.ok) {
            throw new Error(
              result.error ||
                `Failed to create navigation config: ${response.status} ${response.statusText}`,
            );
          }

          if (result.success) {
            console.log(
              `[@hook:useUserInterface:createEmptyNavigationConfig] Successfully created navigation config for: ${userInterface.name}`,
            );
          } else {
            throw new Error(result.error || 'Failed to create navigation config');
          }
        } catch (error) {
          console.error(
            `[@hook:useUserInterface:createEmptyNavigationConfig] Error creating navigation config for ${userInterface.name}:`,
            error,
          );
          throw error;
        }
      },
    [],
  );

  /**
   * Get compatible user interfaces for a device model
   */
  const getCompatibleInterfaces = useMemo(
    () =>
      async (deviceModel: string): Promise<UserInterface[]> => {
        if (!deviceModel) {
          console.warn('[@hook:useUserInterface:getCompatibleInterfaces] No device model provided');
          return [];
        }

        try {
          console.log(
            `[@hook:useUserInterface:getCompatibleInterfaces] Fetching compatible interfaces for device model: ${deviceModel}`,
          );

          const response = await fetch(
            buildServerUrl(`/server/userinterface/getCompatibleInterfaces?device_model=${deviceModel}`)
          );
          
          if (!response.ok) {
            throw new Error(`Failed to fetch compatible interfaces: ${response.status}`);
          }

          const data = await response.json();

          if (data.success && data.interfaces) {
            console.log(
              `[@hook:useUserInterface:getCompatibleInterfaces] Found ${data.interfaces.length} compatible interfaces`,
            );
            return data.interfaces;
          } else {
            console.log(
              `[@hook:useUserInterface:getCompatibleInterfaces] No compatible interfaces found for ${deviceModel}`,
            );
            return [];
          }
        } catch (error) {
          console.error(
            `[@hook:useUserInterface:getCompatibleInterfaces] Error fetching compatible interfaces for ${deviceModel}:`,
            error,
          );
          return [];
        }
      },
    [],
  );

  return {
    getAllUserInterfaces,
    getUserInterface,
    getUserInterfaceByName,
    createUserInterface,
    updateUserInterface,
    deleteUserInterface,
    createEmptyNavigationConfig,
    getCompatibleInterfaces,
  };
};
