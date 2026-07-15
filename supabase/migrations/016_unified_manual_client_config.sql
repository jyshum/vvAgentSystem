alter table public.clients
  add column if not exists site_platform text not null default 'unknown'
    check (site_platform in ('unknown', 'squarespace', 'wordpress', 'webflow', 'shopify', 'repository', 'other')),
  add column if not exists implementation_mode text not null default 'copy_paste'
    check (implementation_mode in ('copy_paste', 'guided', 'github_pr', 'staged_api'));

update public.clients
set site_platform = 'squarespace',
    implementation_mode = 'copy_paste'
where lower(website_domain) = 'budgetyourmd.ca';
