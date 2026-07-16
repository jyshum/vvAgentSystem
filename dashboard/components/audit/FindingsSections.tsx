/** The findings accordion, shared by the AUDIT tab and the legacy run-detail
 *  embed. The implementation stays in components/runs/ until the RUNS redesign
 *  retires that embed; this alias gives the AUDIT tab a stable name without
 *  duplicating the component. */
export { TechnicalAuditChecklist as FindingsSections } from "@/components/runs/TechnicalAuditChecklist";
