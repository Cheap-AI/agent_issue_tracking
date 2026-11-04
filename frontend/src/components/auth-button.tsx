"use client";

import Link from "next/link";
import { supabase, useSession } from "@/lib/supabase";

export function AuthButton() {
  const { session, loading } = useSession();
  if (loading) return null;

  return (
    <div className="fixed right-4 top-4 z-50 flex items-center gap-3 text-sm">
      {session ? (
        <>
          <span className="text-black/50">{session.user.email}</span>
          <button
            onClick={() => supabase.auth.signOut()}
            className="rounded-full border border-black/10 bg-white px-3 py-1 hover:bg-black/5"
          >
            Sign out
          </button>
        </>
      ) : (
        <Link href="/login" className="rounded-full bg-black px-3 py-1 text-white">
          Sign in
        </Link>
      )}
    </div>
  );
}
