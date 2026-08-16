"""
Negeri Sembilan 2026 Election Baseline Forecast Model
======================================================
Builds seat-level win probabilities and coalition win odds via Monte Carlo simulation.

METHODOLOGY
-----------
1. Prior: 2023 seat winner + majority (as % of turnout proxy).
2. Structural adjustment: In 2023 PH+BN ran as unity ticket vs PN+Bersatu (as PN).
   In 2026 PH runs alone; BN+PN have informal pact (25+11=36, no overlap);
   Bersatu breaks from PN and runs solo in 24 seats splitting opposition vote.
3. Johor 2026 spillover: BN swept 48/56 in Johor 11 Jul 2026, PH crushed to 8,
   PN wiped out. This signals ~8-12% Malay-vote swing away from PH and Bersatu.
4. Ethnic composition of seat drives adjustment magnitude:
   - Malay-majority seats: strong pro-BN/PN swing (Johor pattern replicable)
   - Chinese-majority seats: PH holds firm (DAP incumbency + BN Chinese candidates
     benefit from BN's rising credibility but base is thin)
   - Mixed seats: highest volatility, small BN edge
5. Incumbency bonus + candidate quality manual overlay (Tok Mat, Loke, Aminuddin).
6. Monte Carlo: 10,000 simulations with correlated regional swing.

DATA STRUCTURE
--------------
Each seat: {code, name, area, ethnic_mix, 2023_winner, 2023_majority_pct,
           candidates[], base_prob_by_party, current_leader, risk_rating}
"""

import json
import random
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

random.seed(20260801)

# -----------------------------------------------------------------------------
# SEAT-LEVEL DATA (from EC 2023 results + 2026 nomination day)
# -----------------------------------------------------------------------------
# ethnic_mix categories: "malay_majority", "chinese_majority", "mixed_malay",
#   "mixed_chinese", "malay_rural", "indian_influence"
# 2023_majority_pct: winner majority / total valid votes (approximation for swing calc)

