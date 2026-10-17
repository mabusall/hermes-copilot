---
name: copilot-router
description: Automatically evaluates task complexity and recommends or selects the best local Ollama model (DeepSeek-R1 for security/math, Qwen-32B for architecture, Qwen-14B for coding).
version: 1.0.0
author: Engineering Team
license: MIT
---

# Copilot Auto-Router Skill

## Overview
This skill connects to the lightweight 50ms `qwen2.5:0.5b` router to dynamically inspect all models currently loaded in Ollama and determine the optimal model for a given engineering task.

## When to Trigger
Invoke this skill whenever:
- The user asks: *"Which model should I use for [task]?"*
- The user says: *"Auto-route this task: [task]"* or *"Copilot pick model for [task]"*.
- The user is starting a complex feature and wants model guidance before proceeding.

## Execution Steps
1. Run the local dispatcher in recommendation mode:
   ```bash
   python3 /workspace/hermes_copilot.py --recommend "<user_task_description>"
   ```
2. The tool returns a structured JSON evaluation:
   ```json
   {
     "selected_model": "<model_name>",
     "category": "<Security & Logic / Architecture / Routine Coding>",
     "reason": "<Explanation>"
   }
   ```
3. Present the finding clearly in the chat:
   - **Category:** The classified domain of the problem.
   - **Recommended Brain:** The selected model from the local Ollama catalog.
   - **Rationale:** Why this model was chosen over the others.
4. Advise the user to switch if needed:
   - If the recommended model differs from the current active session, prompt:
     `"To switch to this model now, type: /model <selected_model>"`
