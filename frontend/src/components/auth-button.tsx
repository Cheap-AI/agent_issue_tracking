"use client";

import Link from "next/link";
import { supabase, useSession } from "@/lib/supabase";

export function AuthButton() {
  const { session, loading } = useSession();
  if (loading) return null;

  return (
    <div className="account">
      {session ? (
        <>
          <span className="account__email">{session.user.email}</span>
          <button type="button" onClick={() => supabase.auth.signOut()} className="btn btn--small">
            Sign out
          </button>
        </>
      ) : (
        <Link href="/login" className="btn btn--small">
          Sign in
        </Link>
      )}
    </div>
  );
}
