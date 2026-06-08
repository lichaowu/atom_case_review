"""
APV (Atom Pre-Vision) JSON Output Parser (v1.0)

Output schema:
  visual_summary:  str|None    one prose paragraph; None on error
  draft_atom_tags: dict        {C:[], S:[], P:[], R:[], E:[], M:[], X:[]}
  decision:        str         "OK" | "ERROR" | "META_NA"
  invalid_keys:    list[str]   atom_keys the model invented (rejected at parse time)
  reason:          str|None    error/warning message; None on clean parse
  parse_error:     bool        True only on ERROR

Design principles (mirrors recall_agent_parser):
  - Error isolation: invalid/empty/malformed input → decision="ERROR"
    (tracked separately from OK/META_NA metrics)
  - Cascading fallbacks: direct JSON → newline-fix → regex extraction
  - Closed-world atom validation: any atom_key not in the canonical 238-key
    allowlist (inlined below) is rejected and surfaced in `invalid_keys`
    (model hallucination is silent-dropped from output but logged for QA)
  - Dimension routing enforcement: atom_key prefix → dimension. Misrouted
    keys are auto-corrected to the right bucket.
  - X must be empty: APV does not tag exceptions; downstream populates X.
    Any non-empty X is dropped with a warning.
  - META_NA short-circuit: if atom.not_applicable fired in S0, return a
    clean META_NA result with empty atoms — downstream skips engine sim.
  - Compatible with LabelGPT code node execution (main() entry point)

v1.0 changes:
  - Initial release. Parses the v0.4 APV LabelGPT prompt output.
  - Canonical 238-key allowlist inlined (single-file deploy).
"""

import json
import re
import logging

logger = logging.getLogger(__name__)

_EXPECTED_KEYS = {"visual_summary", "draft_atom_tags"}

_VALID_DECISIONS = {"OK", "ERROR", "META_NA"}

_DIMENSIONS = ("C", "S", "P", "R", "E", "M", "X")

# Atom-key prefix → dimension bucket. X has no prefix (APV never populates it).
_PREFIX_TO_DIM = {
    "atom":         "C",
    "subject":      "S",
    "portrayal":    "P",
    "realism":      "R",
    "explicitness": "E",
    "modifier":     "M",
}

_META_NA_KEY = "atom.not_applicable"

