"""Canonical ground names.

Cricsheet names venues descriptively ("Melbourne Cricket Ground"), historical
scorecards use short forms ("Melbourne"), and both add or drop city suffixes.
One ground must be one page, so names are canonicalised conservatively:
curated aliases first, then a city-suffix strip that never touches generic
names such as "County Ground". Anything unrecognised is left exactly as it is.
"""
from __future__ import annotations

import re

GENERIC = {
    'county ground', 'national stadium', 'national cricket stadium', 'sports club', 'cricket club ground', 'university oval',
    'university ground', 'recreation ground', 'cricket ground', 'stadium', 'oval', 'gymkhana ground', 'sports club ground',
    'cricket stadium', 'international cricket stadium', 'international stadium', 'club ground', 'the oval', 'sports ground',
}
DESCRIPTIVE = re.compile(r'stadium|oval|park|ground|gardens|bridge|trafford|headingley|edgbaston|newlands|kingsmead|wanderers|'
                         r'sabina|kensington|lord|premadasa|gabba|waca|basin|gaddafi|arena|complex|field|club|bowl|village', re.I)

ALIASES = {
    # Australia
    'Melbourne': 'Melbourne Cricket Ground', 'Melbourne (Docklands)': 'Docklands Stadium', 'Docklands Stadium, Melbourne': 'Docklands Stadium',
    'Sydney': 'Sydney Cricket Ground', 'Adelaide': 'Adelaide Oval', 'Brisbane': 'Brisbane Cricket Ground', 'Hobart': 'Bellerive Oval',
    'Canberra': 'Manuka Oval', 'W.A.C.A': 'WACA Ground', 'W.A.C.A. Ground': 'WACA Ground', 'Western Australia Cricket Association Ground': 'WACA Ground',
    'Perth Stadium, Perth': 'Perth Stadium', 'Cairns': 'Cazalys Stadium', 'Darwin': 'Marrara Cricket Ground',
    # England
    "Lord's, London": "Lord's", 'The Oval': 'Kennington Oval', 'Kennington Oval, London': 'Kennington Oval', 'Birmingham': 'Edgbaston',
    'Leeds': 'Headingley', 'Manchester': 'Old Trafford', 'Nottingham': 'Trent Bridge', 'Southampton': 'The Rose Bowl', 'Rose Bowl': 'The Rose Bowl',
    'Chester-le-Street': 'Riverside Ground', 'Cardiff': 'Sophia Gardens', 'Bristol': 'County Ground, Bristol', 'Taunton': 'County Ground, Taunton',
    'Worcester': 'County Ground, New Road, Worcester', 'County Ground, New Road': 'County Ground, New Road, Worcester', 'Leicester': 'Grace Road',
    'Derby': 'County Ground, Derby', 'Chelmsford': 'County Ground, Chelmsford', 'Hove': 'County Ground, Hove', 'Northampton': 'County Ground, Northampton',
    'Scarborough': 'North Marine Road Ground', 'Canterbury': 'St Lawrence Ground',
    # India
    'Kolkata': 'Eden Gardens', 'Calcutta': 'Eden Gardens', 'Wankhede': 'Wankhede Stadium', 'Chennai': 'MA Chidambaram Stadium', 'Chepauk': 'MA Chidambaram Stadium',
    'MA Chidambaram Stadium, Chepauk': 'MA Chidambaram Stadium', 'MA Chidambaram Stadium, Chepauk, Chennai': 'MA Chidambaram Stadium',
    'Bengaluru': 'M Chinnaswamy Stadium', 'Bangalore': 'M Chinnaswamy Stadium', 'M.Chinnaswamy Stadium': 'M Chinnaswamy Stadium',
    'Delhi': 'Arun Jaitley Stadium', 'Feroz Shah Kotla': 'Arun Jaitley Stadium', 'Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association Stadium': 'Punjab Cricket Association IS Bindra Stadium', 'Punjab Cricket Association Stadium, Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Ahmedabad': 'Narendra Modi Stadium', 'Sardar Patel Stadium, Motera': 'Narendra Modi Stadium', 'Sardar Patel Stadium': 'Narendra Modi Stadium',
    'Dharamsala': 'Himachal Pradesh Cricket Association Stadium', 'Dharamshala': 'Himachal Pradesh Cricket Association Stadium',
    'Ranchi': 'JSCA International Stadium Complex', 'Pune': 'Maharashtra Cricket Association Stadium', 'Visakhapatnam': 'Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium',
    'Indore': 'Holkar Cricket Stadium', 'Lucknow': 'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium',
    'Thiruvananthapuram': 'Greenfield International Stadium', 'Guwahati': 'Barsapara Cricket Stadium', 'Kanpur': 'Green Park', 'Cuttack': 'Barabati Stadium',
    'Jaipur': 'Sawai Mansingh Stadium', 'Vadodara': 'Kotambi Stadium', 'Raipur': 'Shaheed Veer Narayan Singh International Stadium',
    # Pakistan
    'National Stadium': 'National Stadium, Karachi', 'Karachi': 'National Stadium, Karachi', 'Lahore': 'Gaddafi Stadium', 'Rawalpindi': 'Rawalpindi Cricket Stadium',
    'Multan': 'Multan Cricket Stadium', 'Faisalabad': 'Iqbal Stadium', 'Peshawar': 'Arbab Niaz Stadium',
    # Sri Lanka
    'Colombo (RPS)': 'R Premadasa Stadium', 'R.Premadasa Stadium': 'R Premadasa Stadium', 'R.Premadasa Stadium, Khettarama': 'R Premadasa Stadium',
    'Colombo (SSC)': 'Sinhalese Sports Club Ground', 'Colombo (PSS)': 'P Sara Oval', 'P Saravanamuttu Stadium': 'P Sara Oval', 'Colombo (Moors)': 'Moors Sports Club Ground',
    'Colombo (NCC)': 'Nondescripts Cricket Club Ground', 'Colombo (Colts)': 'Colts Cricket Club Ground', 'Colombo (CCC)': 'Colombo Cricket Club Ground',
    'Colombo (Thurstan)': 'Thurstan College Ground', 'Galle': 'Galle International Stadium', 'Pallekele': 'Pallekele International Cricket Stadium',
    'Kandy': 'Asgiriya Stadium', 'Dambulla': 'Rangiri Dambulla International Stadium', 'Hambantota': 'Mahinda Rajapaksa International Cricket Stadium',
    'Mahinda Rajapaksa International Cricket Stadium, Sooriyawewa': 'Mahinda Rajapaksa International Cricket Stadium',
    # Bangladesh
    'Sher-e-Bangla National Cricket Stadium': 'Shere Bangla National Stadium', 'Mirpur': 'Shere Bangla National Stadium', 'Dhaka': 'Bangabandhu National Stadium',
    'Chittagong': 'Zahur Ahmed Chowdhury Stadium', 'Chattogram': 'Zahur Ahmed Chowdhury Stadium', 'Zohur Ahmed Chowdhury Stadium': 'Zahur Ahmed Chowdhury Stadium',
    'Sylhet': 'Sylhet International Cricket Stadium', 'Sylhet Stadium': 'Sylhet International Cricket Stadium',
    # South Africa
    'Cape Town': 'Newlands', 'Durban': 'Kingsmead', 'Centurion': 'SuperSport Park', 'Johannesburg': 'The Wanderers Stadium', 'New Wanderers Stadium': 'The Wanderers Stadium',
    'Port Elizabeth': "St George's Park", 'Gqeberha': "St George's Park", 'Bloemfontein': 'Mangaung Oval', 'Goodyear Park': 'Mangaung Oval', 'OUTsurance Oval': 'Mangaung Oval',
    'Paarl': 'Boland Park', 'Potchefstroom': 'Senwes Park', 'East London': 'Buffalo Park', 'Kimberley': 'De Beers Diamond Oval', 'Benoni': 'Willowmoore Park',
    'Pietermaritzburg': 'City Oval', 'Kingsmead, Durban': 'Kingsmead',
    # New Zealand
    'Auckland': 'Eden Park', 'Hamilton': 'Seddon Park', 'Napier': 'McLean Park', 'Dunedin': 'University Oval, Dunedin', 'Nelson': 'Saxton Oval',
    'Mount Maunganui': 'Bay Oval', 'Queenstown': 'Queenstown Events Centre', 'Whangarei': 'Cobham Oval', 'New Plymouth': 'Pukekura Park',
    # West Indies
    'Bridgetown': 'Kensington Oval', 'Kingston': 'Sabina Park', 'Port of Spain': "Queen's Park Oval", 'Gros Islet': 'Daren Sammy National Cricket Stadium',
    'Beausejour Stadium, Gros Islet': 'Daren Sammy National Cricket Stadium', 'Darren Sammy National Cricket Stadium, Gros Islet': 'Daren Sammy National Cricket Stadium',
    'Beausejour Stadium': 'Daren Sammy National Cricket Stadium', 'North Sound': 'Sir Vivian Richards Stadium', 'Providence': 'Providence Stadium', 'Roseau': 'Windsor Park',
    'Basseterre': 'Warner Park', "St George's": "National Cricket Stadium, St George's", 'National Cricket Stadium, Grenada': "National Cricket Stadium, St George's",
    "National Cricket Stadium, St George's, Grenada": "National Cricket Stadium, St George's", 'Kingstown': 'Arnos Vale Ground', 'Georgetown': 'Bourda',
    'Tarouba': 'Brian Lara Stadium', "St John's": 'Antigua Recreation Ground',
    # Zimbabwe, Ireland, UAE, Afghanistan homes
    'Harare': 'Harare Sports Club', 'Bulawayo': 'Queens Sports Club', 'Dublin': 'Clontarf Cricket Club Ground', 'Malahide': 'The Village, Malahide',
    'Belfast': 'Civil Service Cricket Club, Stormont', 'Dubai (DICS)': 'Dubai International Cricket Stadium', 'Dubai': 'Dubai International Cricket Stadium',
    'Sharjah': 'Sharjah Cricket Stadium', 'Abu Dhabi': 'Sheikh Zayed Stadium', 'Zayed Cricket Stadium': 'Sheikh Zayed Stadium', 'Zayed Cricket Stadium, Abu Dhabi': 'Sheikh Zayed Stadium',
    # Remaining spellings seen in the archive
    'Brabourne': 'Brabourne Stadium', 'Bready': 'Bready Cricket Club', 'Castle Avenue, Dublin': 'Castle Avenue', "Cazaly's Stadium": 'Cazalys Stadium',
    'Civil Service Cricket Club': 'Civil Service Cricket Club, Stormont', 'Coolidge': 'Coolidge Cricket Ground', 'Grace Road, Leicester': 'Grace Road',
    'Marrara Stadium': 'Marrara Cricket Ground', 'North Sydney': 'North Sydney Oval', 'Sheikhupura': 'Sheikhupura Stadium',
    'Sinhalese Sports Club': 'Sinhalese Sports Club Ground', 'University Oval': 'University Oval, Dunedin', 'Westpac Park': 'Seddon Park',
    'Dr DY Patil Sports Academy, Mumbai': 'Dr DY Patil Sports Academy', 'Dr DY Patil Sports Academy, Navi Mumbai': 'Dr DY Patil Sports Academy',
    'Vidarbha Cricket Association Stadium, Jamtha': 'Vidarbha Cricket Association Stadium', 'The Village, Malahide, Dublin': 'The Village, Malahide',
}

