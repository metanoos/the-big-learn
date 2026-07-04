"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError } from "@/lib/api";

export default function VerifyEmailPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<"verifying" | "ok" | "error">("verifying");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("No token in the link.");
      return;
    }
    fetch("/api/v1/auth/verify-email", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new ApiError(res.status, body.error || res.statusText);
        }
        return res.json();
      })
      .then(() => {
        setStatus("ok");
        setTimeout(() => router.push("/"), 1500);
      })
      .catch((e: any) => {
        setStatus("error");
        setError(e.message);
      });
  }, [token, router]);

  if (status === "verifying") {
    return <p className="text-stone-600 text-sm">Verifying your email…</p>;
  }
  if (status === "ok") {
    return (
      <div className="space-y-2">
        <h1 className="font-serif text-xl text-stone-900">Email verified ✓</h1>
        <p className="text-sm text-stone-600">Heading to the library…</p>
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <h1 className="font-serif text-xl text-stone-900">Verification failed</h1>
      <p className="text-sm text-rose-600">{error}</p>
      <p className="text-xs text-stone-500">
        The link may have expired (24h) or already been used. Sign in and resend
        from your account.
      </p>
    </div>
  );
}
