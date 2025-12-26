# Maintenance Procedure: Battery Balance & Triage
**Target System:** Fullriver DC400-6 AGM Bank (48V Configuration)
**Status:** **CRITICAL WATCH (Imbalance Detected Dec 2025)**

## ⚠️ Safety Critical Warnings
*   **REMOVE ALL JEWELRY.**
*   **Eye Protection:** Required.
*   **Charger Safety:** When manually charging, use **ONLY** an isolated, double-insulated charger (e.g., NOCO Genius 5) to prevent ground faults.

---

## 1. Routine Quarterly Check (Surveillance)

**Frequency:** Every 3 Months (Jan / Apr / Jul / Oct)
**System State:** Float Mode (Green Light).

1.  **Measure:** Touch multimeter probes to the lead posts of each individual 6V battery.
2.  **Analyze:**
    *   **Healthy:** All batteries within **0.1V - 0.2V** of each other.
    *   **Warning:** Gaps >0.3V.
    *   **Critical:** Gaps >0.5V (e.g., 6.5V vs 7.4V).

---

## 2. Corrective Balancing Procedure (The "Fix")

*Perform this procedure if the spread exceeds 0.3V.*

**Equipment:** NOCO Genius 5 (Select **6V AGM** Mode).

**The "In-Circuit" Method:**
1.  **Timing:** Perform during mid-day Float or with Solar OFF.
2.  **Connect:** Clamp the NOCO Red/Black clips directly to the posts of the **LOW** battery.
    *   *Note:* You do not need to disconnect the main battery cables.
3.  **Charge:** Let the NOCO run until the LED goes Solid Green (100%).
4.  **Repeat:** Move to the next lowest battery.

**Target Priorities (Jan 2026 Triage):**
1.  **Battery #10**
2.  **Battery #4**
3.  **Battery #16**
4.  **Battery #5**

---

## 3. Log Sheet Template

| Date | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **String 1**| | | | | | | | |
| **String 2**| | | | | | | | |
