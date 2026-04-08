import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost";

export const metadata: Metadata = {
  title: "Flowora",
  description: "Where AI Agents Flow Together",
  metadataBase: new URL(siteUrl),
  openGraph: {
    title: "Flowora - Where AI Agents Flow Together",
    description: "Build, orchestrate, and scale AI agents with visual workflows.",
    images: ["/logo.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "Flowora - Where AI Agents Flow Together",
    images: ["/logo.png"],
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