DATED = {
    # Cricinfo's short "Perth" means the WACA until the new stadium opened.
    'Perth': (('2018-12-01', 'WACA Ground'), (None, 'Perth Stadium')),
    'Christchurch': (('2012-01-01', 'Lancaster Park'), (None, 'Hagley Oval')),
    'Wellington': (('2000-01-01', 'Basin Reserve'), (None, None)),
    'Nagpur': (('2008-10-01', 'Vidarbha Cricket Association Ground'), (None, 'Vidarbha Cricket Association Stadium')),
    'Rajkot': (('2013-01-01', 'Madhavrao Scindia Cricket Ground'), (None, 'Saurashtra Cricket Association Stadium')),
    'Hyderabad': ((None, None),),
}


def strip_suffix(name):
    """"Wankhede Stadium, Mumbai" becomes "Wankhede Stadium"; "County Ground, Bristol" stays."""
    parts = [p.strip() for p in name.split(',') if p.strip()]
    if len(parts) < 2:
        return name
    base = parts[0]
    if base.lower() in GENERIC or not DESCRIPTIVE.search(base):
        return name
    return base


def canonical_venue(name, date='', fmt=''):
    """Canonical ground for a recorded venue string; unknown names pass through unchanged."""
    if not name:
        return name
    key = ' '.join(str(name).split())
    if key in DATED:
        for cutoff, target in DATED[key]:
            if cutoff is None or (date or '') < cutoff:
                if target is None:
                    if key == 'Wellington' and fmt == 'Test':
                        return 'Basin Reserve'
                    return key
                return target
        return key
    if key in ALIASES:
        return ALIASES[key]
    stripped = strip_suffix(key)
    return ALIASES.get(stripped, stripped)


def canonicalise_matches(matches):
    """Rewrite venue names in place and return {old_name: canonical} for every change."""
    changed = {}
    for m in matches:
        original = m.get('venue')
        if not original:
            continue
        target = canonical_venue(original, m.get('date', ''), m.get('format', ''))
        if target != original:
            m['venue_recorded'] = original
            m['venue'] = target
            changed[original] = target
    return changed
