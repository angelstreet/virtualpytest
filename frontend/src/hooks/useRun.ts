import { useState, useEffect } from 'react';

interface ScriptParameter {
  name: string;
  type: 'positional' | 'optional';
  required: boolean;
  help: string;
  default?: string;
}

interface ScriptAnalysis {
  success: boolean;
  parameters: ScriptParameter[];
  script_name: string;
  has_parameters: boolean;
  error?: string;
}

interface UseRunParams {
  selectedScript: string;
  selectedDevice: string;
  selectedHost: string;
  deviceModel: string;
  showWizard: boolean;
}

export const useRun = ({ selectedScript, selectedDevice, selectedHost, deviceModel, showWizard }: UseRunParams) => {
  const [scriptAnalysis, setScriptAnalysis] = useState<ScriptAnalysis | null>(null);
  const [parameterValues, setParameterValues] = useState<Record<string, string>>({});
  const [analyzingScript, setAnalyzingScript] = useState<boolean>(false);

  // Get userinterface name based on device model
  const getUserinterfaceName = (model: string): string => {
    const modelLower = model.toLowerCase();
    if (modelLower.includes('mobile') || modelLower.includes('phone')) {
      return 'horizon_android_mobile';
    } else if (modelLower.includes('tv') || modelLower.includes('android_tv')) {
      return 'horizon_android_tv';
    } else if (modelLower.includes('host')) {
      return 'perseus_360_web';
    } else {
      return 'horizon_android_mobile'; // default
    }
  };

  // Get default value for parameter
  const getDefaultParameterValue = (param: ScriptParameter): string => {
    if (param.name === 'userinterface_name') {
      return getUserinterfaceName(deviceModel);
    } else if (param.name === 'node') {
      return 'home';
    } else if (param.name === 'device') {
      return selectedDevice || '';
    } else if (param.name === 'host') {
      return selectedHost || '';
    } else if (param.default) {
      return param.default;
    }
    return '';
  };

  // Analyze script parameters when script selection changes
  useEffect(() => {
    const analyzeScript = async () => {
      if (!selectedScript || !showWizard) {
        setScriptAnalysis(null);
        setParameterValues({});
        return;
      }

      setAnalyzingScript(true);
      try {
        const response = await fetch('/server/script/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            script_name: selectedScript,
            device_model: deviceModel,
            device_id: selectedDevice,
          }),
        });

        const analysis: ScriptAnalysis = await response.json();

        if (analysis.success) {
          setScriptAnalysis(analysis);

          // Pre-fill parameter values with smart defaults
          const newParameterValues: Record<string, string> = {};
          analysis.parameters.forEach((param) => {
            newParameterValues[param.name] = getDefaultParameterValue(param);
          });
          setParameterValues(newParameterValues);
        } else {
          setScriptAnalysis(null);
          setParameterValues({});
        }
      } catch (error) {
        console.error('Error analyzing script:', error);
        setScriptAnalysis(null);
        setParameterValues({});
      } finally {
        setAnalyzingScript(false);
      }
    };

    analyzeScript();
  }, [selectedScript, selectedDevice, selectedHost, deviceModel, showWizard]);

  // Update parameter values when device/host changes
  useEffect(() => {
    if (scriptAnalysis) {
      const updatedValues = { ...parameterValues };
      
      scriptAnalysis.parameters.forEach((param) => {
        if (param.name === 'userinterface_name') {
          updatedValues[param.name] = getUserinterfaceName(deviceModel);
        } else if (param.name === 'device') {
          updatedValues[param.name] = selectedDevice || '';
        } else if (param.name === 'host') {
          updatedValues[param.name] = selectedHost || '';
        }
      });
      
      setParameterValues(updatedValues);
    }
  }, [selectedDevice, selectedHost, deviceModel, scriptAnalysis]);

  const handleParameterChange = (paramName: string, value: string) => {
    setParameterValues((prev) => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const validateParameters = () => {
    if (!scriptAnalysis) return { valid: true, errors: [] };

    const errors: string[] = [];

    scriptAnalysis.parameters.forEach((param) => {
      const value = parameterValues[param.name]?.trim();
      if (param.required && !value) {
        errors.push(`${param.name} is required`);
      }
    });

    return { valid: errors.length === 0, errors };
  };

  return {
    scriptAnalysis,
    parameterValues,
    analyzingScript,
    handleParameterChange,
    validateParameters,
    getUserinterfaceName,
  };
};
