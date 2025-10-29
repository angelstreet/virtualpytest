/**
 * Campaign Builder Context
 * 
 * Manages state for the visual campaign builder including:
 * - Campaign graph (nodes, edges)
 * - Campaign configuration
 * - Node selection and editing
 * - Save/Load operations
 */

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import {
  CampaignGraph,
  CampaignNode,
  CampaignEdge,
  CampaignBuilderState,
  CampaignGraphConfig,
  CampaignInput,
  CampaignOutput,
  CampaignReportField,
} from '../../types/pages/CampaignGraph_Types';
import { addEdge, Connection, applyNodeChanges, applyEdgeChanges, NodeChange, EdgeChange } from 'reactflow';

interface CampaignBuilderContextValue {
  // State
  state: CampaignBuilderState;
  
  // Campaign Config
  updateCampaignConfig: (updates: Partial<CampaignBuilderState>) => void;
  
  // Graph Operations
  nodes: CampaignNode[];
  edges: CampaignEdge[];
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  
  // Node Operations
  addNode: (node: CampaignNode) => void;
  updateNode: (nodeId: string, updates: Partial<CampaignNode['data']>) => void;
  deleteNode: (nodeId: string) => void;
  selectedNode: CampaignNode | null;
  selectNode: (nodeId: string | null) => void;
  
  // Data Linking
  linkOutputToInput: (sourceBlockId: string, sourceOutputName: string, targetBlockId: string, targetInputName: string) => void;
  unlinkInput: (blockId: string, inputName: string) => void;
  
  // Campaign I/O
  campaignInputs: CampaignInput[];
  campaignOutputs: CampaignOutput[];
  campaignReports: { mode: 'set' | 'aggregate'; fields: CampaignReportField[] };
  addCampaignInput: (input: CampaignInput) => void;
  addCampaignOutput: (output: CampaignOutput) => void;
  addCampaignReportField: (field: CampaignReportField) => void;
  removeCampaignInput: (name: string) => void;
  removeCampaignOutput: (name: string) => void;
  removeCampaignReportField: (name: string) => void;
  setCampaignReportsMode: (mode: 'set' | 'aggregate') => void;
  
  // Save/Load
  saveCampaign: () => Promise<boolean>;
  loadCampaign: (campaignId: string) => Promise<boolean>;
  resetBuilder: () => void;
}

const CampaignBuilderContext = createContext<CampaignBuilderContextValue | null>(null);

export const useCampaignBuilder = () => {
  const context = useContext(CampaignBuilderContext);
  if (!context) {
    throw new Error('useCampaignBuilder must be used within CampaignBuilderProvider');
  }
  return context;
};

interface CampaignBuilderProviderProps {
  children: ReactNode;
}

// Initial graph with START, SUCCESS, FAILURE terminal nodes
const createInitialGraph = (): CampaignGraph => ({
  nodes: [
    {
      id: 'start',
      type: 'start',
      position: { x: 250, y: 50 },
      data: { label: 'START' },
    },
    {
      id: 'success',
      type: 'success',
      position: { x: 150, y: 500 },
      data: { label: 'SUCCESS' },
    },
    {
      id: 'failure',
      type: 'failure',
      position: { x: 350, y: 500 },
      data: { label: 'FAILURE' },
    },
  ],
  edges: [],
  campaignConfig: {
    inputs: [],
    outputs: [],
    reports: {
      mode: 'aggregate',
      fields: [],
    },
  },
});

