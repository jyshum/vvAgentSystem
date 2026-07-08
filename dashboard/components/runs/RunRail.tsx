const SEGMENTS = ["MEASURE", "DIAGNOSE", "CARDS", "APPROVAL", "IMPLEMENT", "RE-MEASURE"] as const;

type SegState = "done" | "active" | "pending" | "error";

interface RunRailProps {
  status: string;
  errorMessage?: string | null;
}

function segmentStates(status: string): SegState[] {
  switch (status) {
    case "running":
      return ["done", "active", "pending", "pending", "pending", "pending"];
    case "awaiting_approval":
      return ["done", "done", "done", "active", "pending", "pending"];
    case "implementing":
      return ["done", "done", "done", "done", "active", "pending"];
    case "completed":
      return ["done", "done", "done", "done", "done", "pending"];
    case "error": {
      const states = segmentStates("running");
      const activeIndex = states.indexOf("active");
      if (activeIndex !== -1) states[activeIndex] = "error";
      return states;
    }
    default:
      return ["pending", "pending", "pending", "pending", "pending", "pending"];
  }
}

const DOT_COLOR: Record<SegState, string> = {
  done: "var(--white)",
  active: "#d4a017",
  pending: "var(--ghost)",
  error: "var(--neg)",
};

const LABEL_COLOR: Record<SegState, string> = {
  done: "var(--mute)",
  active: "var(--white)",
  pending: "var(--faint)",
  error: "var(--neg)",
};

export function RunRail({ status, errorMessage }: RunRailProps) {
  const states = segmentStates(status);

  return (
    <div className="flex items-center py-3">
      {SEGMENTS.map((label, i) => (
        <div key={label} className="contents">
          <div className="flex items-center flex-shrink-0">
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: DOT_COLOR[states[i]] }}
            />
            <span
              className="font-mono text-[8px] tracking-[0.1em] ml-1.5"
              style={{ color: LABEL_COLOR[states[i]] }}
            >
              {label}
            </span>
          </div>
          {i < SEGMENTS.length - 1 && (
            <span
              className="h-px flex-1 mx-3"
              style={{ background: "var(--hair)" }}
            />
          )}
        </div>
      ))}
      {status === "error" && errorMessage && (
        <span
          className="font-mono text-[8px] ml-4"
          style={{ color: "var(--neg)" }}
          title={errorMessage}
        >
          {errorMessage.length > 80 ? `${errorMessage.slice(0, 80)}…` : errorMessage}
        </span>
      )}
    </div>
  );
}
