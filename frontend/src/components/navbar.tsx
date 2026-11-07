"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AuthButton } from "./auth-button";

const LINKS = [
  { href: "/", label: "Issues" },
  { href: "/about", label: "About" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="topbar">
      <div className="container topbar__inner">
        <Link href="/" className="wordmark" aria-label="Issue Tracker home">
          Issue Tracker
        </Link>
        <nav className="topbar__links" aria-label="Primary">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="navlink"
              aria-current={pathname === link.href ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <AuthButton />
      </div>
    </header>
  );
}
