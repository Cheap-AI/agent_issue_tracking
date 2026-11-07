import "./globals.css";
import type { Metadata } from "next";
import { Navbar } from "@/components/navbar";
import { ChatWidget } from "@/components/chat-widget";

export const metadata: Metadata = {
  title: "Issue Tracking Platform",
  description: "AI-native issue intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Host+Grotesk:wght@400;500&family=Atkinson+Hyperlegible+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        <Navbar />
        {children}
        <ChatWidget />
      </body>
    </html>
  );
}
