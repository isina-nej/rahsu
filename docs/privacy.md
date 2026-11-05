# Research data privacy and deletion

Only authenticated users who deliberately opt into `save_history=true` have their origin/destination and model outputs stored. Anonymous estimates are not persisted. Observed fuel data requires separate explicit consent.

An authenticated participant may delete all their research route and observation records via:
```
DELETE /api/v1/me/study-data/
{"confirmation":"DELETE_MY_STUDY_DATA"}
```
This endpoint requires a valid session and CSRF token and deletes observations before route predictions/requests within one database transaction.

**Limitations:** this does not delete the account, OSM-derived shared obstacle records, preexisting operational logs or offline backups. Production policy must specify backup retention, consent revocation, operator contacts, and rules for eventual data expiry.
