import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'RestockOS | Procurement workspace', description: 'Inventory, supplier quotes and autonomous procurement on NEAR Testnet.' };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
