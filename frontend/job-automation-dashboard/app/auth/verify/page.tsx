"use client"

import { useEffect, useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { authAPI } from "@/lib/auth"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2 } from "lucide-react"

function VerifyPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState("")
  const [isVerifying, setIsVerifying] = useState(true)

  useEffect(() => {
    const token = searchParams.get("token")

    if (!token) {
      setError("No verification token provided")
      setIsVerifying(false)
      return
    }

    const verify = async () => {
      try {
        const response = await authAPI.verifyToken(token)

        // Check if profile is complete
        if (!response.profile_complete) {
          router.push("/profile?onboarding=true")
        } else {
          router.push("/dashboard")
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Verification failed")
        setIsVerifying(false)
      }
    }

    verify()
  }, [searchParams, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Verifying Your Sign-In</CardTitle>
          <CardDescription>Please wait while we verify your magic link</CardDescription>
        </CardHeader>
        <CardContent>
          {isVerifying ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
            </div>
          ) : (
            <Alert variant="destructive">
              <AlertDescription>
                {error || "Verification failed. Please try logging in again."}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>}>
      <VerifyPageContent />
    </Suspense>
  )
}
