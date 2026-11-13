import { cva, type VariantProps } from 'class-variance-authority';
import { type ComponentProps } from 'react';
import { twMerge } from 'tailwind-merge';

const buttonVariants = cva('button', {
  variants: { variant: { default: 'button-primary', outline: 'button-outline', ghost: 'button-ghost', danger: 'button-danger' } },
  defaultVariants: { variant: 'default' },
});

export function Button({ className, variant, ...props }: ComponentProps<'button'> & VariantProps<typeof buttonVariants>) {
  return <button className={twMerge(buttonVariants({ variant }), className)} {...props} />;
}
