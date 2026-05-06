import type { Metadata } from "next";
import { Geist_Mono, Syne } from "next/font/google";

import "@/app/globals.css";
import { Toaster } from "@/components/ui/toaster";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

export const metadata: Metadata = {
  title: "The Cutting Room",
  description: "Frontend upload portal for video edits",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${syne.variable} ${geistMono.variable} min-h-screen`}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
