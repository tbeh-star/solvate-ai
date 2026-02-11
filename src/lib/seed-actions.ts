export type ActionType =
  | "onboarding"
  | "compliance"
  | "query"
  | "quote"
  | "insight";

export type ActionPriority = "critical" | "high" | "medium" | "low";

export interface ActionButton {
  label: string;
  variant: "primary" | "secondary" | "danger";
}

export interface ActionItem {
  id: string;
  type: ActionType;
  priority: ActionPriority;
  title: string;
  summary: string;
  detail: string;
  confidence: number;
  source: string;
  createdAt: string;
  relatedProductId?: string;
  buttons: ActionButton[];
}

/* ── Visual config per action type ─────────────────────────────── */

export const ACTION_TYPE_CONFIG: Record<
  ActionType,
  { label: string; border: string; bg: string; text: string; badge: string }
> = {
  onboarding: {
    label: "Onboarding",
    border: "border-l-blue-500",
    bg: "bg-blue-50",
    text: "text-blue-700",
    badge: "bg-blue-100 text-blue-700",
  },
  compliance: {
    label: "Compliance",
    border: "border-l-red-500",
    bg: "bg-red-50",
    text: "text-red-700",
    badge: "bg-red-100 text-red-700",
  },
  query: {
    label: "Query",
    border: "border-l-amber-500",
    bg: "bg-amber-50",
    text: "text-amber-700",
    badge: "bg-amber-100 text-amber-700",
  },
  quote: {
    label: "Quote",
    border: "border-l-emerald-500",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    badge: "bg-emerald-100 text-emerald-700",
  },
  insight: {
    label: "Insight",
    border: "border-l-violet-500",
    bg: "bg-violet-50",
    text: "text-violet-700",
    badge: "bg-violet-100 text-violet-700",
  },
};

export const PRIORITY_ORDER: Record<ActionPriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

/* ── 7 seed actions ────────────────────────────────────────────── */

