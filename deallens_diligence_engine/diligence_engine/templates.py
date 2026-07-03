"""Diligence checklist templates by business type.

A template is an ordered list of ChecklistItemTemplate. ``general`` is the base
set; the typed templates (smb, saas, retail) extend it with type-specific items.
"""
from __future__ import annotations

from typing import Dict, List

from .models import Category, ChecklistItemTemplate as Item

# --- Base / general template -------------------------------------------------
_GENERAL: List[Item] = [
    # Financial
    Item("fin_statements", Category.FINANCIAL, "Obtain 3-5 years of financial statements", weight=2.0, critical=True),
    Item("fin_tax_returns", Category.FINANCIAL, "Cross-check tax returns against the statements", weight=2.0, critical=True),
    Item("fin_quality_earnings", Category.FINANCIAL, "Assess quality of earnings (real, recurring, sustainable)", weight=2.0, critical=True),
    Item("fin_normalize", Category.FINANCIAL, "Normalize earnings (owner perks, one-offs)", weight=1.5),
    Item("fin_ar_ap", Category.FINANCIAL, "Review AR aging, AP, and outstanding debts", weight=1.0),
    Item("fin_margins", Category.FINANCIAL, "Analyze margin trends over time", weight=1.0),
    # Commercial / market
    Item("com_market", Category.COMMERCIAL, "Assess market size and growth trend", weight=1.0),
    Item("com_competition", Category.COMMERCIAL, "Map competitive landscape and position", weight=1.0),
    Item("com_moat", Category.COMMERCIAL, "Identify barriers to entry / competitive advantages", weight=1.0),
    # Customers
    Item("cust_concentration", Category.CUSTOMERS, "Check customer concentration", weight=2.0, critical=True, concern="customer_concentration"),
    Item("cust_contracts", Category.CUSTOMERS, "Review customer contracts (terms, renewals, cancellation)", weight=1.5),
    Item("cust_retention", Category.CUSTOMERS, "Review retention / churn history", weight=1.5, concern="customer_retention"),
    # Operations
    Item("ops_processes", Category.OPERATIONS, "Understand day-to-day operations and documentation", weight=1.0),
    Item("ops_suppliers", Category.OPERATIONS, "Review key suppliers (contracts, concentration)", weight=1.5, concern="supplier_concentration"),
    Item("ops_assets", Category.OPERATIONS, "Inspect equipment/assets condition and ownership", weight=1.0),
    # People
    Item("ppl_owner_dependence", Category.PEOPLE, "Assess owner dependence", weight=2.0, critical=True, concern="owner_dependence"),
    Item("ppl_key_staff", Category.PEOPLE, "Identify key employees and retention risk", weight=1.5),
    Item("ppl_contracts", Category.PEOPLE, "Review employment contracts and comp", weight=1.0),
    # Legal
    Item("leg_structure", Category.LEGAL, "Confirm corporate structure and ownership", weight=1.0),
    Item("leg_litigation", Category.LEGAL, "Check current/pending/threatened litigation", weight=1.5, critical=True, concern="litigation"),
    Item("leg_licenses", Category.LEGAL, "Verify licenses, permits, regulatory compliance", weight=1.0),
    Item("leg_ip", Category.LEGAL, "Confirm IP ownership (trademarks, patents, domains)", weight=1.0),
    Item("leg_contracts", Category.LEGAL, "Review contracts for change-of-control clauses", weight=1.0),
    # Tax
    Item("tax_filed", Category.TAX, "Confirm all taxes filed and paid", weight=1.5, critical=True, concern="taxes"),
    Item("tax_audits", Category.TAX, "Check audits, disputes, outstanding liabilities", weight=1.0),
    # Deal
    Item("deal_reason", Category.DEAL, "Understand the real reason for selling", weight=1.0),
    Item("deal_structure", Category.DEAL, "Clarify asset vs. share purchase and what's included", weight=1.0),
    Item("deal_transition", Category.DEAL, "Agree transition/handover plan", weight=1.0),
]

# --- Type-specific add-ons ---------------------------------------------------
_SMB_EXTRA: List[Item] = [
    Item("smb_sde", Category.FINANCIAL, "Confirm Seller's Discretionary Earnings (SDE) add-backs", weight=1.5),
    Item("smb_personal_expenses", Category.FINANCIAL, "Separate personal vs. business expenses", weight=1.0),
    Item("smb_lease", Category.OPERATIONS, "Confirm premises lease is assignable", weight=1.5, critical=True, concern="lease"),
]

_SAAS_EXTRA: List[Item] = [
    Item("saas_arr", Category.FINANCIAL, "Validate ARR/MRR and recognition", weight=2.0, critical=True),
    Item("saas_churn", Category.CUSTOMERS, "Review gross/net churn and retention cohorts", weight=2.0, critical=True, concern="customer_retention"),
    Item("saas_code", Category.OPERATIONS, "Review code ownership, tech stack, and tech debt", weight=1.5),
    Item("saas_ip_assignment", Category.LEGAL, "Confirm IP assignment from all developers/contractors", weight=1.5, critical=True),
    Item("saas_security", Category.OPERATIONS, "Review data security and compliance posture", weight=1.0),
]

_RETAIL_EXTRA: List[Item] = [
    Item("ret_lease", Category.OPERATIONS, "Review lease terms, renewal, and assignability", weight=2.0, critical=True, concern="lease"),
    Item("ret_inventory", Category.OPERATIONS, "Verify inventory levels, age, and obsolescence", weight=1.5),
    Item("ret_foot_traffic", Category.COMMERCIAL, "Assess location, foot traffic, and local market", weight=1.5),
    Item("ret_equipment", Category.OPERATIONS, "Inspect fixtures and equipment condition", weight=1.0),
]

_TEMPLATES: Dict[str, List[Item]] = {
    "general": _GENERAL,
    "smb": _GENERAL + _SMB_EXTRA,
    "saas": _GENERAL + _SAAS_EXTRA,
    "retail": _GENERAL + _RETAIL_EXTRA,
}


def available_templates() -> List[str]:
    return sorted(_TEMPLATES.keys())


def get_template(business_type: str) -> List[Item]:
    key = (business_type or "general").lower()
    if key not in _TEMPLATES:
        raise ValueError(
            f"unknown business_type {business_type!r}; use one of {available_templates()}"
        )
    return _TEMPLATES[key]