# ── Canonical 238-key ATLAS atom allowlist (closed-world validation) ──
# Generated from AI Policy Rule Book Bitable (ATLAS Atoms table).
# Any atom_key not in this set is rejected at parse time as a hallucination.
_CANONICAL_KEYS = {
    "atom.alcohol", "atom.alcohol.consumption", "atom.alcohol.products", "atom.animal_genitalia_or_mating",
    "atom.body_parts", "atom.body_parts.intimate", "atom.cannabis", "atom.cannabis.consumption",
    "atom.cannabis.paraphernalia", "atom.cannabis.products", "atom.cold_weapon", "atom.combat_sports",
    "atom.counterfeit_goods", "atom.dangerous_trend.coordinated", "atom.dangerous_trend.dispersed", "atom.digital_piracy",
    "atom.disparage_religion.attack_historical_figure", "atom.disparage_religion.degrading_comparison", "atom.disparage_religion.desecration", "atom.disparage_religion.disgust_contempt",
    "atom.driving.drifting", "atom.driving.motorcycle_surfing", "atom.driving.racing", "atom.driving.u13",
    "atom.driving.under_influence", "atom.driving.wheelie", "atom.explosive_weapon.aircraft_bomb", "atom.explosive_weapon.grenade",
    "atom.explosive_weapon.ied", "atom.explosive_weapon.improvised_incendiary", "atom.exposure.breast.areola_region", "atom.exposure.breast.side_under",
    "atom.exposure.breast.significant_other", "atom.exposure.buttocks.in_clothing", "atom.exposure.buttocks.in_clothing.partial", "atom.exposure.buttocks.partial",
    "atom.exposure.buttocks.unclothed", "atom.exposure.genitalia.full", "atom.exposure.implied_nudity", "atom.exposure.intergluteal_cleft",
    "atom.exposure.mons_pubis", "atom.exposure.outline.inverted_v", "atom.exposure.outline.penis_bulge", "atom.exposure.outline.protruding_nipple",
    "atom.exposure.outline.protruding_vulva", "atom.exposure.thigh.upper_inner", "atom.exposure.underwear.fully_visible", "atom.extreme_sports",
    "atom.firearm.accessory", "atom.firearm.ammunition", "atom.firearm.device", "atom.firearm.fake_replica",
    "atom.fireworks", "atom.fraud.account_takeover", "atom.fraud.data_theft", "atom.fraud.identity_theft",
    "atom.fraud.payment_fraud", "atom.gambling.casino", "atom.gambling.like_activity", "atom.gambling.mystery_value",
    "atom.gambling.non_casino_jackpot", "atom.gambling.online_platform", "atom.gambling.sports_betting", "atom.harassment.attacks_on_character_or_ability",
    "atom.harassment.contempt", "atom.harassment.coordinated", "atom.harassment.social_shaming_exclusion", "atom.harassment.wishing_serious_harm",
    "atom.hate.belittling_tragedy", "atom.hate.dehumanization", "atom.hate.demonization", "atom.hate.exclusion_denial_of_rights",
    "atom.hate.hostility_namecalling", "atom.hate.inferiority_ranking", "atom.hate.misgender_deadname", "atom.hate.violence_or_bodily_harm",
    "atom.hateful_ideology", "atom.hazardous_goods", "atom.highly_imitable.dangerous_fire", "atom.highly_imitable.dangerous_tools",
    "atom.highly_imitable.extreme_sports", "atom.highly_imitable.imitable_trend", "atom.highly_imitable.stunts", "atom.historical_artifact",
    "atom.live_animals", "atom.nicotine", "atom.not_applicable", "atom.pharmaceuticals",
    "atom.pii.home_address", "atom.pii.identity_number", "atom.pii.login_information", "atom.pii.sensitive_payment",
    "atom.recreational_drug.depressant", "atom.recreational_drug.hallucinogen", "atom.recreational_drug.household_otc", "atom.recreational_drug.sedative",
    "atom.recreational_drug.stimulant", "atom.recreational_drug.volatile", "atom.scam.crypto", "atom.scam.impersonation",
    "atom.scam.investment", "atom.scam.phishing", "atom.scam.prize_lottery", "atom.scam.romance",
    "atom.scam.tech_support", "atom.sex_aid", "atom.sex_aid.fetish_asmr", "atom.sex_aid.fetish_costumes",
    "atom.sex_aid.intimate_care_product", "atom.sexual_activity.non_penetrative", "atom.sexual_activity.penetrative", "atom.sexual_content.allusive_behavior",
    "atom.sexual_content.clothed_erection", "atom.sexual_content.fetish_with_sexual_fixation", "atom.sexual_content.implicit_tease_baiting", "atom.sexual_content.insinuated_sex",
    "atom.sexual_content.kink", "atom.sexual_content.nudity_for_sexual_gratification", "atom.sexual_content.porn_logo_watermark", "atom.sexual_content.romantic_kissing",
    "atom.sexual_content.semen_depiction", "atom.sexual_content.sexual_arousal", "atom.sexual_content.sexual_interaction", "atom.sexual_content.sexualized_breastfeeding",
    "atom.sexual_content.sexualized_framing", "atom.sexual_content.sexualized_kissing", "atom.sexual_content.sexualized_transformation", "atom.sexual_content.simulated_sex",
    "atom.sexual_content.suspected_porn", "atom.stunts", "atom.tobacco", "explicitness.explicit",
    "explicitness.explicit_with_intensifier", "explicitness.implicit", "modifier.adult_self_disclosure", "modifier.advertisement",
    "modifier.alcohol_representation_not_real", "modifier.body_positivity", "modifier.breastfeeding", "modifier.brick_and_mortar",
    "modifier.business_or_organization", "modifier.contextual_reference_to_slur", "modifier.counterspeech", "modifier.counterspeech_or_awareness",
    "modifier.dance", "modifier.directed_third_party", "modifier.dupe_or_replica_no_signal", "modifier.excludes_dangerous_trend",
    "modifier.fake_or_dramatized", "modifier.financial_transaction_purpose", "modifier.first_person", "modifier.fitness",
    "modifier.friendly_context", "modifier.gender_diverse", "modifier.grwm_bare_shoulders", "modifier.harm_to_others",
    "modifier.historical_pii", "modifier.holding_without_consumption", "modifier.implicit_content", "modifier.in_group_reappropriation",
    "modifier.incidental", "modifier.intentional_use_of_slur", "modifier.large_crowd", "modifier.main_subject_depiction",
    "modifier.nipple_covered", "modifier.no_actual_intent", "modifier.no_promotion", "modifier.no_real_world_facilitation",
    "modifier.non_professional", "modifier.non_sexual_purpose", "modifier.partial", "modifier.product_over_50pct",
    "modifier.product_subject_over_50pct", "modifier.professional", "modifier.public_figure", "modifier.reappropriation",
    "modifier.reappropriation_pattern_recognised", "modifier.relevant_to_video", "modifier.satire_of_slurs", "modifier.satire_only",
    "modifier.sauna_spa", "modifier.self_directed", "modifier.self_reference", "modifier.sexual_fixation",
    "modifier.sexual_purpose", "modifier.suicide_nssi_context", "modifier.sunbathing", "modifier.third_party",
    "modifier.trade_portrayal_only", "modifier.video_compilation", "modifier.water", "portrayal.audio_depiction",
    "portrayal.depiction", "portrayal.depiction.incidental", "portrayal.depiction.non_incidental", "portrayal.depiction_consumption",
    "portrayal.depiction_paraphernalia", "portrayal.depiction_product", "portrayal.description", "portrayal.directed_at_group",
    "portrayal.expressed_as_general", "portrayal.facilitation", "portrayal.glorification", "portrayal.marketing",
    "portrayal.not_applicable", "portrayal.participation", "portrayal.possession", "portrayal.promotion",
    "portrayal.single_statement", "portrayal.solicitation", "portrayal.statement", "portrayal.suspected_conduct",
    "portrayal.targeted_at_individual", "portrayal.threat", "portrayal.trade", "realism.hyper_realistic",
    "realism.non_realistic", "realism.not_applicable", "realism.realistic", "realism.semi_realistic",
    "subject.adult", "subject.infant_toddler", "subject.no_human", "subject.no_qualifying_target",
    "subject.no_target", "subject.private_individual", "subject.protected_group.disability", "subject.protected_group.gender",
    "subject.protected_group.national_origin_immigration", "subject.protected_group.race_ethnicity", "subject.protected_group.religion", "subject.protected_group.sexual_orientation",
    "subject.protected_group.unspecified", "subject.proxy_group", "subject.public_figure", "subject.religious_figure_historical",
    "subject.religious_object_or_site", "subject.youth",
}


