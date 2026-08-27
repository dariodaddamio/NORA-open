# MTHX / ADAM HX — master pitch brief (Honeywell internal)

**Audience:** Engineering + business sponsors (Honeywell internal).  
**Use:** Copy sections into slides; footnotes preserve **illustrative** vs **internal-quote** data.  
**Companion specs:** [mthx-process-brief.md](mthx-process-brief.md) · plate figure [front-plate.svg](front-plate.svg)

---

## Title / one-liner

**ADAM HX — intelligent, autonomous assembly for microtube heat exchangers**  
Temp-controlled, compressed-air-driven insertion; sensor-capable path to **interference-controlled** tube–tubesheet fit; aligned with **rate, labor, and qualification** pressure in aerospace manufacturing.

---

## Motivation

Commercial aviation and defense sectors are experiencing unprecedented demand, with global commercial aircraft backlogs stretching past a decade and defense spending surging. Delivering on these massive commitments requires a paradigm shift in how quickly and efficiently products can move from design to final assembly. At the same time, the aerospace industry is grappling with a structural shortage of skilled labor and highly constrained supply chains. To meet these aggressive production targets while maintaining aerospace-grade precision, manufacturers must explore intelligent, autonomous systems to supplement existing traditional processes. Autonomous manufacturing could reduce operational risks and mitigate the impact of workforce gaps; assuming its capable of meeting the exact tolerances required for mission-critical flight hardware.

Empowering future engineers to design innovative software and hardware solutions for these autonomous systems is a critical step in building an agile, resilient, and high-capacity aerospace manufacturing ecosystem.

---

## Business narrative — electrification & thermal (paste-ready)

**Speaker line (completes your sentence)**  
From a business perspective, we understand that there is **unprecedented demand** across aerospace because of the **push toward electrification and higher-electric-load architectures** — and **that demand shows up first as a thermal and power-management problem**, not only as a battery story. **More electric accessories, power electronics, and thermal loops** increase the need for **heat rejection and heat transport per kilogram and per liter of installed volume**, in **bleed-air paths, fuel thermal management, accessory cooling,** and related subsystems. At the same time, **OEMs and operators** still expect **cost discipline** and **accelerating production rate** against **commercial backlogs** and **defense ramp**, which means suppliers must deliver **more thermal capability** without **open-ended cost growth** — and must do it under **labor constraints** and **AS9100-grade** repeatability.

**Slide bullets — BUSINESS (tight)**

