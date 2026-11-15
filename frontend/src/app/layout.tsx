import type { Metadata } from "next";
import { JetBrains_Mono, Outfit, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";

// Self-hosted at build time by next/font: no runtime request to Google Fonts.
const outfit = Outfit({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-outfit",
});
const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["500", "600", "700", "800"],
  display: "swap",
  variable: "--font-jakarta",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin", "latin-ext", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "FlexBridge 1.4 — Enterprise Talaba Bandligi va Amaliyot Platformasi",
  description:
    "Talabalar, ish beruvchilar va universitetlar uchun kafolatlangan amaliyot va bandlik ekotizimi.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="uz" suppressHydrationWarning className={`${outfit.variable} ${jakarta.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen flex flex-col bg-background text-on-surface antialiased bg-grid-pattern selection:bg-[#D95F2B]/20 selection:text-[#D95F2B]">
        <ThemeProvider>
          <Navbar />
          <div className="flex-1 w-full pb-28 lg:pl-16 2xl:pl-10">{children}</div>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
