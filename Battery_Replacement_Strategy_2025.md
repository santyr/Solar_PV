# Battery Replacement Strategy: Lightning Goats Lithium Upgrade
## Target Date: August 1, 2027

Based on your existing Schneider XW6848+ inverter and MPPT 60 infrastructure, and your desire for native integration, the **Discover AES LiFePO4** system is the superior choice.

Unlike standard lithium batteries, these units utilize **Closed-Loop Communication**, allowing the battery BMS to take full control of your Schneider equipment via the Xanbus network. This eliminates voltage drift issues and manual programming.

---

### 1. Recommended Hardware: Discover AES Rackmount (48V)

The selected standard for this project is the **Discover AES RACKMOUNT 48-48-5120 (5.12 kWh)**.

**Why this choice?**
*   **Form Factor:** The rackmount shape allows for a "Split Stack" configuration that fits inside your 24-inch high battery box.
*   **Cost:** Significantly better value per kWh than older wall-mount units.
*   **Native Integration:** Plug-and-play with Schneider Xanbus via the LYNK II Gateway.
*   **Dashboard Visibility:** Your InsightLocal dashboard will display exact Battery SoC%, Internal Temperature, and Health stats.

---

### 2. Sizing Configuration

*   **Current Usage:** ~5.3 kWh per day (House + Goats + Laptop + Fridge).
*   **Current Bank:** ~20 kWh usable capacity (AGM).

#### The Plan: 5-Unit Array
*   **Hardware:** 5x Discover AES 48-48-5120 units.
*   **Total Capacity:** **25.6 kWh**.
*   **Autonomy:** ~4 Days of backup without sun (at current load).
*   **Surge Support:** Fully supports the XW6848 surge capacity.
*   **Lifespan:** 15-20+ Years (Calendar Life).

---

### 3. Required Bill of Materials (BOM)

To achieve the "Schneider Compatible" integration and fit the physical space:

| Qty | Part Number | Description | Purpose |
| :--- | :--- | :--- | :--- |
| **5** | `48-48-5120` | AES Rackmount Battery | Main storage (Standard Model). |
| **1** | `950-0049` | AES Battery Combiner | Landing pad for all batteries; includes Master Disconnect. |
| **1** | `950-0025` | LYNK II Gateway | **CRITICAL.** Bridges the battery network to Schneider Xanbus. |
| **6** | `950-0050` | Quick Stack Rack Bracket | Mounting hardware (5 for batteries, 1 for Combiner). |
| **3** | *Custom* | 4 AWG Cable Pairs (4-5 ft) | Connects the "Left Stack" to the Combiner. |
| **1** | *Custom* | CAT5e Patch Cable (4 ft) | Bridges data between stacks. |

---

### 4. Installation Notes (The "Split Stack")

**Physical Constraints:**
*   **Limit:** Box is 24" High x 48" Wide.
*   **Solution:** Install as two side-by-side stacks.

**Layout:**
1.  **Left Stack:** 3 Batteries High. (Height ~21.3").
2.  **Right Stack:** 2 Batteries + 1 Combiner Box on top. (Height ~21.3").

**Wiring Strategy:**
1.  **Main Connection:** Reuse existing 4/0 AWG inverter cables to connect the Inverter to the **Combiner Box**.
2.  **Interconnects:** The Contractor must cut and crimp custom 4 AWG cables on-site to connect the Left Stack to the Combiner (on the Right Stack).
3.  **Solar Controller:** The single MPPT 60 is sufficient. The Discover BMS will manage charge rates automatically.

---

### 5. Roles & Commissioning

**Contractor (Muscle & Wire):**
*   Physical removal of 2,000 lbs of old AGM batteries.
*   Physical installation of new racks/batteries.
*   Custom DC cable fabrication.

**Owner (IT/Soft):**
*   Firmware updates (Inverter, Gateway, LYNK II).
*   Closed-Loop Configuration (Setting the Schneider Gateway to "Discover AES" mode).
*   Home Automation Integration (OpenHAB via Modbus).

### 6. Expected Outcomes

*   **Charge Efficiency:** You will capture significantly more solar energy in the morning (Lithium accepts 100% current until full).
*   **Zero Maintenance:** No equalization, no corrosion, no voltage imbalance checks.
*   **Economic ROI:** The  revenue from the Lightning Goats feeder / routing offsets the hardware cost, making the effective cost of storage nearly zero over the life of the system.
