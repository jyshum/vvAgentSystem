-- Add scheduling columns to clients
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS cycle_frequency text DEFAULT 'weekly',
ADD COLUMN IF NOT EXISTS cycle_day integer DEFAULT 1;

-- Pipeline runs table for LangGraph orchestration
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id uuid REFERENCES clients(id) NOT NULL,
  thread_id text NOT NULL,
  run_type text NOT NULL DEFAULT 'full',
  status text NOT NULL DEFAULT 'running',
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz,
  error_message text,
  CONSTRAINT valid_status CHECK (status IN ('running', 'awaiting_approval', 'implementing', 'completed', 'error'))
);

CREATE INDEX idx_pipeline_runs_client ON pipeline_runs(client_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
