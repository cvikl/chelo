from schemas import Claim, ClaimVerdict, SatelliteDataPoint

# Mapping from claim direction to what satellite trend would verify it
DIRECTION_MATCH = {
    ("increasing", "increasing"): "verified",
    ("increasing", "decreasing"): "misleading",
    ("increasing", "stable"): "misleading",
    ("decreasing", "decreasing"): "verified",
    ("decreasing", "increasing"): "misleading",
    ("decreasing", "stable"): "misleading",
    ("stable", "stable"): "verified",
    ("stable", "increasing"): "misleading",
    ("stable", "decreasing"): "misleading",
    ("denial", "increasing"): "misleading",
    ("denial", "decreasing"): "misleading",
    ("denial", "stable"): "partially_true",
    ("exaggeration", "increasing"): "partially_true",
    ("exaggeration", "decreasing"): "partially_true",
    ("exaggeration", "stable"): "misleading",
}


def _generate_explanation(claim: Claim, satellite: SatelliteDataPoint, verdict: str) -> str:
    if verdict == "verified":
        return (
            f"The claim that {claim.type.replace('_', ' ')} is {claim.direction} "
            f"is supported by satellite data showing a {satellite.trend} trend"
            f"{f' ({satellite.change_percent:+.1f}%)' if satellite.change_percent is not None else ''}."
        )
    elif verdict == "misleading":
        return (
            f"The claim that {claim.type.replace('_', ' ')} is {claim.direction} "
            f"contradicts satellite data, which shows a {satellite.trend} trend"
            f"{f' ({satellite.change_percent:+.1f}%)' if satellite.change_percent is not None else ''}."
        )
    elif verdict == "partially_true":
        return (
            f"The claim about {claim.type.replace('_', ' ')} is partially supported. "
            f"Satellite data shows a {satellite.trend} trend"
            f"{f' ({satellite.change_percent:+.1f}%)' if satellite.change_percent is not None else ''}, "
            f"but the characterization as '{claim.direction}' is not fully accurate."
        )
    else:
        return f"Could not verify this claim against available satellite data."


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
                    claim_type=claim.type,
                    claim_direction=claim.direction,
                    satellite_trend="unknown",
                    satellite_change_percent=None,
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
                claim_type=claim.type,
                claim_direction=claim.direction,
                satellite_trend=satellite.trend,
                satellite_change_percent=satellite.change_percent,
                verdict=verdict,
                explanation=explanation,
            )
        )

    return verdicts
