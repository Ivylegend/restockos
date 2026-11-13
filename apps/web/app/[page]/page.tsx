import { notFound } from 'next/navigation';
import { Workspace, type Page } from '@/components/workspace';

export default async function WorkspacePage({ params }: {params: Promise<{page:string}>}) {
  const { page } = await params;
  if (!['inventory', 'suppliers', 'agent', 'orders', 'treasury', 'settings'].includes(page)) notFound();
  return <Workspace page={page as Page} />;
}
