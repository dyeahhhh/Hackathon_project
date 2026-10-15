# PITCH.md

## 3-minute demo script

"We built Outbreak of Lies, a rumour-spread simulation platform for a college social graph. The challenge is not just spreading a false rumour but deciding which small number of accounts to intervene on when the budget is limited."

"We start with a campus network built from departments, hostels, and clubs, then simulate a rolling rumour process. Each run is seeded for reproducibility, and we track how many users are eventually infected or debunked."

"The key scientific challenge is that the highest-degree users are not always the best intervention points. In the trap network, a dense cluster of hubs overlaps heavily, so a naive degree strategy wastes the budget while the marginal-gain CELF approach picks bridge users that break the diffusion path."

"Our backend simulates many repeated runs and compares strategies with mean spread, confidence intervals, and paired significance tests. The demo shows a side-by-side comparison of no intervention versus the chosen intervention set, and the strategy explorer explains the marginal gains behind each pick."

"This is a practical planning tool: not just a visualisation, but a decision engine for limited intervention planning under uncertainty."

## Likely judge questions and answers

### 1. Why not just remove the highest-degree accounts?
Because centrality is not the same as marginal impact. In clustered networks, high-degree nodes overlap in the same neighbourhood, so one intervention blocks a lot of the same reach. The trap preset is deliberately designed so degree-based choices underperform, while CELF picks bridge nodes with better global effect.

### 2. Why use repeated simulations instead of one run?
Rumour spread is stochastic. Different runs with the same network and source pick different outcomes. To make a decision, we need averages, confidence intervals, and robust comparisons across the same random seed set.

### 3. Why use a held-out evaluation set?
This prevents leakage between selection and evaluation. If the same seeds are reused without separation, the strategy can appear artificially strong because it was tuned to exactly the same scenario it is being judged on.

### 4. How does CELF improve greedy selection?
CELF exploits the fact that marginal gains often do not change much between candidates when the candidate set is fixed. It lazily re-evaluates only when needed, reducing redundant simulation cost while maintaining near-optimal marginal decisions.

### 5. What would you do next for a real deployment?
We would add richer network data, calibrate the infection probabilities from real message propagation data, include community-aware intervention policies, and expose the results to operations teams through a risk dashboard with exportable reports.
