"""
Knowde marketplace taxonomy seed data.

Global templates (org_id=NULL) that get cloned per-org via clone_defaults_for_org().

Source: https://www.knowde.com/marketplace (extracted Feb 2026)
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.taxonomy import service


# ── Industries (13 root nodes) ──

INDUSTRIES: list[dict] = [
    {"name": "Agriculture & Feed", "slug": "agriculture-feed", "sort_order": 1},
    {"name": "Adhesives & Sealants", "slug": "adhesives-sealants", "sort_order": 2},
    {"name": "Automotive & Transportation", "slug": "automotive-transportation", "sort_order": 3},
    {"name": "Building & Construction", "slug": "building-construction", "sort_order": 4},
    {"name": "Consumer Goods", "slug": "consumer-goods", "sort_order": 5},
    {"name": "Electrical & Electronics", "slug": "electrical-electronics", "sort_order": 6},
    {"name": "Food & Nutrition", "slug": "food-nutrition", "sort_order": 7},
    {"name": "Healthcare & Pharma", "slug": "healthcare-pharma", "sort_order": 8},
    {"name": "HI&I Care", "slug": "hii-care", "sort_order": 9},
    {"name": "Industrial", "slug": "industrial", "sort_order": 10},
    {"name": "Paints & Coatings", "slug": "paints-coatings", "sort_order": 11},
    {"name": "Personal Care", "slug": "personal-care", "sort_order": 12},
    {"name": "Printing & Packaging", "slug": "printing-packaging", "sort_order": 13},
]


# ── Product Families (15 root nodes) with subcategories ──

PRODUCT_FAMILIES: list[dict] = [
    {
        "name": "Agrochemicals",
        "slug": "agrochemicals",
        "sort_order": 1,
        "children": [
            {"name": "Crop Protection", "slug": "crop-protection"},
            {"name": "Fertilizers", "slug": "fertilizers"},
            {"name": "Plant Growth Regulators", "slug": "plant-growth-regulators"},
            {"name": "Adjuvants", "slug": "adjuvants"},
        ],
    },
    {
        "name": "Animal Feed & Nutrition",
        "slug": "animal-feed-nutrition",
        "sort_order": 2,
        "children": [
            {"name": "Feed Additives", "slug": "feed-additives"},
            {"name": "Feed Ingredients", "slug": "feed-ingredients"},
            {"name": "Premixes", "slug": "feed-premixes"},
        ],
    },
    {
        "name": "Base Chemicals & Intermediates",
        "slug": "base-chemicals-intermediates",
        "sort_order": 3,
        "children": [
            {"name": "Acids & Bases", "slug": "acids-bases"},
            {"name": "Alcohols & Glycols", "slug": "alcohols-glycols"},
            {"name": "Amines", "slug": "amines"},
            {"name": "Esters", "slug": "esters"},
            {"name": "Ketones", "slug": "ketones"},
            {"name": "Silicones", "slug": "silicones"},
            {"name": "Solvents", "slug": "base-solvents"},
        ],
    },
    {
        "name": "CASE",
        "slug": "case",
        "sort_order": 4,
        "description": "Coatings, Adhesives, Sealants, Elastomers",
        "children": [
            {"name": "Coatings Ingredients", "slug": "coatings-ingredients"},
            {"name": "Adhesive Raw Materials", "slug": "adhesive-raw-materials"},
            {"name": "Sealant Raw Materials", "slug": "sealant-raw-materials"},
            {"name": "Elastomer Ingredients", "slug": "elastomer-ingredients"},
            {"name": "Resins & Binders", "slug": "resins-binders"},
            {"name": "Curing Agents & Crosslinkers", "slug": "curing-agents-crosslinkers"},
        ],
    },
    {
        "name": "Cleaning Ingredients",
        "slug": "cleaning-ingredients",
        "sort_order": 5,
        "children": [
            {"name": "Surfactants", "slug": "cleaning-surfactants"},
            {"name": "Builders & Chelants", "slug": "builders-chelants"},
            {"name": "Enzymes", "slug": "cleaning-enzymes"},
            {"name": "Solvents", "slug": "cleaning-solvents"},
            {"name": "Fragrances", "slug": "cleaning-fragrances"},
        ],
    },
    {
        "name": "Composite Materials",
        "slug": "composite-materials",
        "sort_order": 6,
        "children": [
            {"name": "Fibers & Reinforcements", "slug": "fibers-reinforcements"},
            {"name": "Matrix Resins", "slug": "matrix-resins"},
            {"name": "Core Materials", "slug": "core-materials"},
        ],
    },
    {
        "name": "Cosmetic Ingredients",
        "slug": "cosmetic-ingredients",
        "sort_order": 7,
        "children": [
            {"name": "Cosmetic Actives", "slug": "cosmetic-actives", "children": [
                {"name": "AP/Deo Actives", "slug": "ap-deo-actives"},
                {"name": "Hair Actives", "slug": "hair-actives"},
                {"name": "Oral Care Agents", "slug": "oral-care-agents"},
                {"name": "Skin Actives", "slug": "skin-actives"},
                {"name": "Sunscreen Agents", "slug": "sunscreen-agents"},
            ]},
            {"name": "Functionals", "slug": "cosmetic-functionals", "children": [
                {"name": "Antioxidants & Preservatives", "slug": "cosmetic-antioxidants-preservatives"},
                {"name": "Conditioners", "slug": "cosmetic-conditioners"},
                {"name": "Emulsifiers", "slug": "cosmetic-emulsifiers"},
                {"name": "Rheology Modifiers", "slug": "cosmetic-rheology-modifiers"},
                {"name": "Solvents", "slug": "cosmetic-solvents"},
            ]},
            {"name": "Pigments & Colorants", "slug": "cosmetic-pigments-colorants", "children": [
                {"name": "Color Pigments", "slug": "cosmetic-color-pigments"},
                {"name": "Dyes", "slug": "cosmetic-dyes"},
                {"name": "Effect Pigments", "slug": "cosmetic-effect-pigments"},
                {"name": "Treated Powders", "slug": "cosmetic-treated-powders"},
            ]},
            {"name": "Surfactants & Cleansers", "slug": "cosmetic-surfactants-cleansers", "children": [
                {"name": "Amphoteric Surfactants", "slug": "amphoteric-surfactants"},
                {"name": "Anionic Surfactants", "slug": "anionic-surfactants"},
                {"name": "Cationic Surfactants", "slug": "cationic-surfactants"},
                {"name": "Nonionic Surfactants", "slug": "nonionic-surfactants"},
            ]},
            {"name": "Vitamins, Extracts & Oils", "slug": "vitamins-extracts-oils", "children": [
                {"name": "Botanicals", "slug": "cosmetic-botanicals"},
                {"name": "Essential Oils", "slug": "essential-oils"},
                {"name": "Fixed Oils", "slug": "fixed-oils"},
                {"name": "Marine Extracts", "slug": "marine-extracts"},
            ]},
        ],
    },
    {
        "name": "Elastomers",
        "slug": "elastomers",
        "sort_order": 8,
        "children": [
            {"name": "Silicone Rubber", "slug": "silicone-rubber"},
            {"name": "Natural Rubber", "slug": "natural-rubber"},
            {"name": "Synthetic Rubber", "slug": "synthetic-rubber"},
            {"name": "Thermoplastic Elastomers", "slug": "thermoplastic-elastomers"},
        ],
    },
    {
        "name": "Fluids & Lubricants",
        "slug": "fluids-lubricants",
        "sort_order": 9,
        "children": [
            {"name": "Base Oils", "slug": "base-oils"},
            {"name": "Lubricant Additives", "slug": "lubricant-additives"},
            {"name": "Metalworking Fluids", "slug": "metalworking-fluids"},
            {"name": "Process Oils", "slug": "process-oils"},
        ],
    },
    {
        "name": "Food Ingredients",
        "slug": "food-ingredients",
        "sort_order": 10,
        "children": [
            {"name": "Functional Additives", "slug": "functional-additives", "children": [
                {"name": "Acidulants", "slug": "acidulants"},
                {"name": "Antioxidants", "slug": "food-antioxidants"},
                {"name": "Color Additives", "slug": "color-additives"},
                {"name": "Enzymes", "slug": "food-enzymes"},
                {"name": "Processing Aids", "slug": "processing-aids"},
            ]},
            {"name": "Nutrition & Fortification", "slug": "nutrition-fortification", "children": [
                {"name": "Vitamins", "slug": "food-vitamins"},
                {"name": "Minerals", "slug": "food-minerals"},
                {"name": "Proteins", "slug": "food-proteins"},
                {"name": "Fibers", "slug": "food-fibers"},
                {"name": "Prebiotics & Probiotics", "slug": "prebiotics-probiotics"},
            ]},
            {"name": "Taste & Flavor", "slug": "taste-flavor", "children": [
                {"name": "Flavor Enhancers", "slug": "flavor-enhancers"},
                {"name": "Sweeteners", "slug": "sweeteners"},
                {"name": "Spices & Herbs", "slug": "spices-herbs"},
                {"name": "Taste Modulators", "slug": "taste-modulators"},
            ]},
            {"name": "Texture & Consistency", "slug": "texture-consistency", "children": [
                {"name": "Emulsifiers", "slug": "food-emulsifiers"},
                {"name": "Hydrocolloids", "slug": "hydrocolloids"},
                {"name": "Stabilizers", "slug": "food-stabilizers"},
                {"name": "Starches", "slug": "starches"},
            ]},
            {"name": "Whole Foods, Extracts & Premixes", "slug": "whole-foods-extracts"},
        ],
    },
    {
        "name": "Industrial Additives & Materials",
        "slug": "industrial-additives-materials",
        "sort_order": 11,
        "children": [
            {"name": "Flame Retardants", "slug": "flame-retardants"},
            {"name": "Plasticizers", "slug": "plasticizers"},
            {"name": "Stabilizers", "slug": "industrial-stabilizers"},
            {"name": "Dispersible Polymer Powders", "slug": "dispersible-polymer-powders"},
            {"name": "Fillers & Minerals", "slug": "fillers-minerals"},
        ],
    },
    {
        "name": "Pharmaceuticals & Nutraceuticals",
        "slug": "pharmaceuticals-nutraceuticals",
        "sort_order": 12,
        "children": [
            {"name": "Active Pharmaceutical Ingredients", "slug": "active-pharmaceutical-ingredients"},
            {"name": "Excipients", "slug": "excipients"},
            {"name": "Nutraceutical Ingredients", "slug": "nutraceutical-ingredients"},
        ],
    },
    {
        "name": "Pigments & Colorants",
        "slug": "pigments-colorants",
        "sort_order": 13,
        "children": [
            {"name": "Organic Pigments", "slug": "organic-pigments"},
            {"name": "Inorganic Pigments", "slug": "inorganic-pigments"},
            {"name": "Dyes & Colorants", "slug": "dyes-colorants"},
            {"name": "Special Effect Pigments", "slug": "special-effect-pigments"},
        ],
    },
    {
        "name": "Plastics",
        "slug": "plastics",
        "sort_order": 14,
        "children": [
            {"name": "Basic Thermoplastics", "slug": "basic-thermoplastics", "children": [
                {"name": "Polyolefins", "slug": "polyolefins"},
                {"name": "Styrenics", "slug": "styrenics"},
                {"name": "Polyesters", "slug": "polyesters"},
            ]},
            {"name": "Engineering & Specialty Polymers", "slug": "engineering-specialty-polymers", "children": [
                {"name": "Polyamides", "slug": "polyamides"},
                {"name": "Polycarbonates", "slug": "polycarbonates"},
                {"name": "High-Performance Polymers", "slug": "high-performance-polymers"},
            ]},
            {"name": "Polymer Additives", "slug": "polymer-additives"},
            {"name": "Masterbatches", "slug": "masterbatches"},
            {"name": "Thermoset Resins", "slug": "thermoset-resins"},
            {"name": "3D Printing Polymers", "slug": "3d-printing-polymers"},
        ],
    },
    {
        "name": "Ready-to-Use Products",
        "slug": "ready-to-use-products",
        "sort_order": 15,
        "children": [],
    },
]


# ── Wacker Brand -> Category Mapping ──

WACKER_BRAND_MAPPINGS: list[dict] = [
    {
        "brand": "BELSIL",
        "producer": "Wacker Chemie AG",
        "product_families": ["cosmetic-ingredients"],
        "industries": ["personal-care"],
    },
    {
        "brand": "ELASTOSIL",
        "producer": "Wacker Chemie AG",
        "product_families": ["elastomers"],
        "industries": ["automotive-transportation", "healthcare-pharma", "electrical-electronics"],
    },
    {
        "brand": "GENIOSIL",
        "producer": "Wacker Chemie AG",
        "product_families": ["case"],
        "industries": ["building-construction", "adhesives-sealants"],
    },
    {
        "brand": "VINNAPAS",
        "producer": "Wacker Chemie AG",
        "product_families": ["industrial-additives-materials"],
        "industries": ["building-construction"],
    },
    {
        "brand": "WACKER Silicones",
        "producer": "Wacker Chemie AG",
        "product_families": ["base-chemicals-intermediates"],
        "industries": ["industrial"],
    },
]


async def _insert_tree(
    db: AsyncSession,
    nodes: list[dict],
    taxonomy_type: str,
    parent_id: int | None = None,
) -> int:
    """Recursively insert category tree nodes. Returns count of inserted nodes."""
    count = 0
    for node in nodes:
        children_data = node.pop("children", [])
        cat = await service.create_category(
            db,
            org_id=None,  # global template
            name=node["name"],
            taxonomy_type=taxonomy_type if parent_id is None else "subcategory",
            parent_id=parent_id,
            slug=node["slug"],
            description=node.get("description"),
            sort_order=node.get("sort_order", 0),
        )
        count += 1

        if children_data:
            count += await _insert_tree(db, children_data, taxonomy_type, parent_id=cat.id)

    return count


async def seed_taxonomy(db: AsyncSession) -> dict[str, int]:
    """
    Insert global template taxonomy from Knowde marketplace data.
    Safe to run multiple times (checks for existing data).
    """
    # Check if already seeded
    existing = await service.get_root_categories(db, org_id=None)
    if existing:
        return {"industries": 0, "product_families": 0, "status": "already_seeded"}

    industry_count = await _insert_tree(db, INDUSTRIES, taxonomy_type="industry")
    family_count = await _insert_tree(db, PRODUCT_FAMILIES, taxonomy_type="product_family")

    return {
        "industries": industry_count,
        "product_families": family_count,
        "status": "seeded",
    }
