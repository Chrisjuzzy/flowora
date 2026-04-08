export interface Agent {
  id: number;
  name: string;
  description: string | null;
  config?: any;
  is_active?: boolean;
  is_published?: boolean;
  owner_id?: number;
  category?: string;
  tags?: string;
  version?: string;
  rating?: number;
}

export interface Workflow {
  id: number;
  name: string;
  config_json: {
    steps: {
      step_name: string;
      agent_id: number;
    }[];
  };
  owner_id?: number;
}

export interface Execution {
  id: number;
  agent_id: number;
  prompt_version_id?: number | null;
  status: string;
  result: string;
  timestamp: string;
}

export interface AgentReview {
  id: number;
  user_id: number;
  rating: number;
  comment: string;
  created_at: string;
}

export interface AgentVersion {
  id: number;
  agent_id: number;
  version: string;
  created_at: string;
  description?: string;
}

export interface MarketplaceListing {
  id: number;
  agent_id: number;
  seller_id: number;
  price: number;
  is_active: boolean;
  agent: Agent;
}
