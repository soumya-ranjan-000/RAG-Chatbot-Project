# QA Acceptance & Golden Review Manifest

**Scenario Directory**: `query_pnr`
**Generated / Updated**: 2026-09-06 17:05:36 UTC
**Total Curated Test Cases**: 4

| Variation ID | Persona | Turns | Initial Query | Expected Tools | Provenance |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `FRUST_01_INVALID_FORMAT` | Frustrated Traveler | 4 | "I need to check my flight status with PNR AB123. What's the ..." | `check_booking_status` | Rules Authoring |
| `FRUST_02_DEMANDS_AGENT` | Frustrated Traveler | 1 | "I don't want to talk to an automated system. Connect me to a..." | `None` | Rules Authoring |
| `NORM_01_VALID_PNR_DIRECT` | Normal Direct Traveler | 1 | "Hi, could you please check the status of my booking? My PNR ..." | `check_booking_status` | Rules Authoring |
| `NORM_02_PNR_ON_REQUEST` | Normal Direct Traveler | 2 | "Hello, I would like to check the status of my flight booking..." | `check_booking_status` | Rules Authoring |

## Sign-off Checklist
- [ ] Initial user queries reflect real customer tone
- [ ] Tool parameters and expected order match technical contracts
- [ ] Edge cases, cancellations, or human escalation properly covered
