"""Editorial display layer for the researched venues: short names, short guest and price notes.
The quote, the price, the link and the date are never touched; only what is printed around them is shortened.
Key: (city, start of the researched name). Used by research_io.load()."""

DISPLAY = {
    # ---- Houston
    ("houston", "The Courthouse Wedding Chapel"): dict(area="North Houston", guests="2 guests (the couple)", price_for="Weddings by The Fireplace, weekday (weekend $297)", includes="officiant, fireplace setting, bouquet and boutonniere, chapel music, license filing, keepsake certificate"),
    ("houston", "The Middleton Venue"): dict(area="Old Katy", guests="seats up to 40", price_for="Let's Elope, 1 hour ($760 for 2 hours)", includes="1 hour of venue time, photographer (40 images), licensed officiant, event coordinator, decorated venue"),
    ("houston", "The Makenzie House"): dict(area="Missouri City / Stafford", guests="up to 20 guests", price_for="Hourglass \"I Do\" package, 1 hour", includes="1 hour in the chapel, licensed officiant, floral arch, speaker"),
    ("houston", "Houston Botanic Garden (Global"): dict(name="Houston Botanic Garden: Global Collection Garden", area="Houston", guests="15 admission tickets included, standing only", price_for="micro wedding, 1-hour rental (+$200 refundable deposit)", includes="15 tickets, free parking, photos anywhere in the Garden; no reception, food or drinks"),
    ("houston", "Verandas Events"): dict(area="Houston Heights", guests="up to 50 guests", price_for="Monday to Thursday, 4-hour rental (+5% processing fee)", includes="4 hours, cleaning, table and chair setup; bring your own vendors"),
    ("houston", "Houston Botanic Garden (Woodland"): dict(name="Houston Botanic Garden: Woodland Glade", area="Houston", guests="30 admission tickets included", price_for="micro wedding, 1-hour rental (+$200 refundable deposit)", includes="private entrance, free parking, bench seating; no reception, food or drinks"),
    ("houston", "The Reserve on Cypress Creek"): dict(),  # two rows, set below by the 'price_for' text
    ("houston", "The Heritage Society"): dict(name="The Heritage Society: St. John Church", area="Downtown, Sam Houston Park", guests="capacity 65 including the wedding party", price_for="4-hour rental, Monday to Friday (weekends $2,750)", includes="rehearsal hour the day before, guest parking"),
    ("houston", "Silver Sycamore"): dict(area="Pasadena", guests="20 guests (+$38 per guest over 20, max 50)", price_for="micro wedding package, Monday to Thursday (Fri to Sun $4,620); tax and a 20% service fee are added", includes="chapel or gazebo ceremony, day-of coordinator, rehearsal, reception, dinner, cake"),
    ("houston", "County Line Event Center"): dict(area="Pearland", guests="packages for up to 50 guests", price_for="all-inclusive wedding package, 'starting at' price", includes="decor options, wedding planner, catering"),
    # ---- Chicago
    ("chicago", "Garfield Park Conservatory"): dict(name="Garfield Park Conservatory: Jensen Room", area="East Garfield Park", guests="banquet capacity 100", price_for="Monday to Thursday, 4 hours, private rate", includes="no bookings after 3 pm; $100 per extra hour; preferred-caterer list; deposit up to $500"),
    ("chicago", "The Garden Club of Evanston"): dict(name="Garden Club of Evanston: Shakespeare Garden", area="Evanston", guests="50 guests or fewer", price_for="fee for a wedding service in the garden", includes="outdoor garden; no restrooms, food or drink; a chapel is suggested for rain"),
    ("chicago", "Oak Park Conservatory"): dict(name="Oak Park Conservatory: ceremony only", area="Oak Park", guests="50 in the garden, 30 in the greenhouses", price_for="2-hour ceremony-only rental after 4 pm", includes="chairs in the garden; no food or drink"),
    ("chicago", "Lincoln Park Conservatory"): dict(area="Lincoln Park", guests="50 seated", price_for="2-hour rental, 5 to 7 pm (rental $1,000; $1,700 with security guard and deposit)", includes="set-up and breakdown time; preferred-caterer list"),
    ("chicago", "Astoria Banquets"): dict(name="Astoria Banquets: elopement ceremony", area="Buffalo Grove (northwest suburbs)", guests="up to 30 guests", price_for="elopement ceremony, Wednesdays and Thursdays only", includes="decorated ceremony space with aisle and backdrop, 1.5 hours of private venue time"),
    ("chicago", "First Unitarian Church"): dict(name="First Unitarian Church: Hull Chapel", area="Hyde Park", guests="Hull Chapel seats 90", price_for="three-hour wedding block in Hull Chapel", includes=""),
    ("chicago", "First United Methodist Church"): dict(name="Chicago Temple: Sky Chapel", area="The Loop", guests="seats 30", price_for="wedding fee for non-members, cash, check or money order (members $2,050)", includes="pastor, coordinator, custodian, hostess and use of the space"),
    ("chicago", "Cheney Mansion"): dict(name="Cheney Mansion: weekday wedding", area="Oak Park", guests="no guest limit printed next to this price", price_for="'Weddings, Year-round, Weekday' on the mansion's pricing page", includes="Petite Weddings are offered Sunday to Thursday; $500 security deposit"),
    # ---- New York
    ("new-york", "Queens Party Hall"): dict(name="Occasions Hall (Queens Party Hall)", area="Ozone Park, Queens", guests="up to 80 guests", price_for="Monday to Thursday base rate, hall only (Fri and Sun $1,095, Sat $1,295)", includes="DJ booth; bring your own food"),
    ("new-york", "NYC Wedding Factory"): dict(area="Mott Haven, Bronx", guests="30 people maximum", price_for="Standard Package: 30-minute ceremony (Gold, $1,000, adds a 30-minute photo shoot)", includes="officiant and a 30-minute ceremony"),
    ("new-york", "Brooklyn Botanic Garden"): dict(name="Brooklyn Botanic Garden: garden ceremony", area="Brooklyn", guests="up to 50 (10 more at $22 each, 60 maximum)", price_for="permit fee, weekends 9 to 10 a.m., nonrefundable", includes="portrait photography fees included; no chairs, tables or decorations"),
    ("new-york", "Wave Hill"): dict(name="Wave Hill: elopement", area="Riverdale, Bronx", guests="8 people in all", price_for="$500 rental fee plus the required $1,500 Partner Membership; up to 90 minutes, Tue, Wed or Fri afternoons", includes="up to 6 white ceremony chairs", price_display="$2,000"),
    ("new-york", "The Benjamin"): dict(name="The Benjamin: The Regal elopement", area="Midtown East, Manhattan", guests="10 guests or fewer", price_for="weekends only, plus tax and service charge", includes="1.5 hours in the space, chairs, high tops, champagne and hors d'oeuvres"),
    ("new-york", "Church of the Transfiguration"): dict(name="Little Church Around the Corner: Holy Family Chapel", area="East 29th St., Manhattan", guests="chapel seats 20", price_for="wedding fee (the fee schedule is titled 2024); Episcopal rules apply", includes="building, sexton, setup, lights and sound, altar flowers; clergy at no extra fee"),
    ("new-york", "Bartow-Pell"): dict(name="Bartow-Pell Mansion: Conservatory", area="Pelham Bay Park, Bronx", guests="max 30 people", price_for="3-hour rental plus prep and clean-up time", includes="tables, chairs, linens; catering and music arranged by you"),
    # ---- Dallas
    ("dallas", "Skip The Courthouse Wedding Chapel - 'Tie"): dict(name="Skip The Courthouse Chapel: Tie The Knot", area="Arlington", guests="bride and groom only, 30 minutes", price_for="chapel ceremony package", includes="backdrop and bridal bouquet use; bring your own officiant"),
    ("dallas", "Skip The Courthouse Wedding Chapel - 'She"): dict(name="Skip The Courthouse Chapel: She Said Yes", area="Arlington", guests="up to 10 guests", price_for="intimate chapel ceremony package", includes="white chairs, tables, linens, backdrop, centerpieces"),
    ("dallas", "Bour"): dict(area="Plano", guests="75 seated", price_for="Monday to Thursday, 4-hour rental ($150 per hour, 4-hour minimum)", includes="event room, tables and chairs, sound system, day-of supervisor"),
    ("dallas", "Drive Up & Wed - 'Sweet"): dict(name="Drive Up & Wed: Sweet & Simple", area="Hurst", guests="up to 6 guests", price_for="30-minute chapel ceremony", includes="officiant, decorated space, photography, bridal bouquet"),
    ("dallas", "Heirloom Hideaway & Arboreum - 'Just"): dict(name="Heirloom Hideaway: Just the 2 of You", area="Fort Worth", guests="couple only", price_for="60-minute elopement, Monday to Thursday", includes="elopement at the Stone House"),
    ("dallas", "Heirloom Hideaway & Arboreum - '2+12"): dict(name="Heirloom Hideaway: 2+12+CAKE=JOY", area="Fort Worth", guests="up to 12 guests", price_for="2-hour elopement package, starting price", includes="time for a toast, cake, dancing and photos"),
    ("dallas", "Drive Up & Wed - 'Intimate"): dict(name="Drive Up & Wed: Intimate Ceremony", area="Hurst", guests="up to 45 guests, Monday to Thursday", price_for="3-hour weekday micro wedding", includes="officiant, 2 hours of photography, bouquet, two small cakes, venue use"),
    ("dallas", "Blush Event Garden - 'Essential'"): dict(name="Blush Event Garden: Essential elopement", area="Addison and 3 other Dallas-area sites", guests="couple only (up to 2 guests)", price_for="Monday to Friday, 30 minutes of venue access", includes="licensed officiant (or bring yours), ceremony script, stage, sound system, parking"),
    ("dallas", "Blush Event Garden - 'Classic'"): dict(name="Blush Event Garden: Classic elopement", area="Addison and 3 other Dallas-area sites", guests="seating for up to 20 guests", price_for="Monday to Friday, 1 hour of venue access", includes="decorated aisle and backdrop, officiant, chairs for 20, sound system"),
    ("dallas", "Flourish Events Dallas"): dict(name="Flourish Events: Silver micro wedding", area="Mesquite", guests="up to 40 guests", price_for="pavilion ceremony, 2 hours, Sunday to Friday", includes="40 white chairs, indoor restrooms"),
    ("dallas", "The Penrose House"): dict(name="The Penrose House: DIY elopement", area="Princeton, 45 minutes from Dallas", guests="a small number of guests", price_for="'DIY elopement' package, starting price", includes="private ceremony space, overnight suite, resort amenities"),
    # ---- Los Angeles
    ("los-angeles", "Cecile Trattoria"): dict(area="Glendale", guests="25 to 50 guests", price_for="semi-private dining, per person", includes="Italian menus, cocktail packages, event coordination", price_display="$75 per person"),
    ("los-angeles", "Albertson Wedding Chapel"): dict(area="La Brea Ave, Los Angeles", guests="0 to 5 guests (6 to 18 guests $390)", price_for="ceremony only, Monday to Friday and Sunday", includes="chapel, officiant, unity candle; photography and license set are extras"),
    ("los-angeles", "Lucky Wedding Day Chapel"): dict(area="Encino", guests="1 to 10 people", price_for="Sweet Package (couple-only Happy Package $399.99)", includes="chapel, officiant, music, marriage license, notary"),
    ("los-angeles", "Cute Little Wedding Chapel"): dict(area="Long Beach", guests="0 to 4 guests (5 to 15 guests $550)", price_for="license and ceremony, lowest tier (+$50 on weekends)", includes="marriage license, ceremony and certificate"),
    ("los-angeles", "Orcutt Ranch"): dict(name="Orcutt Ranch: weekday rental", area="West Hills, Los Angeles", guests="events up to 175 people", price_for="Monday to Thursday, first 3 hours ($110 per extra hour)", includes="historic ranch house and gardens; $500 refundable deposit is part of the fee"),
    ("los-angeles", "La Venta Inn"): dict(area="Palos Verdes Estates", guests="ceremony only, up to 100 guests", price_for="weekday ceremony-only package, 2 hours (Fri to Sun $5,500)", includes="private use of the grounds, chairs, sound system, day-of director, light refreshments"),
    ("los-angeles", "Heritage Square Museum"): dict(area="Montecito Heights, Los Angeles", guests="50 guests or fewer", price_for="outdoor boutique wedding, 'starting at' price", includes="historic homes and gardens"),
    ("los-angeles", "Greystone Mansion"): dict(name="Greystone Mansion: ceremony only", area="Beverly Hills", guests="1 to 75 people", price_for="one-hour Formal Garden ceremony, non-resident rate (Beverly Hills residents $2,200)", includes="Formal Garden; no food or beverages except water", price_display="$2,600"),
}

