---
type: community
cohesion: 0.10
members: 25
---

# FHIR Backend

**Cohesion:** 0.10 - loosely connected
**Members:** 25 nodes

## Members
- [[Constructs a FHIR reference for a Patient.]] - rationale - src/backend/fhir_setup.py
- [[Constructs a FHIR reference for a Practitioner.]] - rationale - src/backend/fhir_setup.py
- [[Constructs a FHIR reference for an Organization.]] - rationale - src/backend/fhir_setup.py
- [[Creates and configures a requests.Session with retry logic.      Args         r]] - rationale - src/backend/fhir_client.py
- [[Generates a Patient FHIR resource from a MIMIC row and associates it with a Prac]] - rationale - src/backend/fhir_setup.py
- [[Generates a Practitioner FHIR resource.      Args         first_name (str) Fir]] - rationale - src/backend/fhir_setup.py
- [[Generates an Organization FHIR resource.]] - rationale - src/backend/fhir_setup.py
- [[Organization]] - code
- [[Patient]] - code
- [[Posts a FHIR resource to the server with enhanced error handling and logging.]] - rationale - src/backend/fhir_client.py
- [[Practitioner]] - code
- [[Series]] - code
- [[Session]] - code
- [[create_fhir_session()]] - code - src/backend/fhir_client.py
- [[fhir_client.py]] - code - src/backend/fhir_client.py
- [[fhir_setup.py]] - code - src/backend/fhir_setup.py
- [[generate_organization_resource()]] - code - src/backend/fhir_setup.py
- [[generate_patient_resource()]] - code - src/backend/fhir_setup.py
- [[generate_practitioner_resource()]] - code - src/backend/fhir_setup.py
- [[get_patient_reference()]] - code - src/backend/fhir_setup.py
- [[get_performer_reference()]] - code - src/backend/fhir_setup.py
- [[get_practitioner_reference()]] - code - src/backend/fhir_setup.py
- [[log.py]] - code - src/backend/log.py
- [[post_fhir_resource()]] - code - src/backend/fhir_client.py
- [[setup_org_and_practitioner()]] - code - src/backend/fhir_setup.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/FHIR_Backend
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Module Cluster 20]]
- 4 edges to [[_COMMUNITY_Module Cluster 17]]
- 4 edges to [[_COMMUNITY_Module Cluster 26]]
- 2 edges to [[_COMMUNITY_Tool Execution]]
- 1 edge to [[_COMMUNITY_Code Mapping]]
- 1 edge to [[_COMMUNITY_FHIR Request Handlers]]
- 1 edge to [[_COMMUNITY_FHIR Implementation]]
