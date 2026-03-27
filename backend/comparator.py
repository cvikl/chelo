from schemas import Claim, ClaimVerdict, SatelliteDataPoint

# Mapping: (claim_direction, satellite_trend) -> verdict
DIRECTION_MATCH = {
    ("increasing", "increasing"): "verified",
    ("increasing", "decreasing"): "misleading",
    ("increasing", "stable"): "warning",
    ("decreasing", "decreasing"): "verified",
    ("decreasing", "increasing"): "misleading",
    ("decreasing", "stable"): "warning",
    ("stable", "stable"): "verified",
    ("stable", "increasing"): "misleading",
    ("stable", "decreasing"): "misleading",
    ("denial", "increasing"): "misleading",
    ("denial", "decreasing"): "misleading",
    ("denial", "stable"): "warning",
    ("exaggeration", "increasing"): "warning",
    ("exaggeration", "decreasing"): "warning",
    ("exaggeration", "stable"): "misleading",
}


def _generate_explanation(claim: Claim, satellite: SatelliteDataPoint, verdict: str) -> str:
    param_label = claim.type.replace("_", " ")
    change_str = ""
    if satellite.change_percent is not None:
        change_str = f" ({satellite.change_percent:+.1f}%)"

    if verdict == "verified":
        return (
            f"Satellite data supports this claim. {param_label.capitalize()} shows a "
            f"{satellite.trend} trend{change_str}, consistent with the article's statement."
        )
    elif verdict == "misleading":
        return (
            f"This claim is contradicted by satellite data. {param_label.capitalize()} "
            f"shows a {satellite.trend} trend{change_str}, which directly contradicts "
            f"the article's claim of '{claim.direction}' {param_label}."
        )
    elif verdict == "warning":
        return (
            f"This claim is potentially misleading. While {param_label} data shows a "
            f"{satellite.trend} trend{change_str}, the article's characterization as "
            f"'{claim.direction}' oversimplifies or misframes the evidence."
        )
    else:
        return f"Insufficient satellite data available to verify this claim about {param_label}."


def compare_claims_to_data(
    claims: list[Claim],
    satellite_results: list[SatelliteDataPoint],
) -> list[ClaimVerdict]:
    # Index satellite results by parameter type
    sat_by_type: dict[str, SatelliteDataPoint] = {}
    for result in satellite_results:
        sat_by_type[result.parameter] = result

    verdicts = []
    for claim in claims:
        satellite = sat_by_type.get(claim.type)
        if satellite is None:
            verdicts.append(
                ClaimVerdict(
                    claim_id=claim.id,
                    claim_text=claim.text,
                    exact_quote=claim.exact_quote,
                    claim_type=claim.type,
                    claim_direction=claim.direction,
                    severity=claim.severity,
                    satellite_trend="unknown",
                    satellite_change_percent=None,
                    satellite_data=None,
                    verdict="unverifiable",
                    explanation=f"No satellite data available for {claim.type.replace('_', ' ')}.",
                )
            )
            continue

        verdict = DIRECTION_MATCH.get(
            (claim.direction, satellite.trend), "unverifiable"
        )
        explanation = _generate_explanation(claim, satellite, verdict)

        verdicts.append(
            ClaimVerdict(
                claim_id=claim.id,
                claim_text=claim.text,
                exact_quote=claim.exact_quote,
                claim_type=claim.type,
                claim_direction=claim.direction,
                severity=claim.severity,
                satellite_trend=satellite.trend,
                satellite_change_percent=satellite.change_percent,
                satellite_data=satellite,
                verdict=verdict,
                explanation=explanation,
            )
        )

    return verdicts
