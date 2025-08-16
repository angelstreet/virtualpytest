/**
 * AI Test Case Generator Component - Clean Modern Implementation
 * No fallbacks, no legacy code, minimalist UI
 */

import React, { useState } from 'react';
import { useAITestCase } from '../../hooks/aiagent/useAITestCase';
import { TestCase, AITestCaseRequest } from '../../types/pages/TestCase_Types';

interface AITestCaseGeneratorProps {
  onTestCaseGenerated: (testCase: TestCase) => void;
}

export const AITestCaseGenerator: React.FC<AITestCaseGeneratorProps> = ({
  onTestCaseGenerated
}) => {
  const [prompt, setPrompt] = useState('');
  const [deviceModel, setDeviceModel] = useState('');
  const [interfaceName, setInterfaceName] = useState('');

  const {
    generateTestCase,
    isGenerating,
    compatibilityResults,
    error,
    clearError
  } = useAITestCase();

  const handleGenerate = async () => {
    if (!prompt.trim() || !deviceModel || !interfaceName) {
      return;
    }

    clearError();

    const request: AITestCaseRequest = {
      prompt: prompt.trim(),
      device_model: deviceModel,
      interface_name: interfaceName
    };

    const result = await generateTestCase(request);

    if (result.success && result.test_case) {
      onTestCaseGenerated(result.test_case);
      setPrompt(''); // Clear form on success
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleGenerate();
    }
  };

  const isFormValid = prompt.trim() && deviceModel && interfaceName;

  return (
    <div className="ai-test-case-generator bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-semibold">AI</span>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Generate Test Case</h3>
      </div>

      <div className="space-y-4">
        {/* Prompt Input */}
        <div>
          <label htmlFor="ai-prompt" className="block text-sm font-medium text-gray-700 mb-2">
            Test Case Description
          </label>
          <textarea
            id="ai-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Describe what you want to test (e.g., 'Go to live zap 3 times for each zap check audio video')"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            disabled={isGenerating}
          />
          <p className="text-xs text-gray-500 mt-1">
            Tip: Press Ctrl+Enter to generate
          </p>
        </div>

        {/* Device and Interface Selection */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="device-model" className="block text-sm font-medium text-gray-700 mb-2">
              Device Model
            </label>
            <select
              id="device-model"
              value={deviceModel}
              onChange={(e) => setDeviceModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isGenerating}
            >
              <option value="">Select device...</option>
              <option value="android_mobile">Android Mobile</option>
              <option value="android_tv">Android TV</option>
              <option value="web_browser">Web Browser</option>
            </select>
          </div>

          <div>
            <label htmlFor="interface-name" className="block text-sm font-medium text-gray-700 mb-2">
              User Interface
            </label>
            <select
              id="interface-name"
              value={interfaceName}
              onChange={(e) => setInterfaceName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isGenerating}
            >
              <option value="">Select interface...</option>
              <option value="horizon_android_mobile">Horizon Android Mobile</option>
              <option value="horizon_android_tv">Horizon Android TV</option>
              <option value="horizon_web_browser">Horizon Web Browser</option>
            </select>
          </div>
        </div>

        {/* Generate Button */}
        <button
          onClick={handleGenerate}
          disabled={!isFormValid || isGenerating}
          className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
            isFormValid && !isGenerating
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isGenerating ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Generating...</span>
            </div>
          ) : (
            '🚀 Generate Test Case'
          )}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-start gap-2">
            <span className="text-red-500 text-sm">❌</span>
            <span className="text-red-700 text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Compatibility Results */}
      {compatibilityResults.length > 0 && (
        <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-md">
          <h4 className="text-sm font-medium text-gray-900 mb-3">💡 Compatibility Analysis</h4>
          <div className="space-y-2">
            {compatibilityResults.map((result, index) => (
              <div
                key={index}
                className={`flex items-center justify-between p-2 rounded ${
                  result.compatible
                    ? 'bg-green-100 border border-green-200'
                    : 'bg-red-100 border border-red-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`text-sm ${result.compatible ? 'text-green-700' : 'text-red-700'}`}>
                    {result.compatible ? '✅' : '❌'}
                  </span>
                  <span className="text-sm font-medium text-gray-900">
                    {result.interface_name}
                  </span>
                </div>
                <span className={`text-xs ${result.compatible ? 'text-green-600' : 'text-red-600'}`}>
                  {result.compatible ? 'Compatible' : 'Not Compatible'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