export const CampaignBuilderProvider: React.FC<CampaignBuilderProviderProps> = ({ children }) => {
  const [state, setState] = useState<CampaignBuilderState>({
    graph: createInitialGraph(),
  });

  // Campaign Config
  const updateCampaignConfig = useCallback((updates: Partial<CampaignBuilderState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  // Graph state (React Flow)
  const nodes = state.graph.nodes;
  const edges = state.graph.edges;

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        nodes: applyNodeChanges(changes, prev.graph.nodes) as CampaignNode[],
      },
    }));
  }, []);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        edges: applyEdgeChanges(changes, prev.graph.edges) as CampaignEdge[],
      },
    }));
  }, []);

  const onConnect = useCallback((connection: Connection) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        edges: addEdge({ ...connection, type: 'control' }, prev.graph.edges) as CampaignEdge[],
      },
    }));
  }, []);

  // Node Operations
  const addNode = useCallback((node: CampaignNode) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        nodes: [...prev.graph.nodes, node],
      },
    }));
  }, []);

  const updateNode = useCallback((nodeId: string, updates: Partial<CampaignNode['data']>) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        nodes: prev.graph.nodes.map(node =>
          node.id === nodeId
            ? { ...node, data: { ...node.data, ...updates } }
            : node
        ),
      },
    }));
  }, []);

  const deleteNode = useCallback((nodeId: string) => {
    // Don't allow deleting terminal nodes
    if (['start', 'success', 'failure'].includes(nodeId)) {
      return;
    }

    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        nodes: prev.graph.nodes.filter(node => node.id !== nodeId),
        edges: prev.graph.edges.filter(edge => edge.source !== nodeId && edge.target !== nodeId),
      },
      selectedNode: prev.selectedNode === nodeId ? undefined : prev.selectedNode,
    }));
  }, []);

  const selectedNode = state.selectedNode 
    ? nodes.find(n => n.id === state.selectedNode) || null
    : null;

  const selectNode = useCallback((nodeId: string | null) => {
    setState(prev => ({ ...prev, selectedNode: nodeId || undefined }));
  }, []);

  // Data Linking
  const linkOutputToInput = useCallback((
    sourceBlockId: string,
    sourceOutputName: string,
    targetBlockId: string,
    targetInputName: string
  ) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        nodes: prev.graph.nodes.map(node => {
          if (node.id === targetBlockId && node.data.inputs) {
            return {
              ...node,
              data: {
                ...node.data,
                inputs: node.data.inputs.map(input =>
                  input.name === targetInputName
                    ? {
                        ...input,
                        linkedSource: {
                          blockId: sourceBlockId,
                          outputName: sourceOutputName,
                        },
                      }
                    : input
                ),
              },
            };
          }
          return node;
        }),
      },
    }));
  }, []);

  const unlinkInput = useCallback((blockId: string, inputName: string) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        nodes: prev.graph.nodes.map(node => {
          if (node.id === blockId && node.data.inputs) {
            return {
              ...node,
              data: {
                ...node.data,
                inputs: node.data.inputs.map(input =>
                  input.name === inputName
                    ? { ...input, linkedSource: undefined }
                    : input
                ),
              },
            };
          }
          return node;
        }),
      },
    }));
  }, []);

  // Campaign I/O
  const campaignInputs = state.graph.campaignConfig?.inputs || [];
  const campaignOutputs = state.graph.campaignConfig?.outputs || [];
  const campaignReports = state.graph.campaignConfig?.reports || { mode: 'aggregate', fields: [] };

  const addCampaignInput = useCallback((input: CampaignInput) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        campaignConfig: {
          ...prev.graph.campaignConfig,
          inputs: [...(prev.graph.campaignConfig?.inputs || []), input],
        },
      },
    }));
  }, []);

  const addCampaignOutput = useCallback((output: CampaignOutput) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        campaignConfig: {
          ...prev.graph.campaignConfig,
          outputs: [...(prev.graph.campaignConfig?.outputs || []), output],
        },
      },
    }));
  }, []);

  const addCampaignReportField = useCallback((field: CampaignReportField) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        campaignConfig: {
          ...prev.graph.campaignConfig,
          reports: {
            mode: prev.graph.campaignConfig?.reports?.mode || 'aggregate',
            fields: [...(prev.graph.campaignConfig?.reports?.fields || []), field],
          },
        },
      },
    }));
  }, []);

  const removeCampaignInput = useCallback((name: string) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        campaignConfig: {
          ...prev.graph.campaignConfig,
          inputs: (prev.graph.campaignConfig?.inputs || []).filter(i => i.name !== name),
        },
      },
    }));
  }, []);

  const removeCampaignOutput = useCallback((name: string) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        campaignConfig: {
          ...prev.graph.campaignConfig,
          outputs: (prev.graph.campaignConfig?.outputs || []).filter(o => o.name !== name),
        },
      },
    }));
  }, []);

  const removeCampaignReportField = useCallback((name: string) => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        campaignConfig: {
          ...prev.graph.campaignConfig,
          reports: {
            mode: prev.graph.campaignConfig?.reports?.mode || 'aggregate',
            fields: (prev.graph.campaignConfig?.reports?.fields || []).filter(f => f.name !== name),
          },
        },
      },
    }));
  }, []);

  const setCampaignReportsMode = useCallback((mode: 'set' | 'aggregate') => {
    setState(prev => ({
      ...prev,
      graph: {
        ...prev.graph,
        campaignConfig: {
          ...prev.graph.campaignConfig,
          reports: {
            mode,
            fields: prev.graph.campaignConfig?.reports?.fields || [],
          },
        },
      },
    }));
  }, []);

  // Save/Load (TODO: Implement API calls)
  const saveCampaign = useCallback(async () => {
    console.log('[@CampaignBuilder] Saving campaign:', state);
    // TODO: Implement API call to save campaign
    return true;
  }, [state]);

  const loadCampaign = useCallback(async (campaignId: string) => {
    console.log('[@CampaignBuilder] Loading campaign:', campaignId);
    // TODO: Implement API call to load campaign
    return true;
  }, []);

  const resetBuilder = useCallback(() => {
    setState({
      graph: createInitialGraph(),
    });
  }, []);

  const value: CampaignBuilderContextValue = {
    state,
    updateCampaignConfig,
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
    deleteNode,
    selectedNode,
    selectNode,
    linkOutputToInput,
    unlinkInput,
    campaignInputs,
    campaignOutputs,
    campaignReports,
    addCampaignInput,
    addCampaignOutput,
    addCampaignReportField,
    removeCampaignInput,
    removeCampaignOutput,
    removeCampaignReportField,
    setCampaignReportsMode,
    saveCampaign,
    loadCampaign,
    resetBuilder,
  };

  return (
    <CampaignBuilderContext.Provider value={value}>
      {children}
    </CampaignBuilderContext.Provider>
  );
};
