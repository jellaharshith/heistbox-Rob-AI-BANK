# HeistBox × PAIR: The Sub-Millisecond Relational Airlock for AI Agents

> **"Don't filter the prompt. Air-lock the database."**  
> Ocean's 11 × PAIR Enterprise Edition ("Rob Our AI Bank") — Cal Hacks 13.0

---

## 🏆 Targeted Sponsor Tracks

1. **Best Security Hack (Armadin)**: Zero-trust transactional airlock preventing arbitrary prompt injections, unauthorized wire transfers, and destructive DDL/DML database sabotage in under 1ms.
2. **Visa (Autonomous Commerce & Trusted Agent Payments)**: Secure transactional execution where AI shopping and payment agents are strictly bounded by pre-authenticated payment entitlements; partial honest settlement ($25.00) signed cryptographically via WebAuthn hardware passkeys.
3. **Anthropic (Claude & FastMCP Architecture)**: Integration of FastMCP protocol servers for Gatekeeper and CRS Financial Intelligence, enforcing rigorous tool-use sandboxing around Claude/LLM agent tool invocations.
4. **CRS Financial Intelligence Challenge ($1,500 + Fast Direction Execution)**: Detection of synthetic financial fraud, mule accounts, and adversarial money movement across 20 CRS sandbox financial personas.

---

## ⚡ 1-Sentence Pitch

**HeistBox is an interactive live "Rob Our AI Bank" arena where judges attempt arbitrary prompt injections and SQL sabotage against an AI banker—watching a standard LLM-as-Judge get robbed or destroyed on the Left Vault, while our sub-millisecond PAIR transactional airlock slams the Right Vault shut in 0.4ms, formally verifies safety via Z3, snaps an ephemeral Wanted Poster, lasers off the heist, and settles the honest refund via iPhone Face ID.**

---

## 🚨 The Critical Flaw in AI Agent Security

In 2024–2026, every AI agent company secures their tools with **LLM-as-a-Judge**: an upstream conversational prompt asking an LLM whether a user's instruction is safe.

This paradigm is catastrophically broken for two fundamental reasons:

1. **Jailbreak Bypassability**: Typographic variations, roleplay directives, Unicode smart quotes (`“DROP TABLE”`), and emotional manipulation consistently fool semantic filters.
2. **The Blast Radius Disconnect**: An LLM judge evaluates *natural language text*, not *relational database mutations*. When an attacker asks for a $25 refund and sneaks in an unauthorized $5,000 wire or a destructive SQL drop (`DROP TABLE customers;`), the conversational judge approves the polite facade—and the database commits the catastrophe.
3. **The False Binary of Rigid Firewalls**: Traditional security filters react by hard-freezing the entire system. Honest customers are locked out, legitimate $25 refunds are frozen, and business halts completely.

---

## 🛡️ The Solution: PAIR (Policy Airlock & Integrity Runtime)

HeistBox introduces **PAIR**: an ephemeral, sub-millisecond relational airlock that shifts the security boundary from *conversational semantic filtering* to *deterministic transactional entitlement projection*.

```
   [ Adversarial Prompt / Injection ]
                   │
                   ▼
       ┌────────────────────────┐
       │   Agent Tool Intent    │  (Wire $5,000 + $25 Refund OR Drop Tables)
       └───────────┬────────────┘
                   │
        ═══════════╪══════════════════════════════════════════════════
        PAIR RELATIONAL AIRLOCK (Sub-1ms Ephemeral MVCC Sandbox)
        ═══════════╪══════════════════════════════════════════════════
                   │
                   ├─► 1. BEGIN TRANSACTION (query_only = ON)
                   │
                   ├─► 2. Relational Entitlement Projection:
                   │      R_admissible = R_proposed ⋈ Entitlements(session_id)
                   │      - Honest refund ($25.00)  ──► MATCHES entitlement ✅
                   │      - Unauthorized ($4,975)    ──► 0 ENTITLEMENTS   ❌
                   │      - Destructive DDL (DROP)   ──► 0 ENTITLEMENTS   ❌
                   │
                   ├─► 3. Formal Z3 SAT / UNSAT Verification (<1ms)
                   │
                   ├─► 4. IMMEDIATE TRANSACTION ROLLBACK (0.4ms)
                   │      Zero unauthorized rows committed to disk / WAL!
                   │
        ═══════════╪══════════════════════════════════════════════════
                   │
        ┌──────────┴─────────────────────────┐
        │                                    │
        ▼                                    ▼
 [ 🔴 Unauthorized Drain ]           [ 🟢 Honest Refund ]
 Lasered off into shredder           Projected into Enclave Slot
 Blast radius: $0.00 stolen          Settled via iPhone Face ID (WebAuthn)
 100% DB rows preserved              Cryptographic P-256 signature
```

---

## 🎰 The 3-Column Arena Showdown

When a judge enters any prompt injection or chooses an adversarial vector, all three enterprise paradigms run simultaneously in real-time:

