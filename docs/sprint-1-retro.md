Celebrate/Went well:
Sally got the Render to load with help from Jesse’s first attempts
Daniela tested the final CI pipeline and was able to skip tests
Daniela was able to combine the two prototypes into another version
Jesse consistently reported our progress and created relevant diagrams
Sally created many unit tests to consistently check prototype behavior/progress

What could be improved:
Separating the working files so there are no/less conflicts
Revamping the frontend to be as interactive as before (clickable, but appealing)
Responsibilities should be written down clearly to prevent overlapping work sections
Improve how the backend parses and structures repo files for analysis
Preparing for the workload by researching the tools being used


AI tools reflection:
Claude helped us get through the Render deployment much faster than we could have alone. It fixed the outdated requirements.txt, created app.py as one entry point for the FastAPI backend, and caught the hardcoded 127.0.0.1/api issue that was breaking production fetches. Since deployment debugging usually takes us a lot of trial and error, AI made this part feel much more manageable.
The merge conflicts were still difficult because the team was pushing to main at the same time. Cursor could clean up the structure and syntax of conflicts in app.py, requirements.txt, and test_chat.py, but it could not fully know which teammate’s version was actually correct. We still had to check the running code, so this reminded us that AI can speed up debugging, but we need to stay responsible for the final decisions.

Sprint 2 commitments:
Sally: Improve how the backend parses and structures repo files for analysis
Jesse: Responsibilities should be written down clearly to prevent overlapping work sections

For Sprint 2, the team is committing to refining both our AI responses and our internal coordination to ensure a more efficient development cycle. Sally will lead the effort to optimize how the backend parses and structures repository files, creating a better foundation for data analysis and visualization. Simultaneously, Jesse will help create a breakdown of project responsibilities to eliminate loss of roles and prevent overlapping work. With Daniela translating these goals into dedicated Kanban cards, we are ensuring that structural improvements and clear task ownership are treated as primary deliverables for the upcoming sprint.

Kanban Links:
Sally: https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/issues/24
Jesse: https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/issues/25