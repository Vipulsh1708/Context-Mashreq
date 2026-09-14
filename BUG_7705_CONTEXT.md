# Bug 7705 — Workflow Execution Context

**Ticket ID:** 7705  
**Title:** [Altair] [Tada] Components remain Queued and outputs are unavailable after workflow completion  
**Priority:** 2 (High)  
**Severity:** 3 (Medium)  
**Status:** New  
**Environment:** UAT  
**Assigned to:** Vipul Sharma, EC  

---

## Ticket Metadata

| Field | Value |
|-------|-------|
| Bug ID | 7705 |
| Title | [Altair] [Tada] Components remain Queued and outputs are unavailable after workflow completion |
| Assigned to | Vipul Sharma, EC |
| Priority | 2 (High) |
| Severity | 3 (Medium) |
| State | New |
| Reason | New |
| Area | AI-COE-Board\AICOE TADA Studio |
| Iteration | AI-COE-Board\AICOE TADA Studio |
| Comments | 4 |
| Created by | Vipul Sharma, EC |

---

## Overview

We are investigating a bug related to workflow execution in TADA Studio. The investigation has identified **two related but distinct issues**. They may have a common underlying scalability/performance cause, but they should not be treated as the same bug.

---

## Issue 1 — Workflow Completed but Some Nodes Remain Queued/Running

### Description

* A large/complex workflow is executed.
* The overall workflow eventually shows **Completed**.
* However, when viewing the workflow at the node/component level, some nodes still show **Queued** or **Running**.
* The execution itself can still be opened and inspected.
* The problem is that the **node-level execution state is inconsistent with the overall workflow state**.

### In Short

> The execution is accessible, but some individual nodes have stale/incorrect execution statuses after the workflow has completed.

### Detailed Reproduction Steps (from Ticket)

1. Open TADA Studio in the UAT environment
2. Execute the workflow
3. Wait until the overall workflow displays Completed
4. Open the completed workflow execution in Graph view
5. Review the status of the individual component nodes
6. Select a component that remains in the Queued state
7. Attempt to review the node execution data, logs, and output
8. Observe the message displayed by TADA Studio
9. Repeat the check for other component nodes in the same execution

### Affected Components (QA Reproduction)

* Customer data extraction agent
* End 1

### Example Workflow

* **Workflow Name:** WF-Email-Triage-v7.8
* **Status:** 98% success (702 Completed, 12 Failed)
* **Overall Status:** Completed ✓
* **Issue:** Some component nodes still Queued ✗

---

## Issue 2 — Execution Not Found for Very Large Workflows

### Description

* A very large workflow, particularly one with around **1000+ nodes**, is executed.
* The execution appears in the **Execution History**.
* However, when the user later clicks/opens that execution, the execution details/graph fail to load.
* The UI may show **"Execution Not Found"** even though the execution is visible in the execution list.
* Very large workflows can also cause the UI/UET to become slow, stuck, or unstable, with errors such as **502 Bad Gateway**.
* The issue is therefore related to **retrieving/loading the execution data**, rather than an incorrect node status.

### In Short

> The execution exists in history, but for very large workflows it cannot be opened/retrieved and may show "Execution Not Found."

### Error Message

```
Unable to load node execution data
Node execution not found
```

### Typical Scenarios

* User executes 1000+ node workflow
* Execution completes and appears in history
* User clicks to open the execution
* UI fails to load: "Execution Not Found"
* OR UI becomes slow/stuck with 502 Bad Gateway error

---

## Key Difference

The easiest way to distinguish the two:

### Issue 1

> "I can open the execution, but some nodes incorrectly remain Queued/Running even though the workflow is Completed."

**State Problem** — execution is available, node states are wrong

### Issue 2

> "I can see the execution in history, but I cannot open it; it shows Execution Not Found."

**Retrieval Problem** — execution cannot be opened at all

---

## Comparison Table

|                              | Issue 1                           | Issue 2                              |
| ---------------------------- | --------------------------------- | ------------------------------------ |
| Workflow executes            | Yes                               | Yes                                  |
| Execution appears in history | Yes                               | Yes                                  |
| Execution can be opened      | **Yes**                           | **No**                               |
| Main problem                 | Incorrect node status             | Execution cannot be retrieved/opened |
| Typical scale                | Large/complex workflows           | Particularly 1000+ node workflows    |
| Error                        | Queued/Running state remains      | "Execution Not Found"                |
| Possible common cause        | Scalability/state synchronization | Scalability/execution-data retrieval |

---

## Investigation Approach

### Do NOT assume these are the same bug

Both issues occur with large workflows, but they represent **different failure points**:

