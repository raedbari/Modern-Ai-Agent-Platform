import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Athkachatbots",
    template: "%s | Athkachatbots",
  },
  description:
    "\u0645\u0646\u0635\u0629 \u0627\u062d\u062a\u0631\u0627\u0641\u064a\u0629 \u0644\u0625\u0646\u0634\u0627\u0621 \u0648\u0625\u062f\u0627\u0631\u0629 \u0631\u0648\u0628\u0648\u062a\u0627\u062a \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0627\u0644\u0630\u0643\u064a\u0629.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
