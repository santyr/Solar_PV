# Battery Replacement Recommendation 2029 -2030
## Target System: Schneider Electric XW & MPPT Integration

Based on your existing Schneider XW6848+ inverter and MPPT 60 infrastructure, and your desire for native integration, the **Discover AES LiFePO4** system is the superior choice.

Unlike standard lithium batteries, these units utilize **Closed-Loop Communication**, allowing the battery BMS to take full control of your Schneider equipment via the Xanbus network. This eliminates voltage drift issues and manual programming.

---

### 1. Recommended Hardware: Discover AES Rackmount (48V)

The modern standard for this integration is the **Discover AES RACKMOUNT 48-48-5120 (5.12 kWh)** or the **AES 7.4 kWh** (depending on local availability).

**Why this choice?**
*   **Native Integration:** Plug-and-play with Schneider Xanbus via the LYNK II Gateway.
*   **Dashboard Visibility:** Your InsightLocal dashboard will display exact Battery SoC%, Internal Temperature, and Health stats.
*   **Dynamic Charging:** The battery tells the MPPT exactly how fast to charge based on temperature and fullness.

---

### 2. Sizing Options

*   **Current Usage:** ~4.4 kWh per day.
*   **Current Bank:** ~20 kWh usable capacity (AGM).

#### Option A: The "Smart Match" (Recommended)
**Hardware:** 3x Discover AES 7.4 kWh units (or equivalent ~22 kWh total).
*   **Total Capacity:** ~22.2 kWh.
*   **Autonomy:** ~5 Days of backup without sun.
*   **Inverter Support:** Fully supports the XW6848 surge capacity (285A discharge limit).
*   **Lifespan:** 20+ Years (Calendar Life).

#### Option B: The "Efficient" Choice
**Hardware:** 2x Discover AES 7.4 kWh units.
*   **Total Capacity:** ~14.8 kWh.
*   **Autonomy:** ~3.5 Days of backup without sun.
*   **Note:** This covers your needs easily, but offers slightly less surge buffer for heavy loads compared to Option A.

---

### 3. Required Bill of Materials (BOM)

To achieve the "Schneider Compatible" integration, you need more than just the batteries.

| Item | Qty | Purpose |
| :--- | :-- | :--- |
| **Discover AES Battery** | 2 or 3 | Main storage. |
| **LYNK II Gateway** | 1 | **CRITICAL.** This box translates the battery data into Schneider Xanbus language. |
| **Battery Combiner / Busbar** | 1 | You must convert from Series (old wiring) to Parallel (new wiring). |
| **Battery Interconnect Cables** | Set | To connect each battery to the busbar. |
| **CAT5e Network Cable** | 1 | Connects LYNK II to your Schneider Insight/Gateway. |

---

### 4. Installation Notes

1.  **Wiring Change:** You will **keep** your main 4/0 AWG inverter cables. You will **discard** the short jumper cables between your current Fullriver batteries. The new batteries will be wired in parallel to a common busbar.
2.  **Solar Controller:** Your single MPPT 60 is perfectly fine. The Discover BMS will simply throttle the charge rate if necessary (though your 4.2kW array fits well within the battery limits).
3.  **InsightLocal Setup:** Once installed, you will select "Discover" in the battery setup menu on your Schneider Gateway. No manual voltage parameters (Bulk/Absorb/Float) are needed; the battery sets them automatically.

### 5. Expected Outcomes

*   **Charge Efficiency:** You will capture significantly more solar energy in the morning as Lithium accepts 100% current until full (no resistance tapering).
*   **Zero Maintenance:** No equalization, no corrosion, no specific ventilation requirements.
*   **Cost of Ownership:** While the upfront cost is higher ($12k-$15k est.), the cost per kWh over the 15-20 year lifespan is roughly **$0.50 - $0.58**, providing energy security for decades.
