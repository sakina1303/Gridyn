# India landscape — ideation research

Working project label: **FlexGrid**. Product name and final scope are undecided. Research snapshot: 22 October 2026.

## Verified facts

- India's national planning explicitly anticipates large growth in solar, wind, and storage. CEA's 2025 advisory cites a 2031–32 storage requirement of 73.93 GW / 411.4 GWh. This is a **system planning estimate**, not a campus battery requirement. [CEA advisory](https://cea.nic.in/wp-content/uploads/notification/2025/02/Advisory_on_colocating_Energy_Storage_System_with_Solar_Power_Projects_to_enhance_grid_stability_and_cost_efficiency.pdf)
- Rooftop solar is a government priority, including government buildings and DISCOM participation. [MNRE rooftop programme](https://mnre.gov.in/en/grid-connected-solar-rooftop-programme/)
- A 2024 CEEW review of eight states found limited evidence of demand flexibility at scale and barriers involving DISCOM capacity, regulation, and planning. [CEEW DSM assessment](https://www.ceew.in/publications/how-can-india-scale-electricity-demand-side-management-with-dsm-regulations-and-discoms-action)
- A 2026 CEEW survey of 14 DISCOM representatives found limited feeder and transformer level analytics and concern about granular flexibility data, enrollment, and cost recovery. This is a survey finding, not proof that every DISCOM has the same gap. [CEEW flexibility market study](https://www.ceew.in/publications/how-india-can-create-demand-flexibility-market-five-pillars)
- Smart metering is advancing but availability of *consented, accessible, site level time series* cannot be inferred from installation counts. A Ministry of Power parliamentary answer reported 4.54 crore meters installed under RDSS by February 2026. [Ministry of Power answer](https://powermin.gov.in/sites/default/files/uploads/LS12032026_Eng_0.pdf)
- Time of day tariffs are part of India's consumer rules; specific categories, rates, and windows require the applicable state tariff order. [Ministry of Power rules material](https://powermin.gov.in/sites/default/files/Seeking_Comments_on_Rights_of_Consumers_Rules_2023.pdf), [UPERC example](https://upload.indiacode.nic.in/showfile?actid=AC_UP_88_456_00007_00007_1760515272954&filename=emytd.pdf&type=regulation)
- Indian pilots already shift demand: Tata Power reported a 23 day municipal pumping pilot in Mumbai that shifted 345 kW for three hours daily. This is a company reported pilot outcome. [Tata Power pilot](https://www.tatapower.com/news-and-media/media-releases/tata-power-joins-hands-with-mcgm-for-a-unique-demand-flexibility-program-powered-by-solar-energy)
- An Indian distribution transformer battery VPP project exists: Amperehour describes six sites with 510 kW total capacity in Delhi. This is company reported. [Amperehour project](https://amperehourenergy.com/bses-rajdhani-indias-first-multi-site-virtual-power-plant-vpp/)
- Cooling matters for building demand. BEE's 2024–25 report describes cooling as a major commercial building load, with variation by building type and climate. [BEE India Energy Scenario](https://beeindia.gov.in/sites/default/files/India_Energy_Scenario_Report_2024-25.pdf)

## Research inferences

1. The strongest near term user problem may be **knowing which flexibility is actually usable under incomplete data and operational constraints**, before buying batteries or attempting automated control. This combines CEEW's data gap findings with the existence of mature optimizers.
2. Campuses offer a bounded demonstration with cooling, pumping, EV charging, solar, and optional storage. A campus is a test environment, not by itself a defensible innovation.
3. Feeder or transformer claims need network topology, ratings, and measurements. A site only model can show a connection limit scenario, but cannot claim voltage or power quality outcomes.
4. India Energy Stack is a possible future interoperability path, not an integration to promise now. The Ministry described it as a roadmap effort in 2025. [Ministry answer](https://powermin.gov.in/sites/default/files/uploads/RS18082025_Eng.pdf)

## Open research questions before MVP lock

- Which state and consumer tariff category should anchor a realistic demonstration?
- Can a campus or similar site provide consented 15 minute meter and asset data for later validation?
- What operational constraints do facility managers actually permit for cooling, pumps, and EVs?
- Which public datasets permit credible local solar and demand evaluation, and under what licenses?
- How will uncertainty in inferred flexibility be quantified and communicated?

No production architecture is selected here.