export const SEED_ACTIONS: ActionItem[] = [
  {
    id: "act-001",
    type: "compliance",
    priority: "critical",
    title: "REACH-Registrierung läuft ab: VINNAPAS 5044N",
    summary:
      "Der Regulatory Agent hat erkannt, dass die REACH-Registrierung in 14 Tagen ausläuft. Das Safety Data Sheet muss vor Ablauf aktualisiert und neu eingereicht werden.",
    detail:
      "Ablaufdatum: 25. Februar 2026. Betrifft REACH-Registrierungsnummer 01-2119475104-44-0023. Der Agent hat bereits die aktuelle SDS-Version (Rev. 4.2) identifiziert und ein Update-Template vorbereitet. Notwendige Schritte: (1) SDS Rev. 5.0 generieren, (2) beim ECHA-Portal einreichen, (3) nachgelagerte Kunden informieren. Geschätzter Zeitaufwand: 2–3 Stunden.",
    confidence: 87,
    source: "Regulatory Agent",
    createdAt: "2026-02-11T08:15:00Z",
    relatedProductId: "vinnapas-4712-n",
    buttons: [
      { label: "SDS aktualisieren", variant: "primary" },
      { label: "Zurückstellen", variant: "secondary" },
    ],
  },
  {
    id: "act-002",
    type: "onboarding",
    priority: "high",
    title: "Neues Produkt bereit: ELASTOSIL LR 3003/20",
    summary:
      "Der Onboarding Agent hat das technische Datenblatt geparst und 94% der Produktfelder automatisch befüllt. 3 Felder benötigen manuelle Bestätigung.",
    detail:
      "Automatisch befüllt: Produktname, CAS-Nummer, INCI-Name, physikalische Form, 12 Key Properties, 5 Anwendungsgebiete, 4 Benefits. Offene Felder: (1) Interne Artikelnummer, (2) Mindestbestellmenge, (3) Lagerklassifizierung. Der Agent schlägt vor: Artikelnummer EL-LR3003-20, MOQ 25kg, Lagerklasse 10 (nicht brennbar). Confidence basiert auf Abgleich mit 3 Herstellerdokumenten.",
    confidence: 94,
    source: "Onboarding Agent",
    createdAt: "2026-02-10T14:30:00Z",
    relatedProductId: "elastosil-4500",
    buttons: [
      { label: "Freigeben", variant: "primary" },
      { label: "Prüfen", variant: "secondary" },
      { label: "Zurückstellen", variant: "secondary" },
    ],
  },
  {
    id: "act-003",
    type: "quote",
    priority: "high",
    title: "Preisanfrage: Silicone Fluid AK 350, 20t",
    summary:
      "Kundenanfrage von ChemTrade GmbH für 20 Tonnen Silicone Fluid AK 350. Der Pricing Agent hat einen Angebotspreis von €4.280/t kalkuliert (Marge: 18,3%).",
    detail:
      "Kunde: ChemTrade GmbH (A-Kunde, Jahresvolumen €2,1M). Aktueller Marktpreis: €3.620/t (Quelle: ICIS, Stand 09.02.2026). Letzte 3 Angebote an diesen Kunden: €4.150/t, €4.220/t, €4.300/t. Agent-Empfehlung: €4.280/t basierend auf Kundenhistorie, aktuellem Marktpreis und 20t-Volumenrabatt. Alternativpreis bei 50t: €4.120/t.",
    confidence: 91,
    source: "Pricing Agent",
    createdAt: "2026-02-10T11:45:00Z",
    buttons: [
      { label: "Angebot senden", variant: "primary" },
      { label: "Preis anpassen", variant: "secondary" },
      { label: "Ablehnen", variant: "danger" },
    ],
  },
  {
    id: "act-004",
    type: "insight",
    priority: "medium",
    title: "Preisanomalie: GENIOSIL GF 56 +12% vs. Markt",
    summary:
      "Der Pricing Agent hat eine signifikante Preisabweichung erkannt: Ihr Verkaufspreis für GENIOSIL GF 56 liegt 12% über dem aktuellen Marktdurchschnitt.",
    detail:
      "Ihr aktueller Preis: €6.840/t. Marktdurchschnitt (5 Quellen): €6.107/t. Abweichung: +€733/t (+12,0%). Historischer Durchschnitt der letzten 6 Monate: +3–5% über Markt. Mögliche Ursachen: (1) Letzte Preisanpassung vor 4 Monaten, (2) Wettbewerber haben Preise gesenkt. Empfehlung: Preis auf €6.400/t anpassen (Marge bleibt >15%) oder Premium-Positionierung mit Zusatzservices rechtfertigen.",
    confidence: 78,
    source: "Pricing Agent",
    createdAt: "2026-02-09T16:20:00Z",
    relatedProductId: "geniosil-gptm",
    buttons: [
      { label: "Preis anpassen", variant: "primary" },
      { label: "Ignorieren", variant: "secondary" },
    ],
  },
  {
    id: "act-005",
    type: "query",
    priority: "medium",
    title: "Kundenanfrage: TDS für BELSIL DM 350",
    summary:
      "Ein Kunde hat das technische Datenblatt (TDS) für BELSIL DM 350 angefragt. Der Document Agent hat die aktuelle Version (Rev. 3.1, März 2025) identifiziert.",
    detail:
      "Anfrage von: Müller Cosmetics AG, Kontakt: Thomas Weber (thomas.weber@mueller-cosmetics.de). Angefragtes Dokument: Technical Data Sheet BELSIL DM 350. Gefundene Version: Rev. 3.1, aktualisiert März 2025, 4 Seiten, PDF. Der Agent hat geprüft: Dokument ist aktuell, keine neuere Version beim Hersteller verfügbar. Bereit zum Versand an den Kunden.",
    confidence: 96,
    source: "Document Agent",
    createdAt: "2026-02-09T09:10:00Z",
    relatedProductId: "belsil-dm-065",
    buttons: [
      { label: "Dokument senden", variant: "primary" },
      { label: "Zurückstellen", variant: "secondary" },
    ],
  },
  {
    id: "act-006",
    type: "compliance",
    priority: "medium",
    title: "GHS-Klassifizierung Update: POWERSIL 600",
    summary:
      "Ein neues GHS-Amendment (Rev. 10) betrifft die aktuelle Einstufung von POWERSIL 600. Der Regulatory Agent empfiehlt eine Überprüfung der H- und P-Sätze.",
    detail:
      "GHS Rev. 10 (in Kraft ab 01.01.2027, Übergangsfrist bis 01.07.2027) ändert Kriterien für Kategorie 'Skin Sensitization'. POWERSIL 600 ist aktuell als Skin Sens. 1B (H317) eingestuft. Neue Kriterien könnten eine Herabstufung auf Skin Sens. 1A erfordern, was strengere Kennzeichnung bedeutet. Agent-Empfehlung: Toxikologische Daten prüfen und ggf. Einstufung anpassen. Deadline: nicht dringend (>10 Monate), aber frühzeitige Planung empfohlen.",
    confidence: 72,
    source: "Regulatory Agent",
    createdAt: "2026-02-08T13:45:00Z",
    relatedProductId: "powersil-600",
    buttons: [
      { label: "Überprüfung starten", variant: "primary" },
      { label: "Zurückstellen", variant: "secondary" },
    ],
  },
  {
    id: "act-007",
    type: "onboarding",
    priority: "low",
    title: "Produktdaten-Enrichment: 3 Felder ergänzt für FERMOPURE",
    summary:
      "Der Onboarding Agent hat 3 fehlende Felder für FERMOPURE L-Cystine aus dem Wacker-Herstellerkatalog ergänzt: Schmelzpunkt, optische Drehung und Löslichkeit.",
    detail:
      "Ergänzte Felder: (1) Schmelzpunkt: 260°C (Zersetzung), (2) Optische Drehung [α]D20: -223° bis -218° (c=1, 1N HCl), (3) Löslichkeit: praktisch unlöslich in Wasser, löslich in verdünnten Mineralsäuren. Quelle: Wacker Chemie AG Produktkatalog 2025, Seite 247. Alle Werte mit Herstellerangaben abgeglichen. Keine Abweichungen festgestellt.",
    confidence: 98,
    source: "Onboarding Agent",
    createdAt: "2026-02-07T10:00:00Z",
    relatedProductId: "fermopure-l-cystine",
    buttons: [
      { label: "Bestätigen", variant: "primary" },
      { label: "Verwerfen", variant: "danger" },
    ],
  },
];

/* ── Helper functions ──────────────────────────────────────────── */

export function getActionCounts(
  actions: ActionItem[],
): Record<ActionType | "all", number> {
  const counts: Record<string, number> = { all: actions.length };
  for (const a of actions) {
    counts[a.type] = (counts[a.type] || 0) + 1;
  }
  return counts as Record<ActionType | "all", number>;
}

export function sortActions(
  actions: ActionItem[],
  by: "priority" | "date",
): ActionItem[] {
  return [...actions].sort((a, b) => {
    if (by === "priority") {
      const diff = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
      if (diff !== 0) return diff;
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    }
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });
}

export function timeAgo(isoDate: string): string {
  const now = new Date("2026-02-11T12:00:00Z"); // fixed for deterministic display
  const then = new Date(isoDate);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `vor ${diffMins} Min.`;
  if (diffHours < 24) return `vor ${diffHours} Std.`;
  if (diffDays === 1) return "vor 1 Tag";
  return `vor ${diffDays} Tagen`;
}
