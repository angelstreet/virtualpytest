/**
 * Prompt Disambiguation Component
 * 
 * Modal component for resolving ambiguous navigation node references.
 * Supports two modes:
 * - Select mode: Choose from suggested matches
 * - Edit mode: Manually type/select nodes
 */

import React, { useState } from 'react';
import type {  Ambiguity, AutoCorrection } from '../../types/aiagent/AIDisambiguation_Types';

interface Props {
  ambiguities: Ambiguity[];
  autoCorrections?: AutoCorrection[];
  availableNodes?: string[];
  onResolve: (selections: Record<string, string>, saveToDb: boolean) => void;
  onCancel: () => void;
}

export const PromptDisambiguation: React.FC<Props> = ({
  ambiguities,
  autoCorrections = [],
  availableNodes = [],
  onResolve,
  onCancel
}) => {
  const [mode, setMode] = useState<'select' | 'edit'>('select');
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [saveToDb, setSaveToDb] = useState(true);
  const [editedText, setEditedText] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Check if all ambiguities have selections
  const allSelected = ambiguities.every(a => selections[a.original]);

  // Filter available nodes for search
  const filteredNodes = searchTerm
    ? availableNodes.filter(node => node.toLowerCase().includes(searchTerm.toLowerCase())).slice(0, 20)
    : availableNodes.slice(0, 20);

  const handleProceed = () => {
    if (mode === 'edit') {
      // Parse edited text (simple format: "phrase → node")
      const parsed = parseEditedSelections(editedText);
      onResolve(parsed, saveToDb);
    } else {
      onResolve(selections, saveToDb);
    }
  };

  const insertNode = (node: string) => {
    setEditedText(prev => prev + (prev ? '\n' : '') + node);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-xl font-bold text-gray-900">
            🤔 Clarify Navigation Nodes
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Some references in your prompt are ambiguous. Please select the correct nodes.
          </p>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Auto-corrections banner */}
          {autoCorrections.length > 0 && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm font-medium text-green-900 mb-2">
                ✅ Already auto-applied:
              </p>
              {autoCorrections.map((c, i) => (
                <div key={i} className="text-sm text-green-700 flex items-center gap-2">
                  <span className="font-mono">"{c.from}"</span>
                  <span>→</span>
                  <span className="font-mono font-medium">"{c.to}"</span>
                  {c.source === 'learned' && (
                    <span className="text-xs bg-green-100 px-2 py-0.5 rounded">🎓 Learned</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {mode === 'select' ? (
            <>
              {/* Selection mode */}
              <div className="space-y-4 mb-6">
                {ambiguities.map((amb, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4">
                    <p className="text-sm font-medium text-gray-900 mb-3">
                      What did you mean by <span className="text-blue-600 font-mono">"{amb.original}"</span>?
                    </p>
                    <div className="space-y-2">
                      {amb.suggestions.map(sugg => (
                        <button
                          key={sugg}
                          onClick={() => setSelections({...selections, [amb.original]: sugg})}
                          className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                            selections[amb.original] === sugg
                              ? 'border-blue-500 bg-blue-50 shadow-sm'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                          }`}
                        >
                          <span className="font-mono text-gray-900">{sugg}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Options */}
              <div className="flex items-center gap-4 mb-4">
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={saveToDb}
                    onChange={(e) => setSaveToDb(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span>Remember my choices for next time</span>
                </label>
                
                <button
                  onClick={() => setMode('edit')}
                  className="ml-auto text-sm text-blue-600 hover:text-blue-700 hover:underline"
                >
                  ✏️ Edit manually instead
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Edit mode */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type node names or click to insert:
                </label>
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  placeholder="Type node names, one per line..."
                  className="w-full h-32 px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Tip: Type node names directly or use the chips below
                </p>
              </div>

              {/* Node search */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Available nodes:
                </label>
                <input
                  type="text"
                  placeholder="🔍 Search nodes..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 mb-3"
                />
                <div className="border border-gray-200 rounded-lg p-3 max-h-48 overflow-y-auto bg-gray-50">
                  <div className="flex flex-wrap gap-2">
                    {filteredNodes.map(node => (
                      <button
                        key={node}
                        onClick={() => insertNode(node)}
                        className="px-3 py-1 bg-white hover:bg-blue-50 border border-gray-300 hover:border-blue-400 rounded text-sm font-mono transition-colors"
                      >
                        {node}
                      </button>
                    ))}
                  </div>
                  {filteredNodes.length === 0 && (
                    <p className="text-sm text-gray-500 text-center py-4">
                      No nodes found matching "{searchTerm}"
                    </p>
                  )}
                </div>
              </div>

              <button
                onClick={() => setMode('select')}
                className="text-sm text-blue-600 hover:text-blue-700 hover:underline mb-4"
              >
                ← Back to selection mode
              </button>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleProceed}
            disabled={mode === 'select' && !allSelected}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              (mode === 'edit' || allSelected)
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Proceed with Execution
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * Parse edited text selections
 * Simple format: node names, one per line
 * Or: "original phrase → selected node"
 */
function parseEditedSelections(text: string): Record<string, string> {
  const lines = text.split('\n').filter(l => l.trim());
  const result: Record<string, string> = {};
  
  lines.forEach(line => {
    // Try arrow format: "phrase → node"
    const arrowMatch = line.match(/(.+?)\s*→\s*(.+)/);
    if (arrowMatch) {
      result[arrowMatch[1].trim()] = arrowMatch[2].trim();
    }
    // Otherwise just use line as node name (for simple cases)
  });
  
  return result;
}
