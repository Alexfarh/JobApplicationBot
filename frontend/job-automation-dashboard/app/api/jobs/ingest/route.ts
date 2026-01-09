export async function POST(request: Request) {
  try {
    // Get cookies from the request to pass to backend
    const cookies = request.headers.get("cookie") || ""
    
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/jobs/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cookie": cookies,
      },
    })

    if (!response.ok) {
      throw new Error(`API responded with ${response.status}`)
    }

    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    console.error("Job ingestion error:", error)
    return Response.json(
      { error: error instanceof Error ? error.message : "Failed to ingest jobs" },
      { status: 500 }
    )
  }
}
