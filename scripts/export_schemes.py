"""One-off export tool to generate scheme JSON files from python definitions.
Run this script to regenerate knowledge/schemes/*.json files from SCHEMES_DATA.
"""

import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from shared.config import SCHEMES_DIR

SCHEMES_DATA = [
    {
        "id": "pm-kisan",
        "name": "PM Kisan Samman Nidhi",
        "name_hi": "प्रधानमंत्री किसान सम्मान निधि",
        "ministry": "Ministry of Agriculture and Farmers Welfare",
        "description": "Financial support of Rs 6,000 per year in three equal installments directly to bank accounts of landholding farmer families.",
        "benefits": "₹6,000/year direct cash transfer (3 installments of ₹2,000 each)",
        "official_url": "https://pmkisan.gov.in",
        "category_tags": ["farmer", "agriculture", "financial assistance", "cash transfer"],
        "documents_required": ["Aadhaar Card", "Land Ownership Documents / Khasra-Khatauni", "Bank Account Passbook"],
        "is_active": True,
        "criteria": [
            {
                "field": "occupation",
                "operator": "eq",
                "value": "farmer",
                "description": "Must be an active farmer",
                "disqualification_reason": "Applicant occupation is not farmer"
            },
            {
                "field": "has_bank_account",
                "operator": "is_true",
                "value": True,
                "description": "Must have an active bank account",
                "disqualification_reason": "Applicant does not have a bank account for direct transfer"
            },
            {
                "field": "has_aadhaar",
                "operator": "is_true",
                "value": True,
                "description": "Must possess Aadhaar card",
                "disqualification_reason": "Aadhaar is mandatory for PM-KISAN"
            },
            {
                "field": "land_holding_acres",
                "operator": "gte",
                "value": 0.01,
                "description": "Must own cultivable agricultural land (at least 0.01 acres)",
                "disqualification_reason": "Applicant does not own cultivable agricultural land"
            }
        ]
    },
    {
        "id": "pm-jay",
        "name": "Ayushman Bharat - PM-JAY",
        "name_hi": "आयुष्मान भारत - प्रधानमंत्री जन आरोग्य योजना",
        "ministry": "Ministry of Health and Family Welfare",
        "description": "Health cover of Rs 5 lakh per family per year for secondary and tertiary care hospitalization to poor and vulnerable families.",
        "benefits": "₹5 Lakh/family/year cashless hospital treatment cover",
        "official_url": "https://pmjay.gov.in",
        "category_tags": ["health", "insurance", "hospitalization", "bpl"],
        "documents_required": ["Aadhaar Card", "Ration Card / BPL Card", "Income Certificate"],
        "is_active": True,
        "criteria": [
            {
                "field": "is_bpl",
                "operator": "is_true",
                "value": True,
                "description": "Must be listed under BPL / SECC vulnerable criteria",
                "disqualification_reason": "Applicant is not BPL / SECC eligible"
            },
            {
                "field": "has_aadhaar",
                "operator": "is_true",
                "value": True,
                "description": "Must possess Aadhaar card",
                "disqualification_reason": "Aadhaar is mandatory for Ayushman Card generation"
            }
        ]
    },
    {
        "id": "pm-sym",
        "name": "PM Shram Yogi Maandhan (PM-SYM)",
        "name_hi": "प्रधानमंत्री श्रम योगी मानधन योजना",
        "ministry": "Ministry of Labour and Employment",
        "description": "Old age pension scheme for unorganized workers like street vendors, rickshaw pullers, construction workers.",
        "benefits": "Guaranteed minimum monthly pension of ₹3,000 after age 60",
        "official_url": "https://maandhan.in",
        "category_tags": ["pension", "unorganized labour", "social security"],
        "documents_required": ["Aadhaar Card", "Savings Bank Account / Jan Dhan Account with IFSC"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Entry age must be at least 18 years",
                "disqualification_reason": "Applicant is younger than 18 years"
            },
            {
                "field": "age",
                "operator": "lte",
                "value": 40,
                "description": "Entry age must not exceed 40 years",
                "disqualification_reason": "Applicant is older than 40 years for entry into PM-SYM"
            },
            {
                "field": "annual_income",
                "operator": "lte",
                "value": 180000,
                "description": "Monthly income must not exceed ₹15,000 (Annual <= ₹1,80,000)",
                "disqualification_reason": "Annual income exceeds ₹1,80,000 limit for unorganized workers"
            },
            {
                "field": "occupation",
                "operator": "in",
                "value": ["labourer", "self_employed", "unemployed"],
                "description": "Must be an unorganized worker or labourer",
                "disqualification_reason": "Scheme only applies to unorganized workers"
            }
        ]
    },
    {
        "id": "post-matric-scholarship",
        "name": "Post-Matric Scholarship for SC/ST/OBC Students",
        "name_hi": "उत्तर मैट्रिक छात्रवृत्ति (एससी/एसटी/ओबीसी)",
        "ministry": "Ministry of Social Justice and Empowerment",
        "description": "Financial assistance to SC/ST/OBC students studying at post-matriculation or post-secondary stage.",
        "benefits": "Complete tuition fee waiver + maintenance allowance (up to ₹13,500/yr)",
        "official_url": "https://scholarships.gov.in",
        "category_tags": ["student", "education", "scholarship", "higher education"],
        "documents_required": ["Caste Certificate", "Income Certificate", "Previous Marksheet", "Fee Receipt", "Bank Passbook"],
        "is_active": True,
        "criteria": [
            {
                "field": "occupation",
                "operator": "eq",
                "value": "student",
                "description": "Applicant must currently be a student",
                "disqualification_reason": "Applicant is not enrolled as a student"
            },
            {
                "field": "category",
                "operator": "in",
                "value": ["sc", "st", "obc"],
                "description": "Applicant must belong to SC, ST, or OBC category",
                "disqualification_reason": "Applicant category is not SC, ST, or OBC"
            },
            {
                "field": "annual_income",
                "operator": "lte",
                "value": 250000,
                "description": "Family annual income must not exceed ₹2,50,000",
                "disqualification_reason": "Family annual income exceeds ₹2.5 Lakh limit"
            }
        ]
    },
    {
        "id": "pm-svanidhi",
        "name": "PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi)",
        "name_hi": "पीएम स्वनिधि योजना",
        "ministry": "Ministry of Housing and Urban Affairs",
        "description": "Collateral-free working capital loan to urban and peri-urban street vendors.",
        "benefits": "Working capital loan starting at ₹10,000 with 7% interest subsidy, up to ₹50,000 on prompt repayment",
        "official_url": "https://pmsvanidhi.mohua.gov.in",
        "category_tags": ["street vendor", "loan", "working capital", "self employed"],
        "documents_required": ["Aadhaar Card", "Vending Certificate / Urban Local Body Letter", "Bank Account"],
        "is_active": True,
        "criteria": [
            {
                "field": "occupation",
                "operator": "in",
                "value": ["self_employed", "labourer"],
                "description": "Applicant must be a self-employed vendor or informal worker",
                "disqualification_reason": "Applicant is not in self-employed or informal street trade"
            },
            {
                "field": "has_bank_account",
                "operator": "is_true",
                "value": True,
                "description": "Must have an active bank account",
                "disqualification_reason": "Bank account required for loan disbursement"
            }
        ]
    },
    {
        "id": "pm-mudra",
        "name": "Pradhan Mantri Mudra Yojana (PMMY)",
        "name_hi": "प्रधानमंत्री मुद्रा योजना",
        "ministry": "Ministry of Finance",
        "description": "Loans up to 10 Lakhs to non-corporate, non-farm small/micro enterprises (Shishu, Kishore, Tarun).",
        "benefits": "Collateral-free business loan from ₹50,000 up to ₹10 Lakhs",
        "official_url": "https://www.mudra.org.in",
        "category_tags": ["entrepreneur", "business loan", "msme", "self employed"],
        "documents_required": ["Identity Proof (Aadhaar/Voter ID)", "Business Address Proof", "Quotation / Project Report"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Age must be at least 18 years",
                "disqualification_reason": "Applicant must be an adult (18+)"
            },
            {
                "field": "occupation",
                "operator": "in",
                "value": ["self_employed", "unemployed", "farmer"],
                "description": "Applicant must be setting up or running non-corporate small enterprise",
                "disqualification_reason": "Applicant occupation is not eligible for Mudra loans"
            }
        ]
    },
    {
        "id": "pmay-g",
        "name": "Pradhan Mantri Awas Yojana - Gramin (PMAY-G)",
        "name_hi": "प्रधानमंत्री आवास योजना - ग्रामीण",
        "ministry": "Ministry of Rural Development",
        "description": "Housing assistance to provide pucca house with basic amenities to all homeless and households living in kutcha/dilapidated houses in rural areas.",
        "benefits": "Financial assistance of ₹1,20,000 (plains) to ₹1,30,000 (hilly states) + 90 days MGNREGA wages",
        "official_url": "https://pmayg.nic.in",
        "category_tags": ["housing", "rural", "shelter", "bpl"],
        "documents_required": ["Aadhaar Card", "Job Card under MGNREGA", "Bank Account linked to Aadhaar", "BPL Certificate"],
        "is_active": True,
        "criteria": [
            {
                "field": "is_rural",
                "operator": "is_true",
                "value": True,
                "description": "Applicant must reside in a rural area",
                "disqualification_reason": "PMAY-G is specifically for rural residents"
            },
            {
                "field": "is_bpl",
                "operator": "is_true",
                "value": True,
                "description": "Must be categorized as BPL or homeless / kutcha house household",
                "disqualification_reason": "Applicant is not classified as BPL / housing-deprived"
            }
        ]
    },
    {
        "id": "pm-ujjwala",
        "name": "Pradhan Mantri Ujjwala Yojana 2.0",
        "name_hi": "प्रधानमंत्री उज्ज्वला योजना",
        "ministry": "Ministry of Petroleum and Natural Gas",
        "description": "Provides deposit-free LPG connection to adult women belonging to poor households.",
        "benefits": "Free LPG connection + first refill and hotplate/stove free of cost",
        "official_url": "https://www.pmuy.gov.in",
        "category_tags": ["women", "energy", "clean fuel", "lpg", "bpl"],
        "documents_required": ["Aadhaar Card of Applicant and Adult Family Members", "Ration Card", "Bank Account Details"],
        "is_active": True,
        "criteria": [
            {
                "field": "gender",
                "operator": "eq",
                "value": "female",
                "description": "Applicant must be an adult woman",
                "disqualification_reason": "Ujjwala connection is exclusively issued in the name of an adult woman"
            },
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Applicant must be at least 18 years old",
                "disqualification_reason": "Applicant is under 18 years"
            },
            {
                "field": "is_bpl",
                "operator": "is_true",
                "value": True,
                "description": "Must belong to BPL or underprivileged household",
                "disqualification_reason": "Household does not fall under BPL/deprived criteria"
            }
        ]
    },
    {
        "id": "atal-pension-yojana",
        "name": "Atal Pension Yojana (APY)",
        "name_hi": "अटल पेंशन योजना",
        "ministry": "Ministry of Finance (PFRDA)",
        "description": "Pension scheme targeted towards citizens in the unorganized sector for guaranteed monthly pension.",
        "benefits": "Guaranteed pension of ₹1,000 to ₹5,000 per month after age 60",
        "official_url": "https://www.npscra.nsdl.co.in",
        "category_tags": ["pension", "senior citizen", "social security", "retirement"],
        "documents_required": ["Aadhaar Card", "Active Savings Bank Account with auto-debit facility"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Applicant must be at least 18 years old",
                "disqualification_reason": "Minimum entry age for APY is 18"
            },
            {
                "field": "age",
                "operator": "lte",
                "value": 40,
                "description": "Applicant must be under 40 years old",
                "disqualification_reason": "Maximum entry age for APY is 40"
            },
            {
                "field": "has_bank_account",
                "operator": "is_true",
                "value": True,
                "description": "Must possess a savings bank account",
                "disqualification_reason": "Active bank account required for contribution auto-debit"
            }
        ]
    },
    {
        "id": "stand-up-india",
        "name": "Stand-Up India Scheme",
        "name_hi": "स्टैंड-अप इंडिया योजना",
        "ministry": "Ministry of Finance",
        "description": "Facilitates bank loans between ₹10 lakh and ₹1 crore to at least one SC or ST borrower and at least one woman borrower per bank branch for setting up greenfield enterprises.",
        "benefits": "Bank loan from ₹10 Lakh up to ₹1 Crore for greenfield business",
        "official_url": "https://www.standupmitra.in",
        "category_tags": ["women entrepreneur", "sc", "st", "business loan", "startup"],
        "documents_required": ["Aadhaar Card", "Caste Certificate (if SC/ST)", "Project Report", "Pan Card"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Applicant must be 18+ years",
                "disqualification_reason": "Applicant is under 18 years"
            },
            {
                "field": "occupation",
                "operator": "in",
                "value": ["self_employed", "unemployed"],
                "description": "Setting up a greenfield manufacturing, service, agri-allied, or trading enterprise",
                "disqualification_reason": "Applicant is not establishing a new enterprise"
            }
        ]
    },
    {
        "id": "old-age-pension-nsap",
        "name": "Indira Gandhi National Old Age Pension Scheme (IGNOAPS)",
        "name_hi": "इंदिरा गांधी राष्ट्रीय वृद्धावस्था पेंशन योजना",
        "ministry": "Ministry of Rural Development",
        "description": "Monthly pension for elderly senior citizens living below the poverty line.",
        "benefits": "Monthly pension of ₹500 to ₹1,000 (enhanced with state contribution)",
        "official_url": "https://nsap.nic.in",
        "category_tags": ["senior citizen", "pension", "bpl", "elderly"],
        "documents_required": ["Age Proof / Aadhaar", "BPL Ration Card", "Bank Account Passbook"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 60,
                "description": "Applicant must be 60 years or older",
                "disqualification_reason": "Applicant has not reached senior citizen age (60+)"
            },
            {
                "field": "is_bpl",
                "operator": "is_true",
                "value": True,
                "description": "Applicant household must be Below Poverty Line (BPL)",
                "disqualification_reason": "Applicant household is not classified as BPL"
            }
        ]
    },
    {
        "id": "disability-pension-nsap",
        "name": "Indira Gandhi National Disability Pension Scheme (IGNDPS)",
        "name_hi": "इंदिरा गांधी राष्ट्रीय दिव्यांगता पेंशन योजना",
        "ministry": "Ministry of Rural Development",
        "description": "Social assistance pension for persons with severe and multiple disabilities below the poverty line.",
        "benefits": "Monthly financial pension assistance + medical aids",
        "official_url": "https://nsap.nic.in",
        "category_tags": ["disability", "divyang", "pension", "bpl"],
        "documents_required": ["Disability Certificate (40%+ disability)", "Aadhaar Card", "BPL Certificate", "Bank Passbook"],
        "is_active": True,
        "criteria": [
            {
                "field": "is_disabled",
                "operator": "is_true",
                "value": True,
                "description": "Applicant must be a person with benchmark disability",
                "disqualification_reason": "Applicant is not marked as having a disability"
            },
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Applicant must be at least 18 years old",
                "disqualification_reason": "Applicant is under 18 years"
            },
            {
                "field": "is_bpl",
                "operator": "is_true",
                "value": True,
                "description": "Applicant must belong to BPL family",
                "disqualification_reason": "Applicant does not have BPL status"
            }
        ]
    },
    {
        "id": "pm-vishwakarma",
        "name": "PM Vishwakarma Scheme",
        "name_hi": "पीएम विश्वकर्मा योजना",
        "ministry": "Ministry of Micro, Small and Medium Enterprises",
        "description": "Holistic support to traditional artisans and craftspeople working with hands and tools.",
        "benefits": "Skill training (₹500/day stipend), ₹15,000 toolkit incentive, and collateral-free enterprise loan up to ₹3 Lakh at 5% interest",
        "official_url": "https://pmvishwakarma.gov.in",
        "category_tags": ["artisan", "craftsperson", "self employed", "toolkit", "loan"],
        "documents_required": ["Aadhaar Card", "Mobile Linked to Aadhaar", "Bank Account", "Artisan Trade Certificate/Declaration"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Applicant must be at least 18 years old",
                "disqualification_reason": "Minimum age is 18 years"
            },
            {
                "field": "occupation",
                "operator": "in",
                "value": ["self_employed", "labourer"],
                "description": "Must be engaged in traditional trade or craft work",
                "disqualification_reason": "Applicant is not engaged in traditional artisanal or craft trade"
            }
        ]
    },
    {
        "id": "lakhpati-didi",
        "name": "Lakhpati Didi Initiative",
        "name_hi": "लखपति दीदी योजना",
        "ministry": "Ministry of Rural Development",
        "description": "Empowering women Self-Help Group (SHG) members to earn sustainable annual income of ₹1 Lakh or more through micro-enterprises.",
        "benefits": "Interest-free loan up to ₹5 Lakh, entrepreneurship & financial training, market linkage support",
        "official_url": "https://aajeevika.gov.in",
        "category_tags": ["women", "shg", "rural", "entrepreneurship"],
        "documents_required": ["Aadhaar Card", "SHG Membership Record", "Bank Passbook", "Income Certificate"],
        "is_active": True,
        "criteria": [
            {
                "field": "gender",
                "operator": "eq",
                "value": "female",
                "description": "Applicant must be female",
                "disqualification_reason": "Lakhpati Didi initiative is strictly for women"
            },
            {
                "field": "is_rural",
                "operator": "is_true",
                "value": True,
                "description": "Must be resident in rural area / part of rural SHG",
                "disqualification_reason": "Applicant is not in rural jurisdiction"
            },
            {
                "field": "is_shg_member",
                "operator": "is_true",
                "value": True,
                "description": "Must be an active member of a Self-Help Group (SHG)",
                "disqualification_reason": "Applicant is not an active member of a Self-Help Group (SHG)"
            }
        ]
    },
    {
        "id": "aicte-pragati-scholarship",
        "name": "AICTE Pragati Scholarship for Girl Students",
        "name_hi": "एआईसीटीई प्रगति छात्रवृत्ति (छात्राएं)",
        "ministry": "Ministry of Education",
        "description": "Scholarship to girl students admitted to technical degree or diploma courses in AICTE approved institutions.",
        "benefits": "₹50,000 per annum for every year of technical study",
        "official_url": "https://www.aicte-india.org",
        "category_tags": ["student", "women", "technical education", "engineering", "scholarship"],
        "documents_required": ["College Admission Letter", "10th/12th Marksheet", "Family Income Certificate", "Aadhaar Card"],
        "is_active": True,
        "criteria": [
            {
                "field": "gender",
                "operator": "eq",
                "value": "female",
                "description": "Applicant must be a female student",
                "disqualification_reason": "Pragati scholarship is exclusively for female students"
            },
            {
                "field": "occupation",
                "operator": "eq",
                "value": "student",
                "description": "Applicant must be an enrolled student",
                "disqualification_reason": "Applicant is not enrolled as a student"
            },
            {
                "field": "education_level",
                "operator": "in",
                "value": ["diploma", "technical_degree"],
                "description": "Applicant must be enrolled in a technical degree or diploma course",
                "disqualification_reason": "Applicant is not enrolled in a recognized technical degree or diploma course"
            },
            {
                "field": "annual_income",
                "operator": "lte",
                "value": 800000,
                "description": "Family income must not exceed ₹8,00,000 per annum",
                "disqualification_reason": "Family annual income exceeds ₹8 Lakh limit"
            }
        ]
    },
    {
        "id": "sukanya-samriddhi",
        "name": "Sukanya Samriddhi Yojana (SSY)",
        "name_hi": "सुकन्या समृद्धि योजना",
        "ministry": "Ministry of Finance",
        "description": "Government-backed savings scheme targeted at parents of girl children to build a fund for future education and marriage.",
        "benefits": "Highest sovereign-backed interest rate (8.2%+), full tax exemption under 80C, guaranteed corpus",
        "official_url": "https://www.indiapost.gov.in",
        "category_tags": ["girl child", "savings", "investment", "education", "women"],
        "documents_required": ["Birth Certificate of Girl Child", "Aadhaar Card of Parent/Guardian", "Address Proof"],
        "is_active": True,
        "criteria": [
            {
                "field": "gender",
                "operator": "eq",
                "value": "female",
                "description": "Beneficiary must be a female / girl child",
                "disqualification_reason": "Sukanya Samriddhi is exclusively for female children"
            },
            {
                "field": "age",
                "operator": "lte",
                "value": 10,
                "description": "Account must be opened before girl child turns 10 years old",
                "disqualification_reason": "Age exceeds 10 years maximum opening age"
            }
        ]
    },
    {
        "id": "pm-kusum",
        "name": "PM KUSUM Solar Pump Scheme",
        "name_hi": "प्रधानमंत्री कुसुम योजना",
        "ministry": "Ministry of New and Renewable Energy",
        "description": "Financial subsidy to farmers for installing standalone solar agriculture pumps and solarizing grid-connected agriculture pumps.",
        "benefits": "Up to 60% subsidy on solar agriculture pumps + 30% bank loan (farmer pays only 10%)",
        "official_url": "https://pmkusum.mnre.gov.in",
        "category_tags": ["farmer", "solar", "irrigation", "agriculture"],
        "documents_required": ["Aadhaar Card", "Land Ownership Record (7/12 / Khasra)", "Bank Account"],
        "is_active": True,
        "criteria": [
            {
                "field": "occupation",
                "operator": "eq",
                "value": "farmer",
                "description": "Applicant must be an agricultural cultivator/farmer",
                "disqualification_reason": "Applicant occupation is not farmer"
            },
            {
                "field": "land_holding_acres",
                "operator": "gte",
                "value": 0.5,
                "description": "Applicant must hold at least 0.5 acre of cultivable agricultural land",
                "disqualification_reason": "Applicant holds less than 0.5 acre of land"
            }
        ]
    },
    {
        "id": "pm-matsya-sampada",
        "name": "Pradhan Mantri Matsya Sampada Yojana (PMMSY)",
        "name_hi": "प्रधानमंत्री मत्स्य संपदा योजना",
        "ministry": "Ministry of Fisheries, Animal Husbandry and Dairying",
        "description": "Focused development of fisheries sector with financial subsidies for aquaculture, boats, ponds, and cold chains.",
        "benefits": "40% to 60% capital subsidy on fisheries infrastructure and equipment",
        "official_url": "https://pmmsy.dof.gov.in",
        "category_tags": ["fisheries", "farmer", "aquaculture", "self employed"],
        "documents_required": ["Aadhaar Card", "Land / Water Body Lease or Ownership Proof", "Bank Account Details"],
        "is_active": True,
        "criteria": [
            {
                "field": "works_in_fisheries",
                "operator": "is_true",
                "value": True,
                "description": "Applicant must be actively engaged in fisheries or aquaculture",
                "disqualification_reason": "Applicant does not work in fisheries or aquaculture"
            }
        ]
    },
    {
        "id": "naps-apprenticeship",
        "name": "National Apprenticeship Promotion Scheme (NAPS)",
        "name_hi": "राष्ट्रीय शिक्षुता संवर्धन योजना",
        "ministry": "Ministry of Skill Development and Entrepreneurship",
        "description": "Promotes apprenticeship training by sharing stipend with employers and providing industrial skill training.",
        "benefits": "Monthly stipend support (25% up to ₹1,500/month by Govt) + on-the-job industrial certification",
        "official_url": "https://www.apprenticeshipindia.gov.in",
        "category_tags": ["skill development", "student", "youth", "apprentice", "jobs"],
        "documents_required": ["Aadhaar Card", "Educational Marksheet (10th/12th/ITI/Diploma)", "Bank Passbook"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 14,
                "description": "Applicant must be at least 14 years old",
                "disqualification_reason": "Minimum apprentice age is 14 years"
            },
            {
                "field": "occupation",
                "operator": "in",
                "value": ["student", "unemployed"],
                "description": "Applicant must be a student or job-seeker looking for apprenticeships",
                "disqualification_reason": "Applicant occupation is not eligible for apprenticeship training"
            }
        ]
    },
    {
        "id": "pm-egp-employment",
        "name": "Prime Minister's Employment Generation Programme (PMEGP)",
        "name_hi": "प्रधानमंत्री रोजगार सृजन कार्यक्रम",
        "ministry": "Ministry of Micro, Small and Medium Enterprises",
        "description": "Credit-linked subsidy programme to generate self-employment opportunities through micro-enterprise establishment in rural and urban areas.",
        "benefits": "15% to 35% government capital subsidy on project cost up to ₹50 Lakh (manufacturing) or ₹20 Lakh (service)",
        "official_url": "https://www.kviconline.gov.in",
        "category_tags": ["business loan", "subsidy", "entrepreneur", "self employed"],
        "documents_required": ["Aadhaar Card", "Educational Certificate (8th pass minimum for large projects)", "Detailed Project Report (DPR)", "Caste/Special Category Certificate if applicable"],
        "is_active": True,
        "criteria": [
            {
                "field": "age",
                "operator": "gte",
                "value": 18,
                "description": "Applicant must be at least 18 years old",
                "disqualification_reason": "Applicant is under 18 years"
            },
            {
                "field": "occupation",
                "operator": "in",
                "value": ["self_employed", "unemployed"],
                "description": "Applicant must be establishing a new micro-venture",
                "disqualification_reason": "Applicant is not launching an eligible new enterprise"
            }
        ]
    }
]


def dump_all_schemes():
    """Writes all schemes into individual JSON files in knowledge/schemes."""
    SCHEMES_DIR.mkdir(parents=True, exist_ok=True)
    for s_dict in SCHEMES_DATA:
        file_path = SCHEMES_DIR / f"{s_dict['id']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(s_dict, f, indent=2, ensure_ascii=False)
    print(f"Dumped {len(SCHEMES_DATA)} schemes to {SCHEMES_DIR}")


if __name__ == "__main__":
    dump_all_schemes()
