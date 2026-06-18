import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

const RAILWAY_API = "https://backboard.railway.app/graphql/v2";

async function railwayGraphQL(query: string, variables: Record<string, unknown>) {
  const res = await fetch(RAILWAY_API, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.RAILWAY_API_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, variables }),
  });
  const json = await res.json();
  if (json.errors) throw new Error(json.errors[0].message);
  return json.data;
}

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // Verify admin role
  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();
  if (!clientUser || clientUser.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const { RAILWAY_API_TOKEN, RAILWAY_SERVICE_ID, RAILWAY_ENVIRONMENT_ID } = process.env;
  if (!RAILWAY_API_TOKEN || !RAILWAY_SERVICE_ID || !RAILWAY_ENVIRONMENT_ID) {
    return NextResponse.json({ error: "Railway not configured" }, { status: 503 });
  }

  const { clientId } = await req.json();
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  // Verify client exists
  const { data: client } = await supabase.from("clients").select("id").eq("id", clientId).single();
  if (!client) return NextResponse.json({ error: "Client not found" }, { status: 404 });

  try {
    // Set CLIENT_ID variable on Railway service
    await railwayGraphQL(`
      mutation variableUpsert($input: VariableUpsertInput!) {
        variableUpsert(input: $input)
      }
    `, {
      input: {
        serviceId: RAILWAY_SERVICE_ID,
        environmentId: RAILWAY_ENVIRONMENT_ID,
        name: "CLIENT_ID",
        value: clientId,
      },
    });

    // Trigger redeployment
    const data = await railwayGraphQL(`
      mutation serviceInstanceRedeploy($serviceId: String!, $environmentId: String!) {
        serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
      }
    `, {
      serviceId: RAILWAY_SERVICE_ID,
      environmentId: RAILWAY_ENVIRONMENT_ID,
    });

    return NextResponse.json({ ok: true, data });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Railway API error";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
