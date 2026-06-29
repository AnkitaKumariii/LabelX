"""
Qdrant Seeder — Loads 70+ food additive embeddings into Qdrant.

Usage:
    cd backend
    python services/seed_qdrant.py

Requires QDRANT_URL and QDRANT_API_KEY in environment (or .env file).
"""
import os
import sys
import time
import logging
from pathlib import Path

# Add parent to path so imports work when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.qdrant_service import get_sync_client, upsert_ingredient_sync, COLLECTION_NAME, VECTOR_SIZE
from qdrant_client.models import Distance, VectorParams

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

# ── 70+ Food Additive Database ─────────────────────────────────────────────────

FOOD_ADDITIVES = [
    # ── Preservatives ──────────────────────────────────────────────────────────
    {
        "name": "Sodium Benzoate", "aliases": ["E211", "benzoic acid sodium salt"],
        "safety_rating": "caution",
        "health_impact": "May form benzene (carcinogen) with vitamin C. Linked to hyperactivity in children. Possible thyroid disruption.",
        "conditions_affected": ["ADHD", "thyroid disorders", "asthma"],
        "banned_in": [], "daily_limit_mg": 5.0,
    },
    {
        "name": "Sodium Nitrite", "aliases": ["E250", "nitrous acid sodium salt"],
        "safety_rating": "caution",
        "health_impact": "Can form nitrosamines (carcinogens) during cooking at high heat. Linked to colorectal cancer at high intakes.",
        "conditions_affected": ["cancer risk", "cardiovascular disease"],
        "banned_in": [], "daily_limit_mg": 0.07,
    },
    {
        "name": "Sodium Nitrate", "aliases": ["E251", "chile saltpeter"],
        "safety_rating": "caution",
        "health_impact": "Converts to nitrite in body; same risks as sodium nitrite. Used in cured meats.",
        "conditions_affected": ["cancer risk", "cardiovascular disease"],
        "banned_in": [], "daily_limit_mg": 3.7,
    },
    {
        "name": "Potassium Sorbate", "aliases": ["E202", "sorbic acid potassium salt"],
        "safety_rating": "safe",
        "health_impact": "Generally recognized as safe (GRAS). May cause mild skin irritation in sensitive individuals.",
        "conditions_affected": ["skin sensitivity"],
        "banned_in": [], "daily_limit_mg": 25.0,
    },
    {
        "name": "Calcium Propionate", "aliases": ["E282", "propanoic acid calcium salt"],
        "safety_rating": "safe",
        "health_impact": "GRAS status. Some studies link high intake to behavioral changes in children. Widely used in bread.",
        "conditions_affected": ["ADHD"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Sodium Metabisulfite", "aliases": ["E223", "disodium metabisulfite", "sodium pyrosulfite"],
        "safety_rating": "caution",
        "health_impact": "Can trigger severe asthma attacks in sulfite-sensitive individuals. Can destroy thiamine (Vitamin B1).",
        "conditions_affected": ["asthma", "sulfite sensitivity"],
        "banned_in": [], "daily_limit_mg": 0.7,
    },
    {
        "name": "Sulfur Dioxide", "aliases": ["E220", "sulphur dioxide"],
        "safety_rating": "caution",
        "health_impact": "Asthma trigger. Can cause respiratory problems. Destroys Vitamin B1.",
        "conditions_affected": ["asthma", "COPD", "sulfite allergy"],
        "banned_in": [], "daily_limit_mg": 0.7,
    },
    {
        "name": "EDTA", "aliases": ["Ethylenediaminetetraacetic acid", "E385", "calcium disodium EDTA"],
        "safety_rating": "caution",
        "health_impact": "May reduce absorption of minerals. Some animal studies show reproductive toxicity at high doses.",
        "conditions_affected": ["mineral deficiency"],
        "banned_in": [], "daily_limit_mg": 2.5,
    },
    {
        "name": "TBHQ", "aliases": ["tert-Butylhydroquinone", "E319", "tertiary butylhydroquinone"],
        "safety_rating": "caution",
        "health_impact": "Possible carcinogen at high doses (animal studies). May enhance effects of some toxins. Banned in Japan.",
        "conditions_affected": ["cancer risk"],
        "banned_in": ["Japan"], "daily_limit_mg": 0.7,
    },
    {
        "name": "Butylated Hydroxyanisole", "aliases": ["BHA", "E320"],
        "safety_rating": "harmful",
        "health_impact": "Classified as possible human carcinogen (IARC Group 2B). Endocrine disruptor. Tumor promotion in animal studies.",
        "conditions_affected": ["cancer risk", "hormonal disorders"],
        "banned_in": ["Japan"], "daily_limit_mg": 0.5,
    },
    {
        "name": "Butylated Hydroxytoluene", "aliases": ["BHT", "E321"],
        "safety_rating": "caution",
        "health_impact": "Potential carcinogen. May affect blood clotting and thyroid function. Endocrine disruptor in animal studies.",
        "conditions_affected": ["thyroid disorders", "bleeding disorders"],
        "banned_in": [], "daily_limit_mg": 0.3,
    },
    # ── Artificial Colors ──────────────────────────────────────────────────────
    {
        "name": "Red 40", "aliases": ["Allura Red AC", "E129", "FD&C Red No. 40"],
        "safety_rating": "caution",
        "health_impact": "Linked to hyperactivity in children. Contains benzidine contaminant (known carcinogen). Potential allergen.",
        "conditions_affected": ["ADHD", "allergies"],
        "banned_in": ["Norway", "Finland", "France"], "daily_limit_mg": None,
    },
    {
        "name": "Yellow 5", "aliases": ["Tartrazine", "E102", "FD&C Yellow No. 5"],
        "safety_rating": "caution",
        "health_impact": "Can cause allergic reactions especially in aspirin-sensitive individuals. Linked to hyperactivity. Must carry warning label in EU.",
        "conditions_affected": ["ADHD", "aspirin sensitivity", "allergies"],
        "banned_in": ["Norway", "Austria"], "daily_limit_mg": 7.5,
    },
    {
        "name": "Yellow 6", "aliases": ["Sunset Yellow FCF", "E110", "FD&C Yellow No. 6"],
        "safety_rating": "caution",
        "health_impact": "Linked to hyperactivity in children. May cause allergic reactions. Contains small amounts of carcinogens as impurities.",
        "conditions_affected": ["ADHD", "allergies"],
        "banned_in": ["Norway", "Finland"], "daily_limit_mg": 2.5,
    },
    {
        "name": "Blue 1", "aliases": ["Brilliant Blue FCF", "E133", "FD&C Blue No. 1"],
        "safety_rating": "caution",
        "health_impact": "Limited safety data. May cause allergic reactions. Some studies suggest possible genotoxicity.",
        "conditions_affected": ["allergies"],
        "banned_in": ["Belgium", "France", "Germany", "Switzerland"], "daily_limit_mg": 12.5,
    },
    {
        "name": "Blue 2", "aliases": ["Indigo Carmine", "E132", "FD&C Blue No. 2"],
        "safety_rating": "caution",
        "health_impact": "Associated with brain tumors in male rats (high dose). Possible allergen. Limited human data.",
        "conditions_affected": ["allergies", "cancer risk"],
        "banned_in": ["Norway"], "daily_limit_mg": 5.0,
    },
    {
        "name": "Caramel Color", "aliases": ["E150", "E150a", "E150d", "caramel coloring"],
        "safety_rating": "caution",
        "health_impact": "Class IV caramel (E150d) contains 4-MEI, a possible carcinogen. Widely used in colas and sauces.",
        "conditions_affected": ["cancer risk"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Titanium Dioxide", "aliases": ["E171", "CI 77891"],
        "safety_rating": "harmful",
        "health_impact": "Banned in EU food use (2022). Genotoxic in animal studies. Nanoparticles may accumulate in body.",
        "conditions_affected": ["cancer risk"],
        "banned_in": ["European Union"], "daily_limit_mg": None,
    },
    # ── Artificial Sweeteners ──────────────────────────────────────────────────
    {
        "name": "Aspartame", "aliases": ["E951", "NutraSweet", "Equal", "AminoSweet"],
        "safety_rating": "caution",
        "health_impact": "Contains phenylalanine (DANGEROUS for PKU). WHO classified as possibly carcinogenic (Group 2B, 2023). Headaches in sensitive individuals.",
        "conditions_affected": ["PKU", "phenylketonuria", "migraines", "cancer risk"],
        "banned_in": [], "daily_limit_mg": 40.0,
    },
    {
        "name": "Sucralose", "aliases": ["E955", "Splenda", "trichlorogalactosucrose"],
        "safety_rating": "caution",
        "health_impact": "May alter gut microbiome composition. Recent studies (2023) link to DNA damage at high doses. May elevate glucose/insulin in some people.",
        "conditions_affected": ["diabetes", "gut health"],
        "banned_in": [], "daily_limit_mg": 5.0,
    },
    {
        "name": "Saccharin", "aliases": ["E954", "Sweet'N Low", "sodium saccharin"],
        "safety_rating": "caution",
        "health_impact": "Classified as possible carcinogen in 1970s (removed from list). May disrupt gut microbiome. Bitter metallic aftertaste.",
        "conditions_affected": ["gut health"],
        "banned_in": [], "daily_limit_mg": 5.0,
    },
    {
        "name": "Acesulfame Potassium", "aliases": ["Acesulfame K", "E950", "Ace-K", "Sweet One"],
        "safety_rating": "caution",
        "health_impact": "Limited long-term studies. Animal studies show possible carcinogenicity. May affect insulin response.",
        "conditions_affected": ["diabetes", "cancer risk"],
        "banned_in": [], "daily_limit_mg": 15.0,
    },
    {
        "name": "Steviol Glycosides", "aliases": ["Stevia", "E960", "rebaudioside A", "rebiana"],
        "safety_rating": "safe",
        "health_impact": "Generally safe. Natural origin from stevia plant. May lower blood pressure — caution for hypotension patients.",
        "conditions_affected": ["hypotension"],
        "banned_in": [], "daily_limit_mg": 4.0,
    },
    {
        "name": "Sorbitol", "aliases": ["E420", "D-glucitol", "sorbol"],
        "safety_rating": "caution",
        "health_impact": "Can cause bloating, gas, and diarrhea in large amounts. Not suitable for IBS. Still affects blood sugar (lower GI than sugar).",
        "conditions_affected": ["IBS", "diabetes", "fructose malabsorption"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Xylitol", "aliases": ["E967", "birch sugar"],
        "safety_rating": "safe",
        "health_impact": "Safe for humans. TOXIC TO DOGS. Dental benefits. May cause diarrhea in large amounts. Low GI — suitable for diabetics.",
        "conditions_affected": ["IBS"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Erythritol", "aliases": ["E968"],
        "safety_rating": "caution",
        "health_impact": "Generally safe. Large 2023 study linked high erythritol blood levels to cardiovascular events — more research needed.",
        "conditions_affected": ["cardiovascular disease"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Maltitol", "aliases": ["E965", "maltitol syrup"],
        "safety_rating": "caution",
        "health_impact": "Higher glycemic index than other sugar alcohols — not ideal for diabetics. Can cause digestive issues.",
        "conditions_affected": ["diabetes", "IBS"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Sugars & Syrups ────────────────────────────────────────────────────────
    {
        "name": "High Fructose Corn Syrup", "aliases": ["HFCS", "glucose-fructose syrup", "isoglucose", "corn sugar", "corn syrup"],
        "safety_rating": "caution",
        "health_impact": "Linked to obesity, type 2 diabetes, insulin resistance, and metabolic syndrome. Rapidly raises blood sugar.",
        "conditions_affected": ["diabetes", "obesity", "metabolic syndrome", "cardiovascular disease"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Maltodextrin", "aliases": ["modified corn starch", "glucose polymer"],
        "safety_rating": "caution",
        "health_impact": "Very high glycemic index (higher than sugar). Hidden carbohydrate — raises blood glucose rapidly. Can disrupt gut microbiome.",
        "conditions_affected": ["diabetes", "gut health"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Dextrose", "aliases": ["D-glucose", "corn glucose", "grape sugar"],
        "safety_rating": "caution",
        "health_impact": "Pure glucose — rapidly raises blood sugar. Hidden sugar ingredient that diabetics must monitor.",
        "conditions_affected": ["diabetes", "obesity"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Flavor Enhancers ───────────────────────────────────────────────────────
    {
        "name": "Monosodium Glutamate", "aliases": ["MSG", "E621", "sodium glutamate", "glutamic acid"],
        "safety_rating": "caution",
        "health_impact": "May cause headaches, flushing, sweating in sensitive individuals. High sodium content raises blood pressure.",
        "conditions_affected": ["hypertension", "migraines", "MSG sensitivity"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Disodium Inosinate", "aliases": ["E631", "sodium inosinate", "IMP"],
        "safety_rating": "caution",
        "health_impact": "Often used with MSG to enhance flavor. May worsen gout. Not suitable for those on purine-restricted diets.",
        "conditions_affected": ["gout", "hyperuricemia"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Disodium Guanylate", "aliases": ["E627", "sodium guanylate", "GMP"],
        "safety_rating": "caution",
        "health_impact": "Purine-based flavor enhancer. May trigger gout attacks. Often paired with MSG.",
        "conditions_affected": ["gout", "hyperuricemia"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Emulsifiers ────────────────────────────────────────────────────────────
    {
        "name": "Lecithin", "aliases": ["E322", "soy lecithin", "sunflower lecithin"],
        "safety_rating": "safe",
        "health_impact": "Generally safe. Soy-derived versions may trigger soy allergies. Supports brain health.",
        "conditions_affected": ["soy allergy"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Polysorbate 80", "aliases": ["E433", "Tween 80"],
        "safety_rating": "caution",
        "health_impact": "May disrupt gut microbiome and promote intestinal inflammation. Linked to IBD in animal studies. Possible allergen.",
        "conditions_affected": ["IBD", "Crohn's disease", "gut health", "allergies"],
        "banned_in": [], "daily_limit_mg": 25.0,
    },
    {
        "name": "Polysorbate 60", "aliases": ["E435", "Tween 60"],
        "safety_rating": "caution",
        "health_impact": "Similar concerns to Polysorbate 80. Gut microbiome disruption at regular intake.",
        "conditions_affected": ["IBD", "gut health"],
        "banned_in": [], "daily_limit_mg": 25.0,
    },
    {
        "name": "Carrageenan", "aliases": ["E407", "Irish moss extract"],
        "safety_rating": "caution",
        "health_impact": "Linked to gut inflammation and GI issues. Degraded form (poligeenan) is carcinogenic. May worsen IBS/IBD.",
        "conditions_affected": ["IBS", "IBD", "Crohn's disease", "colitis"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Mono and Diglycerides", "aliases": ["E471", "glyceryl monostearate", "glycerol monostearate"],
        "safety_rating": "caution",
        "health_impact": "May contain trans fats (not required to be labeled). Used as emulsifier in processed foods.",
        "conditions_affected": ["cardiovascular disease"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Thickeners & Stabilizers ───────────────────────────────────────────────
    {
        "name": "Xanthan Gum", "aliases": ["E415"],
        "safety_rating": "safe",
        "health_impact": "Generally safe. May cause digestive discomfort in very large quantities. Safe for celiacs as gluten-free thickener.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Guar Gum", "aliases": ["E412", "guaran"],
        "safety_rating": "safe",
        "health_impact": "Generally safe. Can lower blood sugar and cholesterol (beneficial). May cause GI discomfort at high doses.",
        "conditions_affected": ["diabetes"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Locust Bean Gum", "aliases": ["E410", "carob bean gum", "carob gum"],
        "safety_rating": "safe",
        "health_impact": "Generally safe. Soluble fiber with modest cholesterol-lowering effect.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Pectin", "aliases": ["E440", "citrus pectin", "apple pectin"],
        "safety_rating": "safe",
        "health_impact": "Natural plant fiber. Beneficial for gut health, blood sugar control, and cholesterol. Very safe.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Cellulose", "aliases": ["E460", "microcrystalline cellulose", "MCC", "powdered cellulose"],
        "safety_rating": "safe",
        "health_impact": "Insoluble dietary fiber. Not digested. Used as bulking agent. Generally safe.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Anti-caking & Flow Agents ──────────────────────────────────────────────
    {
        "name": "Silicon Dioxide", "aliases": ["E551", "silica", "amorphous silicon dioxide"],
        "safety_rating": "safe",
        "health_impact": "Generally safe as anti-caking agent. Nanoparticle form has raised concerns but food grade is considered safe.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Sodium Aluminosilicate", "aliases": ["E554", "sodium aluminum silicate"],
        "safety_rating": "caution",
        "health_impact": "Contains aluminum. High aluminum intake linked to neurotoxicity and Alzheimer's disease risk (contested).",
        "conditions_affected": ["kidney disease", "Alzheimer's risk"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Acids & pH Regulators ─────────────────────────────────────────────────
    {
        "name": "Citric Acid", "aliases": ["E330"],
        "safety_rating": "safe",
        "health_impact": "Generally safe in food amounts. May erode tooth enamel at high consumption. Can cause mouth sores in sensitive people.",
        "conditions_affected": ["dental health"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Phosphoric Acid", "aliases": ["E338", "orthophosphoric acid"],
        "safety_rating": "caution",
        "health_impact": "High consumption linked to lower bone density. Excessive phosphorus intake problematic for kidney disease patients.",
        "conditions_affected": ["osteoporosis", "kidney disease"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Lactic Acid", "aliases": ["E270"],
        "safety_rating": "safe",
        "health_impact": "Naturally produced in fermentation. Safe for most people. Can be derived from dairy (not vegan) or plant sources.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Acetic Acid", "aliases": ["E260", "vinegar", "ethanoic acid"],
        "safety_rating": "safe",
        "health_impact": "Generally safe. Main component of vinegar. May have modest blood sugar benefits. Erosive to teeth in large amounts.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Sodium Sources (BP concern) ───────────────────────────────────────────
    {
        "name": "Sodium Benzoate", "aliases": ["E211"],
        "safety_rating": "caution",
        "health_impact": "High sodium content contributes to blood pressure. May form benzene with vitamin C.",
        "conditions_affected": ["hypertension"],
        "banned_in": [], "daily_limit_mg": 5.0,
    },
    {
        "name": "Disodium Phosphate", "aliases": ["E339", "sodium hydrogen phosphate"],
        "safety_rating": "caution",
        "health_impact": "High sodium. High phosphorus intake linked to cardiovascular disease and kidney problems.",
        "conditions_affected": ["hypertension", "kidney disease", "cardiovascular disease"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Sodium Bicarbonate", "aliases": ["E500", "baking soda", "bicarbonate of soda"],
        "safety_rating": "safe",
        "health_impact": "Generally safe in food amounts. High sodium — hypertension patients should monitor intake.",
        "conditions_affected": ["hypertension"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Gluten Sources (Celiac concern) ───────────────────────────────────────
    {
        "name": "Wheat Starch", "aliases": ["modified wheat starch", "wheat flour"],
        "safety_rating": "caution",
        "health_impact": "Contains gluten. DANGEROUS for celiac disease and non-celiac gluten sensitivity.",
        "conditions_affected": ["celiac disease", "gluten sensitivity", "wheat allergy"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Barley Malt", "aliases": ["malt extract", "barley malt extract", "barley flour"],
        "safety_rating": "caution",
        "health_impact": "Contains gluten. Must be avoided by celiac patients. Also a hidden sugar source.",
        "conditions_affected": ["celiac disease", "gluten sensitivity", "diabetes"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Common Allergens ──────────────────────────────────────────────────────
    {
        "name": "Milk Protein", "aliases": ["casein", "whey", "lactoglobulin", "lactalbumin", "milk solids"],
        "safety_rating": "caution",
        "health_impact": "Dairy allergen. Can cause anaphylaxis in milk allergy sufferers. Lactose can cause GI issues in lactose intolerance.",
        "conditions_affected": ["milk allergy", "lactose intolerance"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Soy Protein", "aliases": ["soy isolate", "soybean", "soya", "soy flour"],
        "safety_rating": "caution",
        "health_impact": "Common allergen. May have mild estrogenic effects due to phytoestrogens. GMO concern for some consumers.",
        "conditions_affected": ["soy allergy", "hormonal disorders"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Tree Nut Derivatives", "aliases": ["almond flour", "cashew", "walnut oil", "hazelnut"],
        "safety_rating": "caution",
        "health_impact": "Severe allergen. Can cause anaphylaxis. Must be clearly labeled by law.",
        "conditions_affected": ["tree nut allergy"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Antioxidants ──────────────────────────────────────────────────────────
    {
        "name": "Ascorbic Acid", "aliases": ["Vitamin C", "E300", "L-ascorbic acid"],
        "safety_rating": "safe",
        "health_impact": "Safe and beneficial antioxidant. Can form benzene with sodium benzoate. Very high doses may cause GI upset.",
        "conditions_affected": [],
        "banned_in": [], "daily_limit_mg": 1000.0,
    },
    {
        "name": "Tocopherols", "aliases": ["Vitamin E", "E306", "E307", "E308", "alpha-tocopherol", "mixed tocopherols"],
        "safety_rating": "safe",
        "health_impact": "Natural or synthetic Vitamin E. Generally safe. Very high doses may increase bleeding risk.",
        "conditions_affected": ["bleeding disorders"],
        "banned_in": [], "daily_limit_mg": None,
    },
    # ── Artificial Flavors & Others ────────────────────────────────────────────
    {
        "name": "Natural Flavors", "aliases": ["natural flavoring", "natural flavor"],
        "safety_rating": "caution",
        "health_impact": "Vague regulatory category. Can include animal-derived, allergen-containing, or MSG-like glutamates. Impossible to fully evaluate.",
        "conditions_affected": ["allergies"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Artificial Flavors", "aliases": ["artificial flavoring", "artificial flavor"],
        "safety_rating": "caution",
        "health_impact": "Synthetically produced flavor compounds. Generally tested for safety, but some may cause reactions in sensitive individuals.",
        "conditions_affected": ["allergies"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Modified Food Starch", "aliases": ["modified corn starch", "modified tapioca starch", "E1404", "E1422"],
        "safety_rating": "safe",
        "health_impact": "Generally safe. High glycemic load — raises blood sugar. Wheat-based versions contain gluten.",
        "conditions_affected": ["diabetes", "celiac disease"],
        "banned_in": [], "daily_limit_mg": None,
    },
    {
        "name": "Propylene Glycol", "aliases": ["E1520", "1,2-propanediol"],
        "safety_rating": "caution",
        "health_impact": "Generally safe in food amounts. In large amounts, can cause central nervous system depression. Banned in cat food.",
        "conditions_affected": ["kidney disease", "liver disease"],
        "banned_in": [], "daily_limit_mg": 25.0,
    },
    {
        "name": "Brominated Vegetable Oil", "aliases": ["BVO"],
        "safety_rating": "harmful",
        "health_impact": "Banned by FDA (2024). Bromine builds up in body, linked to neurological issues, heart and liver damage.",
        "conditions_affected": ["neurological disorders", "thyroid disorders"],
        "banned_in": ["United States", "European Union", "Japan"],
        "daily_limit_mg": None,
    },
    {
        "name": "Partially Hydrogenated Oil", "aliases": ["PHO", "partially hydrogenated vegetable oil", "trans fat"],
        "safety_rating": "harmful",
        "health_impact": "Artificial trans fats — banned by FDA. Raise LDL, lower HDL cholesterol. Major risk factor for heart disease.",
        "conditions_affected": ["cardiovascular disease", "diabetes"],
        "banned_in": ["United States", "Canada", "European Union"],
        "daily_limit_mg": None,
    },
    {
        "name": "Potassium Bromate", "aliases": ["E924", "bromic acid potassium salt"],
        "safety_rating": "harmful",
        "health_impact": "Possible carcinogen (IARC Group 2B). Banned in most countries. Still used in some US flour products.",
        "conditions_affected": ["cancer risk", "kidney disease"],
        "banned_in": ["European Union", "Canada", "China", "India", "Brazil"],
        "daily_limit_mg": None,
    },
    {
        "name": "Azodicarbonamide", "aliases": ["ADA", "E927a", "flour bleaching agent"],
        "safety_rating": "harmful",
        "health_impact": "Banned in EU and Australia. Degrades to semicarbazide (possible carcinogen) and urethane (carcinogen) during baking.",
        "conditions_affected": ["cancer risk", "asthma"],
        "banned_in": ["European Union", "Australia", "United Kingdom"],
        "daily_limit_mg": None,
    },
    {
        "name": "Propyl Gallate", "aliases": ["E310", "propyl 3,4,5-trihydroxybenzoate"],
        "safety_rating": "caution",
        "health_impact": "Possible endocrine disruptor. Some animal studies show tumor promotion. Often used with BHA/BHT.",
        "conditions_affected": ["hormonal disorders", "cancer risk"],
        "banned_in": [], "daily_limit_mg": 1.4,
    },
]


def seed():
    logger.info(f"Connecting to Qdrant at {os.getenv('QDRANT_URL', 'http://localhost:6333')}…")
    client = get_sync_client()

    # Ensure collection exists
    try:
        existing = client.get_collections()
        names = [c.name for c in existing.collections]
        if COLLECTION_NAME not in names:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Created collection: {COLLECTION_NAME}")
        else:
            logger.info(f"Collection '{COLLECTION_NAME}' already exists.")
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        sys.exit(1)

    # Deduplicate by name
    seen_names = set()
    unique_additives = []
    for additive in FOOD_ADDITIVES:
        if additive["name"] not in seen_names:
            seen_names.add(additive["name"])
            unique_additives.append(additive)

    logger.info(f"Seeding {len(unique_additives)} food additives…")

    for idx, additive in enumerate(unique_additives):
        try:
            upsert_ingredient_sync(client, idx + 1, additive)
            logger.info(f"  [{idx+1}/{len(unique_additives)}] {additive['name']}")
            time.sleep(0.05)  # Rate limit courtesy
        except Exception as e:
            logger.error(f"  Failed to upsert '{additive['name']}': {e}")

    logger.info(f"Seeding complete! {len(unique_additives)} additives loaded into Qdrant.")
    logger.info("You can expand this dataset using Open Food Facts API: https://world.openfoodfacts.org/data")


if __name__ == "__main__":
    seed()
