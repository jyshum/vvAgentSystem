import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const { name, brand_name, website_domain, brand_variations, target_queries, competitors } = body;

  if (!name?.trim() || !website_domain?.trim()) {
    return NextResponse.json({ error: "name and website_domain are required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("clients")
    .insert({
      name: name.trim(),
      brand_name: (brand_name?.trim() || name.trim()),
      website_domain: website_domain.trim(),
      brand_variations: brand_variations ?? [],
      target_queries: target_queries ?? [],
      competitors: competitors ?? [],
    })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data, { status: 201 });
}
