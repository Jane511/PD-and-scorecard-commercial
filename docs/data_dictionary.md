# Data Dictionary - PD-and-scorecard-commercial

| Field | Description |
| --- | --- |
| `borrower_id` | Synthetic borrower identifier. |
| `facility_id` | Synthetic facility identifier. |
| `segment` | Portfolio segment. |
| `industry` | Australian industry grouping. |
| `product_type` | Facility or product type. |
| `limit` | Approved or committed exposure limit. |
| `drawn` | Current drawn balance. |
| `pd` | Demonstration PD input. |
| `lgd` | Demonstration LGD input. |
| `ead` | Demonstration EAD input. |

## Output files

- `outputs/tables/pd_model_output.csv`
- `outputs/tables/borrower_grade_summary.csv`
- `outputs/tables/policy_decisions.csv`
- `outputs/tables/score_band_output.csv`
