/**
 * Fire TV Remote Configuration
 * Defines button layout and styling for Fire TV infrared remote
 */

import { InfraredRemoteConfig, INFRARED_REMOTE_DEFAULTS } from './infraredRemoteBase';

export const firetvRemoteConfig: InfraredRemoteConfig = {
  remote_info: {
    ...INFRARED_REMOTE_DEFAULTS.remote_info,
    name: 'Fire TV Remote',
    image_url: '/fire_tv_remote.png',
  },
  panel_layout: {
    ...INFRARED_REMOTE_DEFAULTS.panel_layout,
  },
  remote_layout: {
    ...INFRARED_REMOTE_DEFAULTS.remote_layout,
  },
  button_layout: {
    ...INFRARED_REMOTE_DEFAULTS.button_layout,
    buttons: [
      // Power button
      { key: 'POWER', label: 'Power', position: { x: 50, y: 10 }, size: { width: 45, height: 25 }, shape: 'rectangle', comment: 'Power on/off' },
      
      // Navigation pad
      { key: 'UP', label: '↑', position: { x: 50, y: 35 }, size: { width: 30, height: 20 }, shape: 'rectangle', comment: 'Navigate up' },
      { key: 'LEFT', label: '←', position: { x: 25, y: 50 }, size: { width: 30, height: 20 }, shape: 'rectangle', comment: 'Navigate left' },
      { key: 'OK', label: 'OK', position: { x: 50, y: 50 }, size: { width: 30, height: 20 }, shape: 'circle', comment: 'Select/OK' },
      { key: 'RIGHT', label: '→', position: { x: 75, y: 50 }, size: { width: 30, height: 20 }, shape: 'rectangle', comment: 'Navigate right' },
      { key: 'DOWN', label: '↓', position: { x: 50, y: 65 }, size: { width: 30, height: 20 }, shape: 'rectangle', comment: 'Navigate down' },
      
      // Control buttons
      { key: 'BACK', label: 'Back', position: { x: 20, y: 80 }, size: { width: 35, height: 20 }, shape: 'rectangle', comment: 'Go back' },
      { key: 'HOME', label: 'Home', position: { x: 50, y: 80 }, size: { width: 35, height: 20 }, shape: 'rectangle', comment: 'Home screen' },
      { key: 'MENU', label: 'Menu', position: { x: 80, y: 80 }, size: { width: 35, height: 20 }, shape: 'rectangle', comment: 'Menu' },
      
      // Media controls
      { key: 'PLAY_PAUSE', label: '⏯', position: { x: 30, y: 100 }, size: { width: 25, height: 20 }, shape: 'rectangle', comment: 'Play/Pause' },
      { key: 'REWIND', label: '⏪', position: { x: 15, y: 100 }, size: { width: 25, height: 20 }, shape: 'rectangle', comment: 'Rewind' },
      { key: 'FORWARD', label: '⏩', position: { x: 45, y: 100 }, size: { width: 25, height: 20 }, shape: 'rectangle', comment: 'Fast forward' },
      
      // Volume controls
      { key: 'VOLUME_UP', label: 'Vol+', position: { x: 75, y: 100 }, size: { width: 30, height: 15 }, shape: 'rectangle', comment: 'Volume up' },
      { key: 'VOLUME_DOWN', label: 'Vol-', position: { x: 75, y: 115 }, size: { width: 30, height: 15 }, shape: 'rectangle', comment: 'Volume down' },
      { key: 'MUTE', label: 'Mute', position: { x: 75, y: 130 }, size: { width: 30, height: 15 }, shape: 'rectangle', comment: 'Mute' },
      
      // Number pad
      { key: 'KEY_1', label: '1', position: { x: 15, y: 150 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 1' },
      { key: 'KEY_2', label: '2', position: { x: 40, y: 150 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 2' },
      { key: 'KEY_3', label: '3', position: { x: 65, y: 150 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 3' },
      { key: 'KEY_4', label: '4', position: { x: 15, y: 175 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 4' },
      { key: 'KEY_5', label: '5', position: { x: 40, y: 175 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 5' },
      { key: 'KEY_6', label: '6', position: { x: 65, y: 175 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 6' },
      { key: 'KEY_7', label: '7', position: { x: 15, y: 200 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 7' },
      { key: 'KEY_8', label: '8', position: { x: 40, y: 200 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 8' },
      { key: 'KEY_9', label: '9', position: { x: 65, y: 200 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 9' },
      { key: 'KEY_0', label: '0', position: { x: 40, y: 225 }, size: { width: 20, height: 20 }, shape: 'rectangle', comment: 'Number 0' },
    ],
  },
  button_layout_recmodal: {
    ...INFRARED_REMOTE_DEFAULTS.button_layout_recmodal,
    buttons: [
      // Compact layout for recording modal
      { key: 'POWER', label: 'PWR', position: { x: 10, y: 5 }, size: { width: 25, height: 15 }, shape: 'rectangle', comment: 'Power' },
      { key: 'UP', label: '↑', position: { x: 45, y: 20 }, size: { width: 20, height: 15 }, shape: 'rectangle', comment: 'Up' },
      { key: 'LEFT', label: '←', position: { x: 20, y: 35 }, size: { width: 20, height: 15 }, shape: 'rectangle', comment: 'Left' },
      { key: 'OK', label: 'OK', position: { x: 45, y: 35 }, size: { width: 20, height: 15 }, shape: 'circle', comment: 'OK' },
      { key: 'RIGHT', label: '→', position: { x: 70, y: 35 }, size: { width: 20, height: 15 }, shape: 'rectangle', comment: 'Right' },
      { key: 'DOWN', label: '↓', position: { x: 45, y: 50 }, size: { width: 20, height: 15 }, shape: 'rectangle', comment: 'Down' },
      { key: 'BACK', label: 'Back', position: { x: 10, y: 70 }, size: { width: 25, height: 15 }, shape: 'rectangle', comment: 'Back' },
      { key: 'HOME', label: 'Home', position: { x: 40, y: 70 }, size: { width: 25, height: 15 }, shape: 'rectangle', comment: 'Home' },
      { key: 'MENU', label: 'Menu', position: { x: 70, y: 70 }, size: { width: 25, height: 15 }, shape: 'rectangle', comment: 'Menu' },
    ],
  },
};
