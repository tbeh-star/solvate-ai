import { NextResponse } from "next/server";
import { getAccessToken } from "@auth0/nextjs-auth0";

export async function GET() {
  try {
    const token = await getAccessToken();
    return NextResponse.json({ accessToken: token });
  } catch {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }
}
