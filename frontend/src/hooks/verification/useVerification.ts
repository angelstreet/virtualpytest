import { useState, useCallback, useEffect } from 'react';

import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { Verification } from '../../types/verification/Verification_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';
// Define interfaces for verification data structures
interface ImageComparisonDialogData {
  open: boolean;
  sourceUrl: string;
  referenceUrl: string;
  overlayUrl?: string;
  userThreshold?: number;
  matchingResult?: number;
  resultType?: 'PASS' | 'FAIL' | 'ERROR';
  imageFilter?: 'none' | 'greyscale' | 'binary';
}

export const useVerification = ({
  captureSourcePath,
  nodeId,
  treeId,
  userinterfaceName,  // Add userinterface name for reference resolution
  verificationPassCondition,  // 'all' or 'any' - from node data
}: {
  captureSourcePath?: string;
  nodeId?: string | null;
  treeId?: string | null;
  userinterfaceName?: string;  // Optional but recommended for proper reference resolution
  verificationPassCondition?: string;  // 'all' or 'any' - determines pass logic
}) => {
  // Get verification data from centralized context
  const { getAvailableVerificationTypes, currentDeviceId, currentHost } = useDeviceData();

  // State for verification execution (not data fetching)
  const [verifications, setVerifications] = useState<Verification[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Verification[]>([]);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Image comparison modal state
  const [imageComparisonDialog, setImageComparisonDialog] = useState<ImageComparisonDialogData>({
    open: false,
    sourceUrl: '',
    referenceUrl: '',
    overlayUrl: '',
    userThreshold: undefined,
    matchingResult: undefined,
    resultType: undefined,
    imageFilter: 'none',
  });

  // URL processing utilities
  const processImageUrl = useCallback((url: string): string => {
    if (!url) return '';

    console.log(`[@hook:useVerification] Processing image URL: ${url}`);

    // Handle data URLs (base64) - return as is
    if (url.startsWith('data:')) {
      console.log('[@hook:useVerification] Using data URL');
      return url;
    }

    // Handle HTTP URLs - use proxy to convert to HTTPS
    if (url.startsWith('http:')) {
      console.log('[@hook:useVerification] HTTP URL detected, using proxy');
      // URL is already processed by backend
      const proxyUrl = url;
      console.log(`[@hook:useVerification] Generated proxy URL: ${proxyUrl}`);
      return proxyUrl;
    }

    // Handle HTTPS URLs - return as is (no proxy needed)
    if (url.startsWith('https:')) {
      console.log('[@hook:useVerification] Using HTTPS URL directly');
      return url;
    }

    // For relative paths or other formats, use directly
    console.log('[@hook:useVerification] Using URL directly');
    return url;
  }, []);

  const getCacheBustedUrl = useCallback((url: string) => {
    if (!url) return url;
    const timestamp = Date.now();
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}t=${timestamp}`;
  }, []);

  // Image comparison modal handlers
  const openImageComparisonModal = useCallback((data: Partial<ImageComparisonDialogData>) => {
    setImageComparisonDialog({
      open: true,
      sourceUrl: data.sourceUrl || '',
      referenceUrl: data.referenceUrl || '',
      overlayUrl: data.overlayUrl || '',
      userThreshold: data.userThreshold,
      matchingResult: data.matchingResult,
      resultType: data.resultType,
      imageFilter: data.imageFilter || 'none',
    });
  }, []);

  const closeImageComparisonModal = useCallback(() => {
    setImageComparisonDialog((prev) => ({
      ...prev,
      open: false,
    }));
  }, []);

  // Effect to clear success message after delay
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Handle verifications change
  const handleVerificationsChange = useCallback((newVerifications: Verification[]) => {
    setVerifications(prevVerifications => {
      // Clear test results when verifications change (any change, not just length)
      if (JSON.stringify(prevVerifications) !== JSON.stringify(newVerifications)) {
        setTestResults([]);
      }
      return newVerifications;
    });
  }, []);

  // Handle test execution
  const handleTest = useCallback(
    async (event?: React.MouseEvent) => {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }

      if (verifications.length === 0) {
        console.log('[useVerification] No verifications to test');
        return;
      }

      console.log('[useVerification] === VERIFICATION TEST DEBUG ===');
      console.log(
        '[useVerification] Number of verifications before filtering:',
        verifications.length,
      );

      // Filter out empty/invalid verifications before testing
      const validVerifications = verifications.filter((verification, index) => {
        if (!verification.command || verification.command.trim() === '') {
          console.log(
            `[useVerification] Removing verification ${index}: No verification type selected`,
          );
          return false;
        }

        if (verification.verification_type === 'image') {
          const hasImagePath = verification.params?.image_path;
          if (!hasImagePath) {
            console.log(
              `[useVerification] Removing verification ${index}: No image reference specified`,
            );
            return false;
          }
        } else if (verification.verification_type === 'text') {
          const hasText = verification.params?.text && verification.params.text.trim() !== '';
          if (!hasText) {
            console.log(`[useVerification] Removing verification ${index}: No text specified`);
            return false;
          }
        } else if (verification.verification_type === 'adb') {
          const hasSearchTerm =
            verification.params?.search_term && verification.params.search_term.trim() !== '';
          if (!hasSearchTerm) {
            console.log(
              `[useVerification] Removing verification ${index}: No search term specified`,
            );
            return false;
          }
        }

        return true;
      });

      // Update verifications list if any were filtered out
      if (validVerifications.length !== verifications.length) {
        console.log(
          `[useVerification] Filtered out ${verifications.length - validVerifications.length} empty verifications`,
        );
        setVerifications(validVerifications);

        if (validVerifications.length === 0) {
          setError(
            'All verifications were empty and have been removed. Please add valid verifications.',
          );
          return;
        } else {
          setSuccessMessage(
            `Removed ${verifications.length - validVerifications.length} empty verification(s). Testing ${validVerifications.length} valid verification(s).`,
          );
        }
      }

      try {
        setLoading(true);
        setError(null);
        setTestResults([]);

        // Extract capture filename from captureSourcePath for specific capture selection
        let image_source_url = null;
        if (captureSourcePath) {
          image_source_url = captureSourcePath;
          console.log('[useVerification] Using specific capture source:', image_source_url);
        }

        console.log('[useVerification] Submitting batch verification request');
        console.log('[useVerification] Valid verifications count:', validVerifications.length);

        // Device info no longer needed - using single source of truth
        
        // Add userinterface_name to each verification for proper reference resolution
        // Also embed verification_pass_condition in FIRST verification so backend can auto-detect
        const verificationsWithUserInterface = validVerifications.map((v, index) => ({
          ...v,
          userinterface_name: userinterfaceName,  // Add userinterface_name for R2 reference download
          // Embed verification_pass_condition in first verification ONLY (backend auto-detects from verifications[0])
          ...(index === 0 && verificationPassCondition ? { verification_pass_condition: verificationPassCondition } : {})
        }));

        const batchPayload = {
          verifications: verificationsWithUserInterface,
          node_id: nodeId ,        // Use actual node_id or fallback
          tree_id: treeId,          // Use actual tree_id or fallback
          image_source_url: image_source_url,
        };

        console.log('[useVerification] Batch payload:', batchPayload);
        console.log('[useVerification] Verification areas with fuzzy coordinates:', 
          verificationsWithUserInterface.map(v => ({ 
            command: v.command, 
            area: (v.params as any)?.area,
            hasFuzzy: !!((v.params as any)?.area?.fx !== undefined || (v.params as any)?.area?.fy !== undefined)
          }))
        );

        const response = await fetch(buildServerUrl('/server/verification/executeBatch'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host_name: currentHost?.host_name,  // Single source of truth
            device_id: currentDeviceId,  // Single source of truth - no fallbacks
            ...batchPayload,
          }),
        });

        console.log(
          `[useVerification] Fetching from: /server/verification/executeBatch with host: ${currentHost?.host_name} and device: ${currentDeviceId}`,
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('[useVerification] Batch test result:', result);

        // Check if response is async (execution_id present) or synchronous
        if (result.execution_id) {
          console.log('[useVerification] ✅ Async execution started:', result.execution_id);

          // Poll for completion
          const statusUrl = buildServerUrl(`/server/verification/execution/${result.execution_id}/status?host_name=${currentHost?.host_name}&device_id=${currentDeviceId}`);
          
          let attempts = 0;
          const maxAttempts = 30; // 30 * 1000ms = 30 seconds max
          
          while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000)); // Poll every 1s
            attempts++;
            
            const statusResult = await fetch(statusUrl);
            const statusResponse = await statusResult.json();
            
            console.log(`[useVerification] 🔄 Polling attempt ${attempts}/${maxAttempts}:`, {
              status: statusResponse.status,
              progress: statusResponse.progress,
              success: statusResponse.success
            });
            
            // Check if execution is complete (status: completed or error with results)
            // "error" status means verification failed (not met), but execution completed successfully
            const isCompleted = statusResponse.status === 'completed' || 
                               (statusResponse.status === 'error' && statusResponse.progress === 100);
            
            if (isCompleted && statusResponse.result) {
              const finalResult = statusResponse.result;
              
              console.log('[useVerification] ✅ Execution completed with results:', {
                status: statusResponse.status,
                totalCount: finalResult.total_count,
                passedCount: finalResult.passed_count,
                failedCount: finalResult.failed_count,
                hasResults: !!finalResult.results
              });
              
              // Always set test results regardless of overall batch success/failure
              setTestResults(finalResult.results || []);
              console.log('[useVerification] Test results set:', finalResult.results);

              const passedCount = finalResult.passed_count || 0;
              const totalCount = finalResult.total_count || 0;

              if (finalResult.success) {
                setSuccessMessage(`Verification completed: ${passedCount}/${totalCount} passed`);
              } else {
                setSuccessMessage(`Test completed: ${passedCount}/${totalCount} passed`);
              }
              return;
            } else if (statusResponse.status === 'error' && !statusResponse.result) {
              // Only throw error if there's no result data (actual execution failure)
              throw new Error(statusResponse.error || 'Verification execution failed');
            } else if (!statusResponse.success && statusResponse.status === 'pending') {
              // Still running, continue polling
              console.log(`[useVerification] ⏳ Still running (progress: ${statusResponse.progress || 0}%)`);
            }
            
            // Check for timeout or other terminal states
            if (statusResponse.status === 'timeout') {
              throw new Error('Verification execution timeout');
            }
          }
          
          if (attempts >= maxAttempts) {
            throw new Error('Verification execution timeout - no response after 30 seconds');
          }
        } else {
          // Synchronous response (backward compatibility)
          // Always set test results regardless of overall batch success/failure
          setTestResults(result.results || []);
          console.log('[useVerification] Test results set:', result.results);

          const passedCount = result.passed_count || 0;
          const totalCount = result.total_count || 0;

          if (result.success) {
            setSuccessMessage(`Verification completed: ${passedCount}/${totalCount} passed`);
          } else {
            setSuccessMessage(`Test completed: ${passedCount}/${totalCount} passed`);
          }
        }
      } catch (error) {
        console.error('[useVerification] Error during verification test:', error);
        setError(error instanceof Error ? error.message : 'Unknown error during verification test');
      } finally {
        setLoading(false);
      }
    },
    [verifications, currentHost, currentDeviceId, captureSourcePath, nodeId, treeId, userinterfaceName],
  );

  return {
    availableVerificationTypes: getAvailableVerificationTypes(), // Get from context
    verifications,
    loading,
    error,
    testResults,
    successMessage,
    handleVerificationsChange,
    handleTest,
    currentHost,
    currentDeviceId,
    // Image comparison modal
    imageComparisonDialog,
    openImageComparisonModal,
    closeImageComparisonModal,
    // URL processing utilities
    processImageUrl,
    getCacheBustedUrl,
  };
};

export type UseVerificationType = ReturnType<typeof useVerification>;
