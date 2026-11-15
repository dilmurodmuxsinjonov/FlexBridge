import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";

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
    <html lang="uz" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
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
