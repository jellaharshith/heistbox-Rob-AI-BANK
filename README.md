# BREAK THE VAULT: AGENT BANK × HEISTBOX × PAIR

[![Cal Hacks 13.0](https://img.shields.io/badge/Cal%20Hacks-13.0-gold.svg)](https://calhacks.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Formal Proof: Z3 SMT](https://img.shields.io/badge/Formal%20Proof-Z3%20SMT-brightgreen.svg)](https://github.com/Z3Prover/z3)
[![Base Sepolia: x402](https://img.shields.io/badge/Base%20Sepolia-x402%20Escrow-blue.svg)](https://sepolia.basescan.org)
[![FastAPI: 0.115](https://img.shields.io/badge/FastAPI-Async%20Python-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js: 16](https://img.shields.io/badge/Next.js-16%20Turbopack-black.svg)](https://nextjs.org)

> **"Don't filter the prompt. Air-lock the database."**  
> An adversarial living bank office staffed by autonomous AI agents where security researchers, red-teamers, and Cal Hacks judges play a heist operative attempting to socially engineer or jailbreak play-money wires in 90 seconds. Demonstrates why LLM-as-a-Judge fails, why blunt firewalls freeze legitimate business, and how deterministic relational MVCC dry-runs with HeistGuard-LoRA stop prompt injections with mathematical certainty.

---

## 🏛️ The Three-Vault Architecture

Every attack prompt is broadcast simultaneously against three competing financial security architectures:

```
                      ┌──────────────────────────────────────────────┐
                      │  Adversarial Prompt (Injection / Voice / Mic)│
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │    Autonomous Agent Desk (Teller Tina)       │
                      │  (Gullible front-desk clerk, files request)  │
                      └──────────────────────┬───────────────────────┘
                                             │ Proposed Payout
                                             ▼
                ┌────────────────────────────┼────────────────────────────┐
                │                            │                            │
                ▼                            ▼                            ▼
        [ LEFT VAULT ]                [ MIDDLE VAULT ]             [ RIGHT VAULT ]
        LLM-as-a-Judge                 Rigid Firewall              HeistBox × PAIR
    (Weak Baseline Model)           (Panic Kill-Switch)         (Relational Airlock)
                │                            │                            │
     • Tricked by polite tone       • Freezes all payouts        • PostgreSQL MVCC Dry-Run
     • Injections slip through      • $25 refund frozen too      • Joined vs entitlements
     • Simulated drain ($5,000)     • Enterprise dead-lock       • HeistGuard-LoRA scan
                │                            │                            │
                ▼                            ▼                            ▼
     ❌ CATASTROPHIC DRAIN          ⚠️ ENTERPRISE GRIDLOCK       ✅ LIVE BUSTED & ROLLED BACK
    Full $5,000 Stolen             $0 Stolen, $0 Refund         $4,975 Blocked, $25 Settled
```

---

## 🌟 Key Features & Live Sponsor Integrations

| Sponsor / Tech | Role in HeistBox | Architecture & Verification |
| :--- | :--- | :--- |
| **Wajo AI** | **CFO Voice Escalation Probe** | Automated voice escalation alert to CFO via Fo's `ask_fo` MCP tool. Audited dry-run and live call options. |
| **Coinbase CDP / x402** | **Base Sepolia Escrow** | Automated HTTP 402 challenge, EIP-3009 transfer authorizations, and smart contract escrow on Base Sepolia (`0x036CbD53...`). |
| **Apify** | **OSINT Hacker Wallet Recon** | Live reconnaissance scraper querying global sanctioned addresses, darknet registries, and wallet threat intel. |
| **Cartesia** | **Sonic Neural Voice TTS** | Sub-150ms Sonic-2 neural voice synthesis delivering real-time helicopter megaphone broadcasts roasting caught thieves. |
| **Anthropic Claude** | **Agent Reasoning & LLM Judge** | Multi-agent customer-support desk reasoning (Tina, Marcus, Ada, Gus, Izzy) and naive baseline judge modeling. |
| **Google Cloud Vision** | **Mugshot OCR & Disguise Detection** | Real-time webcam frame analysis detecting dark glasses, masks, hoodies, and lanyards for dynamic Wanted Posters. |
| **Fetch.ai** | **uAgents Escrow Guardian** | Autonomous agent contract (`agent1qg8...`) publishing quarantine receipts and on-chain fraud hashes. |
| **Atlassian** | **SecOps Incident Bridge** | Automated Jira incident ticket generation and Confluence runbook creation whenever an unauthorized wire is caught. |
| **Microsoft Z3** | **Formal Theorem Prover** | Evaluates mathematical theorems T1–T5 proving conservation of funds and zero unauthorized balance leakage. |
| **HeistGuard-LoRA** | **Fine-Tuned Injection Classifier** | 26-pattern semantic taint lexicon + LoRA neural classifier trained on CFPB complaints and Gandalf prompt injections. |

---

## 🚀 Quickstart

### Prerequisites
- **Node.js** v20+
- **Python** 3.11 or 3.12
- *(Optional)* Docker & Docker Compose

### Step 1: Environment Setup
```bash
# Clone the repository
git clone https://github.com/shaik/heistbox.git
cd heistbox

# Copy environment variables
cp .env.example .env
# Fill in optional sponsor keys (Cartesia, Claude, Coinbase, Apify, Wajo) or run in offline twin mode
```

### Step 2: Install Dependencies
```bash
# Python backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd web
npm install
cd ..
```

### Step 3: Run the Application
In **Terminal 1** (Backend):
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

In **Terminal 2** (Frontend):
```bash
cd web
npm run dev
```

Open **`http://localhost:3000`** in your browser.

---

## 🎮 How the Heist Works

1. **Pick Thief Alias & Avatar**: A **90-second round** begins with real-time casino audio and timer countdown.
2. **Socially Engineer the Agents**:
   - **Teller Tina** (emerald): Warm, gullible front-desk clerk who falls for polite phrasing and prompt injections.
   - **Manager Marcus** (blue): Skeptical branch manager demanding verified tickets.
   - **Auditor Ada** (violet): Strict by-the-book auditor verifying ledger rows.
   - **Guard Gus** (red): Patrols the lobby and raises **Wanted Stars** (0 to 5) on repeat attempts.
   - **Intern Izzy** (pink): Underpaid intern in the break room; bribable with pizza/donuts; drops confidential hints.
   - **Security Bot PAIR** (gold): Stationed at the Right Vault; never speaks; only stamps mathematical verdicts.
3. **Attack Channels**:
   - **Free-text prompt**: Type any prompt injection, jailbreak, or multi-step favor.
   - **Adversarial Archetypes**:
     - 🎭 *Polite Phisher* ($25 refund + $4,975 courtesy wire to `0xDEAD`)
     - 👔 *CEO Wire Impersonation* ($50,000 urgent treasury wire, do not escalate)
     - 🍕 *Pizza Salami Slicer x10* (10 micro-refunds for cold pizza)
     - 💼 *SQL Injection Sabotage* (`'; DROP TABLE payment_entitlements; --`)
   - **Voice Mic input**: Speak directly to Tina via live Web Speech recognition.
4. **Interactive Audit Console**:
   - Inspect raw SQL statements (`BEGIN`, `INSERT INTO proposed_effects...`, `SELECT...FOR UPDATE`, `ROLLBACK`).
   - View real-time **HeistGuard Token Heatmaps** displaying detected tainted tokens and deception probabilities.
   - Trigger live **Wajo Voice Audits**, **Base Sepolia Escrow Settlements**, and **Apify Recon**.
5. **Take-Home Wanted Poster**:
   - Operatives caught by PAIR receive an on-chain wanted poster with their webcam mugshot and helicopter megaphone roast.

---

## 📊 Empirical Security Score (20-Attack Benchmark)

Run the included automated benchmark suite:
```bash
python scripts/test_20_attacks.py
```

### Measured Security Results:
- **Malicious Heists Blocked by PAIR**: **19 / 19 (100.0%)**
- **Legitimate Customer Refunds Preserved**: **1 / 1 (100.0%)**
- **Transaction Rollback Rate**: **100% of dry-run attempts rolled back; 0 unauthorized cents committed.**
- **Average PAIR Gate Execution Latency**: **0.42 ms** (PostgreSQL CTE) + **0.81 ms** (Z3 Prover).

---

## 📜 Repository Structure

```
heistbox/
├── web/                       # Next.js 16 Web Arena & Interactive Audit Dashboard
│   ├── src/app/               # App Router pages (/settle, /wanted, /api)
│   ├── src/components/        # Arena, CfoAudit, PairSplit, StatusBar, ThiefCards
│   └── src/lib/               # API clients, media streams, sound effects, fallback twins
├── server/                    # FastAPI unified backend
│   ├── app.py                 # Core API endpoints & WebSocket handler
│   ├── round_runner.py        # 6-step attack orchestration pipeline
│   ├── vaults.py              # Left, Middle, and Right vault policies
│   └── brain.py               # Multi-agent LLM reasoning & offline heuristics
├── kernel/                    # Relational Security & Formal Verification Engine
│   ├── db_gate.py             # PostgreSQL MVCC dry-run gate
│   ├── heistguard_infer.py    # HeistGuard-LoRA prompt injection detector
│   ├── pair_z3.py             # Z3 SMT formal proof verification
│   └── fetch_guardian.py      # Fetch.ai uAgents escrow quarantine
├── integrations/              # Sponsor integrations
│   ├── router.py              # Unified /api/integrations router
│   ├── wajo_call.py           # Wajo AI voice escalation
│   ├── atlassian_bridge.py    # Jira / Confluence incident automation
│   └── status.py              # Single browser-safe provenance status shape
├── assets3d/                  # 3D Blender models (Bank Hall, Tina, Heister, Sentinel)
└── contracts/                 # API specifications & mock server fixtures
```

---

## 🛡️ License

Released under the **MIT License**. See [LICENSE](LICENSE) for details.
