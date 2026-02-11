export default function ComingSoon() {
  return (
    <main className="bg-gradient-dark min-h-screen flex flex-col items-center justify-center px-6 relative overflow-hidden">
      {/* Subtle radial glow */}
      <div
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse, rgba(196,184,154,0.06) 0%, transparent 70%)",
        }}
      />

      {/* Content */}
      <div className="relative z-10 text-center max-w-2xl">
        {/* Logo / Brand */}
        <h1 className="animate-fade-in text-glow text-5xl sm:text-6xl md:text-7xl font-light tracking-tight mb-6">
          <span className="font-medium">Solvate</span>{" "}
          <span className="text-accent">AI</span>
        </h1>

        {/* Tagline */}
        <p className="animate-fade-in-delay-1 text-lg sm:text-xl md:text-2xl text-muted font-light leading-relaxed mb-4">
          The Operating System for Chemical Distribution.
        </p>

        {/* Coming Soon */}
        <p className="animate-fade-in-delay-2 text-sm uppercase tracking-[0.3em] text-muted/60 mb-12">
          Coming Soon
        </p>

        {/* CTA Button */}
        <div className="animate-fade-in-delay-3 mb-20">
          <a
            href="mailto:hello@solvate.ai"
            className="btn-glass inline-flex items-center gap-2 px-8 py-3.5 rounded-full text-foreground text-sm tracking-wide uppercase"
          >
            Get in Touch
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              className="opacity-60"
            >
              <path
                d="M3 8h10M9 4l4 4-4 4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>
        </div>

        {/* Trust Badges */}
        <div className="animate-fade-in-delay-4 flex flex-col items-center gap-8">
          {/* Hosted in Germany */}
          <p className="text-xs uppercase tracking-[0.25em] text-muted/50">
            Hosted in Germany
          </p>

          {/* Compliance Badges */}
          <div className="flex items-center justify-center">
            <div className="trust-badge flex flex-col items-center gap-2">
              <GDPRBadge />
              <span className="text-xs tracking-wider text-muted/60">
                GDPR
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0a0a08] to-transparent pointer-events-none" />
    </main>
  );
}

/* ---------- SVG Badge Components ---------- */

function GDPRBadge() {
  // EU star circle
  const stars = Array.from({ length: 12 }, (_, i) => {
    const angle = (i * 30 - 90) * (Math.PI / 180);
    const x = 24 + 18 * Math.cos(angle);
    const y = 24 + 18 * Math.sin(angle);
    return (
      <text
        key={i}
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="central"
        fill="currentColor"
        fontSize="7"
      >
        &#9733;
      </text>
    );
  });

  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 48 48"
      fill="none"
      className="text-foreground/50"
    >
      {stars}
    </svg>
  );
}