SEATS = [
    # N01-N04 Jelebu (rural Malay/Chinese mixed, some Chinese pockets)
    {"code":"N01","name":"Chennah","parl":"Jelebu","ethnic":"mixed_chinese",
     "y2023_winner":"PH","y2023_maj_pct":0.187,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Anthony Loke","incumbent":True,"star":True},
                   {"party":"BN","name":"Siow Kong Choon","incumbent":False}]},
    {"code":"N02","name":"Pertang","parl":"Jelebu","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.246,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Umry Abdul Khois","incumbent":False},
                   {"party":"BN","name":"Jalaluddin Alias","incumbent":True,"star":True},
                   {"party":"BERSATU","name":"Faizal Fadli","incumbent":False}]},
    {"code":"N03","name":"Sungai Lui","parl":"Jelebu","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.038,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Zainal Fikri","incumbent":False},
                   {"party":"BN","name":"Razi Ali","incumbent":True},
                   {"party":"BERSATU","name":"Mazrulhisham","incumbent":False}]},
    {"code":"N04","name":"Klawang","parl":"Jelebu","ethnic":"malay_rural",
     "y2023_winner":"PH","y2023_maj_pct":0.063,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Bakri Sawir","incumbent":True},
                   {"party":"PN","name":"Danni Rais","incumbent":False},
                   {"party":"BERSATU","name":"Adib Musa","incumbent":False}]},
    # N05-N08 Jempol
    {"code":"N05","name":"Serting","parl":"Jempol","ethnic":"malay_majority",
     "y2023_winner":"PN","y2023_maj_pct":0.041,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Yaacob Mahmood","incumbent":False},
                   {"party":"PN","name":"Fairuz Isa","incumbent":True},
                   {"party":"BERSATU","name":"Noraffendy Salleh","incumbent":False}]},
    {"code":"N06","name":"Palong","parl":"Jempol","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.036,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Zahin Zinal Abidin","incumbent":False},
                   {"party":"BN","name":"Mustapha Nagoor","incumbent":True},
                   {"party":"BERSATU","name":"Rebin Birham","incumbent":False}]},
    {"code":"N07","name":"Jeram Padang","parl":"Jempol","ethnic":"mixed_malay",
     "y2023_winner":"BN","y2023_maj_pct":0.089,"contest":"4-way",
     "candidates":[{"party":"PH","name":"G Manivannan","incumbent":False},
                   {"party":"BN","name":"Zaidy Abdul Kadir","incumbent":True},
                   {"party":"BERSATU","name":"Sri Sanjeevan","incumbent":False},
                   {"party":"ASLI","name":"Dayana Dal","incumbent":False}]},
    {"code":"N08","name":"Bahau","parl":"Jempol","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.606,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Teo Kok Seong","incumbent":True,"star":True},
                   {"party":"BN","name":"Chong Fui Ming","incumbent":False}]},
    # N09-N14 Seremban (urban, mixed)
    {"code":"N09","name":"Lenggeng","parl":"Seremban","ethnic":"mixed_malay",
     "y2023_winner":"BN","y2023_maj_pct":0.032,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Zarinna Abu Zarin","incumbent":False},
                   {"party":"BN","name":"Asna Amin","incumbent":True},
                   {"party":"BERSATU","name":"Zool Amali","incumbent":False}]},
    {"code":"N10","name":"Nilai","parl":"Seremban","ethnic":"mixed_chinese",
     "y2023_winner":"PH","y2023_maj_pct":0.322,"contest":"5-way",
     "candidates":[{"party":"PH","name":"J Arul Kumar","incumbent":True},
                   {"party":"BN","name":"Lai Chien Kong","incumbent":False},
                   {"party":"BERSATU","name":"V Saravana","incumbent":False},
                   {"party":"BERJASA","name":"Zamani Ibrahim","incumbent":False},
                   {"party":"IND","name":"Omar Mohd Isa","incumbent":False}]},
    {"code":"N11","name":"Lobak","parl":"Seremban","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.746,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Chew Seh Yong","incumbent":True},
                   {"party":"PN","name":"P Kumar","incumbent":False}]},
    {"code":"N12","name":"Temiang","parl":"Seremban","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.328,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Ho Weng Wah","incumbent":False},
                   {"party":"BN","name":"Leaw Kok Chan","incumbent":False},
                   {"party":"BERSATU","name":"Fazly Hamid","incumbent":False}]},
    {"code":"N13","name":"Sikamat","parl":"Seremban","ethnic":"mixed_malay",
     "y2023_winner":"PH","y2023_maj_pct":0.115,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Nor Azman Mohamad","incumbent":False},
                   {"party":"PN","name":"Razali Abu Samah","incumbent":False},
                   {"party":"BERSATU","name":"Tun Faisal Ismail","incumbent":False,"star":True}]},
    {"code":"N14","name":"Ampangan","parl":"Seremban","ethnic":"mixed_malay",
     "y2023_winner":"PH","y2023_maj_pct":0.019,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Nazri Kassim","incumbent":False},
                   {"party":"PN","name":"Rafie Ab Malek","incumbent":False},
                   {"party":"BERSATU","name":"Noor Azah Harun","incumbent":False}]},
    # N15-N19 Kuala Pilah (Malay heartland)
    {"code":"N15","name":"Juasseh","parl":"Kuala Pilah","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.008,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Aidil Abdullah","incumbent":False},
                   {"party":"BN","name":"Ismail Lasim","incumbent":True},
                   {"party":"BERSATU","name":"Zuhaimi Md Yusof","incumbent":False}]},
    {"code":"N16","name":"Seri Menanti","parl":"Kuala Pilah","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.038,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Kamarul Arifin Wafa","incumbent":False},
                   {"party":"BN","name":"Sufian Maradzi","incumbent":True},
                   {"party":"BERSATU","name":"Megat Shahriman","incumbent":False}]},
    {"code":"N17","name":"Senaling","parl":"Kuala Pilah","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.078,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Hanis Alimin","incumbent":False},
                   {"party":"BN","name":"Qayyum Abd Jalil","incumbent":False},
                   {"party":"BERSATU","name":"Izaffi Istear Khan","incumbent":False}]},
    {"code":"N18","name":"Pilah","parl":"Kuala Pilah","ethnic":"mixed_malay",
     "y2023_winner":"PH","y2023_maj_pct":0.087,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Noorzunita Begum","incumbent":True},
                   {"party":"BN","name":"S Leza Md Yasin","incumbent":False}]},
    {"code":"N19","name":"Johol","parl":"Kuala Pilah","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.203,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Zailan Munawar","incumbent":False},
                   {"party":"BN","name":"Saiful Yazan Sulaiman","incumbent":True}]},
    # N20-N24 Rasah (urban Seremban, mixed & Chinese)
    {"code":"N20","name":"Labu","parl":"Rasah","ethnic":"malay_majority",
     "y2023_winner":"PN","y2023_maj_pct":0.076,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Ahmad Faez","incumbent":False},
                   {"party":"BN","name":"Siti Nur Umaira","incumbent":False},
                   {"party":"BERSATU","name":"Hanifah Abu Baker","incumbent":True}]},
    {"code":"N21","name":"Bukit Kepayang","parl":"Rasah","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.783,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Nicole Tan","incumbent":True},
                   {"party":"PN","name":"Lee Boon Shian","incumbent":False}]},
    {"code":"N22","name":"Rahang","parl":"Rasah","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.601,"contest":"4-way",
     "candidates":[{"party":"PH","name":"Siau Meow Kong","incumbent":True},
                   {"party":"BN","name":"Yap Siok Moy","incumbent":False},
                   {"party":"BERSATU","name":"Tang Jay Son","incumbent":False},
                   {"party":"PSM","name":"S Tinagaran","incumbent":False}]},
    {"code":"N23","name":"Mambau","parl":"Rasah","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.649,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Lee Kai Yet","incumbent":False},
                   {"party":"PN","name":"Erik Michael","incumbent":False},
                   {"party":"BERSATU","name":"N Sarawanan","incumbent":False}]},
    {"code":"N24","name":"Seremban Jaya","parl":"Rasah","ethnic":"mixed_chinese",
     "y2023_winner":"PH","y2023_maj_pct":0.599,"contest":"3-way",
     "candidates":[{"party":"PH","name":"S Mugunthan","incumbent":False},
                   {"party":"BN","name":"R T Thinalan","incumbent":False},
                   {"party":"BERSATU","name":"R Mahendran","incumbent":False}]},
    # N25-N28 Rembau (rural Malay + some Indian)
    {"code":"N25","name":"Paroi","parl":"Rembau","ethnic":"mixed_malay",
     "y2023_winner":"PN","y2023_maj_pct":0.144,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Ahmad Shahir","incumbent":False},
                   {"party":"PN","name":"Kamarol Ridzuan","incumbent":True},
                   {"party":"BERSATU","name":"Nazree Yunos","incumbent":False}]},
    {"code":"N26","name":"Chembong","parl":"Rembau","ethnic":"malay_majority",
     "y2023_winner":"BN","y2023_maj_pct":0.222,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Danish Nazran","incumbent":False},
                   {"party":"BN","name":"Zairul Bahri Idris","incumbent":True}]},
    {"code":"N27","name":"Rantau","parl":"Rembau","ethnic":"mixed_malay",
     "y2023_winner":"BN","y2023_maj_pct":0.336,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Azizul Hakim","incumbent":False},
                   {"party":"BN","name":"Mohamad Hasan (Tok Mat)","incumbent":True,"star":True}]},
    {"code":"N28","name":"Kota","parl":"Rembau","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.011,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Allif Ibrahim","incumbent":False},
                   {"party":"BN","name":"Suhaimi Aini","incumbent":True},
                   {"party":"BERSATU","name":"Akmal Noradzmi","incumbent":False}]},
    # N29-N33 Port Dickson (mixed, some Chinese)
    {"code":"N29","name":"Chuah","parl":"Port Dickson","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.489,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Yew Boon Lye","incumbent":True},
                   {"party":"BN","name":"Pau Jeou Ching","incumbent":False}]},
    {"code":"N30","name":"Lukut","parl":"Port Dickson","ethnic":"chinese_majority",
     "y2023_winner":"PH","y2023_maj_pct":0.531,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Choo Ken Hwa","incumbent":True},
                   {"party":"PN","name":"Sathes Kumar","incumbent":False},
                   {"party":"IND","name":"Teo Seng Lee","incumbent":False}]},
    {"code":"N31","name":"Bagan Pinang","parl":"Port Dickson","ethnic":"malay_majority",
     "y2023_winner":"PN","y2023_maj_pct":0.180,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Nasir Rahman","incumbent":False},
                   {"party":"PN","name":"Abdul Fatah Zakaria","incumbent":True},
                   {"party":"BERSATU","name":"Sheikh Junaidy","incumbent":False}]},
    {"code":"N32","name":"Linggi","parl":"Port Dickson","ethnic":"malay_majority",
     "y2023_winner":"BN","y2023_maj_pct":0.101,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Aminuddin Harun (MB)","incumbent":False,"star":True},
                   {"party":"BN","name":"Faizal Ramli","incumbent":True},
                   {"party":"BERSATU","name":"Zamri Said","incumbent":False}]},
    {"code":"N33","name":"Sri Tanjung","parl":"Port Dickson","ethnic":"indian_influence",
     "y2023_winner":"PH","y2023_maj_pct":0.281,"contest":"5-way",
     "candidates":[{"party":"PH","name":"G Rajasekaran","incumbent":True},
                   {"party":"BN","name":"A Achutan","incumbent":False},
                   {"party":"BERSATU","name":"M Leevineshwaraan","incumbent":False},
                   {"party":"IND","name":"Islah Wahyudi","incumbent":False},
                   {"party":"IND","name":"A Saravanan","incumbent":False}]},
    # N34-N36 Tampin (Malay rural south)
    {"code":"N34","name":"Gemas","parl":"Tampin","ethnic":"malay_rural",
     "y2023_winner":"PN","y2023_maj_pct":0.319,"contest":"3-way",
     "candidates":[{"party":"PH","name":"Siti Aishah Seman","incumbent":False},
                   {"party":"PN","name":"Ridzuan Ahmad","incumbent":True},
                   {"party":"BERSATU","name":"Azman Abdullah","incumbent":False}]},
    {"code":"N35","name":"Gemencheh","parl":"Tampin","ethnic":"malay_rural",
     "y2023_winner":"BN","y2023_maj_pct":0.114,"contest":"2-way",
     "candidates":[{"party":"PH","name":"Abd Latif Tambi","incumbent":False},
                   {"party":"BN","name":"Suhaimizan Bizar","incumbent":True}]},
    {"code":"N36","name":"Repah","parl":"Tampin","ethnic":"indian_influence",
     "y2023_winner":"PH","y2023_maj_pct":0.278,"contest":"2-way",
     "candidates":[{"party":"PH","name":"S Veerapan","incumbent":True},
                   {"party":"BN","name":"Koh Kim Swee","incumbent":False}]},
]

