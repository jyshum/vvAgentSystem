export interface ClientTab {
  label: string;
  href: string;
}

export function clientTabs(clientId: string): ClientTab[] {
  return [
    { label: "OVERVIEW", href: `/admin/clients/${clientId}/overview` },
    { label: "QUERIES", href: `/admin/clients/${clientId}/queries` },
    { label: "RUNS", href: `/admin/clients/${clientId}/runs` },
    { label: "CARDS", href: `/admin/clients/${clientId}/cards` },
    { label: "CONFIG", href: `/admin/clients/${clientId}/config` },
    { label: "REPORTS", href: `/admin/clients/${clientId}/reports` },
  ];
}