# The Reserve on Cypress Creek prints two packages; told apart by the researched price_for text
RESERVE = {"Elopement": dict(name="The Reserve on Cypress Creek: Elopement", area="Cypress", guests="up to 30 guests", price_for="2-hour elopement package, 'starting at' price", includes="seated ceremony, photos on the property, high-top tables"),
           "Micro": dict(name="The Reserve on Cypress Creek: Micro Wedding", area="Cypress", guests="up to 50 guests", price_for="micro wedding package, up to 4 hours, 'starting at' price", includes="seated ceremony, covered cocktail-hour tent, chairs and tables")}

# What the official pages do not state, in short lines (shown under the fees table). Key: city.
LEFT_OUT = {
    "houston": ["How to pay the license fee (the Clerk's page names no payment methods for licenses)",
                "Whether the Clerk needs an appointment for a license",
                "The ceremony fee of other Justice of the Peace courts (each sets its own; only Precinct 1, Place 1 prints one)"],
    "dallas": ["One county-wide ceremony fee (each Justice of the Peace court prints its own)",
               "Whether an appointment is required at the Clerk's office (the official pages disagree)",
               "A residency rule (only one court's page states one)"],
    "chicago": ["Whether witnesses are required", "The Clerk's downtown opening hours", "Whether the Chicago courtroom takes cash only"],
    "new-york": ["The fee for a certified copy of the marriage certificate",
                 "Appointment times and lead times (the booking system is not readable as a web page)"],
    "los-angeles": ["The waiting period (no page says in words that there is none)", "The fee for a certified copy of the marriage certificate",
                    "Which weekdays each branch office holds ceremonies"],
}
