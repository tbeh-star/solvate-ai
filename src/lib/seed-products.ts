export interface SeedProduct {
  id: string;
  name: string;
  brand: string;
  category: string;
  inci_name?: string;
  cas_number?: string;
  physical_form?: string;
  producer: string;
  description: string;
  key_properties: string[];
  applications: string[];
  benefits: string[];
}

export const BRANDS = [
  "BELSIL",
  "ELASTOSIL",
  "GENIOSIL",
  "VINNAPAS",
  "POWERSIL",
  "FERMOPURE",
] as const;

export const SEED_PRODUCTS: SeedProduct[] = [
  {
    id: "belsil-dm-065",
    name: "BELSIL DM 0.65",
    brand: "BELSIL",
    category: "Silicone Fluids",
    inci_name: "Disiloxane",
    physical_form: "Liquid",
    producer: "Wacker Chemie AG",
    description:
      "Colorless, clear fluid of low viscosity and high volatility. Evaporates from the skin without producing a cooling or stinging effect.",
    key_properties: [
      "Low viscosity and high volatility",
      "Non-polar, insoluble in water",
      "Miscible with alcohols, esters, and organic solvents",
      "Low heat of vaporization",
      "Evaporates rapidly without residues",
    ],
    applications: [
      "Hair conditioners",
      "Hair styling products",
      "Makeup and color cosmetics",
      "Skin care formulations",
      "Sun care products",
      "Antiperspirant/deodorant delivery systems",
    ],
    benefits: [
      "Uniform spreading of actives and pigments",
      "Improves rub-in properties in color cosmetics",
      "Reduces stickiness",
      "Imparts lubricity and smooth skin feel",
      "Improves wet combability in hair care",
    ],
  },
  {
    id: "belsil-dm-100",
    name: "BELSIL DM 100",
    brand: "BELSIL",
    category: "Silicone Fluids",
    inci_name: "Dimethicone",
    physical_form: "Liquid",
    producer: "Wacker Chemie AG",
    description:
      "Linear, non-reactive polydimethylsiloxane with low surface tension and high spreading coefficient. Optimal viscosity for cosmetic formulations.",
    key_properties: [
      "Linear polydimethylsiloxane",
      "Non-reactive and unmodified",
      "Low surface tension",
      "High spreading coefficient",
      "Flexible polymer backbone",
    ],
    applications: [
      "Hair care products",
      "Skin care formulations",
      "Makeup applications",
      "Color cosmetics",
      "Personal care products",
    ],
    benefits: [
      "Excellent spreading properties",
      "Thin film formation",
      "Compatible with various cosmetic ingredients",
      "Optimal for emulsion systems",
    ],
  },
  {
    id: "belsil-adm-1370",
    name: "BELSIL ADM 1370",
    brand: "BELSIL",
    category: "Silicone Fluids, Functional",
    inci_name: "Amodimethicone",
    physical_form: "Liquid",
    producer: "Wacker Chemie AG",
    description:
      "Aminofunctional polydimethylsiloxane with low odor profile. Ideal for sensitive personal care applications, particularly hair care formulations.",
    key_properties: [
      "Aminofunctional polydimethylsiloxane",
      "Viscosity < 4000 mm\u00B2/s",
      "Low odor profile",
      "Positively charged in acidic conditions",
      "Interacts with negatively charged hair surface",
    ],
    applications: [
      "Shampoos",
      "Rinse-off conditioners",
      "Hair masks and serums",
      "Styling products",
      "Anti-static formulations",
    ],
    benefits: [
      "Improves wet and dry combing",
      "Soft and smooth hair feel",
      "Excellent color protection",
      "Heat protection benefits",
      "Reduces electrostatic fly-away",
    ],
  },
  {
    id: "belsil-eg-6000",
    name: "BELSIL EG 6000",
    brand: "BELSIL",
    category: "Silicone Elastomer Gels",
    inci_name: "Dimethicone and Divinyldimethicone/Dimethicone Crosspolymer",
    physical_form: "Gel",
    producer: "Wacker Chemie AG",
    description:
      "Silicone copolymer network blended with volatile dimethicone. Transparent, colorless gel with excellent shear-thinning behavior and thickening properties.",
    key_properties: [
      "Silicone copolymer network",
      "Transparent, colorless gel",
      "Highly shear-thinning",
      "Acts as thickening agent",
      "Non-greasy, silky feel",
      "Leaves non-tacky matte film",
    ],
    applications: [
      "Skin care products",
      "Makeup foundations",
      "Eye and lip makeup",
      "After-sun products",
      "Deodorants",
      "Hair styling products",
    ],
    benefits: [
      "Smooth, non-greasy silky skin feel",
      "Matte effect on skin",
      "Versatile thickening agent",
      "Adds cushiony feel to formulations",
      "Excellent pigment incorporation",
    ],
  },
  {
    id: "belsil-tms-803",
    name: "BELSIL TMS 803",
    brand: "BELSIL",
    category: "Silicone Resins",
    physical_form: "Resin",
    producer: "Wacker Chemie AG",
    description:
      "Co-hydrolysis product of tetraalkoxysilane (Q unit) and trimethylethoxysilane (M unit). Three-dimensional siloxane polymer network with unique resin properties.",
    key_properties: [
      "Co-hydrolysis product (Q-M structure)",
      "Three-dimensional siloxane network",
      "Crosslinked polymer structure",
      "Silicone resin characteristics",
    ],
    applications: [
      "Cosmetic formulations",
      "Resinous personal care components",
      "Structural polymer applications",
    ],
    benefits: [
      "Unique three-dimensional network structure",
      "Film-forming properties",
      "Enhanced durability in formulations",
    ],
  },
  {
    id: "elastosil-4500",
    name: "ELASTOSIL 4500",
    brand: "ELASTOSIL",
    category: "Silicone Sealants",
    physical_form: "Paste",
    producer: "Wacker Chemie AG",
    description:
      "One-component, acid-curing silicone sealant for high temperature applications up to 250\u00B0C. Cures at room temperature to give permanently flexible silicone rubber.",
    key_properties: [
      "One-component, acid-curing system",
      "Non-sag formulation",
      "Flexible from -40\u00B0C to +250\u00B0C",
      "Rapid crosslinking, quickly tack-free",
      "Short-term resistance up to 275\u00B0C",
    ],
    applications: [
      "High-temperature joint sealing",
      "Oven and chimney construction",
      "Industrial sealing applications",
    ],
    benefits: [
      "Outstanding heat resistance up to 250\u00B0C",
      "Excellent primerless adhesion to glass and ceramics",
      "Good tooling properties",
      "Maintains elastic properties at extreme temperatures",
    ],
  },
  {
    id: "geniosil-gptm",
    name: "GENIOSIL GPTM",
    brand: "GENIOSIL",
    category: "Organofunctional Silanes",
    cas_number: "2530-83-8",
    physical_form: "Liquid",
    producer: "Wacker Chemie AG",
    description:
      "3-Glycidoxypropyltrimethoxysilane. Epoxyfunctional alkoxysilane used as coupling agent for mineral-filled plastics and as adhesion promoter in adhesives and sealants.",
    key_properties: [
      "Epoxyfunctional alkoxysilane",
      "Bifunctional organic molecule with silyl group",
      "Molecular bridge between inorganic and organic substrates",
      "Miscible with standard organic solvents",
      "Physically dissolvable in water up to 5 wt%",
    ],
    applications: [
      "Mineral-filled plastics (coupling agent)",
      "Adhesives and sealants",
      "Coatings, paints, primers",
      "Filler treatment (glass, ATH, kaolin, mica)",
      "Composites",
    ],
    benefits: [
      "Improves filler dispersibility",
      "Lowers resin viscosity, allows higher filler loading",
      "Marked increase in water resistance",
      "Improves adhesion to substrate",
      "Enhances mechanical properties",
    ],
  },
  {
    id: "geniosil-aptm",
    name: "GENIOSIL APTM",
    brand: "GENIOSIL",
    category: "Organofunctional Silanes",
    cas_number: "13822-56-5",
    physical_form: "Liquid",
    producer: "Wacker Chemie AG",
    description:
      "3-Aminopropyltrimethoxysilane. Aminofunctional alkoxysilane serving as adhesion promoter and surface modifier for various industrial applications.",
    key_properties: [
      "Aminofunctional alkoxysilane",
      "Bifunctional amine structure",
      "Molecular bridge between organic and inorganic substrates",
      "Highly miscible with organic solvents",
      "Highly soluble in neutral water",
    ],
    applications: [
      "Adhesion promoter in formulations",
      "Surface modifier for fillers and pigments",
      "Adhesives, sealants, coatings",
      "Glass-fiber reinforced polymers",
      "Composites",
    ],
    benefits: [
      "Improves filler dispersibility",
      "Enhances mechanical properties",
      "Reduces filler sedimentation",
      "Greatly increases water and corrosion resistance",
      "Effective adhesion promoter",
    ],
  },
  {
    id: "vinnapas-4712-n",
    name: "VINNAPAS 4712 N",
    brand: "VINNAPAS",
    category: "Dispersible Polymer Powders",
    physical_form: "Powder",
    producer: "Wacker Chemie AG",
    description:
      "Dispersible polymer powder suited for tile adhesives with optimum adhesion to wood and excellent water resistance. ANSI/ISO compliant.",
    key_properties: [
      "Dispersible polymer powder",
      "Vinyl acetate-ethylene (VAE) copolymer",
      "High performance formulation",
      "ANSI/ISO compliant",
    ],
    applications: [
      "Tile adhesives",
      "Ceramic bonding",
      "Wood substrate bonding",
      "Construction materials",
    ],
    benefits: [
      "Optimum adhesion to wood",
      "Excellent water resistance",
      "Standards compliant formulation",
      "High performance in construction applications",
    ],
  },
  {
    id: "vinnapas-5343-e",
    name: "VINNAPAS 5343 E",
    brand: "VINNAPAS",
    category: "Dispersible Polymer Powders",
    physical_form: "Powder",
    producer: "Wacker Chemie AG",
    description:
      "Dispersible polymer powder for paver joint sand applications. Imparts flexibility while reducing wash-out in outdoor environments.",
    key_properties: [
      "Dispersible polymer powder",
      "Flexible formulation",
      "Wash-out resistant",
      "Weather resistant",
    ],
    applications: [
      "Paver joint sand",
      "Outdoor tile applications",
      "Flexible joint filling",
    ],
    benefits: [
      "Flexibility with reduced wash-out",
      "Weather resistance for outdoor use",
      "Easy to incorporate in dry-mix formulations",
    ],
  },
  {
    id: "powersil-600",
    name: "POWERSIL 600 A/B",
    brand: "POWERSIL",
    category: "Two-Component Silicone Elastomers",
    physical_form: "Liquid (A/B system)",
    producer: "Wacker Chemie AG",
    description:
      "Two-component silicone elastomer system for applications requiring custom mixing and tailored property profiles in power transmission and electrical systems.",
    key_properties: [
      "Two-component A:B system",
      "Customizable property profile",
      "Excellent cure characteristics",
      "Superior electrical properties",
      "Outstanding thermal performance",
    ],
    applications: [
      "Custom elastomer formulations",
      "Specialized power equipment",
      "High-performance electrical components",
      "Transmission system applications",
    ],
    benefits: [
      "Customizable properties via mixing ratio",
      "Versatile formulation flexibility",
      "Superior electrical insulation",
      "Outstanding thermal stability",
    ],
  },
  {
    id: "fermopure-l-cystine",
    name: "FERMOPURE L-Cystine PHARMA",
    brand: "FERMOPURE",
    category: "Amino Acids",
    cas_number: "56-89-3",
    physical_form: "Powder",
    producer: "Wacker Chemie AG",
    description:
      "L-Cystine amino acid dimer produced via fermentation from non-animal raw materials. Practically insoluble in water, dissolves in dilute alkali solutions.",
    key_properties: [
      "Amino acid dimer (disulfide bond)",
      "Purity: 98.5\u2013101.0%",
      "Complies with Eur.Ph. and FCC",
      "Fermentation-derived, non-animal origin",
      "BSE/TSE-free",
    ],
    applications: [
      "Pharmaceutical excipient",
      "API synthesis (expectorants)",
      "Cell culture media",
      "Personal care formulations",
    ],
    benefits: [
      "Non-GMO microorganisms",
      "Kosher and halal certified",
      "36-month shelf life",
      "Natural designation (Regulation 1334/2008/EC)",
    ],
  },
  {
    id: "fermopure-l-cysteine",
    name: "FERMOPURE L-Cysteine PHARMA",
    brand: "FERMOPURE",
    category: "Amino Acids",
    cas_number: "7048-04-6",
    physical_form: "Powder",
    producer: "Wacker Chemie AG",
    description:
      "L-Cysteine Hydrochloride Monohydrate. Sulfur-containing natural amino acid produced via fermentation from non-animal and non-human raw materials.",
    key_properties: [
      "L-Cysteine Hydrochloride Monohydrate",
      "Purity: 98.5\u2013101.0%",
      "Complies with Eur.Ph. and USP",
      "Freely soluble in water",
      "Fermentation-derived, non-animal origin",
    ],
    applications: [
      "Pharma excipient and API synthesis",
      "Process aid in insulin fermentation",
      "Cell culture media",
      "Hair-perm formulations",
      "Personal care",
    ],
    benefits: [
      "Non-GMO source materials",
      "Kosher and halal certified",
      "BSE/TSE-free",
      "24-month shelf life",
      "Pharmaceutical grade compliance",
    ],
  },
];
