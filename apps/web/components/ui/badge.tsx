import { cva } from 'class-variance-authority';
import type { ReactNode } from 'react';

const badgeVariants = cva('badge', {
  variants: { variant: { neutral: '', good: 'badge-good', warn: 'badge-warn', bad: 'badge-bad', info: 'badge-info' } },
  defaultVariants: { variant: 'neutral' },
});

export function Badge({ children, variant }: {children: ReactNode; variant?: 'neutral'|'good'|'warn'|'bad'|'info'}) {
  return <span className={badgeVariants({ variant })}>{children}</span>;
}
