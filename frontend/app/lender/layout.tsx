export default function LenderLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
      {/* Atmospheric backdrop for the quantum/lender glass design system.
          Fixed + behind content (-z-10) so it doesn't affect layout flow
          or scroll with the page. */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-24 w-[32rem] h-[32rem] rounded-full bg-accent/20 dark:bg-accent/25 blur-[110px]" />
        <div className="absolute top-1/3 -right-24 w-[28rem] h-[28rem] rounded-full bg-cyanAccent/15 dark:bg-cyanAccent/20 blur-[110px]" />
        <div className="absolute bottom-0 left-1/4 w-[26rem] h-[26rem] rounded-full bg-primary/10 dark:bg-primary/20 blur-[110px]" />
      </div>
      {children}
    </div>
  );
}
