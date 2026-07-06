-- 009_agentic_qa.sql
-- Columns for card QA, policy-based auto-approve, and post-implementation verification.

alter table public.action_cards
    add column if not exists auto_approved boolean default false,
    add column if not exists verification jsonb;

-- Per-client override/allowlist: action types the admin has explicitly cleared
-- for auto-approval (in addition to history-earned eligibility).
alter table public.clients
    add column if not exists auto_approve_action_types text[] default '{}';

create index if not exists idx_action_cards_auto_approved
    on public.action_cards(auto_approved) where auto_approved = true;
