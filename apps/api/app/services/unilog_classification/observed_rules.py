"""Small reviewed phrase policy derived from the official challenge descriptions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ObservedPhraseRule:
    canonical: str
    family: str | None
    variants: tuple[str, ...]


# These phrases were reviewed against the complete 1,000-row input. The builder retains only
# variants actually present in its input, so this policy does not manufacture vocabulary entries.
OBSERVED_PHRASE_RULES = (
    ObservedPhraseRule(
        "Cut and Grind Disc", "Abrasives", ("cut and grind disc", "cut n grind disc")
    ),
    ObservedPhraseRule(
        "Metal Cut-Off Disc", "Abrasives", ("metal cut-off disc", "metal cut off disc")
    ),
    ObservedPhraseRule(
        "Masonry Cut-Off Disc", "Abrasives", ("masonry cut-off disc", "masonry cut off disc")
    ),
    ObservedPhraseRule("Cut-Off Disc", "Abrasives", ("cut-off disc", "cut off disc")),
    ObservedPhraseRule("Grinding Wheel", "Abrasives", ("grinding wheel",)),
    ObservedPhraseRule("Sanding Belt", "Abrasives", ("sanding belt",)),
    ObservedPhraseRule("Sanding Disc", "Abrasives", ("sanding disc",)),
    ObservedPhraseRule("Abrasive Disc", "Abrasives", ("abrasive disc",)),
    ObservedPhraseRule("Stikit Film", "Abrasives", ("stikit film",)),
    ObservedPhraseRule("Sanding Sponge", "Abrasives", ("sanding sponge",)),
    ObservedPhraseRule("Decking", "Decking and Railing", ("decking",)),
    ObservedPhraseRule("Fascia", "Decking and Railing", ("fascia",)),
    ObservedPhraseRule("Rail Kit", "Decking and Railing", ("rail kit", "t-rail kit")),
    ObservedPhraseRule("Rail Panel", "Decking and Railing", ("rail panel",)),
    ObservedPhraseRule("Baluster", "Decking and Railing", ("baluster", "balusters")),
    ObservedPhraseRule("Post Sleeve", "Decking and Railing", ("post sleeve",)),
    ObservedPhraseRule("Post Trim", "Decking and Railing", ("post trim",)),
    ObservedPhraseRule("Patio Door", "Doors and Windows", ("patio door", "patio dr")),
    ObservedPhraseRule("Box Cover", "Electrical", ("box cover",)),
    ObservedPhraseRule("GFCI Outlet", "Electrical", ("gfci outlet",)),
    ObservedPhraseRule("Load Center", "Electrical", ("load center",)),
    ObservedPhraseRule("Cord Connector", "Electrical", ("cord connector", "cord conn")),
    ObservedPhraseRule("Cord Grip", "Electrical", ("cord grip",)),
    ObservedPhraseRule("Electrical Tape", "Electrical", ("electrical tape", "elect tape")),
    ObservedPhraseRule("Wall Light", "Lighting", ("wall light", "wall lt")),
    ObservedPhraseRule("Pendant Light", "Lighting", ("pendant light", "pendant lt")),
    ObservedPhraseRule("Ceiling Light", "Lighting", ("ceiling light", "ceiling lt")),
    ObservedPhraseRule("Strip Light", "Lighting", ("strip light",)),
    ObservedPhraseRule("Wrap Light", "Lighting", ("wrap light",)),
    ObservedPhraseRule("Downlight", "Lighting", ("downlight", "down light")),
    ObservedPhraseRule("Chandelier", "Lighting", ("chandelier", "chandelier lt")),
    ObservedPhraseRule("Wall Timer", "Electrical", ("wall timer",)),
    ObservedPhraseRule("Dimmer", "Electrical", ("dimmer",)),
    ObservedPhraseRule("Dishwasher", "Appliances", ("dishwasher",)),
    ObservedPhraseRule("Electric Dryer", "Appliances", ("electric dryer", "elect dryer")),
    ObservedPhraseRule("Gas Dryer", "Appliances", ("gas dryer",)),
    ObservedPhraseRule("Dryer", "Appliances", ("dryer",)),
    ObservedPhraseRule("Washer", "Appliances", ("washer",)),
    ObservedPhraseRule("Laundry Center", "Appliances", ("laundry center",)),
    ObservedPhraseRule("Electric Range", "Appliances", ("electric range", "elect range")),
    ObservedPhraseRule("Gas Range", "Appliances", ("gas range",)),
    ObservedPhraseRule("Range", "Appliances", ("range",)),
    ObservedPhraseRule("Refrigerator", "Appliances", ("refrigerator", "fridge")),
    ObservedPhraseRule("Microwave", "Appliances", ("microwave",)),
    ObservedPhraseRule("Beverage Center", "Appliances", ("beverage center",)),
    ObservedPhraseRule("Coffee Maker", "Appliances", ("coffee maker",)),
    ObservedPhraseRule("Espresso Machine", "Appliances", ("espresso machine",)),
    ObservedPhraseRule("Cooktop", "Appliances", ("cooktop",)),
    ObservedPhraseRule("Oven", "Appliances", ("oven",)),
    ObservedPhraseRule("Freezer", "Appliances", ("freezer",)),
    ObservedPhraseRule("Saw Blade", "Cutting Tools", ("saw blade",)),
    ObservedPhraseRule("Tile Blade", "Cutting Tools", ("tile blade",)),
    ObservedPhraseRule("Planer Knives", "Cutting Tools", ("planer knives",)),
    ObservedPhraseRule("Drive Bit", "Power Tool Accessories", ("drive bit",)),
    ObservedPhraseRule("Drill Bit", "Power Tool Accessories", ("drill bit",)),
    ObservedPhraseRule("Router Bit", "Power Tool Accessories", ("router bit",)),
    ObservedPhraseRule("Bit Holder", "Power Tool Accessories", ("bit holder",)),
    ObservedPhraseRule("Bit Set", "Power Tool Accessories", ("bit set",)),
    ObservedPhraseRule("Socket Adapter", "Hand Tools", ("socket adapter",)),
    ObservedPhraseRule("Circular Saw", "Power Tools", ("circular saw", "circ saw")),
    ObservedPhraseRule("Hammer Drill", "Power Tools", ("hammer drill",)),
    ObservedPhraseRule("Drill", "Power Tools", ("drill",)),
    ObservedPhraseRule("Impact Driver", "Power Tools", ("impact driver",)),
    ObservedPhraseRule("Impact Wrench", "Power Tools", ("impact wrench",)),
    ObservedPhraseRule("Angle Impact", "Power Tools", ("angle impact",)),
    ObservedPhraseRule("Angle Grinder", "Power Tools", ("angle grinder",)),
    ObservedPhraseRule("Die Grinder", "Power Tools", ("die grinder",)),
    ObservedPhraseRule("Grinder", "Power Tools", ("grinder",)),
    ObservedPhraseRule("Orbit Sander", "Power Tools", ("orbit sander",)),
    ObservedPhraseRule("Sander", "Power Tools", ("sander",)),
    ObservedPhraseRule("Blower", "Power Tools", ("blower",)),
    ObservedPhraseRule("Roofing Nailer", "Power Tools", ("roofing nailer",)),
    ObservedPhraseRule("Brad Nailer", "Power Tools", ("brad nailer",)),
    ObservedPhraseRule("Framing Nailer", "Power Tools", ("framing nailer",)),
    ObservedPhraseRule("Nailer", "Power Tools", ("nailer",)),
    ObservedPhraseRule("String Trimmer", "Outdoor Power Equipment", ("string trimmer",)),
    ObservedPhraseRule("Hedge Trimmer", "Outdoor Power Equipment", ("hedge trimmer",)),
    ObservedPhraseRule("Rotary Tool", "Power Tools", ("rotary tool",)),
    ObservedPhraseRule("Heated Glove", "Protective Apparel", ("heated glove",)),
    ObservedPhraseRule("Heated Hoodie", "Protective Apparel", ("heated hoodie",)),
    ObservedPhraseRule("Safety Glasses", "Safety", ("safety glasses",)),
    ObservedPhraseRule("Fire Extinguisher", "Safety", ("fire extinguisher",)),
    ObservedPhraseRule("Carbon Monoxide Alarm", "Safety", ("carbon monoxide alarm", "co alarm")),
    ObservedPhraseRule("Smoke Detector", "Safety", ("smoke detector",)),
    ObservedPhraseRule("Folding Knife", "Hand Tools", ("folding knife",)),
    ObservedPhraseRule("Mini Snip", "Hand Tools", ("mini snip",)),
    ObservedPhraseRule("Wrench Set", "Hand Tools", ("wrench set",)),
    ObservedPhraseRule("Mechanics Set", "Hand Tools", ("mechanics set",)),
    ObservedPhraseRule("Battery Pack", "Power Tool Accessories", ("battery pack", "powerpack")),
    ObservedPhraseRule("Starter Kit", "Power Tool Accessories", ("starter kit",)),
    ObservedPhraseRule("Charger", "Power Tool Accessories", ("charger",)),
    ObservedPhraseRule("Organizer", "Tool Storage", ("organizer",)),
    ObservedPhraseRule("Fence", "Power Tool Accessories", ("fence",)),
    ObservedPhraseRule("Paper Bag", "Dust Collection", ("paper bag",)),
    ObservedPhraseRule("Filter", "Filtration", ("filter",)),
    ObservedPhraseRule("Faucet", "Plumbing", ("faucet",)),
    ObservedPhraseRule("Valve", "Plumbing", ("valve",)),
    ObservedPhraseRule("Coupling", "Plumbing", ("coupling",)),
    ObservedPhraseRule("Adapter", "Plumbing", ("adapter",)),
)


GENERIC_PRODUCT_TERMS = frozenset(
    {"accessory", "assembly", "component", "item", "kit", "part", "product", "replacement"}
)


@dataclass(frozen=True, slots=True)
class ObservedAbbreviationRule:
    raw_token: str
    expanded_phrase: str
    context_variants: tuple[str, ...]
    ambiguous: bool = False


OBSERVED_ABBREVIATION_RULES = (
    ObservedAbbreviationRule("Lt", "Light", ("wall lt", "pendant lt", "ceiling lt")),
    ObservedAbbreviationRule("Elect", "Electric", ("elect dryer", "elect range", "elect tape")),
    ObservedAbbreviationRule("Circ", "Circular", ("circ saw",)),
    ObservedAbbreviationRule("Conn", "Connector", ("cord conn",)),
    ObservedAbbreviationRule("Dr", "Door", ("patio dr",)),
    ObservedAbbreviationRule("Cand", "Candelabra", ("incan cand", "led cand"), ambiguous=True),
)
