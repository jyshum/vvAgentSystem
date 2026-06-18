"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

interface InviteClientFormProps {
  clientId: string;
}

export function InviteClientForm({ clientId }: InviteClientFormProps) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");

    const res = await fetch("/api/admin/invite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, clientId }),
    });

    if (res.ok) {
      setStatus("sent");
      setEmail("");
    } else {
      setStatus("error");
    }
  }

  return (
    <form onSubmit={handleInvite} className="flex items-end gap-3">
      <div className="flex-1">
        <Input
          label="Invite client user"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="client@company.com"
          required
        />
      </div>
      <Button
        type="submit"
        variant="solid"
        disabled={status === "sending"}
        className="mb-3.5 py-[11px] px-[20px] text-[12px]"
      >
        {status === "sending" ? "Sending..." : status === "sent" ? "Sent!" : "Invite"}
      </Button>
    </form>
  );
}
