import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  Typography, 
  Box, 
  Slider,
  Switch,
  FormControlLabel,
  Divider
} from '@mui/material';
import React from 'react';

export interface SubtitleStyle {
  fontSize: 'small' | 'medium' | 'large';
  fontFamily: 'default' | 'serif' | 'monospace';
  textStyle: 'white' | 'yellow' | 'white-border' | 'black-background';
  opacity: number;
  showOriginal: boolean;
  showTranslation: boolean;
  targetLanguage: string;
}

interface SubtitleSettingsProps {
  open: boolean;
  onClose: () => void;
  settings: SubtitleStyle;
  onSettingsChange: (settings: SubtitleStyle) => void;
  originalLanguage?: string;
}

const FONT_SIZES = [
  { value: 'small', label: 'Small', size: '0.8rem' },
  { value: 'medium', label: 'Medium', size: '1rem' },
  { value: 'large', label: 'Large', size: '1.2rem' }
];

const FONT_FAMILIES = [
  { value: 'default', label: 'Default', family: 'Roboto, Arial, sans-serif' },
  { value: 'serif', label: 'Serif', family: 'Georgia, serif' },
  { value: 'monospace', label: 'Monospace', family: 'Courier New, monospace' }
];

const TEXT_STYLES = [
  { 
    value: 'white', 
    label: 'White Text', 
    preview: { color: '#ffffff', textShadow: '2px 2px 4px rgba(0,0,0,0.9)' }
  },
  { 
    value: 'yellow', 
    label: 'Yellow Text', 
    preview: { color: '#ffff00', textShadow: '2px 2px 4px rgba(0,0,0,0.9)' }
  },
  { 
    value: 'white-border', 
    label: 'White with Border', 
    preview: { 
      color: '#ffffff', 
      textShadow: '0 0 2px #000000, 0 0 2px #000000, 0 0 2px #000000, 0 0 2px #000000' 
    }
  },
  { 
    value: 'black-background', 
    label: 'Black Background', 
    preview: { 
      color: '#ffffff', 
      backgroundColor: 'rgba(0,0,0,0.9)', 
      padding: '2px 6px', 
      borderRadius: '2px' 
    }
  }
];

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'it', name: 'Italian' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'ru', name: 'Russian' },
  { code: 'ja', name: 'Japanese' },
  { code: 'ko', name: 'Korean' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ar', name: 'Arabic' },
  { code: 'hi', name: 'Hindi' }
];

export const SubtitleSettings: React.FC<SubtitleSettingsProps> = ({
  open,
  onClose,
  settings,
  onSettingsChange,
  originalLanguage
}) => {
  const handleSettingChange = (key: keyof SubtitleStyle, value: any) => {
    onSettingsChange({
      ...settings,
      [key]: value
    });
  };

  const getPreviewStyle = () => {
    const baseStyle = {
      fontSize: FONT_SIZES.find(f => f.value === settings.fontSize)?.size || '1rem',
      fontFamily: FONT_FAMILIES.find(f => f.value === settings.fontFamily)?.family || 'Roboto, Arial, sans-serif',
      opacity: settings.opacity,
      ...TEXT_STYLES.find(s => s.value === settings.textStyle)?.preview
    };
    return baseStyle;
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="sm" 
      fullWidth
      PaperProps={{
        sx: {
          backgroundColor: '#1a1a1a',
          color: 'white'
        }
      }}
    >
      <DialogTitle sx={{ color: 'white' }}>
        Subtitle Settings
      </DialogTitle>
      
      <DialogContent>
        {/* Preview */}
        <Box sx={{ mb: 3, p: 2, backgroundColor: '#000', borderRadius: 1, textAlign: 'center' }}>
          <Typography variant="h6" sx={{ mb: 1, color: '#ccc' }}>
            Preview
          </Typography>
          <Typography style={getPreviewStyle()}>
            Sample subtitle text
          </Typography>
          {settings.showOriginal && settings.showTranslation && (
            <Typography 
              style={{
                ...getPreviewStyle(),
                fontSize: `calc(${getPreviewStyle().fontSize} * 0.9)`,
                opacity: 0.8,
                marginTop: '4px'
              }}
            >
              Translated subtitle text
            </Typography>
          )}
        </Box>

        {/* Font Size */}
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel sx={{ color: 'white' }}>Font Size</InputLabel>
          <Select
            value={settings.fontSize}
            onChange={(e) => handleSettingChange('fontSize', e.target.value)}
            sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' } }}
          >
            {FONT_SIZES.map(size => (
              <MenuItem key={size.value} value={size.value}>
                {size.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Font Family */}
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel sx={{ color: 'white' }}>Font Style</InputLabel>
          <Select
            value={settings.fontFamily}
            onChange={(e) => handleSettingChange('fontFamily', e.target.value)}
            sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' } }}
          >
            {FONT_FAMILIES.map(font => (
              <MenuItem key={font.value} value={font.value}>
                <span style={{ fontFamily: font.family }}>{font.label}</span>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Text Style */}
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel sx={{ color: 'white' }}>Text Style</InputLabel>
          <Select
            value={settings.textStyle}
            onChange={(e) => handleSettingChange('textStyle', e.target.value)}
            sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' } }}
          >
            {TEXT_STYLES.map(style => (
              <MenuItem key={style.value} value={style.value}>
                <span style={style.preview}>{style.label}</span>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Opacity */}
        <Box sx={{ mb: 3 }}>
          <Typography sx={{ color: 'white', mb: 1 }}>
            Opacity: {Math.round(settings.opacity * 100)}%
          </Typography>
          <Slider
            value={settings.opacity}
            onChange={(_, value) => handleSettingChange('opacity', value)}
            min={0.3}
            max={1}
            step={0.1}
            sx={{ color: 'white' }}
          />
        </Box>

        <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.2)' }} />

        {/* Language Settings */}
        <Typography variant="h6" sx={{ color: 'white', mb: 2 }}>
          Language Options
        </Typography>

        {/* Original Language Display */}
        {originalLanguage && (
          <Box sx={{ mb: 2 }}>
            <Typography sx={{ color: '#ccc', mb: 1 }}>
              Original Language: {LANGUAGES.find(l => l.code === originalLanguage)?.name || originalLanguage}
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.showOriginal}
                  onChange={(e) => handleSettingChange('showOriginal', e.target.checked)}
                  sx={{ '& .MuiSwitch-switchBase.Mui-checked': { color: 'white' } }}
                />
              }
              label="Show original subtitles"
              sx={{ color: 'white' }}
            />
          </Box>
        )}

        {/* Translation Settings */}
        <FormControlLabel
          control={
            <Switch
              checked={settings.showTranslation}
              onChange={(e) => handleSettingChange('showTranslation', e.target.checked)}
              sx={{ '& .MuiSwitch-switchBase.Mui-checked': { color: 'white' } }}
            />
          }
          label="Show translated subtitles"
          sx={{ color: 'white', mb: 2 }}
        />

        {settings.showTranslation && (
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel sx={{ color: 'white' }}>Target Language</InputLabel>
            <Select
              value={settings.targetLanguage}
              onChange={(e) => handleSettingChange('targetLanguage', e.target.value)}
              sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' } }}
            >
              {LANGUAGES.map(lang => (
                <MenuItem key={lang.code} value={lang.code}>
                  {lang.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} sx={{ color: 'white' }}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};