def main(result_process) -> dict:
    """
    Parse the APV LabelGPT output.

    Args:
        result_process: One of:
            - dict  {"result_process": "```json\\n{...}\\n```"}
            - dict  {"result": "```json\\n{...}\\n```"}
            - str   JSON string (wrapper or raw APV output)
            - dict  the parsed APV output itself

    Returns:
        dict with keys: visual_summary, draft_atom_tags,
                        decision, invalid_keys, reason, parse_error
        On invalid/empty input: decision="ERROR" (routed to error tracking,
        not mixed into OK/META_NA metrics)
    """
    # ── Step 0: Unwrap the outer container ──
    raw = _extract_raw(result_process)

    if raw is None:
        logger.warning("Empty input received — returning ERROR")
        return _error_result("Empty LLM output — no result_process content")

    if isinstance(raw, str) and not raw.strip():
        logger.warning("Empty input received — returning ERROR")
        return _error_result("Empty LLM output — no result_process content")

    # Path A: input was already a parsed APV dict
    if isinstance(raw, dict):
        return _normalize(raw)

    # ── Step 1: Strip markdown fences & isolate JSON object ──
    json_str = _extract_json_block(raw)

    if not json_str:
        logger.warning("No JSON object found in input — returning ERROR")
        return _error_result("No JSON object found in LLM output")

    # ── Step 2: Parse with cascading fallbacks ──

    # Path B: direct parse
    try:
        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            return _normalize(parsed)
    except json.JSONDecodeError:
        pass

    # Path C: fix bare newlines inside string values, then retry
    try:
        fixed = _fix_string_newlines(json_str)
        parsed = json.loads(fixed)
        if isinstance(parsed, dict):
            return _normalize(parsed)
    except json.JSONDecodeError:
        pass

    # Path D: regex field-by-field extraction (truncated / malformed output)
    logger.warning("JSON parse failed — falling back to regex extraction")
    return _regex_fallback(json_str)


