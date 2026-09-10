import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'Mindful — Space to talk',
  description:
    'An experimental AI support space. Not a psychologist, therapy, or emergency service.',
  robots: { index: false, follow: false },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
