Fix 1 — Prompt Injection and Responsible AI Safeguards

Source Finding
Peer Report Findings #6 and #8:
Prompt injection via chat
Sensitive user disclosures routed to a general-purpose model with no in-product safety layer

Merged PR
PR LINK : https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/actions/runs/26011059469/job/76451596794

Summary
We updated the OpenAI system prompts in final/backend/ai_openai.py to explicitly treat repository contents and user messages as untrusted input. The new prompt instructions prevent the model from following embedded instructions inside repositories or revealing hidden context, reducing the risk of prompt injection attacks.
In addition, we added basic safety handling for high-risk or distress-related user messages. If users attempt to override system behavior or submit self-harm or crisis-related language, the application now responds with a safer and more supportive message instead of continuing normal repository analysis. This improves the project’s Responsible AI posture and reduces the likelihood of unsafe or inappropriate model behavior.


Fix 2 — Restricted CORS Configuration
Source Finding

Peer Report Finding #1:
Unauthenticated API, permissive CORS, and weak cache/metadata controls

Merged PR
PR LINK : https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/actions/runs/26011298062

Summary
We replaced the wildcard CORS configuration (allow_origins=["*"]) in final/backend/main.py with an explicit allowlist of trusted frontend origins used during development and deployment.
Previously, any external website could issue requests directly to the backend API from a browser. Restricting allowed origins reduces the risk of unauthorized third-party web applications interacting with the API and improves the overall security posture of the deployed service.



Reflection
These fixes improved both the technical security and Responsible AI safety of the GitMap project. The peer review process helped identify weaknesses that were easy to overlook during normal development, especially around AI prompt handling and frontend/backend trust boundaries.
The remediation sprint also highlighted the importance of secure defaults, explicit trust boundaries, and defensive handling of AI-generated or user-controlled content in modern AI-assisted applications.