# -----------------------------------------------------------------------------
# BASELINE MODEL PARAMETERS (as of 2026-07-19, updated by daily cron)
# -----------------------------------------------------------------------------
MODEL_PARAMS = {
    "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    "polling_day": "2026-08-01",
    "days_to_polling": (datetime(2026,8,1) - datetime.now()).days,
    # Coalition-wide swing vs 2023 (in vote-share points)
    # Positive = gain vs 2023. Applied differently by ethnic seat type.
    #
    # UPDATED 23 Jul (Day 6): Vodus Research 437-sample poll (9-21 Jul) published
    # 22 Jul night. Statewide popular vote: PH 42, BN 35, PN 7, undecided 14.
    # Seat projection PH 17 / BN 15 / PN 2 / TCTC 2 — hung. Priors softened to
    # reflect PH holding urban/Chinese and mixed seats better than Johor spillover
    # implied. BN Malay gain still real but ~50% smaller than Johor swing.
    # Small NS sample (437 vs Vodus Johor 1,303) — kept some Johor anchor.
    #
    # UPDATED 28 Jul evening (Day 11 — early voting day):
    # 1) PN election director Muhammad Sanusi Md Nor is now under police
    #    investigation over 23 Jul Jempol 'Tanah Melayu' remarks (S.505B Penal Code
    #    + S.233 CMA, 2 police reports, IP opened). BN chairman Zahid publicly
    #    disciplined the remarks and reminded parties to respect the royal
    #    institution. NS Palace issued formal statement Monday distancing itself
    #    from parties. Early voting turnout 86%+ at 2pm — uniformed vote historically
    #    leans BN.
    # 2) DKU committal proceedings ADJOURNED to 28 Sept, effectively removing the
    #    royal-institution attack vector PN had been leaning on for the final
    #    96 hours.
    # 3) Ong Kian Ming (analyst) forecast BN-PN 23-25 seats yesterday — analyst
    #    tier signal, not poll.
    # Net: PN swing -0.01 across ethnic types (leadership damage + defused vector).
    # BN swing +0.01 across malay-lean seats (Zahid discipline win + uniformed vote).
    "swing_vs_2023": {
        "PH": {"malay_rural": -0.08, "malay_majority": -0.06, "mixed_malay": -0.02,
               "mixed_chinese": +0.01, "chinese_majority": +0.00, "indian_influence": +0.01},
        "BN": {"malay_rural": +0.05, "malay_majority": +0.07, "mixed_malay": +0.05,
               "mixed_chinese": +0.02, "chinese_majority": +0.02, "indian_influence": +0.02},
        "PN": {"malay_rural": -0.03, "malay_majority": -0.02, "mixed_malay": -0.04,
               "mixed_chinese": -0.03, "chinese_majority": -0.03, "indian_influence": -0.03},
        "BERSATU": {"malay_rural": +0.04, "malay_majority": +0.03, "mixed_malay": +0.03,
                    "mixed_chinese": +0.02, "chinese_majority": +0.01, "indian_influence": +0.02},
    },
    # Simulation params
    "regional_swing_sd": 0.035,     # coalition-wide swing std dev (widened for poll uncertainty)
    "seat_specific_sd": 0.045,      # seat-level idiosyncratic noise (widened)
    "incumbent_bonus": 0.02,
    "star_bonus": 0.03,
    "n_simulations": 10000,
}