1. **Execution state synchronization problem** — execution is available, but node states are incorrect.
2. **Execution retrieval/loading problem** — execution is listed, but its details cannot be opened.

### Investigation Strategy

The investigation should:

1. **Reproduce Issue 1 separately** — verify node status inconsistency
2. **Reproduce Issue 2 separately** — verify execution retrieval failure
3. **Debug state synchronization** — where are node states tracked?
4. **Debug execution retrieval** — where does "Execution Not Found" come from?
5. **Identify root causes** — are they related or separate?
6. **Test both scenarios** — ensure fixes address the actual problems

---

## Files to Investigate

* Workflow orchestration/scheduler service
* Component state management
* Execution data retrieval service
* Node execution status tracking
* Workflow completion logic

---

## Reproduction Workflow Details

### Execution Statistics (from Workflow Execution View)

| Field | Value |
|-------|-------|
| Workflow Name | WF-Email-Triage-v7.8 (Copyconnected with UI) |
| Workflow Version | v7.8 |
| Total Nodes | 714 |
| Success Rate | 98% |
| Completed | 702 ✓ |
| Failed | 12 ✗ |
| Duration | 49m 13s |
| Overall Status | **Completed** |
| Environment | UAT |
| Execution ID | 0c370d29-c444-4d77-b4db-e9dc0c7b4e86 |

### Affected Nodes

| Component | Status | Issue |
|-----------|--------|-------|
| Customer data extraction agent | Queued | Unable to load node execution data |
| End 1 | Queued | Node execution not found |

### Error Messages Displayed

When attempting to review node execution data:
```
Unable to load node execution data
Node execution not found
```

Modal popup shows error icon (⚠️) with red circle indicating failed data retrieval.

---

## QA Validation & Reproduction

**QA Lead:** Vasudev Singh, EC  
**Validated by:** Lakshay Kumar Gudral, EC  
**Reproduced by:** Lakshay Kumar Gudral, EC (47 minutes ago)  
**Status:** ✓ Successfully reproduced during QA validation

### QA Observations

During QA validation in UAT, the reported issue was **successfully reproduced**:

* There are **2 nodes that remain in Queued state** and do not proceed to successful execution
* When attempting to open these nodes to review execution details:
  - Error message: "Unable to load node execution data"
  - Secondary error: "Node execution not found"
* The workflow overall shows as "Completed" but final output is unavailable
* User cannot retrieve or review execution data for queued nodes

---

## Comments from Team

### Lakshay Kumar Gudral, EC (47m ago)

> The reported issue has been successfully reproduced during QA validation:
> 
> There are 2 nodes that remain in Queued state and do not proceed to successful execution:
> * Customer data extraction agent
> * End 1

### Ghazanfar Ali, EC (Monday)

> The overall TADA Studio workflow is marked Completed, but many component nodes remain in the Queued state. Opening the affected nodes displays "Unable to load node execution data" and "Node execution not found," and the final workflow output is unavailable.
> 
> **The parent workflow should not report completion until all required component executions reach a valid terminal state.**

---

## UI/UX Observations from Bug Screenshots

### Workflow Execution Graph View
* Overall workflow status shows: **Completed** (status badge)
* Execution metrics show: 98% success rate, 702 completed nodes, 12 failed nodes
* Node-level status: Multiple nodes show **Queued** state (not matching overall completion status)
* Graph displays node execution flow with color-coded status indicators

### Node Execution Modal (Error State)
When user clicks on a queued component node:
* Modal title shows node name (e.g., "Customer Data Extraction Agent", "End 1")
* Modal displays error icon (red circle with exclamation mark)
* Error message: "Unable to load node execution data"
* Secondary text: "Node execution not found"
* No execution data, logs, or output available in the modal
* User cannot proceed to view or debug the node's execution

### Workflow Completion Inconsistency
* Overall workflow status: **Completed** ✓
* Individual node statuses: Some remain **Queued** ✗
* Final workflow output: Unavailable (blocked due to incomplete node executions)
* User expectation: Completed workflow should have all nodes in a terminal state

---

## Summary of Fixes Needed

### Fix 1: Workflow Completion State

The workflow should **NOT** be marked as "Completed" until **ALL** component nodes reach a valid terminal state (Completed, Failed, or Skipped).

### Fix 2: Node Execution Retrieval

Nodes in Queued state should either:
* Allow proper display of their "Queued" status (without "not found" error), OR
* Prevent clicking on queued nodes until they have execution data

### Fix 3: Workflow Output Availability

The workflow's final output should be **blocked/unavailable** until all components reach terminal states. Do not allow users to access partial/incomplete results.

---

**Last Updated:** 2026-09-10  
**Context Created For:** Vipul Sharma, EC (AI Engineer - Tada Studio)
