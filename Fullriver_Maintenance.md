# Maintenance Procedure: Individual Battery Balance Check
**Target System:** Fullriver DC400-6 AGM Bank (48V Configuration)
**Frequency:** Quarterly (Jan / Apr / Jul / Oct)

## ⚠️ Safety Critical Warnings
*   **DO NOT disconnect any cables.** The system should remain live and running during this test.
*   **REMOVE ALL JEWELRY.** Take off rings, watches, and bracelets. If metal touches a Positive and Negative terminal simultaneously, it will weld instantly and cause severe burns.
*   **Eye Protection:** Safety glasses are recommended.

---

## 1. Preparation

**Equipment Needed:**
*   Digital Multimeter.

**System State:**
*   Perform this test mid-day when the Charge Controller shows **FLOAT** (Green light).
*   *Reason:* Imbalances are most visible when the batteries are under the "pressure" of a charge voltage.

**Multimeter Setup:**
*   Turn dial to **DC Volts** (Symbol: `V` with a straight line `—`).
*   If not auto-ranging, select the **20V** range.

---

## 2. The Procedure

**Note:** You have a total of 16 batteries (2 strings of 8). You need to measure each grey box individually.

1.  **Access:** Open the battery box to expose the tops of the batteries.
2.  **Isolate the Block:**
    *   Ignore the messy interconnect cables for a moment. Focus on **one** rectangular battery case.
    *   Identify the **Positive (+)** and **Negative (-)** post built into that specific plastic case.
3.  **Measure:**
    *   Touch the **RED** probe to the Positive (+) post of the battery.
    *   Touch the **BLACK** probe to the Negative (-) post of the **same** battery.
4.  **Record:** Write down the voltage (e.g., "6.85V") and the battery position (e.g., "String 1, Battery 1").
5.  **Repeat:** Move to the next battery and repeat until all 16 are recorded.

---

## 3. Analyzing the Data

Since the batteries are wired together, they naturally try to "share" voltage. However, the resistance of a bad battery will create a voltage gap.

### ✅ The Healthy Scenario
*   **Reading:** All batteries are within **0.1V to 0.2V** of each other.
*   *Example:* 6.85V, 6.84V, 6.86V, 6.82V.
*   **Action:** None required. The bank is balanced.

### ⚠️ The Warning Scenario (Drift)
*   **Reading:** One or two batteries are **0.3V to 0.5V** apart from the average.
*   *Example:* Most are 6.8V, but one is **6.4V** or **7.1V**.
*   **Action:** Mark this battery with a piece of tape. Check it again in a month. It is likely the weak link.

### ❌ The Failure Scenario (Short/Open)
*   **Reading:** A massive gap (**>0.5V** difference).
*   *Example:* Most are 6.8V, but one is **6.1V** (Dead Cell) or **7.5V** (Cooking).
*   **Action:** This battery has failed.
    *   If it reads **Low (e.g., 6.1V):** It has a shorted cell and is draining the others.
    *   If it reads **High (e.g., 7.5V):** It has high resistance and is boiling itself.
    *   *Immediate Recommendation:* Plan for bank replacement.

---

## 4. Log Sheet Template

| Date | String 1 (Left) | | | | String 2 (Right) | | | |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **[Today]**| B1: ____ V | B2: ____ V | B3: ____ V | B4: ____ V | B1: ____ V | B2: ____ V | B3: ____ V | B4: ____ V |
| | B5: ____ V | B6: ____ V | B7: ____ V | B8: ____ V | B5: ____ V | B6: ____ V | B7: ____ V | B8: ____ V |