# 2023 baseline vote shares by ethnic type (approximate, PH+BN unity vs PN)
# Format: {ethnic: (PH+BN_share, PN_share)}
# We reconstruct rough PH vs BN split within the unity ticket.
BASELINE_2023 = {
    "malay_rural":       {"PH+BN": 0.62, "PN": 0.38, "PH_share_of_pb": 0.42},
    "malay_majority":    {"PH+BN": 0.55, "PN": 0.45, "PH_share_of_pb": 0.45},
    "mixed_malay":       {"PH+BN": 0.68, "PN": 0.32, "PH_share_of_pb": 0.55},
    "mixed_chinese":     {"PH+BN": 0.78, "PN": 0.22, "PH_share_of_pb": 0.72},
    "chinese_majority":  {"PH+BN": 0.85, "PN": 0.15, "PH_share_of_pb": 0.82},
    "indian_influence":  {"PH+BN": 0.72, "PN": 0.28, "PH_share_of_pb": 0.62},
}


def base_vote_shares(seat):
    """Compute 2026 baseline vote shares from 2023 unity+swing decomposition."""
    e = seat["ethnic"]
    b = BASELINE_2023[e]
    ph_share_2023 = b["PH+BN"] * b["PH_share_of_pb"]
    bn_share_2023 = b["PH+BN"] * (1 - b["PH_share_of_pb"])
    pn_share_2023 = b["PN"]
    sw = MODEL_PARAMS["swing_vs_2023"]
    ph = max(0.02, ph_share_2023 + sw["PH"][e])
    bn = max(0.02, bn_share_2023 + sw["BN"][e])
    pn = max(0.02, pn_share_2023 + sw["PN"][e])
    # Bersatu draws from PN and BN Malay share, not PH
    bersatu_pull = sw["BERSATU"][e]
    # Which coalition actually contests this seat?
    parties = {c["party"] for c in seat["candidates"]}
    shares = {}
    if "PH" in parties: shares["PH"] = ph
    if "BN" in parties: shares["BN"] = bn
    if "PN" in parties: shares["PN"] = pn
    # BN and PN don't overlap by pact — pull from the one present
    if "BERSATU" in parties:
        shares["BERSATU"] = bersatu_pull
        # Redistribute the pull from whoever's present (mostly from BN/PN Malay)
        if "BN" in shares:
            shares["BN"] = max(0.02, shares["BN"] - bersatu_pull * 0.6)
        if "PN" in shares:
            shares["PN"] = max(0.02, shares["PN"] - bersatu_pull * 0.4)
    # Small parties/independents
    other_share = 0.0
    for c in seat["candidates"]:
        if c["party"] in ("IND","PSM","BERJASA","ASLI"):
            other_share += 0.015
            shares[c["party"]+"_"+c["name"][:8]] = 0.015
    # Candidate quality adjustments
    for c in seat["candidates"]:
        key = c["party"] if c["party"] in shares else None
        if key is None:
            continue
        if c.get("incumbent"):
            shares[key] += MODEL_PARAMS["incumbent_bonus"]
        if c.get("star"):
            shares[key] += MODEL_PARAMS["star_bonus"]
    # Normalize
    total = sum(shares.values())
    return {k: v/total for k, v in shares.items()}


