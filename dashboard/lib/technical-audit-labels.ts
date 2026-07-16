/** Human-readable names for each audit check, keyed by check_id.
 *
 *  The backend stamps every unknown result with the same generic summary
 *  ("Applicable check could not complete"), which then propagates into the
 *  finding group and its action card. That string is an outcome, not a title,
 *  so it is useless as a heading. check_id is the stable identity of what the
 *  check verifies, so we resolve a real name from it for display. */
const CHECK_TITLES: Record<string, string> = {
  "canonical.integrity": "Canonical URL",
  "freshness.dates": "Content freshness",
  "images.alt_text": "Image alt text",
  "images.integrity": "Image integrity",
  "integration.bing": "Bing sitemap submission",
  "integration.gsc_sitemap": "Search Console sitemap",
  "links.external_health": "External link health",
  "links.internal_health": "Internal link health",
  "llms_txt.integrity": "llms.txt file",
  "meta_description.integrity": "Meta description",
  "meta_title.integrity": "Meta title",
  "performance.crux": "Field performance (CrUX)",
  "performance.lcp_image": "LCP image loading",
  "performance.lighthouse": "Lab performance (Lighthouse)",
  "robots_txt.access": "Robots.txt crawler access",
  "robots_txt.integrity": "Robots.txt integrity",
  "schema.coverage": "Structured data coverage",
  "schema.integrity": "Structured data integrity",
  "sitemap.coverage": "Sitemap coverage",
  "sitemap.discovery": "Sitemap discovery",
  "sitemap.entry_health": "Sitemap entry health",
  "sitemap.integrity": "Sitemap integrity",
  "source_support.link_health": "Citation source health",
  "tls.certificate": "TLS certificate",
  "tls.https_redirect": "HTTPS redirect",
  "tls.mixed_content": "Mixed content",
};

/** The placeholder summary the backend writes for every unknown result. */
export const GENERIC_UNKNOWN_SUMMARY = "Applicable check could not complete";

/** Title-case a bare check_id as a last resort when no curated name exists. */
export function humanizeCheckId(checkId: string): string {
  return checkId.replace(/[._]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

/** A stable, human name for a check. */
export function checkTitle(checkId: string | undefined): string {
  if (!checkId) return "Check";
  return CHECK_TITLES[checkId] ?? humanizeCheckId(checkId);
}

/** The title to show for a finding: the check's real name when the summary is
 *  the generic "could not complete" placeholder, otherwise the summary itself
 *  (which, for pass/fail/review, already describes the specific outcome). */
export function findingTitle(checkId: string | undefined, summary: string): string {
  return summary === GENERIC_UNKNOWN_SUMMARY ? checkTitle(checkId) : summary;
}
