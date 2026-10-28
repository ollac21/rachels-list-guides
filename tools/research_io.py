"""Reads .cache/research/<city>.json and applies the editorial drops decided while reading the research."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / ".cache" / "research"

# venues whose price is a permit or a hall base rate rather than a small-wedding price: not listed
DROP_VENUES = {
    "new-york": ["Brooklyn Bridge Park"],
    "chicago": ["Park District of Oak Park - outdoor park ceremony permit", "Berger Park Cultural Center"],
    "dallas": ["City of Dallas park", "Soma Winery"],
}
# venues read by hand from the researchers' cached pages after their JSON was written
ADD_VENUES = {
    "chicago": [{
        "name": "First Unitarian Church of Chicago - Hull Chapel", "url": "https://firstuchicago.org/?p=446", "area": "Hyde Park",
        "guests": "Hull Chapel seats 90", "max_guests": 90, "price_display": "$1,500", "amount": 1500,
        "price_for": "three-hour wedding block in Hull Chapel", "includes": "",
        "quote": "The fee for a three-hour wedding block is $2,500 for the Sanctuary and $1,500 for Hull Chapel.",
        "date_read": "2026-10-28"}],
}
# where the page prints no guest limit next to the price, say so instead of repeating a limit from another page
OVERRIDES = {
    ("los-angeles", "Cecile Trattoria"): {"per_person": True, "max_guests": 0},
    ("chicago", "Cheney Mansion"): {"guests": "no guest limit printed next to this price", "max_guests": 0},
}

# which courthouse rows to show (a key, or a start of the row's label), in this order; other rows are not shown
PICK = {
    "houston": ["license_fee", "Marriage license fee if neither", "ceremony_fee", "Same JP court: Saturday", "Same JP court: what to bring",
                "Same JP court: appointments", "waiting_period", "validity", "id_needed", "how_to_book", "Premarital course",
                "Downtown Personal Records"],
    "dallas": ["license_fee", "ceremony_fee", "Other courthouse ceremony fee: JP 3-1", "Other courthouse ceremony fee: JP 5-1",
               "waiting_period", "validity", "id_needed", "how_to_book", "How you can pay the license fee", "Twogether",
               "County Clerk office address", "Certified copy"],
    "los-angeles": ["license_fee", "license_fee_confidential", "ceremony_fee", "witness_fee", "validity", "id_needed",
                    "both_present", "how_to_book", "ceremony_booking", "ceremony_length", "express_ceremony", "main_office"],
    "new-york": ["license_fee", "ceremony_fee", "waiting_period", "validity", "id_needed", "how_to_book",
                 "Ceremony group size", "Ceremony arrival hours", "Witness", "Marriage certificate after",
                 "License the same day", "Marrying inside the 24-hour wait"],
    "chicago": ["license_fee", "ceremony_fee", "waiting_period", "validity", "id_needed", "How to get the license",
                "Where the civil ceremony happens", "Ceremony booking in Chicago", "Ceremony days and hours",
                "Saturday ceremonies", "Return the signed license", "Certified copy"],
}


def load(city):
    f = RES / (city + ".json")
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    for av in ADD_VENUES.get(city, []):
        if not any(v["url"] == av["url"] for v in d.get("venues", [])):
            d.setdefault("venues", []).append(dict(av))
    drops = DROP_VENUES.get(city, [])
    if drops and d.get("venues"):
        d["venues"] = [v for v in d["venues"] if not any(v["name"].startswith(x) for x in drops)]
    for v in d.get("venues", []):
        v["max_guests"] = v.get("max_guests") or 0
        v["guests"] = v.get("guests") or "guest limit not printed next to this price"
        for (c, prefix), patch in OVERRIDES.items():
            if c == city and v["name"].startswith(prefix):
                v.update(patch)
    import display as _display
    for v in d.get("venues", []):
        patch = None
        for (c, prefix), p in _display.DISPLAY.items():
            if c == city and v["name"].startswith(prefix):
                patch = p
                break
        if patch is not None and v["name"].startswith("The Reserve on Cypress Creek"):
            patch = _display.RESERVE["Elopement" if "Elopement" in v["price_for"] else "Micro"]
        if patch:
            v.update({k: x for k, x in patch.items() if x != ""})
        if "price_display" not in (patch or {}):
            v["price_display"] = "${:,.0f}".format(v["amount"]) if float(v["amount"]).is_integer() else "${:,.2f}".format(v["amount"])
        v.setdefault("_researched_name", v["name"])
    pick = PICK.get(city)
    if pick and d.get("courthouse"):
        facts, used = d["courthouse"]["facts"], set()
        out = []
        for want in pick:
            for i, f in enumerate(facts):
                if i not in used and (f["key"] == want or f["label"].startswith(want)):
                    out.append(f)
                    used.add(i)
                    break
        d["courthouse"]["facts"] = out
    return d