def simulate():
    """Run Monte Carlo. Return per-seat probabilities and coalition seat distributions."""
    N = MODEL_PARAMS["n_simulations"]
    seat_wins = {s["code"]: {} for s in SEATS}
    coalition_seats = {"PH":[], "BN":[], "PN":[], "BERSATU":[], "OTHER":[],
                       "BN+PN":[]}  # BN+PN informal pact
    for sim in range(N):
        # Correlated coalition-wide swings for this simulation
        regional = {
            "PH":       random.gauss(0, MODEL_PARAMS["regional_swing_sd"]),
            "BN":       random.gauss(0, MODEL_PARAMS["regional_swing_sd"]),
            "PN":       random.gauss(0, MODEL_PARAMS["regional_swing_sd"]),
            "BERSATU":  random.gauss(0, MODEL_PARAMS["regional_swing_sd"]),
        }
        seat_counts = {"PH":0,"BN":0,"PN":0,"BERSATU":0,"OTHER":0}
        for seat in SEATS:
            shares = base_vote_shares(seat)
            noisy = {}
            for k, v in shares.items():
                coalition_key = k if k in regional else None
                sw = regional.get(coalition_key, 0)
                idio = random.gauss(0, MODEL_PARAMS["seat_specific_sd"])
                noisy[k] = max(0.005, v + sw + idio)
            # Winner
            winner_key = max(noisy, key=noisy.get)
            winner_coalition = winner_key if winner_key in seat_counts else "OTHER"
            seat_counts[winner_coalition] += 1
            seat_wins[seat["code"]][winner_coalition] = \
                seat_wins[seat["code"]].get(winner_coalition, 0) + 1
        for k in coalition_seats:
            if k == "BN+PN":
                coalition_seats[k].append(seat_counts["BN"] + seat_counts["PN"])
            else:
                coalition_seats[k].append(seat_counts[k])
    return seat_wins, coalition_seats


