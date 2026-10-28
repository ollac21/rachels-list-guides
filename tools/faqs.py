"""Hand-written FAQ sets, one per page: 5 questions from Google's People-also-ask (see content/_paa.json),
each answered in 2 sentences with the page's own numbers. Numbers are pulled from the research files so
they cannot drift from the tables. Used by tools/make_content.py."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / ".cache" / "research"
TODAY = "Oct 28, 2026"


def money(n):
    n = float(n)
    return "${:,.0f}".format(n) if n == int(n) else "${:,.2f}".format(n)


from research_io import load  # noqa: E402  (applies the editorial drops)


def fact(d, key):
    return next((f for f in d["courthouse"]["facts"] if f["key"] == key), None)


def venues(city):
    d = load(city)
    return sorted((v for v in d["venues"] if not v.get("per_person")), key=lambda v: v["amount"]) if d else []


def cheapest(city, min_guests=0):
    vs = [v for v in venues(city) if v.get("max_guests", 0) >= min_guests]
    return vs[0] if vs else None


def _nm(v):
    return v["name"].replace("&", "and")


# ---------------------------------------------------------------- courthouse pages
def courthouse_new_york():
    d = load("new-york")
    lic, cer = fact(d, "license_fee"), fact(d, "ceremony_fee")
    c0 = cheapest("new-york", 10)
    return [
        {"q": "How do you get married at a courthouse in New York City?",
         "a": "Make an appointment online through Project Cupid or by phone (City Clerk offices take no walk-ins), then go to a borough office with valid photo ID and the {l} fee. "
              "After the 24-hour wait, book the {c} City Clerk ceremony at any of the five borough offices and bring at least one witness over 18.".format(l=lic["display"], c=cer["display"])},
        {"q": "How much does a courthouse wedding cost in NYC?",
         "a": "As of {t}, the City Clerk charges {l} for the marriage license and {c} for the civil ceremony, {s} in all. "
              "Both figures come from the City's own NYC311 pages linked in the table.".format(t=TODAY, l=lic["display"], c=cer["display"], s=money(lic["amount"] + cer["amount"]))},
        {"q": "How many people are allowed in a courthouse wedding in NYC?",
         "a": "The City Clerk's ceremony page says no more than 6 attendees, including the couple and the witness. "
              "For a bigger party, see the small-venue prices on our NYC venues page, from {p}.".format(p=c0["price_display"] if c0 else "the listed prices")},
        {"q": "How quickly can I get married in NYC?",
         "a": "With complete documents you leave the City Clerk office with the {l} license the same day, but the ceremony must be at least 24 hours after you receive it. "
              "A judicial waiver from the County Clerk can allow a ceremony inside that wait, with no fee.".format(l=lic["display"])},
        {"q": "Is it cheaper to get married at a courthouse?",
         "a": "The City Clerk's fees total {s}. The lowest price we verified for a small venue in NYC is {p} ({n}), so the courthouse is the cheaper start; compare both pages before you decide.".format(
             s=money(lic["amount"] + cer["amount"]), p=c0["price_display"] if c0 else "n/a", n=_nm(c0) if c0 else "")},
    ]


def courthouse_chicago():
    d = load("chicago")
    lic, cer = fact(d, "license_fee"), fact(d, "ceremony_fee")
    c0 = cheapest("chicago", 10)
    return [
        {"q": "How much does it cost to get married in a Chicago courthouse?",
         "a": "As of {t}, the Cook County Clerk charges {l} for the marriage license and the Circuit Court of Cook County asks a {c} administrative fee for an in-person civil ceremony: {s} in all. "
              "Certified copies of the marriage certificate are extra ($15, and $4 for each additional copy).".format(
                  t=TODAY, l=lic["display"], c=money(cer["amount"]), s=money(lic["amount"] + cer["amount"]))},
        {"q": "Where do you get married at the courthouse in Chicago?",
         "a": "In-person civil ceremonies are held at the Marriage and Civil Union Court, 119 W. Randolph St. (lower level), where a Cook County judge marries you. "
              "You first get the license at a Clerk's Vital Records office; downtown it is 118 N. Clark St., Room 120."},
        {"q": "What days can you get married at the courthouse in Chicago?",
         "a": "In person, Tuesday through Friday from 9 a.m. to 12 p.m. and 2 p.m. to 4 p.m., plus Saturdays 9 a.m. to 12 p.m. by appointment only. "
              "Virtual (Zoom) ceremonies are on Mondays, by appointment."},
        {"q": "How long does it take to get married at the courthouse in Chicago?",
         "a": "The Clerk issues the license while you wait, but it takes effect 1 day after it is issued, so the earliest ceremony is the next day (the license is valid for 60 days). "
              "The court takes no appointment for an in-person ceremony Tuesday to Friday; arrive no later than 30 minutes before closing."},
        {"q": "Is it cheaper to get married at a courthouse?",
         "a": "The official fees here total {s}. The lowest small-venue price we verified in Chicago is {p} ({n}), so the courthouse is the cheaper start; see both pages before you decide.".format(
             s=money(lic["amount"] + cer["amount"]), p=c0["price_display"] if c0 else "n/a", n=_nm(c0) if c0 else "")},
    ]


def courthouse_los_angeles():
    d = load("los-angeles")
    lic, conf, cer, wit = fact(d, "license_fee"), fact(d, "license_fee_confidential"), fact(d, "ceremony_fee"), fact(d, "witness_fee")
    exp = fact(d, "express_ceremony")
    c0 = cheapest("los-angeles", 10)
    return [
        {"q": "How much does a courthouse wedding cost in Los Angeles?",
         "a": "As of {t}, Los Angeles County charges {l} for a public marriage license ({cf} for a confidential one) and {c} for a civil ceremony at a county office: {s} in all. "
              "A county-provided witness is {w} more.".format(t=TODAY, l=lic["display"], cf=conf["display"], c=cer["display"], s=money(lic["amount"] + cer["amount"]), w=wit["display"])},
        {"q": "Can you get married at the courthouse in Los Angeles?",
         "a": "The county marries you at its Registrar-Recorder/County Clerk offices: civil ceremonies are by appointment only, prepaid, and last 15 minutes. "
              "The county gives no ceremony appointment until you hold your license, and outside officiants are not allowed in its chapels."},
        {"q": "How do you get a marriage license in Los Angeles County?",
         "a": "Both of you complete the application online, then book an in-person appointment at a county office (up to 3 weeks ahead) and go together with valid photo ID. "
              "The license costs {l} (public) or {cf} (confidential) and is valid for 90 days.".format(l=lic["display"], cf=conf["display"])},
        {"q": "Can you get married the same day in Los Angeles?",
         "a": "The county offers a 45-minute express appointment at all seven of its branch offices, which it describes as license and ceremony in one visit. "
              "You still need the application and the {s} in fees.".format(s=money(lic["amount"] + cer["amount"]))},
        {"q": "Is it cheaper to get married at a courthouse?",
         "a": "The county's fees total {s}. The lowest small-venue price we verified in Los Angeles is {p} ({n}), so the county office is the cheaper start; see both pages before you decide.".format(
             s=money(lic["amount"] + cer["amount"]), p=c0["price_display"] if c0 else "n/a", n=_nm(c0) if c0 else "")},
    ]


def courthouse_houston():
    d = load("houston")
    lic, lic2, cer = fact(d, "license_fee"), next(f for f in d["courthouse"]["facts"] if f["label"].startswith("Marriage license fee if neither")), fact(d, "ceremony_fee")
    c0 = cheapest("houston", 10)
    tot = lic["amount"] + cer["amount"]
    return [
        {"q": "How much does it cost to get married at the courthouse in Houston, TX?",
         "a": "As of {t}, the Harris County Clerk charges {l} for the marriage license ({l2} if neither applicant shows Texas residency on their ID), and Justice of the Peace Precinct 1, Place 1 charges {c} for a weekday courthouse ceremony, cash only: {s} in all. "
              "Other Harris County justice courts set their own fees.".format(t=TODAY, l=lic["display"], l2=lic2["display"], c=cer["display"], s=money(tot))},
        {"q": "How do I get married at the courthouse in Houston?",
         "a": "Both of you apply in person at one of the Harris County Clerk's 11 locations with valid photo ID, then wait 72 hours. "
              "Book a ceremony with a Justice of the Peace, bring the license and cash, and return the signed license to the Clerk within 90 days."},
        {"q": "Can you get married at the Harris County courthouse?",
         "a": "Yes: Harris County Justices of the Peace perform courthouse ceremonies. Precinct 1, Place 1 lists Monday, Tuesday and Thursday 11:00 AM to 12:00 PM at {c}, and Saturdays 10:00 AM to 1:00 PM at $200 when available.".format(c=cer["display"])},
        {"q": "Can you get a marriage license and get married in the same day in Texas?",
         "a": "Not by default: Texas requires a 72-hour wait after the license is issued. The Harris County Clerk's page says the wait is waived for active military and for couples with a Twogether in Texas certificate, which also takes up to $60 off the fee."},
        {"q": "Is a courthouse wedding cheaper than a wedding?",
         "a": "The official fees here total {s}. The lowest Houston venue price we verified for a group of 10 or more is {p} ({n}), so the courthouse is the cheaper start; compare both pages before you decide.".format(
             s=money(tot), p=c0["price_display"] if c0 else "n/a", n=_nm(c0) if c0 else "")},
    ]


def courthouse_dallas():
    d = load("dallas")
    lic, cer = fact(d, "license_fee"), fact(d, "ceremony_fee")
    jp31 = next(f for f in d["courthouse"]["facts"] if "JP 3-1" in f["label"])
    jp51 = next(f for f in d["courthouse"]["facts"] if "JP 5-1" in f["label"])
    c0 = cheapest("dallas", 10)
    return [
        {"q": "How to get married at the courthouse in Dallas?",
         "a": "Fill in the Dallas County marriage license application online and keep the order number. Both of you go to the County Clerk's Records Building (500 Elm St., Suite 2100) with photo ID and pay the {l} license fee (no personal checks), wait 72 hours, then book a ceremony with a Justice of the Peace court.".format(l=lic["display"])},
        {"q": "How much is it to get married at the courthouse in Dallas?",
         "a": "As of {t}, the license costs {l} and each Justice of the Peace court sets its own ceremony fee: {j51} at JP 5-1, {c} by appointment at JP 2-2 and {j31} at JP 3-1. "
              "That makes {lo} to {hi} in fees, depending on the court.".format(
                  t=TODAY, l=lic["display"], j51=money(jp51["amount"]), c=money(cer["amount"]), j31=money(jp31["amount"]),
                  lo=money(lic["amount"] + jp51["amount"]), hi=money(lic["amount"] + jp31["amount"]))},
        {"q": "Can you get married the same day in Dallas?",
         "a": "Not by default: Texas law requires 72 hours after the license is issued. A district judge can waive the wait, and the Dallas County Clerk's page says a Twogether in Texas certificate waives it and takes $60 off the license fee."},
        {"q": "Can I get married at a courthouse in Texas?",
         "a": "Yes: in Dallas County, ceremonies are performed by Justice of the Peace courts, each with its own hours and fee. For example JP 2-2 marries couples Monday to Friday from 10:30a to 3:30p for {c} cash only by appointment.".format(c=money(cer["amount"]))},
        {"q": "Is it cheaper to get married at a courthouse?",
         "a": "The official fees here run {lo} to {hi}. The lowest Dallas venue price we verified for a group of 10 or more is {p} ({n}), so the courthouse is the cheaper start; compare both pages before you decide.".format(
             lo=money(lic["amount"] + jp51["amount"]), hi=money(lic["amount"] + jp31["amount"]), p=c0["price_display"] if c0 else "n/a", n=_nm(c0) if c0 else "")},
    ]


def _finds_text(city):
    f = {}
    try:
        ff = json.loads((ROOT / "content" / "_finds.json").read_text())
        f = ff.get(city, {})
    except Exception:
        pass
    return f


def _dress():
    dd = json.loads((ROOT / ".cache" / "dresses.json").read_text())
    g = next((x for x in dd["under500"] if x["brand"] == "BHLDN"), dd["under500"][0])
    return g


def venue_faq(city, name, courthouse_fee_text=""):
    vs = venues(city)
    lo, hi = vs[0], vs[-1]
    under = [v for v in vs if v["amount"] < 1000]
    caps = [v["max_guests"] for v in vs if v.get("max_guests")]
    f = _finds_text(city)
    g = _dress()
    parts = [money(g["price"]) + " dress"]
    total = lo["amount"] + g["price"]
    if f.get("florist"):
        parts.append(money(f["florist"]["amount"]) + " flowers"); total += f["florist"]["amount"]
    if f.get("photographer"):
        parts.append(money(f["photographer"]["amount"]) + " photos"); total += f["photographer"]["amount"]
    if under:
        under_txt = "{k} of the {n} venues print a price under $1,000: {l}.".format(
            k=len(under), n=len(vs), l="; ".join("{} {}".format(_nm(v), v["price_display"]) for v in under[:4]))
    else:
        under_txt = "None of the {n} venues we verified prints a price under $1,000; the lowest is {p} ({v}).".format(n=len(vs), p=lo["price_display"], v=_nm(lo))
    return [
        {"q": "What is a normal cost for a wedding venue in {}?".format(name),
         "a": "We do not quote an average, because an average hides what each venue actually prints. On this page {n} venues print prices from {lo} to {hi}, each quoted from its own website on {t}.".format(
             n=len(vs), lo=lo["price_display"], hi=hi["price_display"], t=TODAY)},
        {"q": "What are some cheap wedding venues in {} under $1,000?".format(name),
         "a": under_txt + " Prices are for the package or hours each venue names, so read the row before you book."},
        {"q": "What is a small wedding considered?",
         "a": "There is no official cutoff, so we use each venue's own words: the guest limits printed on this page run from {a} to {b} people. "
              "Every venue here prints its price for a small, micro, weekday or elopement booking.".format(a=min(caps) if caps else "a few", b=max(caps) if caps else "")},
        {"q": "How much does a micro wedding cost in {}?".format(name),
         "a": "The venue prices we verified run {lo} to {hi}. Add the sample finds on this page (a {p}) to the cheapest venue and you get about {tot} before catering, rings and tax.".format(
             lo=lo["price_display"], hi=hi["price_display"], p=", ".join(parts), tot=money(total))},
        {"q": "Is $5,000 enough for a wedding in {}?".format(name),
         "a": "For a small group it can be: the cheapest verified venue ({lo}) plus the sample finds comes to about {tot}, and even the most expensive venue here is {hi}. "
              "A 100-guest wedding is a different budget, because this page prices small groups only.".format(lo=lo["price_display"], tot=money(total), hi=hi["price_display"])},
    ]


CITIES = [("houston", "Houston"), ("chicago", "Chicago"), ("new-york", "New York"), ("dallas", "Dallas"), ("los-angeles", "Los Angeles")]


def _all_venues():
    out = []
    for c, n in CITIES:
        for v in venues(c):
            out.append((c, n, v))
    return out


def _license_range():
    lic = []
    for c, n in CITIES:
        d = load(c)
        if d and d.get("courthouse"):
            f = fact(d, "license_fee")
            if f and f.get("amount") is not None:
                lic.append((f["amount"], n))
    return min(lic), max(lic)


def hub_faq():
    av = _all_venues()
    lo = min(av, key=lambda t: t[2]["amount"])
    hi = max(av, key=lambda t: t[2]["amount"])
    caps = sorted(v["max_guests"] for _, _, v in av if v.get("max_guests"))
    cities = len({c for c, _, _ in av})
    return [
        {"q": "What would be considered a micro wedding?",
         "a": "There is no official cutoff, so we use each venue's own words: the guest limits printed next to the {n} prices on our city pages run from {a} to {b} people. "
              "Every venue listed prints its price for a small, micro, weekday or elopement booking.".format(n=len(av), a=caps[0], b=caps[-1])},
        {"q": "What is a normal cost for a wedding venue?",
         "a": "We do not quote an average, because an average hides what each venue prints. Across {c} cities the verified prices run from {lo} ({ln}, {lc}) to {hi} ({hn}, {hc}), each from the venue's own website on {t}.".format(
             c=cities, lo=lo[2]["price_display"], ln=_nm(lo[2]), lc=lo[1], hi=hi[2]["price_display"], hn=_nm(hi[2]), hc=hi[1], t=TODAY)},
        {"q": "Is 100 guests a micro wedding?",
         "a": "Not by the venues on this page: the largest guest limit printed next to a price here is {b} people. Venues that host 100 guests price a different kind of day, so we list them only when they print a small-group price.".format(b=caps[-1])},
        {"q": "What is a realistic budget for a small wedding?",
         "a": "For the venue alone, the prices we verified run from {lo} to {hi}. The rest depends on you; our city pages add one real find each for the dress, flowers and photos so you can see how the lines add up.".format(
             lo=lo[2]["price_display"], hi=hi[2]["price_display"])},
        {"q": "Is $5,000 enough for a wedding?",
         "a": "For a small group it can be: all {n} venue prices on our city pages are {hi} or less, before the dress, flowers, photos and food. A 100-guest wedding is a different budget, because these pages price small groups only.".format(
             n=len(av), hi=hi[2]["price_display"])},
    ]


def packages_faq():
    d = json.loads((RES / "packages.json").read_text())
    pk = sorted(d["packages"], key=lambda x: x["amount"])
    lo, hi = pk[0], pk[-1]
    (la, ln), (ha, hn) = _license_range()
    return [
        {"q": "Is eloping cheaper than having a wedding?",
         "a": "On this page the {n} packages print prices from {lo} to {hi}, each from the provider's own website on {t}. A package replaces a venue, an officiant and sometimes photos, so compare it with the venue prices on our city pages.".format(
             n=len(pk), lo=lo["price_display"], hi=hi["price_display"], t=TODAY)},
        {"q": "Does eloping make you legally married?",
         "a": "Only the marriage license and a ceremony by an authorized officiant do; a package is not the license. The licenses we checked cost {la} in {lc} to {ha} in {hc} (see each courthouse page for the official wording).".format(
             la=money(la), lc=ln, ha=money(ha), hc=hn)},
        {"q": "What is the average budget for an elopement?",
         "a": "We do not quote an average. The packages here run {lo} to {hi}, and they include different things, so read the Includes line on each row before you compare.".format(
             lo=lo["price_display"], hi=hi["price_display"])},
        {"q": "Is $5,000 enough for a wedding?",
         "a": "For an elopement or micro wedding, yes: every package listed is {hi} or less before the license fee ({la} to {ha}) and any travel. A large guest list is a different budget.".format(
             hi=hi["price_display"], la=money(la), ha=money(ha))},
        {"q": "What does an elopement package include?",
         "a": "It depends on the provider: some include only a ceremony site and an officiant, others add photos or flowers. Each row on this page names what the provider's own page lists, and the price covers only that."},
    ]


def houston_venue_faq():
    base = venue_faq("houston", "Houston")
    vs = venues("houston")
    d = load("houston")
    lo, hi = vs[0], vs[-1]
    cheapest3 = vs[:3]
    under = [v for v in vs if v["amount"] < 1000]
    lic, cer = fact(d, "license_fee"), fact(d, "ceremony_fee")
    return [
        {"q": "What are the best venues for a micro wedding in Houston?",
         "a": "We do not rank venues; we list the ones that print a small-group price on their own website. The three lowest are {l}, with {n} priced venues in all, from {lo} to {hi}.".format(
             l="; ".join("{} {} ({})".format(_nm(v), v["price_display"], v["guests"].split("(")[0].strip()) for v in cheapest3), n=len(vs), lo=lo["price_display"], hi=hi["price_display"])},
        base[1],
        {"q": "How much does a small wedding cost in Texas?",
         "a": "We do not quote an average. In Houston the venue prices we verified run {lo} to {hi}, and the official courthouse fees are {l} for the license plus {c} for a ceremony at Justice of the Peace Precinct 1, Place 1.".format(
             lo=lo["price_display"], hi=hi["price_display"], l=lic["display"], c=cer["display"])},
        base[4],
        base[0],
    ]


def get(key):
    if key == "small-wedding-venues-houston" and load("houston"):
        return houston_venue_faq()
    if key == "micro-wedding-venues":
        return hub_faq()
    if key == "elopement-packages":
        return packages_faq()
    fn = {"courthouse-wedding-new-york": courthouse_new_york, "courthouse-wedding-chicago": courthouse_chicago, "courthouse-wedding-los-angeles": courthouse_los_angeles,
          "courthouse-wedding-houston": courthouse_houston, "courthouse-wedding-dallas": courthouse_dallas}.get(key)
    if fn:
        return fn()
    if key.startswith("small-wedding-venues-"):
        city = key[len("small-wedding-venues-"):]
        names = {"houston": "Houston", "chicago": "Chicago", "new-york": "NYC", "dallas": "Dallas", "los-angeles": "Los Angeles"}
        if load(city) and load(city).get("venues"):
            return venue_faq(city, names[city])
    return None
