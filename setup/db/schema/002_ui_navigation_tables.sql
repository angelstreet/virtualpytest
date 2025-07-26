-- VirtualPyTest UI and Navigation Tables Schema
-- This file contains tables for user interfaces and navigation trees

-- User interface definitions
CREATE TABLE userinterfaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    models UUID[] DEFAULT '{}', -- array of device model IDs
    min_version VARCHAR(50),
    max_version VARCHAR(50),
    description TEXT,
    config JSONB DEFAULT '{}', -- UI-specific configuration
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, team_id)
);

-- Navigation tree structures
CREATE TABLE navigation_trees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    userinterface_id UUID REFERENCES userinterfaces(id) ON DELETE CASCADE,
    root_tree_id UUID, -- self-reference for root trees
    parent_id UUID REFERENCES navigation_trees(id) ON DELETE CASCADE,
    description TEXT,
    metadata JSONB DEFAULT '{}', -- tree structure, coordinates, etc.
    is_root BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, userinterface_id, team_id)
);

-- Navigation tree version history
CREATE TABLE navigation_trees_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tree_id UUID REFERENCES navigation_trees(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}', -- historical tree structure
    change_description TEXT,
    changed_by UUID, -- user who made the change
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add foreign key constraint after table creation
ALTER TABLE navigation_trees 
ADD CONSTRAINT fk_navigation_trees_root 
FOREIGN KEY (root_tree_id) REFERENCES navigation_trees(id) ON DELETE SET NULL;

-- Add indexes for performance
CREATE INDEX idx_userinterfaces_team_id ON userinterfaces(team_id);
CREATE INDEX idx_navigation_trees_team_id ON navigation_trees(team_id);
CREATE INDEX idx_navigation_trees_userinterface ON navigation_trees(userinterface_id);
CREATE INDEX idx_navigation_trees_parent ON navigation_trees(parent_id);
CREATE INDEX idx_navigation_trees_root ON navigation_trees(root_tree_id);
CREATE INDEX idx_navigation_trees_is_root ON navigation_trees(is_root);
CREATE INDEX idx_navigation_trees_history_tree_id ON navigation_trees_history(tree_id);
CREATE INDEX idx_navigation_trees_history_team_id ON navigation_trees_history(team_id);

-- Add comments
COMMENT ON TABLE userinterfaces IS 'User interface definitions and configurations';
COMMENT ON TABLE navigation_trees IS 'Navigation tree structures for UI testing';
COMMENT ON TABLE navigation_trees_history IS 'Version history for navigation trees'; 