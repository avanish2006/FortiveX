import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "react-hot-toast";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SalesPilot AI — Autonomous Sales Voice Agent",
  description:
    "AI-powered sales voice agent with real-time voice interaction, lead qualification, and CRM integration.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: "#1f2937", color: "#f9fafb", border: "1px solid #374151" },
          }}
        />
      </body>
    </html>
  );
}