- **Thermal capability ↑ per mass / volume** for next-gen missions (bleed air, **fuel thermal management**, accessory / power-electronics cooling).
- **Cost trajectory:** stable or **down** at **rate** — no “better performance only if unit cost explodes.”
- **Volume / rate:** industry production must **accelerate** to match **fleet demand and defense spend**; attach **Honeywell scale** only with a **cited** figure from **[investor.honeywell.com](https://investor.honeywell.com/)** (segment or company — **do not** use uncited headline \$ on external decks).

**Slide bullets — ENGINEERING (tight)**

- **Assemble 10k–30k+ sub‑1 mm** microtubes into perforated plates **without** **deformation-driven** leak or **tubesheet** damage.
- **Extreme tolerances** and **process evidence** aligned to **FAA / EASA** expectations and **AS9100** (traceability, FAI, change control).
- **Scale + speed + autonomy:** repeat the above **at production rate** with **minimal touch time** and **measurable** in-process quality.

**Key questions (alternate phrasing — matches “problem” slide)**

1. How do we **scale repeatable** assembly and manufacturing of **leak-tight, high-density, modular** microtube heat exchangers?
2. How do we **apply** this MTHX manufacturing capability to **win** on **next-gen aircraft** thermal and platform programs (share / position / qualification path)?

**Asset:** Microtube bundle photo (internal slide) — workspace: `assets/c__Users_dario_AppData_Roaming_Cursor_User_workspaceStorage_ce4c11e1470a188bff99d2f0457a5513_images_image-d5cb8179-ae67-41aa-82f1-f9010da515de.png`

---

## Evidence base — sourced answers (why cooling, why compact HX, applications)

**How to use this section**  
These sources **substantiate** (a) rising **aircraft thermal-management** burden, especially under **electrification**, (b) the **system penalty** if heat rejection hardware is heavy or draggy, and (c) **where heat exchangers sit** in real aircraft thermal architectures. They **do not** by themselves “prove” that **your** round-tube **MTHX** is the only solution — they justify **investment in compact, high–surface-density HX** and **manufacturing** for that class of hardware. Cross-link to **Research synthesis** (Mezzo / *Sci Rep*) for **UA / compactness** physics.

### A. Why is **better cooling** (and better **heat rejection hardware**) needed?

| Claim (paraphrase) | Why it matters for the pitch | Primary source |
| ------------------ | ---------------------------- | -------------- |
| **Electrified / highly electric aircraft** can generate **far more waste heat** than traditional aircraft **electrical** systems; that heat is **harder to reject** than combustion-engine exhaust paths because losses live in **motors, power electronics, batteries**, etc., **not** as intrinsically coupled to **freestream** exhaust. | Frames **electrification → TMS sizing** as a **first-class** design problem, not a footnote. | **NASA Glenn** — Stalcup, Dever, Sachs-Wetstone, *Thermal Management Key Performance Parameter Development and System Analysis for the SUSAN Electrofan Aircraft*, AIAA SciTech 2025 (NTRS **20240015505**). PDF: [NASA NTRS download](https://ntrs.nasa.gov/api/citations/20240015505/downloads/Stalcup%20SUSAN%20SciTech%202025%20Manuscript.pdf). Landing: [NTRS citation](https://ntrs.nasa.gov/citations/20240015505). |
| **Megawatt-class** electric aircraft propulsion produces **large waste heat** at **relatively low rejection temperatures (<200 °C)**, driving **large, heavy** thermal-management systems and **drag** penalties; NASA’s **HEATheR** program explicitly targets **lower losses** and **outer-mold-line (OML)** rejection to cut **mass / drag**. | Supports the **SWaP + drag** story for **next-gen** programs — any HX technology that improves **UA per mass/volume** feeds that bottleneck. | **NASA Facts** — *HEATheR Activity* factsheet (GRC, NP-2021-01-097-GRC). PDF: [NASA HEATheR factsheet](https://www.nasa.gov/wp-content/uploads/2025/04/heather-factsheet2021-1.pdf). |
| **More electric aircraft** add **generators, batteries, inverters/converters**; **additional waste heat** must be **evacuated** while the TMS still serves **conventional cooling, de-icing, and environmental control** — design must stay **lightweight, redundant, efficient, safe**. | Links **business “electrification”** slide to **concrete TMS functions** sponsors already recognize. | **Modelon** (vendor / systems-engineering blog) — O’Donovan, *Designing Thermal Management Systems for More Electric Aircraft* (2024). [modelon.com blog](https://modelon.com/blog/designing-thermal-management-systems-for-more-electric-aircraft/). |

**Quotable lines (use verbatim only with attribution):**

- NASA (SUSAN / electrified TMS): *“These aircraft produce most or all their propulsive power using electrical powertrains, so they generate **orders of magnitude more waste heat** than electrical power systems on traditional fuel-burning aircraft.”* — Stalcup et al., NTRS **20240015505**, Introduction (PDF above).
- NASA (HEATheR): *“MW electrical power systems produce a **large amount of waste heat** with relatively **low rejection temperatures (<200 °C)**, requiring **large, heavy** thermal management systems that **often produce additional drag**.”* — HEATheR factsheet PDF above.

### B. **Where do aircraft heat exchangers / thermal loops show up?** (applications)

| Application area | Role (high level) | Source |
| ---------------- | ----------------- | ------ |
| **Environmental Control System (ECS)**; **fighter** cooling demand tied to **electronics / weapons thermal loads** | SBIR topic: thermal loads **increased ECS cooling** requirements; **future aircraft** need **advanced HX** to **minimize ECS size and weight**; explicitly ties assessment to **F-35 JSF ECS** heat exchangers in the topic abstract. | **U.S. Navy SBIR** FY2005.2 Topic **N05-087** — *Microchannel Heat Exchangers for Aircraft Thermal Management* (Creare abstract on [navysbir.com](https://www.navysbir.com/05_2/122.htm)). |
| **Fuel and ram air as terminal heat sinks**; **liquid loops** + **vapor-cycle** transport | Terminal sinks are **ambient air** (e.g. **ram-air / skin HX**) and **fuel** (**fuel–liquid HX**); transport often **liquid coolant** and/or **vapor compression**. | **Modelon** blog (same as §A): [link](https://modelon.com/blog/designing-thermal-management-systems-for-more-electric-aircraft/). |
| **Aviation heat exchangers** broadly (design methods, aircraft **component cooling**, engine-related thermal management) | Open-access survey chapter — use for **taxonomy** and **“HX are core aircraft components”** language, not as MTHX-specific endorsement. | Carozza, *Heat Exchangers in the Aviation Engineering*, IntechOpen (2017). **DOI:** [10.5772/67486](https://doi.org/10.5772/67486). Chapter page: [intechopen.com/chapters/54148](https://www.intechopen.com/chapters/54148). |

**Bleed-air / ECS physics (secondary, general-audience):** Wikipedia’s [*Bleed air*](https://en.wikipedia.org/wiki/Bleed_air) and [*Environmental control system (aircraft)*](https://en.wikipedia.org/wiki/Environmental_control_system_(aircraft)) entries describe **hot compressor bleed** conditioned through **heat exchangers** before cabin use — useful for **talk tracks**, not as **authority** in a certification argument.

### C. Why **microchannel / microtube-class** HX get traction (link to MTHX)

| Mechanism | Source |
| --------- | ------ |
| **Microchannels** offer improved **heat transfer / pressure drop** characteristics vs **plate-fin** in contexts where **ECS size/mass** is constrained; **manufacturing cost** was flagged as the historic barrier — aligns with **automation / process** investment. | Navy SBIR abstract — [navysbir.com](https://www.navysbir.com/05_2/122.htm). |
| **Compact micro-channel heat exchangers** listed among **emerging** aircraft TMS technologies requiring **simulation / test** before integration. | **Modelon** blog — [same article](https://modelon.com/blog/designing-thermal-management-systems-for-more-electric-aircraft/). |
| **UA/volume scaling**, **primary-surface** argument, **high-pressure** compact cores | **Mezzo** — [_Why Microtubes_](https://mezzotechnologies.com/why-microtubes/) (see **Research synthesis** table). |
| **Micro** surface-area-density band (**β**), **geometry optimization** | **Alharbi et al.,** *Sci Rep* (2025) — [DOI 10.1038/s41598-025-19763-4](https://doi.org/10.1038/s41598-025-19763-4). |

### D. One-line logic chain for slides

**Electrification increases onboard waste heat and TMS penalties (NASA, Modelon) → heat is rejected via fuel and air-side HX in real architectures (Modelon, Carozza, Navy SBIR) → compact micro-scale HX address SWaP when manufacturable (Navy SBIR, Modelon, Mezzo / *Sci Rep*) → **MTHX automation** attacks the **manufacturing** bottleneck assumed in those same compact-HX narratives.**

---

## Explicit assumptions (outline for sponsors)

These are **premises** the pitch rests on — not universal laws. Mark what Honeywell product / thermal teams must **confirm** vs what is **frozen for this concept study**.

### 1. Microtube HX are the right bet — **why** and **how**

**What we assume**  
Microtube (fine-tube, high-hole-count) heat exchangers remain a **credible and valuable** architecture for at least one meaningful slice of **aerospace thermal hardware** over the investment horizon.

**Why (strategic / program economics)**

- **Thermal path criticality:** Environmental control, oil/fuel cooling, bleed-air, and power-thermal subsystems still drive **schedule, weight, and sustainment cost** on new and retrofit programs.
- **SWaP-C pressure:** Customers keep asking for **smaller envelopes, lower mass, and predictable life-cycle cost**; the HX is often in the **packaging-constrained** part of the vehicle.
- **Rate + labor:** The **same** backlog and labor story in **Motivation** hits hardest where **touch hours per unit** are high — dense tube fields are a poster child.

**How (physics / architecture — mechanism, not a product claim)**

- **Area density:** Very large numbers of **small parallel passages** increase **heat transfer surface per unit volume** compared with many **coarser** single-path or low-count designs, _when_ fluid distribution and fin efficiency are managed.
- **Distributed redundancy:** Many tubes can offer **graceful degradation** semantics vs a single large passage (program-dependent; not asserted for every qualification basis).
- **Materials pathway:** **Stainless** microtubes + **controlled braze** are a **known industrial pattern** for corrosion resistance and joint integrity; the open problem is **repeatable assembly at scale**, not whether microtubes exist.

---

#### Research synthesis — why microtube / microchannel HX **often win SWaP trades** (not “best everywhere”)

External sources support the **directional** story: **smaller hydraulic diameter → more transfer area and UA packed into a given envelope**, at the cost of **manufacturing and joining difficulty** — which is exactly where **automation** matters.

| Theme                        | What the literature / industry says                                                                                                                                                                                                                                                                                                                                                                             | Source type                                                                                                                                                                                         |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **UA–volume scaling**        | For tube-side dominated thinking, **overall conductance per unit core volume** tightens rapidly as tube diameter **D** shrinks — a **~1/D²** scaling argument is commonly used to explain why **sub‑mm** tubes can deliver **orders-of-magnitude** higher **UA/V** than **~10 mm** “conventional” tubes in the same architectural class (idealized; real cores add manifold, wall, and maldistribution losses). | **Vendor engineering explainer** — [Mezzo Technologies, _Why Microtubes_](https://mezzotechnologies.com/why-microtubes/)                                                                            |
| **Primary surface**          | Microtube cores are often described as **primary-surface** exchangers: the **tube wall** is the main heat-transfer surface, **not** extended **secondary fins** — relevant when **weight** and **internal volume** drive the trade.                                                                                                                                                                             | Same — [Mezzo, _Why Microtubes_](https://mezzotechnologies.com/why-microtubes/)                                                                                                                     |
| **Wall resistance**          | In many microtube regimes, **metal wall thermal resistance** is **small vs convective terms**, so **316 SS** can still be competitive vs higher‑k alloys **for overall UA** (still program-specific).                                                                                                                                                                                                           | Same — [Mezzo, _Why Microtubes_](https://mezzotechnologies.com/why-microtubes/)                                                                                                                     |
| **“Micro” compactness band** | Compact HX taxonomy by **surface-area density β** puts **micro** cores roughly above **~15,000 m²/m³** (vs **compact** and **meso** bands) — microtube arrays are a practical way to land in that **β** regime.                                                                                                                                                                                                 | **Peer-reviewed** intro — [Alharbi et al., _Scientific Reports_ 15, 12418 (2025)](https://doi.org/10.1038/s41598-025-19763-4) (cites **Shah & Sekulic** classification)                             |
| **Geometry still matters**   | Even inside “micro,” **channel shape** optimization can move **thermo-hydraulic goodness** (~**j/f** or similar) on the order of **~20–30%** vs baselines in validated CFD DoEs — i.e. **micro** is necessary but not sufficient; **design + manufacturing quality** set the win.                                                                                                                               | Same — [Alharbi et al., _Sci Rep_ (2025)](https://doi.org/10.1038/s41598-025-19763-4)                                                                                                               |
| **Aerospace narrative**      | Trade press / supplier comms position **microtube** cores as a path to **higher heat-transfer density** and **lower installed weight/volume** for **next-gen thermal management** (ECS, thermal control).                                                                                                                                                                                                       | **Industry / trade** — e.g. [Intergalactic — _Microtube technology… aerospace thermal control_](https://ig.space/commslink/microtube-technology-a-catalyst-for-next-gen-aerospace-thermal-control/) |

**Honeywell-adjacent figure (use with extreme care)**  
A **literature review** paragraph in [Alharbi et al., _Sci Rep_ (2025)](https://doi.org/10.1038/s41598-025-19763-4) states that **Honeywell** microchannel **fuel-to-air** HX work and trade studies pointed to on the order of **~20–30%** **volume and/or weight** reduction vs **compact plate-fin** designs, per **their** cited reference chain. Treat this as **third-party reporting**, **not** an approved Honeywell claim for this deck — **confirm internally** before putting a number on a sponsor slide.

**Why we avoid saying “microtubes are _the best_”**

- **Best at what duty?** Fouling, icing, inspectability, **first-unit cost**, and **qualification calendar** can favor **other** architectures despite raw **UA/V**.
- **Microchannel ≠ your exact round-tube braze stack** — many papers study **etched / rectangular** microchannels; arguments are **analogous**, not one-to-one.
- **Manufacturing is the gating item** — precision joining and **yield** dominate **LCC**; that is the **ADAM** thesis, not hand-waving **physics wins**.

---

**What we are _not_ assuming**

- We are **not** claiming this geometry beats **every** competing HX architecture on **all** metrics (cost, fouling, icing, inspectability) without **program-specific** trades.
- We are **not** assuming a particular **Honeywell SKU** adopts this exact **140×140** concept — that is an **internal product** decision.

**Sponsor ask:** Agree (or falsify) that **microtube HX** deserve **automation investment** alongside other thermal form factors; if “no,” pivot the story to **process IP** transferable to other dense-perforation assemblies.

---

### 2. Initial design constraints (this MTHX / ADAM concept)

These bound **this** reference design and the **BOM / throughput** math in this brief. They are **not** a released drawing or qualification basis.

| Domain                  | Constraint                                                                             | Notes                                                                                                                                                                                          |
| ----------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hole field**          | **140 × 140** grid, **19,600** positions                                               | Tube count aligned with grid; pitch follows **inscribed square** in **R = 19 cm** plate family ([process brief §2](mthx-process-brief.md)).                                                    |
| **Tubes**               | **SS316**, **Ø1.0 mm** OD (slot / ID per released spec), **~1.1 ft** length pre-finish | **1 ft** **plate-to-plate** active length **after laser trim** ([process brief §1](mthx-process-brief.md)).                                                                                    |
| **Metallurgical stack** | **12 × 0.2 mm** foils, **CNC stack-drilled** through pack                              | **Front / back:** `SS316 \| BNi-2 \| SS316` each; **between:** **six** **6061** cards — **2.4 mm** metal pack before closure ([process brief §1](mthx-process-brief.md)).                      |
| **Braze / release**     | **Vacuum braze** using **BNi-2** foils in the stack                                    | **KOH bath** removes **six** **Al** cards post-braze; chemistry scaled in [process brief §4](mthx-process-brief.md).                                                                           |
| **Insertion**           | **Layered** load via **HDPE cassette**                                                 | **142** tubes per layer → **~138** full layers; **compressed-air** layer burst; **hinged lid** after **~2/3** layer; **motorized** cassette index ([process brief §3](mthx-process-brief.md)). |
| **Process intent**      | **Autonomous** alignment + insertion path                                              | Sensor / calibration story targets **interference fit**, **leak risk**, and **tubesheet warping** (see **Key questions**).                                                                     |

**Explicitly out of scope for this outline**  
Final **tolerance stack**, **FAI** sampling, **braze profile** sign-off, **ITAR/export** classification, and **supplier qualification** — those replace table shorthand with **Honeywell standard** artifacts.

---

## Key questions / problems

1. **How might we create an intelligent robotic system capable of automatically aligning and inserting tens of thousands of delicate tubes into a tubesheet without causing material deformation in heat exchangers?**

2. **How might we deploy sensor-equipped automated manufacturing equipment that dynamically calibrates to achieve a perfect interference fit, preventing both microscopic fluid leaks and stress-induced tubesheet warping in heat exchangers?**

---

## Constraints and considerations

- Aerospace manufacturing demands **ultra-tight tolerances**, often in the **sub-micron** range, for structural integrity, performance, and efficiency in mission-critical applications.
- Aerospace systems rely on **high-performance materials** (titanium alloys, composite resins, advanced ceramics), which add processing complexity and specialized machining.
- **Regulatory certification** (e.g. **FAA**, **EASA**) constrains how fast new production methods can be adopted; new processes must demonstrate **consistent airworthy output**.
- **AS9100** imposes **configuration management**, **digital traceability**, and **first article inspection** — autonomous cells must map cleanly into that QMS.
- New technology must **integrate with legacy robotics, controls, and lines** to avoid unacceptable downtime.
- Programs favor **rapid iteration** without new hard tooling for every design change.
- Unlike automotive, aerospace is often **low volume**, so **fixed tooling amortization** is painful.
- **High integration cost** and **long ROI horizons** remain adoption barriers.

**Internal deck discipline:** Pair vision with a **credible qualification path** (risk reduction, metrology, FAI strategy), not only hardware demos.

---

## Slide pack — Problem (starred)

**Headline:** _THE PROBLEM(S)_ — or _Why autonomous MTHX assembly is a Honeywell-relevant problem_

**Two-column framing (optional on slide)**  
**BUSINESS** | **ENGINEERING** — mirror bullets in **Business narrative — electrification & thermal** above.

**Key question (on slide):**  
_How do we scale **repeatable, leak-tight, high-density** microtube heat exchangers under **labor and rate** pressure without sacrificing **tubesheet and tube integrity**?_

**Business → engineering chain**

- **Business:** Electrification and **higher thermal loads per SWaP** push **HX** up the value chain; **backlogs** and **defense ramp** require **throughput** and **predictable cost** without abandoning **cost-down** expectations.
- **Engineering consequence:** **Tens of thousands of sub‑1 mm tubes**, **tight hole fields**, and **braze / finish** steps that today imply **touch labor**, **variation**, **deformation risk**, and **rework risk**.
- **Risk if unchanged:** Schedule slip, yield loss, and **qualification drag** on any process that cannot be **traced** and **repeated**.

**Patents / existing solutions (framing, not legal advice)**  
Landscape includes **HX architectures**, **braze materials**, **tube handling**, and **perforated plates** — the differentiator to argue is **end-to-end integration**: **dispense → insert → join → release → trim** with **in-process sensing** and **digital thread**, not a single component patent.

---

## Slide pack — Cost breakdown (starred)

**Headline:** _Where cost and time go (ADAM HX path)_

Map costs to **your** process (see [mthx-process-brief.md](mthx-process-brief.md)).

### Parts / materials (BOM categories)

| Category           | What                                                                       | Notes                                                                                            |
| ------------------ | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Microtubes         | **19,600×** SS **316**, **Ø1.0 mm**, **~1.1 ft** length                    | Dominates BOM uncertainty (see illustrative $ below).                                            |
| SS316 foils        | **4×** **0.2 mm** plies in **two** 3‑ply faces (outer SS / BNi / inner SS) | Area ≈ **πR²** per ply, **R = 190 mm** (or inscribed square for pattern — use released drawing). |
| BNi-2              | **2×** **0.2 mm** foils (same plan as plates)                              | Braze alloy; priced as **foil / preform**, not commodity kg.                                     |
| Al 6061            | **6×** **0.2 mm** cards                                                    | Removed in **KOH** after braze (process cost + waste stream).                                    |
| HDPE cassette      | **1×**, **142** slots/layer, hinge, motorized index                        | **NRE + machining** dominates vs resin kg.                                                       |
| Spacers / fixtures | Stack assembly                                                             | Often **reusable**; amortize over N units.                                                       |
| KOH + water        | Dissolve **six** Al sheets                                                 | Stoichiometry / volumes in [mthx-process-brief §4](mthx-process-brief.md).                       |
| Consumables        | Gas, cutters, PPE, waste                                                   | Line item in real quote.                                                                         |

### Time / operations (labor + machine)

| Step               | Buckets                                                                         |
| ------------------ | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **CNC**            | **12‑ply stack** drill **140×140**; align; deburr; inspect                      |
| **Stack + spacer** | Mechanical assembly of **2.4 mm** metal pack                                    |
| **Load**           | **~138** cassette cycles × (air burst + index + lid logic) — see **Throughput** |
| **Braze**          | **Vacuum braze** profile; **FAI / sampling** policy                             | _Typical practice: batch multiple parts per furnace cycle — amortize setup; replace with **Honeywell standard** in internal model._ |
| **KOH**            | Chilled bath, **intervals**, rinse, inspection                                  |
| **Finish**         | Laser trim to **1 ft** plate‑to‑plate; final QC                                 |

**Scrap / rework** — explicit line in real model (tube bend, mis‑seat, braze void).

---

## Slide pack — Business value (starred)

**Headline:** _Why this matters to Honeywell and customers_

**Market context (public, illustrative)**

- Analyst press summaries cite **aircraft heat exchanger** market on the order of **single‑digit billions USD** with mid‑single‑digit **CAGR** and drivers in production, fleet modernization, and **MRO** (e.g. [MarketsandMarkets via PR Newswire, 2025/2030 headline](https://www.prnewswire.com/news-releases/aircraft-heat-exchanger-market-worth-6-45-billion-by-2030---exclusive-report-by-marketsandmarkets-302609886.html)). Treat as **TAM framing**, not Honeywell share.

**Honeywell scale (official numbers)**

- Cite **Aerospace Technologies** sales from **Honeywell investor materials / 10‑K** (e.g. [investor.honeywell.com](https://investor.honeywell.com/)) — **do not** imply this program revenue.

**Platform economics (illustrative only)**

- DoD **F‑35** sustainment and life‑cycle themes are **publicly documented** (e.g. [GAO F‑35 sustainment products](https://www.gao.gov/products/gao-24-106703)) — use to justify _“small yield / weight / sustainment improvements scale on large programs”_ **without** claiming \$ savings for ADAM HX without internal analysis.

**Value levers (internal story)**

- **Touch time down**; **variation down**; **traceability up**; **iteration** without new fixed tooling; path to **AS9100‑compatible** data.

---

## Illustrative BOM (USD, order-of-magnitude — NOT a quote)

**Method:** Web‑visible **indicative** ranges + **physics-based quantities**. Replace every number with **supplier quotes** before budget decisions.

### Geometry used for mass (rough)

- Plate **disc** (for foil area proxy): **R = 190 mm** → \(A = \pi R^2 \approx 1.134\times10^5\ \mathrm{mm}^2\) per ply.
- **Tube length:** **1.1 ft** ≈ **0.335 m** per tube (use **released drawing** if different).
- **Total tube meterage:** \(19\,600 \times 0.335 \approx 6\,570\ \mathrm{m}\).

### Tubes (largest uncertainty)

| Assumption                                              | Extended cost |
| ------------------------------------------------------- | ------------- |
| Low **\$2/m** (high-volume specialty tubing — _verify_) | **~\$13k**    |
| Mid **\$8/m**                                           | **~\$53k**    |
| High **\$20/m** (low volume / premium)                  | **~\$131k**   |

\*Public list prices for **1 mm OD 316 capillary** are often **MOQ / RFQ**; industry listings rarely show stable \$/m. **Quote 3+ qualified tube vendors.\***

### SS316 plate foils (4 × 0.2 mm, full disc)

- Volume ≈ \(4 \times A \times 0.2 \approx 9.1\times10^4\ \mathrm{mm}^3 \approx 91\ \mathrm{cm}^3\).
- Mass @ **~8.0 g/cm³** ≈ **0.73 kg**.
- Commodity **316 sheet** indicators in trade press / regional guides often **~\$4.5–6/kg FOB** (e.g. industry summaries such as [ssalloy-steel.com 316 price commentary](https://ssalloy-steel.com/price/316-stainless-steel-price/)) — **raw** metal only **~\$3–5**.
- **Precision blanks / rolled foil** typically **multiple×**; **illustrative processed material** **\$50–250** for this mass band unless you have a cut quote.

### BNi-2 foils (2 × 0.2 mm)

- Volume ≈ **half** of SS stack foils → ~**0.36 kg** equivalent mass order-of-magnitude.
- Commercial listings vary **widely** (foil format, purity, MOQ); see supplier pages such as [Alexy Metals — AM Ni-2 / BNi-2 foil](https://alexymetals.com/products/am-ni-2-foil) for **RFQ** posture.
- **Illustrative \$100–800** for **two** production foils at this area **before** Honeywell supply chain discount.

### 6061 Al cards (6 × 0.2 mm)

- Volume ≈ \(6 \times A \times 0.2\), mass ≈ **0.37 kg**.
- Market commentary for **6061 sheet** often **~\$2.5–3.5/lb** retail band in trade articles (e.g. [Luokaiwei 6061 price commentary](https://luokaiweialuminum.com/2025/06/30/6061-aluminum-price-per-pound-in-2025/)) — **commodity** **~\$5–25**; thin **precision** stock higher.

### KOH (per HX, chemistry from brief)

- **~1.0–1.2 kg** KOH **charge** per full Al strip (see [mthx-process-brief §4](mthx-process-brief.md)).
- Industrial **bulk** KOH pricing is often quoted **per ton** in trade indexes (e.g. summaries on [accio.com KOH cost page](https://www.accio.com/plp/potassium-hydroxide-cost)); **small packaged** lab grades cost **much** more.
- **Illustrative chemical \$5–80** per unit **including** packaging + disposal allocation (highly variable).

### HDPE cassette

- **Custom** part: **\$500–5k NRE** + **\$100–400** material + machining (placeholder until drawing RFQ).

### Braze furnace + KOH + trim (outsourced or internal)

- Use **internal router rates**. Placeholder **\$2k–20k** **variable** per HX **excluding** amortized capital.

### Illustrative scenario totals (very wide)

| Scenario                                    | Low        | High        |
| ------------------------------------------- | ---------- | ----------- |
| **Materials + consumables** (excl. capital) | **~\$25k** | **~\$180k** |
| **+ NRE cassette (one-time / amortize)**    | +\$0.5k    | +\$5k       |

**Speaker note:** The **tube line** dominates; tightening it collapses uncertainty fastest.

---

## Throughput — time to complete one **140×140** HX

**Symbols**

- \(N = 19\,600\) tubes
- \(n\_\ell = 142\) tubes/layer
- \(L = \lceil N / n\_\ell \rceil\) layers → **138** full layers (4 positions unused unless you rebalance counts)

**Layer load time**

\[
T*\text{load} = L \times t*\text{layer}
\]

where \(t\_\text{layer}\) = air burst + mechanical settle + cassette **index** + lid actuation + (optional) vision check.

| \(t\_\text{layer}\) | \(T\_\text{load}\) |
| ------------------- | ------------------ |
| 15 s                | **~0.6 h**         |
| 30 s                | **~1.2 h**         |
| 60 s                | **~2.3 h**         |

**Other blocks (placeholders — replace with standard times)**

| Step                        | Illustrative range                    |
| --------------------------- | ------------------------------------- |
| CNC stack + drill + inspect | **8–40 h** (highly process-dependent) |
| Stack / spacer assembly     | **2–12 h**                            |
| Vacuum braze (machine time) | **4–24 h** + **queue**                |
| KOH + rinse + inspect       | **2–12 h** (interval strategy)        |
| Trim + final QC             | **2–8 h**                             |

**Example end-to-end (mid assumptions)**  
\(T\_\text{load} \approx 1.2\ \text{h}\) + CNC **16 h** + stack **4 h** + braze **12 h** + KOH **4 h** + trim **4 h** ≈ **~41 h active** + **calendar queue** for furnace and labor.

**Batch braze note:** If Honeywell runs **K parts** per cycle, allocate **setup + cycle** as \((T*\text{setup} + T*\text{cycle})/K\) per HX in business cases.

---

## Technical appendix (condensed)

- **Stack:** Front **SS316 | BNi-2 | SS316**; **six** **6061** cards; back **SS316 | BNi-2 | SS316** — **12 × 0.2 mm**; **CNC stack‑drilled** **140×140**; **spacers** set final gaps.
- **Tubes:** **SS316**, **Ø1.0 mm**, **ID ~0.7 mm**, **~1.1 ft**; **1 ft** **plate‑to‑plate** after trim.
- **Cassette:** **HDPE**, **142**/layer, **hinge** at **~2/3** layer, **motorized** reload, **compressed air** layer insertion.
- **Join / release:** **Vacuum braze**; **KOH** removes **six** **Al** cards (chemistry: [mthx-process-brief §4](mthx-process-brief.md)).
- **Plate drawing:** [front-plate.svg](front-plate.svg) (rim, slots, mounting holes — **not** a released drawing).

---

## Devils Invent / winning deck pattern (how to stage this story)

Prior **Devils Invent** decks that won (including themes like **autonomy in aerospace**) tend to use:

1. **Sharp problem** + **quantified or sourced** “why now.”
2. **Named solution / system** (“agent,” line, or architecture).
3. **Constraints honestly called out** (regulatory, integration, ROI).
4. **Evidence path** (demo, simulation, pilot, partners).
5. **Ask** (sponsor, lab access, customer intro).

**Important:** The extracted **Devils Invent 2024** PDF in Downloads is **UAS / airspace** themed — **reuse the structure**, **not** UAM market statistics, in the MTHX deck.

**TODO — paste 3–5 “winning lines”** from:

- _Devils Invent — Aerospace Factory to the Future_ (PDF)
- _LinkedIn Devils Invent — Elevating the Aerospace Workforce_ (PDF)

into the next revision of this brief so tone matches **your** latest winning narrative.

---

## Public financial / labor anchors (optional slide fodder)

- **Aircraft HX market** headline growth — [PR Newswire / MarketsandMarkets summary](https://www.prnewswire.com/news-releases/aircraft-heat-exchanger-market-worth-6-45-billion-by-2030---exclusive-report-by-marketsandmarkets-302609886.html).
- **Honeywell Aerospace** segment — **[investor.honeywell.com](https://investor.honeywell.com/)** filings.
- **F-35 sustainment scale (illustrative)** — [GAO](https://www.gao.gov/products/gao-24-106703).
- **Manufacturing labor / unit labor cost** discussion — e.g. [FAA labor factor discussion PDF](https://www.faa.gov/sites/faa.gov/files/regulations_policies/policy_guidance/benefit_cost/econ-value-section-7-labor-cost-factors.pdf) (dated; use for **pattern**, not Honeywell rate).

---

## Disclaimers

- **KOH** is hazardous — procedures require **HSE** signoff.
- **Financial numbers** here are **illustrative**; **no** procurement or forecasting authority.
- **Geometry** in this repo is for **communication**; **released drawings** rule manufacturing.
- **Export / ITAR** — classify program content before external distribution.

---

## Revision log

| Date       | Note                                                                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-04-11 | Master brief created from thread + process brief + indicative web sourcing.                                                                |
| 2026-04-11 | Research synthesis: microtube / microchannel rationale (Mezzo, _Sci Rep_ 2025, trade); Honeywell % caveated as third-party citation.       |
| 2026-04-11 | Business narrative (electrification + thermal): paste-ready speaker line, BUSINESS/ENGINEERING bullets, slide problem framing, image path. |
| 2026-04-11 | Evidence base: NASA NTRS SUSAN TMS, HEATheR factsheet, Modelon MEA blog, Navy SBIR N05-087, IntechOpen Carozza DOI; logic chain for slides. |
