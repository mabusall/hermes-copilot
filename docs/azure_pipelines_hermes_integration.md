# Automating Code Review with Hermes Agent & Azure Pipelines

This guide outlines the architectural best practice for integrating the **Hermes Agent** as a core component of the Software Development Life Cycle (CI/CD) within an enterprise **Azure DevOps** environment.

## Architectural Concept
Instead of hosting Hermes Agent as a 24/7 server waiting for webhooks or relying on local developer machines, the agent is integrated dynamically as a Task inside **Azure Pipelines**. 

With this architecture, whenever a developer creates a Pull Request (PR), the pipeline automatically spins up a containerized Build Agent equipped with Hermes. The agent analyzes the code changes, writes professional feedback, provides an Approval/Rejection decision, and then the container is gracefully destroyed.

## Key Benefits
1. **Enhanced Security:** No need to open inbound ports or use tools like Ngrok. 
2. **Resource Efficiency:** The agent only consumes server compute resources when a PR is active (for a few minutes), rather than running continuously.
3. **Native Integration:** All review decisions, errors, and agent thought processes are natively recorded in Azure DevOps logs.

## Technical Implementation Overview

### 1. Configure Build Validation
Set up a policy in `Azure Repos -> Branch Policies` to require the successful execution of a specific pipeline (Build Validation) before any code can be merged into the `main` branch.

### 2. Conceptual `azure-pipelines.yml`
Below is a conceptual example of how to write the pipeline to work with the Docker container we previously configured (assuming this container is pushed as an Image to your company's Container Registry):

```yaml
trigger: none
pr:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  # Use the Pipeline's temporary access token instead of a personal PAT for enhanced security
  - name: AZURE_DEVOPS_EXT_PAT
    value: $(System.AccessToken) 

jobs:
- job: HermesCodeReview
  displayName: 'Hermes AI Autonomous Code Review'
  container:
    image: 'your-company-registry/hermes-sandbox-pro:latest' # The container image we prepared
    options: --user root
  steps:
  - script: |
      echo "Starting Hermes AI Review for PR $(System.PullRequest.PullRequestId)"
      
      # Issue a command for the agent to review the code autonomously without human intervention
      hermes chat -q "You are an expert Code Reviewer. Use Azure CLI to fetch PR #$(System.PullRequest.PullRequestId) in $(Build.Repository.Name). Review the changed files for security vulnerabilities and SOLID principles. Finally, leave a professional comment on the PR using az devops."
    displayName: 'Run Hermes Agent Analysis'
```

### 3. What will Hermes do autonomously during this step?
1. It receives the prompt and reads the PR ID and Project Name from the system environment variables.
2. It uses the `az devops` CLI tool (installed inside the container) to fetch the changed files (Git Diff).
3. It utilizes the underlying LLM (e.g., Gemini Pro / Flash) to analyze the code and detect bugs or improvement opportunities.
4. It uses `az devops` again to post a comment directly on the Azure DevOps PR page, and may even provide alternative Code Suggestions.

---
*This document serves as the architectural roadmap for the final production deployment. The current objective is to master the container creation locally and verify the agent's capabilities before rolling out this automation company-wide.*