def summarize(seat_wins, coalition_seats):
    N = MODEL_PARAMS["n_simulations"]
    # Seat-level probs
    seat_probs = []
    for seat in SEATS:
        w = seat_wins[seat["code"]]
        probs = {k: v/N for k, v in w.items()}
        leader = max(probs, key=probs.get) if probs else "UNK"
        lead_prob = probs.get(leader, 0)
        # Classify
        if lead_prob >= 0.90:
            classification = "Safe"
        elif lead_prob >= 0.75:
            classification = "Likely"
        elif lead_prob >= 0.60:
            classification = "Lean"
        elif lead_prob >= 0.50:
            classification = "Toss-up"
        else:
            classification = "Too Close to Call"
        seat_probs.append({
            **seat,
            "probs": probs,
            "leader": leader,
            "leader_prob": lead_prob,
            "classification": classification,
        })
    # Coalition-level: probability of majority (≥19 seats) and government-forming
    def stats(arr):
        s = sorted(arr)
        return {
            "mean": sum(arr)/len(arr),
            "median": s[len(s)//2],
            "p10": s[len(s)//10],
            "p90": s[len(s)*9//10],
            "min": s[0],
            "max": s[-1],
            "p_majority": sum(1 for x in arr if x >= 19)/len(arr),
        }
    coalition_stats = {k: stats(v) for k, v in coalition_seats.items()}

    # Government formation probability
    # Assumes: PH governs if PH alone ≥19. BN+PN governs if BN+PN ≥19.
    # Otherwise hung -> whoever has plurality forms minority govt.
    gov_wins = {"PH":0, "BN+PN":0, "Hung/Other":0}
    for i in range(N):
        ph_s = coalition_seats["PH"][i]
        bnpn_s = coalition_seats["BN+PN"][i]
        if ph_s >= 19:
            gov_wins["PH"] += 1
        elif bnpn_s >= 19:
            gov_wins["BN+PN"] += 1
        elif ph_s > bnpn_s:
            gov_wins["PH"] += 1
        else:
            gov_wins["BN+PN"] += 1
    gov_probs = {k: v/N for k, v in gov_wins.items()}
    return seat_probs, coalition_stats, gov_probs


def main():
    seat_wins, coalition_seats = simulate()
    seat_probs, coalition_stats, gov_probs = summarize(seat_wins, coalition_seats)

    out = {
        "meta": MODEL_PARAMS,
        "government_probability": gov_probs,
        "coalition_seat_stats": coalition_stats,
        "seats": seat_probs,
    }

    out_path = Path("/home/user/workspace/ns-tracker/data/model_output.json")
    out_path.parent.mkdir(exist_ok=True, parents=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)

    # Print quick summary
    print(f"Generated: {MODEL_PARAMS['generated_at']}")
    print(f"Days to polling: {MODEL_PARAMS['days_to_polling']}")
    print("\nGOVERNMENT WIN PROBABILITY")
    for k, v in sorted(gov_probs.items(), key=lambda x: -x[1]):
        print(f"  {k:12s} {v:.1%}")
    print("\nCOALITION SEAT PROJECTIONS (mean, p10-p90 range, p_majority≥19)")
    for k, s in coalition_stats.items():
        print(f"  {k:8s} mean={s['mean']:.1f}  range={s['p10']}-{s['p90']}  P(≥19)={s['p_majority']:.1%}")
    print("\nSEAT-LEVEL CLASSIFICATIONS")
    for cls in ["Safe","Likely","Lean","Toss-up","Too Close to Call"]:
        seats_in = [s for s in seat_probs if s["classification"] == cls]
        print(f"  {cls:20s} {len(seats_in)} seats")
    print(f"\nWritten: {out_path}")

if __name__ == "__main__":
    main()
