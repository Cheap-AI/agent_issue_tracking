"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase, useSession } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const { session } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // After the Google redirect lands back here with a session, go home.
  useEffect(() => {
    if (session) router.replace("/dashboard");
  }, [session, router]);

  const signInWithGoogle = async () => {
    setBusy(true);
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/login` },
    });
    if (error) {
      setError(error.message);
      setBusy(false);
    }
  };

  return (
    <main className="container page page--center">
      <section className="panel signin" aria-labelledby="signin-heading">
        <h1 id="signin-heading">Sign in</h1>
        <button type="button" onClick={signInWithGoogle} disabled={busy} className="btn">
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z" />
            <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z" />
            <path fill="#FBBC05" d="M10.5 28.7a14.5 14.5 0 0 1 0-9.4l-7.9-6.1a24 24 0 0 0 0 21.6l7.9-6.1z" />
            <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.8 2.3-8.4 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z" />
          </svg>
          Continue with Google
        </button>
        {error && (
          <p className="notice notice--bad" role="alert">
            {error}
          </p>
        )}
      </section>
    </main>
  );
}
