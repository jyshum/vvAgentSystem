import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
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
  // Step 1: Auth
  const supabase = await createClient();
  const { data: { user }, error: userError } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized", detail: userError?.message ?? "no user session" }, { status: 401 });
  }

  // Step 2: Confirm service role key is present
  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json({ error: "Config", detail: "SUPABASE_SERVICE_ROLE_KEY missing on server" }, { status: 503 });
  }

  // Step 3: Role check via admin client (bypasses RLS)
  const admin = createAdminClient();
  const { data: clientUser, error: roleError } = await admin
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (roleError || !clientUser) {
    return NextResponse.json({
      error: "Forbidden",
      detail: `client_users lookup: ${roleError?.message ?? "no row found"} | user_id=${user.id}`,
    }, { status: 403 });
  }

  if (clientUser.role !== "admin") {
    return NextResponse.json({
      error: "Forbidden",
      detail: `role='${clientUser.role}', need 'admin'`,
    }, { status: 403 });
  }

  // Step 4: Railway vars
  const { RAILWAY_API_TOKEN, RAILWAY_SERVICE_ID, RAILWAY_ENVIRONMENT_ID, RAILWAY_PROJECT_ID } = process.env;
  if (!RAILWAY_API_TOKEN || !RAILWAY_SERVICE_ID || !RAILWAY_ENVIRONMENT_ID || !RAILWAY_PROJECT_ID) {
    const missing = ["RAILWAY_API_TOKEN", "RAILWAY_SERVICE_ID", "RAILWAY_ENVIRONMENT_ID", "RAILWAY_PROJECT_ID"]
      .filter(k => !process.env[k]).join(", ");
    return NextResponse.json({ error: "Railway not configured", detail: `missing: ${missing}` }, { status: 503 });
  }

  // Step 5: Parse body
  const { clientId } = await req.json();
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  // Step 6: Verify client exists
  const { data: client, error: clientError } = await admin.from("clients").select("id").eq("id", clientId).single();
  if (!client) {
    return NextResponse.json({ error: "Client not found", detail: clientError?.message }, { status: 404 });
  }

  try {
    await railwayGraphQL(`
      mutation variableUpsert($input: VariableUpsertInput!) {
        variableUpsert(input: $input)
      }
    `, {
      input: {
        projectId: RAILWAY_PROJECT_ID,
        serviceId: RAILWAY_SERVICE_ID,
        environmentId: RAILWAY_ENVIRONMENT_ID,
        name: "CLIENT_ID",
        value: clientId,
      },
    });

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