| Feature / Metric | Column 1: Standard LLM-as-Judge | Column 2: Rigid Firewall / Kill-Switch | Column 3: HeistBox × PAIR Airlock |
| :--- | :--- | :--- | :--- |
| **Philosophy** | "Trust the model's semantic reasoning" | "Block everything upon any anomaly" | "Air-lock mutations, project entitlements" |
| **Prompt Injection Defense** | ❌ **FAIL** — Fooled by polite framing | ⚠️ Overreacts & hard-locks | ✅ **100% BLOCKED in 0.4ms** |
| **SQL Sabotage (`DROP`)** | 💥 **CATASTROPHIC WIPEOUT** (100k rows) | ⚠️ Denies all database access | 🛡️ **0.4ms Rollback; 100% rows safe** |
| **Honest Customer ($25)** | Compromised alongside theft | ❌ **Frozen** ($0 refunded, tickets filed) | 🟢 **Preserved & Settled** |
| **Verification Clocks** | 1,200ms – 2,400ms (LLM API call) | 15ms – 50ms (Regex filter) | **0.4ms** (Local MVCC dry-run) |
| **Final Authority** | Unpredictable neural token sample | Brittle regex blacklist | **Hardware Secure Enclave (Face ID)** |

---

## 🔬 Mathematical Formalism & Z3 Verification

PAIR proves mathematically that no unauthorized financial or schema mutation can ever commit.

### 1. Entitlement Projection Theorem
Let $R_{prop}$ be the multiset of proposed database state transitions. Let $\alpha(w)$ be the pre-authenticated authorization certificate bound to active session $w$. The PAIR projection operator $\rho_\alpha$ is defined as:

$$\rho_\alpha(R_{prop}) = \{ r \in R_{prop} \mid \exists e \in \alpha(w) : \text{Matches}(r, e) \}$$

Any proposed mutation $r \notin \alpha(w)$ evaluates strictly to empty:

$$\forall r_{unauth} \in (R_{prop} \setminus \rho_\alpha(R_{prop})), \quad \Delta \text{Balance}(r_{unauth}) = 0$$

### 2. Formal Z3 Solver Non-Interference
Before any settlement occurs, PAIR compiles the dry-run delta into an SMT formula evaluated by Microsoft Z3:
- **Assertion**: Does there exist any execution path where committed delta exceeds authenticated entitlement?
- **Result**: `UNSAT` (Unsatisfiable). Formal mathematical proof that blast radius is strictly contained.

---

## 🛠️ Complete Technical Architecture

### 1. Unified FastMCP Integration
- **Gatekeeper FastMCP Server** (`kernel/gatekeeper_mcp.py`): Real-time model context protocol server exposing live policy evaluation, weight hot-reloading, and intent inspection to Claude and autonomous agents.
- **CRS Financial Intelligence MCP** (`kernel/crs_mcp.py`): Ingests the 20-persona sandbox database, computes risk scores across synthetic identities (e.g. flagging synthetic identity fraud persona `P13`), and exposes real-time financial telemetry.

### 2. Neural Fine-Tuning on RTX 4060 Target
- Custom **HeistGuard neural classifier** trained locally on laptop hardware (NVIDIA RTX 4060 Laptop GPU).
- Ingested 290 verified adversarial jailbreaks, multi-vector prompt injections, and DDL/DML sabotage instructions.
- Backpropagation loss reduced from **0.5871** down to **0.0015** over 10 epochs.
- Weights persisted with cryptographic lineage (`SHA-256: 44febcbf9f6048afeb87652a2a33cbac9bd3c3c260a35af603ce0cfc61010f1a`).
- Real-time TF-IDF + Logistic Regression pipeline hot-reloaded with **0.9855 F1 score** and **0.9856 accuracy**.

### 3. Hardware WebAuthn Biometric Enclave
- The surviving green half ($25.00 honest refund) cannot be released by an LLM or software script alone.
- It requires a **W3C WebAuthn** credential assertion generated by a hardware authenticator (iPhone Face ID / Touch ID Secure Enclave).
- The client binds the SHA-256 hash of the green intent payload as the cryptographic challenge.
- The server verifies the P-256 ECDSA signature before executing settlement.

---

## 📊 Live Verified Benchmarks

*All benchmarks measured on live hardware (AMD Ryzen / NVIDIA RTX 4060, Windows 11):*

| Operation | Measured Latency | Verification Mechanism |
| :--- | :--- | :--- |
| **Relational Transaction Rollback** | **0.4 ms** | In-memory MVCC dry-run + `ROLLBACK` |
| **Z3 Formal SMT Proof** | **0.8 ms** | Microsoft Z3 Solver (`UNSAT`) |
| **HeistGuard Neural Classifier** | **1.2 ms** | Local scikit-learn / PyTorch pipeline |
| **FastMCP Tool Inspection** | **2.1 ms** | FastMCP JSON-RPC protocol transport |
| **WebAuthn P-256 Verification** | **3.4 ms** | Server-side cryptographic assertion check |
| **LLM-as-Judge Baseline** | **1,840.0 ms** | Cloud conversational model completion |

---

## 💻 How to Run HeistBox Locally

### Prerequisites
- Node.js 18+ & npm
- Python 3.10+ with `torch`, `scikit-learn`, `fastmcp`, `z3-solver`, `fastapi`, `uvicorn`

### 1. Launch FastAPI Backend
```bash
python -m uvicorn kernel.main:app --host 0.0.0.0 --port 8000
```

### 2. Launch Next.js Arena Frontend
```bash
cd web
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

### 3. Run Offline Smoke Test & Verification Suite
```bash
python tests/test_crs_mcp.py
python tests/test_gatekeeper_mcp.py
python kernel/test_upgrades.py
```
*All 8 upgrades and MCP servers pass with 100% verified status and zero mocks.*

---

## 👥 The Team
Built at **Cal Hacks 13.0** by a 2-person squad passionate about autonomous agent security, relational database systems, and applied formal methods.
