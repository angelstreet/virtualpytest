import React from 'react';
import { Box } from '@mui/material';
import { RemotePanel } from '../../controller/remote/RemotePanel';
import { DesktopPanel } from '../../controller/desktop/DesktopPanel';
import { WebPanel } from '../../controller/web/WebPanel';
import { VNCStream } from '../../controller/av/VNCStream';
import { HDMIStream } from '../../controller/av/HDMIStream';
import { DEFAULT_DEVICE_RESOLUTION } from '../../../config/deviceResolutions';

interface TestCaseBuilderPanelsProps {
  // Show Panel Conditions
  showRemotePanel: boolean;
  showAVPanel: boolean;
  
  // Host & Device
  selectedHost: any;
  selectedDeviceId: string | null;
  isControlActive: boolean;
  userinterfaceName: string;
  
  // AV Panel State
  isAVPanelCollapsed: boolean;
  isAVPanelMinimized: boolean;
  captureMode: string;
  isVerificationVisible: boolean;
  
  // Handlers
  handleDisconnectComplete: () => void;
  handleAVPanelCollapsedChange: (collapsed: boolean) => void;
  handleAVPanelMinimizedChange: (minimized: boolean) => void;
  handleCaptureModeChange: (mode: 'stream' | 'screenshot' | 'video') => void;
}

export const TestCaseBuilderPanels: React.FC<TestCaseBuilderPanelsProps> = ({
  showRemotePanel,
  showAVPanel,
  selectedHost,
  selectedDeviceId,
  isControlActive,
  userinterfaceName,
  isAVPanelCollapsed,
  isAVPanelMinimized,
  captureMode,
  isVerificationVisible,
  handleDisconnectComplete,
  handleAVPanelCollapsedChange,
  handleAVPanelMinimizedChange,
  handleCaptureModeChange,
}) => {
  const selectedDevice = selectedHost?.devices?.find((d: any) => d.device_id === selectedDeviceId);
  const deviceModel = selectedDevice?.device_model;
  const remoteCapability = selectedDevice?.device_capabilities?.remote;
  const hasMultipleRemotes = Array.isArray(remoteCapability) || deviceModel === 'fire_tv';
  const isDesktopDevice = deviceModel === 'host_vnc';

  return (
    <>
      {/* Remote/Desktop Panel */}
      {showRemotePanel && selectedHost && selectedDeviceId && isControlActive && (
        <>
          {isDesktopDevice ? (
            // Desktop device: DesktopPanel + WebPanel
            <>
              <DesktopPanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel || 'host_vnc'}
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                initialCollapsed={true}
              />
              <WebPanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel || 'host_vnc'}
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                initialCollapsed={true}
              />
            </>
          ) : hasMultipleRemotes && deviceModel === 'fire_tv' ? (
            // Fire TV: AndroidTvRemote + InfraredRemote
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'row',
                gap: 2,
                position: 'absolute',
                right: 10,
                bottom: 20,
                zIndex: 1000,
                height: 'auto',
              }}
            >
              <RemotePanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel || 'fire_tv'}
                remoteType="android_tv"
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                streamCollapsed={isAVPanelCollapsed}
                streamMinimized={isAVPanelMinimized}
                streamHidden={showAVPanel}
                captureMode={captureMode}
                initialCollapsed={true}
              />
              <RemotePanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel || 'fire_tv'}
                remoteType="ir_remote"
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                streamCollapsed={isAVPanelCollapsed}
                streamMinimized={isAVPanelMinimized}
                streamHidden={showAVPanel}
                captureMode={captureMode}
                initialCollapsed={true}
              />
            </Box>
          ) : hasMultipleRemotes ? (
            // Other devices with multiple remotes
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'row',
                gap: 2,
                position: 'absolute',
                right: 10,
                bottom: 20,
                zIndex: 1000,
                height: 'auto',
              }}
            >
              {((Array.isArray(remoteCapability) ? remoteCapability : [remoteCapability]) as string[])
                .filter(Boolean)
                .map((remoteType: string, index: number) => (
                  <RemotePanel
                    key={`${selectedDeviceId}-${remoteType}`}
                    host={selectedHost}
                    deviceId={selectedDeviceId}
                    deviceModel={deviceModel || 'unknown'}
                    remoteType={remoteType}
                    isConnected={isControlActive}
                    onReleaseControl={handleDisconnectComplete}
                    deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                    streamCollapsed={isAVPanelCollapsed}
                    streamMinimized={isAVPanelMinimized}
                    captureMode={captureMode}
                    initialCollapsed={index > 0}
                  />
                ))}
            </Box>
          ) : (
            // Single remote device
            <RemotePanel
              host={selectedHost}
              deviceId={selectedDeviceId}
              deviceModel={deviceModel || 'unknown'}
              isConnected={isControlActive}
              onReleaseControl={handleDisconnectComplete}
              deviceResolution={DEFAULT_DEVICE_RESOLUTION}
              streamCollapsed={isAVPanelCollapsed}
              streamMinimized={isAVPanelMinimized}
              captureMode={captureMode}
              isVerificationVisible={isVerificationVisible}
              isNavigationEditorContext={false}
            />
          )}
        </>
      )}

      {/* AV Panel */}
      {showAVPanel && selectedHost && selectedDeviceId && (
        <Box
          sx={{
            position: 'absolute',
            left: 240,
            bottom: 20,
            zIndex: 999,
          }}
        >
          {deviceModel === 'host_vnc' ? (
            <VNCStream
              host={selectedHost}
              deviceId={selectedDeviceId}
              deviceModel={deviceModel}
              isControlActive={isControlActive}
              userinterfaceName={userinterfaceName}
              onCollapsedChange={handleAVPanelCollapsedChange}
              onMinimizedChange={handleAVPanelMinimizedChange}
              onCaptureModeChange={handleCaptureModeChange}
            />
          ) : (
            <HDMIStream
              host={selectedHost}
              deviceId={selectedDeviceId}
              deviceModel={deviceModel}
              isControlActive={isControlActive}
              userinterfaceName={userinterfaceName}
              onCollapsedChange={handleAVPanelCollapsedChange}
              onMinimizedChange={handleAVPanelMinimizedChange}
              onCaptureModeChange={handleCaptureModeChange}
              deviceResolution={DEFAULT_DEVICE_RESOLUTION}
            />
          )}
        </Box>
      )}
    </>
  );
};

