export interface Deal {
  deal_record?: any;
  deal_name?: string;
  evidence_count?: number;
  id: string;
  status: string;
  source: string;
  asset_name: string;
  creditor: string;
  current_balance: string;
  asset_address: string;
  missing_count: number;
  minimum_data_passed: boolean;
  owner: string;
  action_tag: string;
  next_action: string;
  created_at: string;
  updated_at: string;
}

export interface DealDetail extends Deal {
  raw_input: string;
  deal_record: any;
  status_history: any[];
}
