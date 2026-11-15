import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

// Self-hosted at build time by next/font: no runtime request to Google Fonts.
const inter = Inter({
  subsets: ["latin", "latin-ext", "cyrillic"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
  variable: "--font-inter",
});
const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["500", "600", "700", "800"],
  display: "swap",
  variable: "--font-jakarta",
});

export const metadata: Metadata = {
  title: "FlexBridge 1.4 — Enterprise Talaba Bandligi va Amaliyot Platformasi",
  description: "Talabalar, ish beruvchilar va universitetlar uchun kafolatlangan amaliyot va bandlik ekotizimi.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="uz" className={`dark ${inter.variable} ${jakarta.variable}`}>
      <body className="min-h-screen flex flex-col bg-background text-on-surface antialiased bg-grid-pattern selection:bg-primary/20 selection:text-primary">
        <Navbar />
        <div className="flex-1 w-full">{children}</div>
        <Footer />
      </body>
    </html>
  );
}