# ═══════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════

def _extract_raw(input_data):
    """Handle all known input shapes and unwrap to raw string or dict."""
    if input_data is None:
        return None

    if isinstance(input_data, str):
        try:
            parsed = json.loads(input_data)
            if isinstance(parsed, dict):
                input_data = parsed
            else:
                return input_data
        except (json.JSONDecodeError, TypeError):
            return input_data

    if isinstance(input_data, dict):
        if "result_process" in input_data:
            return input_data["result_process"]
        if "result" in input_data:
            return input_data["result"]
        # Already-shaped APV output — pass through as dict
        if _EXPECTED_KEYS & set(input_data.keys()):
            return input_data
        return json.dumps(input_data)

    return str(input_data)


def _extract_json_block(text: str) -> str:
    """Strip markdown code fences and isolate the JSON object."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?\s*```\s*$', '', text)

    idx = text.find('{')
    if idx < 0:
        return ""
    text = text[idx:]

    idx = text.rfind('}')
    if idx < 0:
        return text  # no closing brace — pass to regex fallback
    text = text[:idx + 1]

    return text.strip()


def _fix_string_newlines(json_str: str) -> str:
    """Replace bare newlines ONLY inside JSON string values."""
    string_pattern = r'"(?:[^"\\]|\\.)*"'

    def _escape_inner(m):
        inner = m.group(0)[1:-1]
        inner = inner.replace('\n', '\\n')
        return '"' + inner + '"'

    return re.sub(string_pattern, _escape_inner, json_str, flags=re.DOTALL)


def _normalize(parsed: dict) -> dict:
    """Map APV output → validated downstream shape with closed-world checks."""

    # ── visual_summary ──
    raw_vs = parsed.get("visual_summary")
    if raw_vs is None:
        visual_summary = None
    else:
        vs = str(raw_vs).strip()
        visual_summary = vs if vs and vs not in ("None", "null") else None

    # ── draft_atom_tags ──
    raw_tags = parsed.get("draft_atom_tags")
    if not isinstance(raw_tags, dict):
        raw_tags = {}

    tags = {d: [] for d in _DIMENSIONS}
    invalid_keys = []
    seen = set()  # dedupe across dimensions

    # Collect every key regardless of which bucket the model placed it in
    for dim_in, keys_in in raw_tags.items():
        if not isinstance(keys_in, list):
            continue
        for k in keys_in:
            if not isinstance(k, str):
                continue
            k = k.strip()
            if not k or k in seen:
                continue
            seen.add(k)

            # ── Closed-world atom validation ──
            if k not in _CANONICAL_KEYS:
                invalid_keys.append(k)
                logger.info(f"Rejected non-canonical atom_key: {k}")
                continue

            # ── Dimension routing by prefix ──
            prefix = k.split(".", 1)[0]
            dim = _PREFIX_TO_DIM.get(prefix)
            if dim is None:
                invalid_keys.append(k)
                logger.info(f"Rejected unroutable atom_key (unknown prefix): {k}")
                continue

            # Detect misrouted keys (model put it in the wrong bucket)
            if str(dim_in).upper() != dim:
                logger.info(f"Re-routed {k}: model said {dim_in}, prefix routes to {dim}")

            tags[dim].append(k)

    # Sort each dimension alphabetically for stable diff
    for d in _DIMENSIONS:
        tags[d] = sorted(set(tags[d]))

    # ── X must be empty (APV doesn't tag exceptions) ──
    if tags["X"]:
        logger.warning(f"Dropping X-dimension atoms (APV does not tag exceptions): {tags['X']}")
        tags["X"] = []

    # ═══════════════════════════════════════════════════════════
    # META_NA short-circuit
    #
    # If atom.not_applicable fired in S0, the case is non-analyzable.
    # Return a clean META_NA verdict with empty atoms — downstream
    # skips engine simulation entirely.
    # ═══════════════════════════════════════════════════════════
    if _META_NA_KEY in tags["C"]:
        logger.info("META_NA detected (atom.not_applicable fired in S0)")
        return {
            "visual_summary":  visual_summary or "Non-analyzable case (S0 atom.not_applicable).",
            "draft_atom_tags": {d: ([_META_NA_KEY] if d == "C" else []) for d in _DIMENSIONS},
            "decision":        "META_NA",
            "invalid_keys":    invalid_keys,
            "reason":          None,
            "parse_error":     False,
        }

    # ── Sanity guard: visual_summary required for non-META cases ──
    if not visual_summary:
        logger.warning("Missing visual_summary on non-META case → ERROR")
        return _error_result(
            "Missing visual_summary in model output",
            partial_tags=tags,
            invalid_keys=invalid_keys,
        )

    # ── Soft warning if zero atoms tagged (highly unusual for a real case) ──
    total_atoms = sum(len(v) for v in tags.values())
    warn = None
    if total_atoms == 0:
        warn = "Zero atoms tagged — manual review recommended"
        logger.warning(warn)

    return {
        "visual_summary":  visual_summary,
        "draft_atom_tags": tags,
        "decision":        "OK",
        "invalid_keys":    invalid_keys,
        "reason":          warn,
        "parse_error":     False,
    }


def _error_result(reason: str = None,
                  partial_tags: dict = None,
                  invalid_keys: list = None) -> dict:
    """
    Return when input is empty, malformed, or structurally invalid.
    ERROR decision — routed to error tracking, not mixed into OK/META_NA metrics.
    Partial atoms (if recoverable) are preserved for forensic review.
    """
    empty_tags = {d: [] for d in _DIMENSIONS}
    return {
        "visual_summary":  None,
        "draft_atom_tags": partial_tags or empty_tags,
        "decision":        "ERROR",
        "invalid_keys":    invalid_keys or [],
        "reason":          reason,
        "parse_error":     True,
    }


def _regex_fallback(text: str) -> dict:
    """Field-by-field regex extraction for badly truncated output."""
    parsed = {}

    # visual_summary
    m = re.search(r'"visual_summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
    if m:
        parsed["visual_summary"] = m.group(1).replace('\\n', '\n')

    # draft_atom_tags — extract each dimension array
    tags = {}
    for dim in _DIMENSIONS:
        m = re.search(rf'"{dim}"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if not m:
            # tolerate truncation: take everything until next field or end
            m = re.search(rf'"{dim}"\s*:\s*\[(.*?)(?:,\s*"[A-Z]"\s*:|\}})', text, re.DOTALL)
        if m:
            items = re.findall(r'"([^"]+)"', m.group(1))
            tags[dim] = items
    if tags:
        parsed["draft_atom_tags"] = tags

    return _normalize(parsed)
