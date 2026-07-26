import Link from "next/link";

export default function AboutPage() {
  return (
    <main style={{ minHeight: "100vh", padding: "1rem" }}>
      <nav style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
        <Link href="/">Home</Link>
        <Link href="/about">About</Link>
      </nav>

      <div style={{ maxWidth: "500px", margin: "0 auto" }}>
        <h1>About Page</h1>
        <p>This is a second page to show navigation in Next.js.</p>
      </div>
    </main>
  );
}
