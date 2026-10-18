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
      <body>
        <Navbar />
        {children}
        <ChatWidget />
      </body>
    </html>
  );
}
