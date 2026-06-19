"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Textarea } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { ReportView } from "@/components/report/ReportView";
import { weekRangeLabel } from "@/lib/utils";
import type {
  Report,
  TrackerRun,
  TrackerResultClient,
  Client,
} from "@/lib/types";

interface ReportEditorProps {
  initialReport: Report;
  run: TrackerRun | null;
  results: TrackerResultClient[];
  client: Client;
  previousRuns: TrackerRun[];
}

export function ReportEditor({
  initialReport,
  run,
  results,
  client,
  previousRuns,
}: ReportEditorProps) {
  const [report, setReport] = useState<Report>(initialReport);
  const [saving, setSaving] = useState(false);

  function update(partial: Partial<Report>) {
    setReport((prev) => ({ ...prev, ...partial }));
  }

  async function save(newStatus?: "draft" | "published") {
    setSaving(true);
    const supabase = createClient();

    const updates: Record<string, unknown> = {
      exec_summary: report.exec_summary,
      work_completed: report.work_completed,
      priorities: report.priorities,
      highlights: report.highlights,
      blockers: report.blockers,
      notes: report.notes,
      search_console: report.search_console,
    };

    if (newStatus) {
      updates.status = newStatus;
      if (newStatus === "published") updates.published_at = new Date().toISOString();
      else updates.published_at = null;
    }

    await supabase.from("reports").update(updates).eq("id", report.id);

    if (newStatus) update({ status: newStatus, published_at: updates.published_at as string | null });
    setSaving(false);
  }

  function addListItem(field: "work_completed" | "priorities" | "highlights" | "blockers") {
    const arr = [...(report[field] as { text: string }[])];
    if (field === "work_completed") {
      (arr as { text: string; done: boolean }[]).push({ text: "", done: false });
    } else {
      arr.push({ text: "" });
    }
    update({ [field]: arr });
  }

  function updateListItem(field: string, index: number, value: string) {
    const arr = [...(report[field as keyof Report] as { text: string }[])];
    arr[index] = { ...arr[index], text: value };
    update({ [field]: arr });
  }

  function removeListItem(field: string, index: number) {
    const arr = [...(report[field as keyof Report] as { text: string }[])];
    arr.splice(index, 1);
    update({ [field]: arr });
  }

  const inputCls =
    "flex-1 bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-1.5 px-2 outline-none focus:border-[rgba(245,244,241,0.42)]";
  const removeBtnCls =
    "text-[var(--faint)] hover:text-[var(--neg)] bg-transparent border-none cursor-pointer text-sm";
  const addBtnCls =
    "font-mono text-[9px] tracking-[0.15em] uppercase py-[7px] px-4 mt-1 mb-6 cursor-pointer transition-colors bg-transparent text-[var(--mute)] border border-[var(--ghost)] hover:text-[var(--white)] hover:border-[rgba(245,244,241,0.42)]";

  return (
    <div
      style={{
        position: "fixed",
        top: "78px",
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        background: "var(--ink)",
      }}
    >
      {/* 48px chrome bar */}
      <div
        style={{
          height: "48px",
          flexShrink: 0,
          padding: "0 24px",
          borderBottom: "1px solid var(--hair)",
          background: "rgba(14,14,15,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Left: breadcrumb + date */}
        <div className="flex items-center gap-3">
          <Link
            href={`/admin/clients/${client.id}/reports`}
            className="font-mono text-[9px] tracking-[0.12em] uppercase opacity-50 hover:opacity-100 transition-opacity"
            style={{ color: "var(--faint)" }}
          >
            ← {client.name}
          </Link>
          <span style={{ color: "var(--hair)" }}>/</span>
          <span
            className="font-mono text-[9px] tracking-[0.12em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            {weekRangeLabel(report.week_start)}
          </span>
        </div>

        {/* Right: status + buttons */}
        <div className="flex items-center gap-2">
          <span
            className="font-mono text-[8px] tracking-[0.1em] uppercase py-[4px] px-[9px]"
            style={{
              color: report.status === "published" ? "var(--ink)" : "var(--mute)",
              background: report.status === "published" ? "var(--pos)" : "transparent",
              border: report.status !== "published" ? "1px solid rgba(245,244,241,0.42)" : "none",
            }}
          >
            {report.status}
          </span>

          <Button
            variant="outline"
            onClick={() => save()}
            disabled={saving}
            className="py-[6px] px-[14px] text-[10px]"
          >
            {saving ? "Saving..." : "Save Draft"}
          </Button>

          {report.status === "draft" ? (
            <Button
              variant="solid"
              onClick={() => save("published")}
              disabled={saving}
              className="py-[6px] px-[14px] text-[10px]"
            >
              Publish Report
            </Button>
          ) : (
            <Button
              variant="outline"
              onClick={() => save("draft")}
              disabled={saving}
              className="py-[6px] px-[14px] text-[10px]"
            >
              Unpublish
            </Button>
          )}
        </div>
      </div>

      {/* Editor body */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar — fields only */}
        <aside
          style={{
            width: "380px",
            flexShrink: 0,
            borderRight: "1px solid var(--hair)",
            overflowY: "auto",
            padding: "28px 24px",
            background: "var(--ink-soft)",
          }}
        >
          <SectionLabel>Executive Summary</SectionLabel>
          <Textarea
            value={report.exec_summary}
            onChange={(e) => update({ exec_summary: e.target.value })}
            placeholder="One short paragraph: the headline story of the week..."
            rows={4}
          />

          <SectionLabel>Highlights / Wins</SectionLabel>
          {report.highlights.map((h, i) => (
            <div key={i} className="flex items-center gap-2 mb-2">
              <input
                type="text"
                value={h.text}
                onChange={(e) => updateListItem("highlights", i, e.target.value)}
                placeholder="Win or highlight..."
                className={inputCls}
              />
              <button onClick={() => removeListItem("highlights", i)} className={removeBtnCls}>
                &times;
              </button>
            </div>
          ))}
          <button onClick={() => addListItem("highlights")} className={addBtnCls}>
            + Add Highlight
          </button>

          <SectionLabel>Work Completed</SectionLabel>
          {report.work_completed.map((w, i) => (
            <div key={i} className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={w.done}
                onChange={(e) => {
                  const arr = [...report.work_completed];
                  arr[i] = { ...arr[i], done: e.target.checked };
                  update({ work_completed: arr });
                }}
                className="w-4 h-4 shrink-0 cursor-pointer accent-[var(--white)]"
              />
              <input
                type="text"
                value={w.text}
                onChange={(e) => updateListItem("work_completed", i, e.target.value)}
                placeholder="Task description..."
                className={inputCls}
              />
              <button onClick={() => removeListItem("work_completed", i)} className={removeBtnCls}>
                &times;
              </button>
            </div>
          ))}
          <button onClick={() => addListItem("work_completed")} className={addBtnCls}>
            + Add Item
          </button>

          <SectionLabel>Next Week Priorities</SectionLabel>
          {report.priorities.map((p, i) => (
            <div key={i} className="flex items-center gap-2 mb-2">
              <span
                className="font-mono text-[9px] tracking-[0.1em] shrink-0 min-w-[20px] text-center"
                style={{ color: "var(--faint)" }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <input
                type="text"
                value={p.text}
                onChange={(e) => updateListItem("priorities", i, e.target.value)}
                placeholder="Priority..."
                className={inputCls}
              />
              <button onClick={() => removeListItem("priorities", i)} className={removeBtnCls}>
                &times;
              </button>
            </div>
          ))}
          <button onClick={() => addListItem("priorities")} className={addBtnCls}>
            + Add Priority
          </button>

          <SectionLabel>Blockers / Risks</SectionLabel>
          {report.blockers.map((b, i) => (
            <div key={i} className="flex items-center gap-2 mb-2">
              <input
                type="text"
                value={b.text}
                onChange={(e) => updateListItem("blockers", i, e.target.value)}
                placeholder="Blocker or risk..."
                className={inputCls}
              />
              <button onClick={() => removeListItem("blockers", i)} className={removeBtnCls}>
                &times;
              </button>
            </div>
          ))}
          <button onClick={() => addListItem("blockers")} className={addBtnCls}>
            + Add Blocker
          </button>

          <SectionLabel>Notes / Observations</SectionLabel>
          <Textarea
            value={report.notes}
            onChange={(e) => update({ notes: e.target.value })}
            placeholder="Optional observations..."
            rows={5}
          />
        </aside>

        {/* Preview panel */}
        <div
          style={{
            flex: 1,
            background: "#080809",
            overflowY: "auto",
            padding: "32px 24px 60px",
          }}
        >
          <ReportView
            report={report}
            run={run}
            results={results}
            clientName={client.name}
            brandName={client.brand_name}
            domain={client.website_domain}
            previousRuns={previousRuns}
          />
        </div>
      </div>
    </div>
  );
}
