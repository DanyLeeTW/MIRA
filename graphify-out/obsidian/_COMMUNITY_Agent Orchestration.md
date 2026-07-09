---
type: community
cohesion: 0.11
members: 24
---

# Agent Orchestration

**Cohesion:** 0.11 - loosely connected
**Members:** 24 nodes

## Members
- [[.chat()_1]] - code - src/assistants.py
- [[.chat_completion()]] - code - src/assistants.py
- [[.initialize_message_history()_1]] - code - src/assistants.py
- [[.initialize_message_history()]] - code - src/assistants.py
- [[.should_continue()]] - code - src/assistants.py
- [[.update_patient_info()]] - code - src/assistants.py
- [[A class representing an AI assistant with various attributes and methods for int]] - rationale - src/assistants.py
- [[A class representing an AI assistant without tool use.      Attributes]] - rationale - src/assistants.py
- [[BaseModel]] - code
- [[Config]] - code - src/assistants.py
- [[Determine if the conversation should continue based on step count and completion]] - rationale - src/assistants.py
- [[Formats a conversation represented as a list of messages into a nicely formatted]] - rationale - src/assistants.py
- [[Generates a chat completion response based on the provided user input.]] - rationale - src/assistants.py
- [[MedAssistant]] - code - src/assistants.py
- [[PatientAssistant]] - code - src/assistants.py
- [[Process a new input message and generate a response.          This method adds t]] - rationale - src/assistants.py
- [[Response]] - code - src/assistants.py
- [[Run the chat method of the speaker, whether it is async or not]] - rationale - src/assistants.py
- [[Simulates a medical conversation between a physician and a patient.      This fu]] - rationale - src/conv.py
- [[Update the patient info in the patient context.]] - rationale - src/assistants.py
- [[assistants.py]] - code - src/assistants.py
- [[call_chat()]] - code - src/assistants.py
- [[format_conversation()]] - code - src/assistants.py
- [[run_simulation()]] - code - src/conv.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_Orchestration
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Module Cluster 24]]
- 5 edges to [[_COMMUNITY_Visualization Output]]
- 3 edges to [[_COMMUNITY_Module Cluster 20]]
- 3 edges to [[_COMMUNITY_Module Cluster 17]]
- 3 edges to [[_COMMUNITY_Module Cluster 26]]
- 2 edges to [[_COMMUNITY_Module Cluster 27]]

## Top bridge nodes
- [[MedAssistant]] - degree 14, connects to 2 communities
- [[assistants.py]] - degree 12, connects to 2 communities
- [[PatientAssistant]] - degree 11, connects to 2 communities
- [[.chat()_1]] - degree 5, connects to 1 community
- [[Response]] - degree 4, connects to 1 community