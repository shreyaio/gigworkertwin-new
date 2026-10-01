---
title: "Uber India Driver-Partner Policy Corpus, Organised by the Fairwork Location-based Platform Work Principles"
corpus_version: "2026.09-lb1"
compiled_on: "2026-09-13"
jurisdiction: IN
subject_population: Driver partners using the Uber Driver app in India (cars, auto-rickshaws, motorbikes)
standard: Fairwork Location-based Platform Work Principles
standard_effective_from: "2024-10-15"
standard_source: Fairwork_LocationBased_Principles_verbatim.md
criteria: 33
refiled_on: "2026-09-22"
refiled_from_standard: Fairwork AI Principles
refile_basis: "Fairwork_Uber_India_Codebook_v2.docx, Table B (161 chunk-criterion links)"
levers: [L1, L2, L3, L4, L5]
thresholds: ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2", "5.1", "5.2"]
source_count: 31
extract_count: 126
absence_count: 42
content_rule: Verbatim only. Every quoted passage is reproduced word for word from the cited Uber page.
audience_rule: Driver-facing policy, plus rider-facing or all-user policy that operates on the driver.
evaluation_rule: No assessment, scoring, endorsement or criticism appears in this document.
absence_rule: Where Uber publishes nothing, the absence is recorded explicitly and nothing is inferred.
---

# Uber India Driver-Partner Policy Corpus, Organised by the Fairwork Location-based Platform Work Principles

A verbatim compilation of officially published Uber documentation applicable to driver
partners in India, segmented by the five Fairwork Location-based Platform Work Principles and
their ten thresholds, and anchored to the thirty-three criteria beneath them.

## 1. Scope and method

**Scope.** This document compiles text that Uber itself publishes and that applies, or is served, to driver partners in India. Four families of source were used: the Uber legal hub with the jurisdiction selector set to India; the Uber India driver product pages under `uber.com/in/en/drive`; the Uber Help centre articles for Driving and Delivering; and Uber India newsroom and blog posts published under Uber bylines.

**Extraction.** Each page was opened and its rendered text captured directly, including text held inside collapsed accordions and shadow-DOM containers, so that quoted passages match the published wording exactly. Quotations preserve Uber's own spelling, punctuation, capitalisation and any typographical errors present on the page. Where Uber sets a passage in full capitals, the capitals are retained.

**Segmentation.** Each extracted passage is filed under the Fairwork lever and threshold whose subject matter it addresses. A passage that bears on more than one threshold is placed under the threshold it speaks to most directly and is not duplicated. Every passage additionally carries a `criteria` field naming every criterion it bears on, with the judgement recorded against it, so a passage filed under one threshold is still reachable from the others it evidences.

**Which standard this corpus is filed against.** Version 2026.09 of this corpus was filed against the **Fairwork AI Principles**. Uber India is rated by Fairwork under the **Fairwork Location-based Platform Work Principles**, which differ in subject at thresholds 3.2 and 4.2 and differ in threshold naming throughout. This version, 2026.09-lb1, is re-filed against the location-based standard so that the corpus, the codebook and the published rating all address the same rules. Nothing was re-collected. Verbatim text, `chunk_id`, `source_id`, `policy_surfaces`, `section`, `audience` and citations are unchanged. What changed is `threshold`, the addition of `criteria`, and the addition of `refiled_from` on the thirty-nine extracts that moved. `chunk_id` and absence identifiers are **not** renumbered: they are opaque stable keys, and the codebook cites them.

**Basis of the re-file.** Threshold assignment is derived from Table B of `Fairwork_Uber_India_Codebook_v2.docx`, which records 161 links between corpus extracts and the 33 location-based criteria. An extract is filed under the threshold holding the greatest number of its links. Where two thresholds tie, the filing in corpus v2026.09 stands if that threshold's subject is preserved between the two standards, which is every threshold except 3.2 and 4.2; otherwise the tie falls to the strongest judgement recorded, then to threshold order. Five extracts link to no location-based criterion and are filed in Appendix D.

**Jurisdiction labelling.** Uber publishes some driver-facing material only in global or non-India versions. Where a passage comes from such a page, the `jurisdiction` field says so, and a note records what indicates the page is not India-specific. No global text is presented as though Uber had published it for India.

**Audience rule.** A passage is included only if it operates on the driver partner. Driver-facing text carries `audience: driver`. Text published to riders or to all users that nonetheless operates on the driver — because it sets conduct the driver is held to, defines a ground on which the driver loses access, fixes how the driver is paid, or allocates a risk the driver bears — carries `audience: mixed` and states why in a `driver_relevance` field. Rider-only material is excluded and logged in Appendix C.

**The driver contract.** Uber publishes the India driver Services Agreement on the India legal hub under the title *India Earner Car Subscription Model Terms and Conditions* (S32). It is reproduced clause by clause and supplies text to every lever. Its own scope statement limits it to six categories: Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green.

**Known boundary.** No published driver contract was located for Uber Moto, Uber Auto, Uber Intercity, Uber Hire or courier work in India. For those categories the governing contract remains behind authentication at `drivers.uber.com/profile` (S28), and no text from it is reproduced or paraphrased here. The Mumbai auto document that is published (S33) is a rider-facing addendum, not a driver contract.

**Two pay models appear in the sources and both are reproduced.** The Services Agreement (S32, effective 01 October 2025) and the Mumbai auto addendum (S33, effective 29 July 2025) describe a subscription model in which the driver sets the fare, the app shows a non-binding Suggested Fare, and the driver pays Uber for access through a Drive Pass. The Uber Help and India driver product pages (S09, S11, S12) describe a commission model in which Uber calculates the fare and deducts a Service Fee from it. Both were live on Uber's own properties at the retrieval date. This document records what each says and does not reconcile them.

**Exclusions.** Third-party commentary, press coverage, regulatory analysis, litigation material, and evaluative or ratings-based research including the Fairwork India reports were not used as sources of policy text. Those documents contain assessment, and this compilation is confined to what Uber states.

## 2. How to read an entry

Every entry carries the same fields, in the same order, so the document can be parsed mechanically.

- **chunk_id**: Stable identifier, formed as lever-threshold-sequence
- **source_id**: Identifier of the source in the register in section 3
- **source_type**: Class of Uber publication
- **jurisdiction**: Jurisdiction the source page states or is served under
- **audience**: `driver`, or `mixed` where rider-facing text operates on the driver
- **driver_relevance**: Present only on `mixed` entries
- **levers**: Fairwork lever
- **threshold**: Fairwork threshold under the location-based standard, or `OUT_OF_FRAME`
- **criteria**: Every location-based criterion the passage bears on, each with the judgement recorded against it in the codebook
- **refiled_from**: Present only where the location-based threshold differs from the v2026.09 filing
- **policy_surfaces**: Tags naming the policy mechanisms described
- **section**: Heading or clause within the source document
- **note**: Present only where a qualification about scope or applicability is required

Verbatim passages follow as block quotations. A citation line closes the entry. Where a
threshold has no matching Uber text, a **Recorded absences** block states plainly what
Uber does not address. Each recorded absence names the criterion it bears on.

## 3. Source register

Retrieval date for all sources: 2026-09-13.

| ID | Title | Type | Jurisdiction | Document date |
| --- | --- | --- | --- | --- |
| S01 | Uber Community Guidelines | `company_policy_legal_hub` | India | 2025-04-21 (page states: Last modified: 4/21/2025) |
| S02 | Deactivations: Losing Account Access | `company_policy_product_page` | India (India driver site) | Not stated on page |
| S03 | Uber Pro Terms and Conditions | `company_policy_legal_hub` | India | 2026-08-05 (page states: Last modified: 8/5/2026) |
| S04 | Uber Non-Discrimination Policy | `company_policy_legal_hub` | India | 2024-07-23 (page states: Last modified: 7/23/2024) |
| S05 | Zero Tolerance Policy | `company_policy_legal_hub` | Global document listed on the India legal hub index | 2023-05-19 (page states: Last modified: 5/19/2023) |
| S06 | How Uber Uses Communications Intelligence to Improve Your Experience | `company_policy_legal_hub` | India | 2026-07-07 (page states: Last modified: 7/7/2026) |
| S08 | Uber Privacy Notice: Drivers and Delivery People | `company_policy_privacy_notice` | Global. No India-specific carve-out appears in the text and no separate India driver priva… | 2026-09-01 (page states: Last updated: September 1, 2026) |
| S09 | How earnings are calculated for rides (Uber Help, Driving and Delivering) | `company_help_centre` | Uber Help article served to India; uses per-kilometre terminology | Not stated on page |
| S10 | Upfront fares (Uber Help, Driving and Delivering) | `company_help_centre` | Uber Help article. The product list inside it names US and global ride types, indicating a… | Not stated on page |
| S11 | Upfront Fares, explained (Tracking Your Earnings, Driver App basics) | `company_policy_product_page` | India | Not stated on page |
| S12 | How much can drivers make with Uber? | `company_policy_product_page` | India | Not stated on page |
| S13 | How payments work (Driver App basics) | `company_policy_product_page` | India | Not stated on page |
| S14 | How star ratings work (Driver App basics) | `company_policy_product_page` | India | Not stated on page |
| S15 | Drive with confidence (Driver Safety) | `company_policy_product_page` | India | Not stated on page |
| S16 | Driver requirements | `company_policy_product_page` | India | Not stated on page |
| S17 | Contact Uber (Drivers: How to Get Help) | `company_policy_product_page` | India | Not stated on page |
| S18 | Driving time limit (Uber Help, Driving and Delivering) | `company_help_centre` | Uber Help global English article. No India-specific version was located. | Not stated on page |
| S19 | What is Trip Radar and how does it work? (Uber Help, Driving and Delivering) | `company_help_centre` | Uber Help article. The text references the GMB union and speeds in mph, indicating a UK-fa… | Not stated on page |
| S20 | Uber's New Features to Make Driving Safer, Easier, and Fairer | `company_newsroom` | India | 2024-11-15 (dateline on page) |
| S21 | Uber announces 2nd edition of Driver Advisory Council | `company_newsroom` | India | 2023-04-17 (dateline on page) |
| S22 | Moving Forward Together: Launching Driver Advisory Council | `company_newsroom` | India | 2022-03-24 (dateline on page) |
| S23 | Uber introduces Uber Care for its driver partner community in India | `company_newsroom` | India | 2018-11-26 (dateline on page) |
| S24 | Uber commits INR 100 crores towards driver welfare initiatives | `company_newsroom` | India | 2021-12-15 (dateline on page) |
| S25 | Uber puts Safety at the heart of Driver Experience | `company_newsroom` | India | 2019-01-29 (dateline on page) |
| S26 | Driving with Uber: Setting the record straight | `company_blog` | India | 2017-03-03 (dateline on page) |
| S27 | Keeping driver partners at heart | `company_newsroom` | India | 2018-12-20 (dateline on page) |
| S28 | Agreeing to terms and conditions (Uber Help, Driving and Delivering) | `company_help_centre` | Uber Help article served to India | Not stated on page |
| S30 | I have an inquiry about cancellation fee (Uber Help, Driving and Delivering) | `company_help_centre` | Uber Help article served to India | Not stated on page |
| S31 | Uber Legal Hub, India index (jurisdiction and language selector) | `company_policy_legal_hub` | India | Not stated on page |
| S32 | Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions) | `company_contract_driver_facing` | India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, U… | 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025 |
| S33 | Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai) | `company_terms_rider_facing` | India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners,… | 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025 |

**S01. Uber Community Guidelines**

- **publisher**: Uber India Systems Private Limited
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/legal/general-community-guidelines/>
- **document_date**: 2025-04-21 (page states: Last modified: 4/21/2025)
- **retrieved_at**: 2026-09-13

**S02. Deactivations: Losing Account Access**

- **publisher**: Uber Technologies Inc. / Uber India Systems Private Limited
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **url**: <https://www.uber.com/in/en/drive/driver-app/deactivation-review/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S03. Uber Pro Terms and Conditions**

- **publisher**: Uber India Systems Private Limited
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/legal/uber-pro-program-terms/>
- **document_date**: 2026-08-05 (page states: Last modified: 8/5/2026)
- **retrieved_at**: 2026-09-13

**S04. Uber Non-Discrimination Policy**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/legal/non-discrimination-policy/>
- **document_date**: 2024-07-23 (page states: Last modified: 7/23/2024)
- **retrieved_at**: 2026-09-13

**S05. Zero Tolerance Policy**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: Global document listed on the India legal hub index
- **url**: <https://www.uber.com/global/en/legal/zero-tolerance-policy/>
- **document_date**: 2023-05-19 (page states: Last modified: 5/19/2023)
- **retrieved_at**: 2026-09-13

**S06. How Uber Uses Communications Intelligence to Improve Your Experience**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/legal/communication-intelligence/>
- **document_date**: 2026-07-07 (page states: Last modified: 7/7/2026)
- **retrieved_at**: 2026-09-13

**S08. Uber Privacy Notice: Drivers and Delivery People**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **url**: <https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/>
- **document_date**: 2026-09-01 (page states: Last updated: September 1, 2026)
- **retrieved_at**: 2026-09-13

**S09. How earnings are calculated for rides (Uber Help, Driving and Delivering)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India; uses per-kilometre terminology
- **url**: <https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S10. Upfront fares (Uber Help, Driving and Delivering)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article. The product list inside it names US and global ride types, indicating a non-India-specific version.
- **url**: <https://help.uber.com/driving-and-delivering/article/what-is-the-upfront-fare?nodeId=bc83ed7e-6725-41de-afcb-72d263e5589f>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S11. Upfront Fares, explained (Tracking Your Earnings, Driver App basics)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/drive/basics/tracking-your-earnings/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S12. How much can drivers make with Uber?**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/drive/how-much-drivers-make/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S13. How payments work (Driver App basics)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/drive/basics/how-payments-work/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S14. How star ratings work (Driver App basics)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/drive/basics/how-ratings-work/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S15. Drive with confidence (Driver Safety)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/drive/safety/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S16. Driver requirements**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/drive/requirements/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S17. Contact Uber (Drivers: How to Get Help)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/drive/contact/>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S18. Driving time limit (Uber Help, Driving and Delivering)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help global English article. No India-specific version was located.
- **url**: <https://help.uber.com/en/driving-and-delivering/article/driving-time-limit?nodeId=a50a72e1-d315-4154-ac66-b17bd5bd050a>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S19. What is Trip Radar and how does it work? (Uber Help, Driving and Delivering)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article. The text references the GMB union and speeds in mph, indicating a UK-facing version.
- **url**: <https://help.uber.com/driving-and-delivering/article/what-is-trip-radar-and-how-does-it-work?nodeId=b6fb7065-ce66-490c-a911-d4e6d5c10d29>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S20. Uber's New Features to Make Driving Safer, Easier, and Fairer**

- **publisher**: Uber Newsroom India (IndiaSA Comms)
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/newsroom/uber-features-to-make-driving-safer-easier-and-fairer/>
- **document_date**: 2024-11-15 (dateline on page)
- **retrieved_at**: 2026-09-13

**S21. Uber announces 2nd edition of Driver Advisory Council**

- **publisher**: Uber Newsroom India (IndiaSA Comms Team)
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/newsroom/uber-second-edition-driver-advisory-council/>
- **document_date**: 2023-04-17 (dateline on page)
- **retrieved_at**: 2026-09-13

**S22. Moving Forward Together: Launching Driver Advisory Council**

- **publisher**: Uber Newsroom India (IndiaSA Comms Team)
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/newsroom/uber-driver-advisory-council/>
- **document_date**: 2022-03-24 (dateline on page)
- **retrieved_at**: 2026-09-13

**S23. Uber introduces Uber Care for its driver partner community in India**

- **publisher**: Uber Newsroom India (Shonali Chakravarty)
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/newsroom/ubercare/>
- **document_date**: 2018-11-26 (dateline on page)
- **retrieved_at**: 2026-09-13

**S24. Uber commits INR 100 crores towards driver welfare initiatives**

- **publisher**: Uber Newsroom India (IndiaSA Comms Team)
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/newsroom/uber-commits-inr-100-crores-towards-driver-welfare-initiatives/>
- **document_date**: 2021-12-15 (dateline on page)
- **retrieved_at**: 2026-09-13

**S25. Uber puts Safety at the heart of Driver Experience**

- **publisher**: Uber Newsroom India (IndiaSA Comms Team)
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/newsroom/uber-puts-safety-at-the-heart-of-driver-experience/>
- **document_date**: 2019-01-29 (dateline on page)
- **retrieved_at**: 2026-09-13

**S26. Driving with Uber: Setting the record straight**

- **publisher**: Uber Blog India (Amit Jain, President of Uber India)
- **source_type**: `company_blog`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/blog/drivingwithuber/>
- **document_date**: 2017-03-03 (dateline on page)
- **retrieved_at**: 2026-09-13

**S27. Keeping driver partners at heart**

- **publisher**: Uber Newsroom India (Prabhjeet Singh)
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/newsroom/keeping-driver-partners-at-heart/>
- **document_date**: 2018-12-20 (dateline on page)
- **retrieved_at**: 2026-09-13

**S28. Agreeing to terms and conditions (Uber Help, Driving and Delivering)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India
- **url**: <https://help.uber.com/en/driving-and-delivering/article/agreeing-to-terms-and-conditions?nodeId=44cf1f0e-27ca-4919-9621-f1321a0381c1>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S30. I have an inquiry about cancellation fee (Uber Help, Driving and Delivering)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India
- **url**: <https://help.uber.com/driving-and-delivering/article/request-cancellation-fee?nodeId=41fee0a6-8941-4418-bf25-3327db4f50aa>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S31. Uber Legal Hub, India index (jurisdiction and language selector)**

- **publisher**: Uber Technologies Inc.
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **url**: <https://www.uber.com/in/en/legal/?country=india&lang=en>
- **document_date**: Not stated on page
- **retrieved_at**: 2026-09-13

**S32. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions)**

- **publisher**: Uber India Systems Private Limited
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **url**: <https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/>
- **document_date**: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025
- **retrieved_at**: 2026-09-13

**S33. Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai)**

- **publisher**: Uber India Systems Private Limited
- **source_type**: `company_terms_rider_facing`
- **jurisdiction**: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners.
- **url**: <https://www.uber.com/in/en/legal/india-auto-saas-rider-terms-and-conditions---mumbai/>
- **document_date**: 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025
- **retrieved_at**: 2026-09-13

## 4. Lever L1 — Fair Pay

- **lever**: L1
- **fairwork_principle**: P1
- **thresholds**: 1.1, 1.2

### 4.1 Threshold 1.1 — Ensures workers earn at least the local minimum wage after costs

- **threshold_id**: 1.1
- **lever**: L1
- **criteria**: `1.1.a`, `1.1.b`
- **extract_count**: 33
- **audience_driver**: 30
- **audience_mixed**: 3
- **absence_count**: 0

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> The platform takes appropriate steps to ensure both of the following:

- **[1.1.a]** Payment must be on time and in-full.
- **[1.1.b]** Workers earn at least the local minimum wage, or the wage set by collective sectoral agreement (whichever is higher) in the place where they work, in their active hours, after costs.[4]

> **INLINED FOOTNOTE [4]**
> In order to evidence this, where the platform is responsible for paying workers the platform must either: (a) have
> a documented policy that ensures that all workers receive at least the local minimum wage after costs in their
> active hours; or (b) provide summary statistics of transaction and cost.

#### Extracts from official Uber documentation

##### What drivers earn from a ride fare

- **chunk_id**: `L1-1.1-001`
- **source_id**: S09
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India; uses per-kilometre terminology
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `earnings_composition`, `service_fee`, `tips`
- **section**: Section heading: What drivers earn

Verbatim text:

> You earn the rider’s base price plus time and distance rates, minus the Service Fee you pay to Uber. Any additional fees don’t contribute to your earnings.
>
> You also earn 100% of tips from riders.

*Citation: Uber Technologies Inc. How earnings are calculated for rides (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article served to India; uses per-kilometre terminology. Section heading: What drivers earn. URL: https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S09.*

##### What riders pay and which components reach the driver

- **chunk_id**: `L1-1.1-002`
- **source_id**: S09
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India; uses per-kilometre terminology
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `fare_structure`, `surge`, `additional_fees`
- **section**: Section heading: What riders pay

Verbatim text:

> The rider pays a base price, plus charges based on the time and distance of the trip, and additional fees:
>
> Rider’s price: You earn what the rider pays for their base price plus time and distance rates, minus the service fee you pay to Uber. Any additional fees the rider pays don’t contribute to your earnings. The rider’s price starts with a base price, per-minute amounts, and per-kilometer amounts. These can be increased by:
>
> Surge, which causes prices to increase when rider demand is higher than the number of drivers online
>
> Extra features a rider chooses, like Uber Comfort Electric or Uber Pet trips, rides reserved in advance, trips far out of town, or where your rider makes you wait before the trip.
>
> Additional fees: The additional fees do not contribute to your earnings but offset charges like regulatory fees, airport fees, booking fees, and others.

*Citation: Uber Technologies Inc. How earnings are calculated for rides (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article served to India; uses per-kilometre terminology. Section heading: What riders pay. URL: https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S09.*

##### Why the rider price exceeds driver earnings

- **chunk_id**: `L1-1.1-003`
- **source_id**: S09
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India; uses per-kilometre terminology
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (SUPPORTS)
- **policy_surfaces**: `fare_transparency`
- **section**: Section heading: Why riders pay more than driver earnings

Verbatim text:

> When the rider sees their price, it includes the base price, time and distance rates plus all of the additional fees. These additional fees a rider pays can increase the overall price of the trip, especially with airport trips. To determine your earnings, it’s best to look at the fare components on your receipt.

*Citation: Uber Technologies Inc. How earnings are calculated for rides (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article served to India; uses per-kilometre terminology. Section heading: Why riders pay more than driver earnings. URL: https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S09.*

##### Where the service fee percentage and rate card are disclosed

- **chunk_id**: `L1-1.1-004`
- **source_id**: S09
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India; uses per-kilometre terminology
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (SUPPORTS), `3.1.d` (SUPPORTS)
- **policy_surfaces**: `wage_records`, `service_fee_disclosure`, `driver_addendum`
- **section**: Section headings: Viewing earnings statement breakdown; Finding trip receipts

Verbatim text:

> You can always check the fare components, other fees, and service fee percentages in your driver addendum at drivers.uber.com by going to Profile and then scrolling down to the Contracts section before you accept a trip.
>
> Additionally for completed trips, this information will appear at the trip level within your Driver app, and on the earnings section of drivers.uber.com.
>
> For trips in progress, you can see your rates (base fare, time, distance) on the trip waybill.
>
> You can find trip receipts for past trips in the Earnings tab of your Driver app or the earnings section of drivers.uber.com.

*Citation: Uber Technologies Inc. How earnings are calculated for rides (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article served to India; uses per-kilometre terminology. Section headings: Viewing earnings statement breakdown; Finding trip receipts. URL: https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S09.*

##### Who bears the cost of rider promotions and discounts

- **chunk_id**: `L1-1.1-005`
- **source_id**: S09
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India; uses per-kilometre terminology
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (SUPPORTS)
- **policy_surfaces**: `service_fee`, `promotions`
- **section**: Section heading: Rider promotions and discounts

Verbatim text:

> Any promotions or discounts offered to riders are covered through the Service Fees you already pay Uber.

*Citation: Uber Technologies Inc. How earnings are calculated for rides (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article served to India; uses per-kilometre terminology. Section heading: Rider promotions and discounts. URL: https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S09.*

##### Inputs Uber states it uses to calculate Upfront Fares

- **chunk_id**: `L1-1.1-006`
- **source_id**: S11
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL), `3.2.d` (ASSERTED)
- **policy_surfaces**: `upfront_fares`, `pricing_algorithm`, `surge`
- **section**: Section heading: How are Upfront Fares calculated?

Verbatim text:

> While most platforms are still calculating fares per minute and mile, at Uber, we know there’s more to a trip than its length and distance. So we built the technology to make it happen.
>
> When calculating Upfront Fares, we take 3 key categories into account: details, demand, and data.
>
> Trip details
>
> The basic details of a trip will always factor into how Upfront Fares are calculated. These include:
>
> Estimated trip length
>
> Estimated trip duration
>
> Pickup location
>
> Dropoff location
>
> Real-time demand
>
> How much you can make is impacted by the current demand in your area. These include:
>
> Surge pricing
>
> How busy is it in your area
>
> How busy is it at the destination
>
> How likely are you to get another trip quickly
>
> Traffic
>
> Historic data
>
> Key earnings trends and data help to create more accurate predictions. These include:
>
> Areas with high and low demand
>
> Areas with high and low earnings
>
> Estimated demand at locations
>
> Estimated demand at various times throughout the day

*Citation: Uber Technologies Inc. Upfront Fares, explained (Tracking Your Earnings, Driver App basics). Jurisdiction stated or inferred: India. Section heading: How are Upfront Fares calculated?. URL: https://www.uber.com/in/en/drive/basics/tracking-your-earnings/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S11.*

##### Information shown to the driver before accepting, and fare adjustment on change

- **chunk_id**: `L1-1.1-007`
- **source_id**: S11
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `upfront_fares`, `pre_acceptance_disclosure`, `fare_adjustment`
- **section**: Section headings: What you’ll see upfront; Upfront Fares can be higher or lower than the pricing based on fixed time and distance rates. Why is this?; When changes happen

Verbatim text:

> Make informed decisions about which rides you accept.
>
> How much you’ll make, including surge pricing
>
> Where you’ll go
>
> Time and distance to pickup location
>
> Time and distance to drop off location
>
> To create more consistent earning opportunities for everyone in the same area. We look at conditions by the second to make sure every offer you get is just as good as the ones you miss.
>
> Technology can only predict so much. When unexpected traffic, construction, or extended wait times happen, you’ll get an automatic fare adjustment to help make it right.

*Citation: Uber Technologies Inc. Upfront Fares, explained (Tracking Your Earnings, Driver App basics). Jurisdiction stated or inferred: India. Section headings: What you’ll see upfront; Upfront Fares can be higher or lower than the pricing based on fixed time and distance rates. Why is this?; When changes happen. URL: https://www.uber.com/in/en/drive/basics/tracking-your-earnings/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S11.*

##### Upfront fare composition, exclusions and the no-downward-revision rule

- **chunk_id**: `L1-1.1-008`
- **source_id**: S10
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article. The product list inside it names US and global ride types, indicating a non-India-specific version.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `upfront_fares`, `exclusions`, `tolls_tips`, `pricing_experiments`
- **section**: Article body
- **note**: This Uber Help article is not India-specific. The ride-type list it contains names US and other non-India products. It is reproduced here because it is Uber’s own statement of how upfront fares operate, but its India applicability is not asserted on the page.

Verbatim text:

> Upfront fares let you see how much you’ll make and where you’ll go before accepting a request.
>
> The amount you see upfront is calculated using several factors, including:
>
> Base fares
>
> Estimated trip length and duration
>
> Pickup distance
>
> Surge pricing
>
> Payments for factors that we can’t predict, such as wait times and tips, are still added after the trip.
>
> To help you make your decisions, we’ll show the cross streets closest to the pickup and dropoff points. As always, it’s up to you to decide if you want to accept requests. When trips take a surprise turn—when there’s unexpected traffic, for example, or a change of address—the fare will update accordingly.
>
> If you find a route that’s more efficient and finish the trip quicker than expected, you’ll still get the upfront fare. In that case, as long as pickup and dropoff addresses don’t change, the upfront fare can only increase.
>
> Since the upfront fare factors in pickup distance, you won’t receive a separate long pickup fee for trips with long pickups.
>
> Tips, tolls, and any other surcharges are not included in the fare that’s shown upfront. Tolls, fees, surcharges, and any tips paid to you by riders will be paid to you with the fare upon final payout.
>
> As Uber works to improve its marketplace, we may occasionally test functionality and pricing for different groups of drivers.

*Citation: Uber Technologies Inc. Upfront fares (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article. The product list inside it names US and global ride types, indicating a non-India-specific version. Article body. URL: https://help.uber.com/driving-and-delivering/article/what-is-the-upfront-fare?nodeId=bc83ed7e-6725-41de-afcb-72d263e5589f. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S10.*

##### Components Uber lists as determining Indian driver earnings

- **chunk_id**: `L1-1.1-009`
- **source_id**: S12
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `fare_structure`, `minimum_trip_earnings`, `service_fee`, `cancellation_fee`, `surge`
- **section**: Section heading: How earnings are calculated

Verbatim text:

> The money you make driving with the Uber app depends on when, where, and how often you drive. Find out how your fares are calculated and learn about promotions, which can help increase your earnings.
>
> You might be wondering how much you can make driving with Uber. The following factors help determine the amount you earn for each trip.
>
> Standard fare
>
> You earn a fare for every completed trip.
>
> Surge
>
> Check the heat map in your app to find out when and where rider demand is high, so you can earn more on top of your standard fare.
>
> Minimum trip earnings
>
> Each city has a minimum amount that you’ll earn for any trip. This makes sure your earnings reflect the effort you put in, even on short trips.
>
> Service fee
>
> This fee helps fund things like app development and customer support.
>
> Cancellations
>
> In most instances, you’ll receive a cancellation fee if a rider cancels a request.

*Citation: Uber Technologies Inc. How much can drivers make with Uber?. Jurisdiction stated or inferred: India. Section heading: How earnings are calculated. URL: https://www.uber.com/in/en/drive/how-much-drivers-make/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S12.*

##### Promotions, tipping, payout timing and cash trips

- **chunk_id**: `L1-1.1-010`
- **source_id**: S12
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL), `2.2.c` (CONTRADICTS)
- **policy_surfaces**: `promotions`, `tips`, `payout_timing`, `cash_trips`
- **section**: Section headings: Promotions and how they work; Getting tipped for your service; When and how you get paid

Verbatim text:

> In-app promotions based on where the Driver app expects the most ride requests in your area help you plan ahead and set goals to maximize earnings. Not all promotions are available to all drivers. See terms below.
>
> Reach a set number of trips
>
> Earn extra money if you complete a set number of trips in a certain amount of time when the offer is available.
>
> Drive during busy times
>
> Get paid extra for trips in certain areas at busy times.
>
> After every trip, riders can easily tip you directly in the app. You always keep 100% of your tips.
>
> It’s easy to get paid. All you need is a bank account. Your earnings are transferred every week.
>
> With cash, you get paid immediately after you complete a trip. The app will show the amount to collect from your customer and calculate fees that you owe to Uber.
>
> Running your own business comes with flexibility and also overhead. Fuel, insurance, and vehicle maintenance might be tax-deductible, and Uber has partnerships to offer discounts that support you.

*Citation: Uber Technologies Inc. How much can drivers make with Uber?. Jurisdiction stated or inferred: India. Section headings: Promotions and how they work; Getting tipped for your service; When and how you get paid. URL: https://www.uber.com/in/en/drive/how-much-drivers-make/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S12.*

##### Disclaimers attached to the India earnings page

- **chunk_id**: `L1-1.1-011`
- **source_id**: S12
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (CONTRADICTS), `3.2.a` (CONTRADICTS)
- **policy_surfaces**: `earnings_disclaimer`, `promotions`
- **section**: Page footnotes 1 and 2

Verbatim text:

> Material provided on this page is for informational purposes only and does not guarantee earnings. Earnings structures may differ by city. Always check your city-specific website for the most accurate details on delivery fares in your city.
>
> Uber will inform you when you are eligible for a promotion. Restrictions to promotions apply. Any restrictions and terms will be shared with you in the specific promotion or tool. Uber reserves the right to change or cancel any promotion, including but not limited to the requirements necessary to get such a promotion.

*Citation: Uber Technologies Inc. How much can drivers make with Uber?. Jurisdiction stated or inferred: India. Page footnotes 1 and 2. URL: https://www.uber.com/in/en/drive/how-much-drivers-make/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S12.*

##### Mechanism and cadence of payment to the driver bank account

- **chunk_id**: `L1-1.1-012`
- **source_id**: S13
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.a` (SUPPORTS)
- **policy_surfaces**: `payout_mechanism`, `bank_account`
- **section**: Section headings: How payments work; How to set up a bank transfer

Verbatim text:

> When you drive with Uber, your earnings are transferred automatically, so you don’t have to worry about paperwork. Find out how to add a bank account and how to cash out.
>
> To add your bank account in the Driver app, go to Payments in the app menu. Alternatively, visit drivers.uber.com, sign in, and go to the Banking tab in your dashboard.
>
> Fill in your bank details, full address, and date of birth exactly as they appear on a recent bank statement. If any of the details are incorrect, your deposit may be delayed.

*Citation: Uber Technologies Inc. How payments work (Driver App basics). Jurisdiction stated or inferred: India. Section headings: How payments work; How to set up a bank transfer. URL: https://www.uber.com/in/en/drive/basics/how-payments-work/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S13.*

##### Instant payments, upfront tipping and the Earnings Hub announced for India

- **chunk_id**: `L1-1.1-013`
- **source_id**: S20
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.a` (SUPPORTS)
- **policy_surfaces**: `payout_timing`, `tips`, `earnings_transparency`, `service_fee_disclosure`
- **section**: Section headings: Easier Earnings and Flexibility; Transparent and Fair Processes

Verbatim text:

> Upfront Tipping: Riders can add a tip before a trip, encouraging faster matches and boosting driver earnings, especially during peak hours.
>
> Instant Payments: Drivers can now instantly cash out earnings up to four times a day, giving them quick access to their income in just seconds.
>
> Earnings Hub: A clearer, more transparent breakdown of weekly earnings shows drivers their share, Uber’s portion, and local taxes, reinforcing Uber’s commitment to transparency.

*Citation: Uber Newsroom India (IndiaSA Comms). Uber's New Features to Make Driving Safer, Easier, and Fairer. Jurisdiction stated or inferred: India. Section headings: Easier Earnings and Flexibility; Transparent and Fair Processes. URL: https://www.uber.com/in/en/newsroom/uber-features-to-make-driving-safer-easier-and-fairer/. Document date: 2024-11-15 (dateline on page). Retrieved: 2026-09-13. Source ID: S20.*

##### Payment processing time and fare changes attributed to Driver Advisory Council input

- **chunk_id**: `L1-1.1-014`
- **source_id**: S21
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.a` (SUPPORTS)
- **policy_surfaces**: `payout_timing`, `fare_revision`
- **section**: Section heading: Transparency in driver earnings

Verbatim text:

> We also got insights into the reasons why some driver partners ask for extra money or refuse online payments. Fuel prices had gone up and driver partners’ earnings were impacted. Online payments were transferred to the driver partners’ accounts after almost a week. To address these issues, we increased fares in major cities to offset the fuel price increases. We also sped up the processing time for online trip payments by introducing a ‘Daily Pay’ process. Now drivers receive payments the day after the trip, except for weekends, when payments hit their accounts on Monday.

*Citation: Uber Newsroom India (IndiaSA Comms Team). Uber announces 2nd edition of Driver Advisory Council. Jurisdiction stated or inferred: India. Section heading: Transparency in driver earnings. URL: https://www.uber.com/in/en/newsroom/uber-second-edition-driver-advisory-council/. Document date: 2023-04-17 (dateline on page). Retrieved: 2026-09-13. Source ID: S21.*

##### Uber India statements on driver earnings levels and incentives

- **chunk_id**: `L1-1.1-015`
- **source_id**: S26
- **source_type**: `company_blog`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (ASSERTED)
- **policy_surfaces**: `earnings_level`, `incentives`
- **section**: Section headings: How much does a driver make with Uber?; How do incentives work? Have incentives changed and why?; Are drivers earning more or less now?; Why do some drivers earn more or less than others?
- **note**: Published 3 March 2017. Uber has not republished an equivalent India-wide earnings figure on its current driver pages, so this remains the most specific figure Uber has itself stated for India in a public document located during this search.

Verbatim text:

> Driving using the Uber App is very different to working as a private driver, taxi driver or even, for example, a shop assistant, where people have set hours and set hourly wages. Uber is at heart an entrepreneurial activity. Earnings are not one size fits all.
>
> Individual driver earnings vary widely and individual driver behaviour – where, when and how much or little drivers choose to drive – also vary widely, which makes averages difficult. Currently, 80% of drivers across India who are online for more than six hours a day make between ₹1,500 and ₹2,500 net, after Uber’s service fee.
>
> Drivers earn money from fares paid by riders, but also from incentives (for instance a driver may earn a certain amount of money once they’ve hit a certain number of trips). These incentives vary widely by individual drivers. They are dynamic, as is our business model, and we are constantly seeking to understand, assess and improve both earnings from fares and our incentives structure.
>
> With sustained high demand from both riders and drivers we can shift from startup mode to a more sustainable business model and begin reducing higher levels of incentives, and invest more in drivers and our products for the long term.
>
> Driver earnings have evolved over time and while some drivers do earn less than three years ago, we believe that driver earnings in India are attractive for the majority even after reductions in incentives and drivers’ costs are taken into account.

*Citation: Uber Blog India (Amit Jain, President of Uber India). Driving with Uber: Setting the record straight. Jurisdiction stated or inferred: India. Section headings: How much does a driver make with Uber?; How do incentives work? Have incentives changed and why?; Are drivers earning more or less now?; Why do some drivers earn more or less than others?. URL: https://www.uber.com/in/en/blog/drivingwithuber/. Document date: 2017-03-03 (dateline on page). Retrieved: 2026-09-13. Source ID: S26.*

##### Pro Perk additional per-trip earning and its exclusions

- **chunk_id**: `L1-1.1-016`
- **source_id**: S03
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `tiered_earnings`, `promotions`, `exclusions`
- **section**: Section heading: Pro Perk - Additional Earnings

Verbatim text:

> Who is Eligible: Driver Partners who achieve either Gold, Platinum or Diamond Tier. Pro Perk is only available in certain Participating Cities, which are subject to change at Uber’s sole discretion without notice.* This Reward is only applicable for Driver Partners who complete the trips using four-wheelers.
>
> Details: Pro Perk provides an additional earning for each Uber Trip taken by Driver Partners in Gold, Platinum and Diamond Tiers. The additional amount may vary based on the Tier of the Driver Partner. This Reward is not applicable on Reserve, Uber Black, IxC, Rentals and Uber XL Trips. Earnings from promos, tips, wait/cancel fees, tolls, and taxes are not included in the calculation of this additional earning.
>
> Uber does not guarantee that Driver Partners will experience higher earnings than earnings received prior to the launch of this Reward.
>
> *Pro Perk currently is only available in the following markets: Hyderabad, Mumbai and Chandigarh. Any further changes to the list of Participating Cities for the purpose of this Reward will be notified by the Uber Driver App.

*Citation: Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction stated or inferred: India. Section heading: Pro Perk - Additional Earnings. URL: https://www.uber.com/in/en/legal/uber-pro-program-terms/. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved: 2026-09-13. Source ID: S03.*

##### Conditions under which a driver receives a cancellation fee

- **chunk_id**: `L1-1.1-017`
- **source_id**: S30
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `cancellation_fee`
- **section**: Article body

Verbatim text:

> A rider cancels a trip request more than the allowed number of minutes after you accept the trip (varies by location) and you’re running on time
>
> A rider doesn’t arrive at the pickup location within the allowed number of minutes of your arrival (varies by location)

*Citation: Uber Technologies Inc. I have an inquiry about cancellation fee (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article served to India. Article body. URL: https://help.uber.com/driving-and-delivering/article/request-cancellation-fee?nodeId=41fee0a6-8941-4418-bf25-3327db4f50aa. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S30.*

##### Uber's description of pricing as an automated process

- **chunk_id**: `L1-1.1-018`
- **source_id**: S08
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `pricing_algorithm`, `automated_decision`
- **section**: Section II.C.2 Pricing

Verbatim text:

> When you provide transportation or a delivery, Uber uses algorithms to determine the amount you’re paid. If you are in a city where the fare is calculated per minute and per mile, you’ll earn a base fare plus additional money for the time and distance you travel (these rates vary by city). If you are in a city where Uber provides an upfront fare that you can review before determining whether to accept the ride or delivery, such fares are calculated based on factors including the current driving conditions, similar destinations, demand for rides at that time, surcharges and reimbursement for tolls, surge pricing and promotions. Uber’s service fees are subtracted from all fares.

*Citation: Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction stated or inferred: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Section II.C.2 Pricing. URL: https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved: 2026-09-13. Source ID: S08.*

##### Drive Pass, the paid subscription that is the stated consideration for platform access

- **chunk_id**: `L1-1.1-020`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (CONTRADICTS)
- **policy_surfaces**: `subscription_model`, `drive_pass`, `platform_access_cost`
- **section**: Section 4.1 Drive Pass

Verbatim text:

> Drive Pass. In consideration of Uber’s provision of the Uber Service, you or your Drivers agree to select and purchase a Drive Pass. Drive Pass is a paid for subscription service provided by Uber that entitles you or your Drivers to access the Uber Service to seek, receive and fulfill requests for Transportation Services from Users. The duration and validity of your Drive Pass will be specified to you and your Drivers in the Driver App at the time of selection of Pass. You agree that the use of the Drive Pass is subject to terms and conditions contained in the Pass Terms (as amended from time to time).
>
> “Drive Pass” means the pass, howsoever termed, selected and purchased by you or Drivers via the Driver App which entitles you to utilise the Uber Service to seek, receive and fulfil requests for Transportation Services from Users. The operation and validity of Drive Pass shall be governed by the Pass Terms available here.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 4.1 Drive Pass. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Service Fee as a fallback charge, and Uber's right to change it

- **chunk_id**: `L1-1.1-021`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (CONTRADICTS), `3.2.a` (PARTIAL)
- **policy_surfaces**: `service_fee`, `unilateral_amendment`, `platform_access_cost`
- **section**: Section 4.2 Fees

Verbatim text:

> Fees. If for any reason Drive Pass is not available to you or in your Territory, you acknowledge and agree that in order to access the Uber Service and/or the Driver App, and for provision of Uber Service, Uber may at its sole discretion, charge you certain periodic fees (whether at the time of signing up on the Driver App or on an ongoing basis), which may be structured as fixed amounts or as variable amounts (“Service Fee”). Uber reserves the right to change the Service Fee (if applicable) at any time at Uber's discretion based upon local market factors, and Uber will provide you with notice in the event of such change. Continued use of Uber Service after any such change in the Service Fee shall constitute your consent to such change.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 4.2 Fees. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### The driver sets the fare and the Suggested Fare is non-binding

- **chunk_id**: `L1-1.1-022`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (CONTRADICTS)
- **policy_surfaces**: `fare_setting`, `suggested_fare`, `fare_negotiation`, `uber_role`
- **section**: Sections 4.3.1 and 4.3.2 Fare Calculation and Payment; definition 1.10 Suggested Fare

Verbatim text:

> You are entitled to charge a fare for each instance of completed Transportation Services provided to a User (“Fare”). You are also entitled to charge the User for any Tolls, taxes or fees incurred during the provision of Transportation Services, if applicable and as communicated to you.
>
> The parties acknowledge and agree that the Suggested Fare provided in the Driver App is for reference purposes only. Uber does not control or interfere with the actual provision of Transportation Services by you, nor does it set, regulate, collect, negotiate, fix or enforce fares. The Uber App may display a Suggested Fare based on typical market rates for a given route as per applicable laws, serving solely as a guideline for you and the User to negotiate and agree upon the final fare.
>
> “Suggested Fare” means the indicative amount suggested by Uber solely for reference purposes, without any binding effect on you or the User, which may include tolls, taxes, and third-party charges, but does not include Uber One membership fees, User’s arrears from a previous trip, insurance, or any other amount not related to the particular instance of Transportation Services.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 4.3.1 and 4.3.2 Fare Calculation and Payment; definition 1.10 Suggested Fare. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### The driver as limited payment collection agent for amounts owed to Uber

- **chunk_id**: `L1-1.1-023`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `collection_agent`, `remittance`, `third_party_fees`
- **section**: Section 4.3.3

Verbatim text:

> You are entitled to collect from Users and you shall subsequently remit to Uber, via any methods made available to you by Uber from time to time, all amounts that are due to Uber or are unrelated to your Fare for Transportation Services, including but not limited to, applicable Uber One membership fee, insurance fees, User Negative Balance on a non-Uber Service trip, airport fees or any other third-party fees. You act as limited payment collection agent for Uber in respect of any amounts due to Uber that you collect from Users, and the collection and remittance of such amounts is not linked to or dependent upon the provision of Transportation Services provided by you directly to the Users.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 4.3.3. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Promotional incentives are discretionary and subject to set-off

- **chunk_id**: `L1-1.1-024`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.a` (PARTIAL)
- **policy_surfaces**: `incentives`, `deductions`, `discretion`
- **section**: Section 4.3.4

Verbatim text:

> Uber may, at its sole discretion, make additional payments to you from time to time, unrelated to the Transportation Services provided by you to Users, such as for promotional incentives. Uber reserves the right to deduct any outstanding amounts owed by you, including amounts that are due for remittance to Uber under Section 4.3.3 above, from such payments.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 4.3.4. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Responsibility for collecting the fare, digital payment handling and the weekly remittance

- **chunk_id**: `L1-1.1-025`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `fare_collection`, `payout_timing`, `collection_agent`, `service_fee`
- **section**: Sections 4.3.5 and 4.3.6

Verbatim text:

> You shall be solely responsible to collect the Fare directly from the User, whether it is the Suggested Fare displayed on the Uber App or such amount as mutually agreed solely between you and the User. Where a User wishes to pay the Fare using a digital mode of payment, you: (a) appoint Uber as your limited payment collection agent solely for the purpose of accepting the Suggested Fare, applicable Tolls, and any other amounts depending on the Territory via the payment processing functionality facilitated by the Uber Services; and (b) agree that payment made by User to Uber shall be considered the same as payment made directly by User to you. Any difference in the Suggested Fare and mutually agreed fare between you or your Drivers and the Users shall be settled directly by the User to you in cash or any other mode agreed upon by both the parties. Where Uber acts your payment collection agent, Uber agrees to remit, or cause to be remitted, to you on at least a weekly basis the Suggested Fare less any applicable Service Fee or any other applicable charges as may be communicated by Uber from time to time.
>
> Where payment is collected directly by you and not facilitated by Uber, the mode of payment and the actual amount paid shall be solely and independently determined by you and the User, without any involvement or control of Uber.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 4.3.5 and 4.3.6. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Allocation of the risk of underpayment, non-payment and cancellation to the driver

- **chunk_id**: `L1-1.1-026`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.a` (CONTRADICTS), `4.1.b` (CONTRADICTS)
- **policy_surfaces**: `payment_risk`, `dispute_resolution`, `cancellation`, `earnings_responsibility`
- **section**: Sections 4.3.7 and 4.3.8

Verbatim text:

> You may charge the User for any applicable Tolls incurred during the provision of Transportation Services. Uber does not oversee and does not assume any responsibility for Fare collection, handling short payments, or mediating payment disputes between you and the User. Any disagreements concerning Fares must be resolved directly between you and the User. Uber bears no liability for any underpayment, overpayment, or non-payment by the User and you acknowledge that all earnings from providing Transportation Services are your sole responsibility.
>
> Uber shall not be responsible for any cancellation of any requests for Transportation Services by the Users or a User's decision to not avail Transportation Services from you.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 4.3.7 and 4.3.8. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### User Negative Balance and who bears the recovery burden

- **chunk_id**: `L1-1.1-027`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.a` (CONTRADICTS)
- **policy_surfaces**: `user_negative_balance`, `remittance`, `payment_risk`
- **section**: Section 4.3.9

Verbatim text:

> In the event that a User has insufficient funds to pay for a given instance of Transportation Services on a non-Uber Service trip (whether in whole or part, each such event is considered an underpayment), Uber shall record it as a negative balance on the User’s account (“User Negative Balance”). If you provide Transportation Services to a User with a User Negative Balance, you may be notified via the Driver App. In such an event:
>
> the Uber App will reflect that the total amount owing by the User comprises (i) the transaction amount owing for that trip; and (ii) the User Negative Balance;
>
> you are under no obligation to compel or demand payment for the User Negative Balance from the User and Uber acknowledges and agrees that it (Uber) bears ultimate responsibility for seeking recourse for any User Negative Balance from Users; and
>
> where the User pays the User Negative Balance in cash to you, you acknowledge and agree that you shall remit such funds to Uber in accordance with Section 4.3.3 above.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 4.3.9. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Tax registration, remittance and GST liability placed on the driver

- **chunk_id**: `L1-1.1-028`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `tax_liability`, `gst`, `cost_allocation`
- **section**: Section 4.4 Taxes

Verbatim text:

> Taxes. You acknowledge and agree that you are required to: (a) complete all tax registration obligations and calculate and remit all tax liabilities related to your provision of Transportation Services as required by applicable law; and (b) provide Uber with all relevant tax information (including a valid GST, PAN, Aadhar Number and Tax Registration Number belonging to you, to the extent that such numbers are required of you). You further acknowledge and agree that you are responsible for all taxes on your respective income arising from the provision of Transportation Services. Further, You shall be solely responsible for paying GST on the transportation services provided by you to the Users and Uber shall have no liability to pay tax on such services on your behalf.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 4.4 Taxes. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Equipment, tools and materials to be supplied by the driver at their own expense

- **chunk_id**: `L1-1.1-029`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (CONTRADICTS)
- **policy_surfaces**: `cost_allocation`, `equipment`
- **section**: Section 2.2 Provision of Transportation Services

Verbatim text:

> As between Uber and you, you agree and acknowledge that: (a) you and/or your Driver shall solely determine the most effective, efficient and safe manner to perform each instance of Transportation Services; and (b) you and/or your Driver shall possess all necessary equipment, tools and other materials necessary to perform Transportation Services, at your own expense.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.2 Provision of Transportation Services. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Device and data plan costs placed on the driver

- **chunk_id**: `L1-1.1-030`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (CONTRADICTS)
- **policy_surfaces**: `cost_allocation`, `equipment`, `data_costs`
- **section**: Section 2.8.3 Device

Verbatim text:

> Device. In your use of the Device: (i) you and/or your Drivers are responsible for the acquisition, cost and maintenance of such Device as well as any necessary wireless data plan; and (ii) Uber shall make available the Driver App for installation on such Device.
>
> You agree, and shall inform each applicable Driver that: (i) use of the Driver App on the Device requires an active data plan with a wireless carrier associated with the Device, which data plan will be provided either by you or the applicable Driver at your or their own expense; and (ii) use of the Driver App on a Device may consume very large amounts of data through the data plan. Uber advises that the Device should only be used under a data plan with unlimited or very high data usage limits, and Uber shall not be responsible or liable for any fees, costs, or overage charges associated with any data plan.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.8.3 Device. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### The same fare model stated to riders for Mumbai auto trips

- **chunk_id**: `L1-1.1-031`
- **source_id**: S33
- **source_type**: `company_terms_rider_facing`
- **jurisdiction**: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners.
- **audience**: `mixed`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `fare_setting`, `suggested_fare`, `fare_negotiation`, `direct_payment`
- **section**: Sections 2.1, 2.2 and 2.3 Fare Estimation, Negotiation & Payment Responsibilities
- **driver_relevance**: Rider-facing addendum. It states the fare mechanism the Mumbai auto driver partner operates under, including that the Suggested Fare does not bind the driver, that rider and driver negotiate the fare, and that the rider pays the driver directly.
- **note**: Rider-facing addendum. It states Uber's position on the auto SaaS fare model in Mumbai and is reproduced because it describes the driver partner's fare-setting role from the other side of the transaction.

Verbatim text:

> The Uber App may display a Suggested Fare, but this amount is not binding on the Driver Partner or You. The Suggested Fare is shown merely for reference. You and the Driver Partner may mutually agree on a different fare before or during the ride.
>
> Uber does not interfere in the negotiation of final fare between the Rider and the Driver Partner. You must pay the agreed fare directly to the Driver Partner in cash or any other mode agreed upon by both parties. However, on request, Uber may facilitate digital payments for Driver Partners based on suggested fare displayed on the app. Any difference in the suggested fare and mutually agreed fare between the Rider and the Driver Partner shall be settled directly to the Driver Partner in cash or any other mode agreed upon by both the parties. Uber does not assume responsibility for disputes regarding payment. Any disagreements between the Driver Partner and You concerning fares must be resolved directly between them. Uber does not provide transportation services and is not responsible for setting or enforcing fares or resolving disputes, if any.
>
> You are solely responsible for paying any applicable additional charges:
>
> Tolls, state taxes, parking fees, or route-specific surcharges as communicated by the Driver Partner.
>
> Any other costs incurred during the trip.

*Citation: Uber India Systems Private Limited. Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai). Jurisdiction stated or inferred: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners. Sections 2.1, 2.2 and 2.3 Fare Estimation, Negotiation & Payment Responsibilities. URL: https://www.uber.com/in/en/legal/india-auto-saas-rider-terms-and-conditions---mumbai/. Document date: 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025. Retrieved: 2026-09-13. Source ID: S33.*

##### Platform-related charges collected from riders that are unrelated to the trip

- **chunk_id**: `L1-1.1-032`
- **source_id**: S33
- **source_type**: `company_terms_rider_facing`
- **jurisdiction**: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners.
- **audience**: `mixed`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.b` (PARTIAL)
- **policy_surfaces**: `third_party_fees`, `service_fee`
- **section**: Section 3 Platform-Related Charges & Other Fees
- **driver_relevance**: Rider-facing addendum. It operates on the driver because these are the non-trip amounts the driver collects from the rider and remits to Uber under S32 Section 4.3.3.

Verbatim text:

> Certain charges may apply to You that are unrelated to any specific trip, including, Uber One membership fees (if applicable), insurance fees, outstanding payments from non-auto Uber trips, Airport/ station pickup surcharges or access fees.The collection of such fees is not linked to or dependent on the provision of actual passenger transportation services rendered by the Drivers directly to the riders
>
> Uber may charge administrative or service fees including applicable GST and other taxes.

*Citation: Uber India Systems Private Limited. Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai). Jurisdiction stated or inferred: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners. Section 3 Platform-Related Charges & Other Fees. URL: https://www.uber.com/in/en/legal/india-auto-saas-rider-terms-and-conditions---mumbai/. Document date: 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025. Retrieved: 2026-09-13. Source ID: S33.*

##### Non-refundability and allocation of fare disputes between rider and driver

- **chunk_id**: `L1-1.1-033`
- **source_id**: S33
- **source_type**: `company_terms_rider_facing`
- **jurisdiction**: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners.
- **audience**: `mixed`
- **levers**: L1
- **threshold**: 1.1
- **criteria**: `1.1.a` (CONTRADICTS), `4.1.b` (CONTRADICTS)
- **policy_surfaces**: `payment_risk`, `dispute_resolution`, `non_refundable`
- **section**: Section 4.1 Limitation of Liability
- **driver_relevance**: Rider-facing addendum. It allocates the risk of an incomplete ride, stating that what the rider has paid the driver is not refundable, and that fare and service disputes are settled between rider and driver with Uber outside them.

Verbatim text:

> Uber only facilitates connections between Riders and Driver Partners and is not responsible for ride completion, fare disputes, delays, or service quality. Any dispute over fare, service refusal, or ride experience must be resolved directly between the Rider and the Driver Partner. Any charges paid by the user to the Driver Partner is non-refundable, even in cases where a ride is not completed.

*Citation: Uber India Systems Private Limited. Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai). Jurisdiction stated or inferred: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners. Section 4.1 Limitation of Liability. URL: https://www.uber.com/in/en/legal/india-auto-saas-rider-terms-and-conditions---mumbai/. Document date: 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025. Retrieved: 2026-09-13. Source ID: S33.*

##### Uber's reserved right to deduct and recover amounts from driver payments

- **chunk_id**: `L3-3.1-010`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L3
- **threshold**: 1.1
- **criteria**: `1.1.a` (PARTIAL)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `deductions`, `contract_breach`, `recovery_of_damages`
- **section**: Footer note headed Policy violations

Verbatim text:

> Policy violations: This page outlines common reasons for losing account access, but if a driver violates any terms of their contractual agreement with Uber, or any applicable terms or policies, including the Community Guidelines, they can lose access to all or part of the Uber platform. We reserve the right to deduct, compensate, or recover damages related to misuse of the platform from any amount that the driver may have to receive, besides taking the appropriate legal actions. Examples of amounts that may be deducted, compensated, or charged, if improper behavior is suspected, include, but are not limited to, fees, promotions, referral values, promotional codes, trip prices, trip adjustment prices, cancellation fees, promotional trip prices, and miscellaneous payments.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Footer note headed Policy violations. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

*No absence is recorded under this threshold.*

### 4.2 Threshold 1.2 — Ensures workers earn at least a local living wage after costs

- **threshold_id**: 1.2
- **lever**: L1
- **criteria**: `1.2.a`
- **extract_count**: 0
- **audience_driver**: 0
- **audience_mixed**: 0
- **absence_count**: 5

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> In some places, the minimum wage is not enough to allow workers to afford a basic
> but decent standard of living. To achieve this point platforms must ensure that work-
> related costs do not push workers below local living wage. The platform takes
> appropriate steps to ensure the following:

- **[1.2.a]** Workers earn at least a local living wage, or the wage set by collective sectoral agreement (whichever is higher) in the place where they work, in their active hours, after costs.[5][6]

> **INLINED FOOTNOTE [5]**
> Where a living wage does not exist, Fairwork will use the Global Living Wage Coalition's Anker Methodology
> to estimate one.

> **INLINED FOOTNOTE [6]**
> In order to evidence this, where the platform is responsible for paying workers the platform must either: (a)
> have a documented policy that ensures the workers receive at least the local living wage after costs in their active
> hours; or (b) provide summary statistics of transaction and cost data evidencing all workers earn a living wage after
> costs.

#### Extracts from official Uber documentation

*No extract from official Uber documentation is filed under this threshold.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_1_2_01** — bears on `1.2.a`: No official Uber document located for India states a minimum wage floor, a living wage floor, or any guaranteed hourly or daily earnings level for driver partners. Uber does not explicitly mention the local minimum wage or the local living wage in the India driver documentation reviewed.
- **absence_1_2_02** — bears on `1.2.a`: The published India driver Services Agreement states the opposite of a company-set wage: “Uber does not control or interfere with the actual provision of Transportation Services by you, nor does it set, regulate, collect, negotiate, fix or enforce fares” (S32, Section 4.3.2), and “you acknowledge that all earnings from providing Transportation Services are your sole responsibility” (S32, Section 4.3.7).
- **absence_1_2_03** — bears on `1.2.a`: No official Uber document located for India states that remuneration is measured after work-related costs are deducted. The Services Agreement allocates those costs to the driver: equipment, tools and materials “at your own expense” (S32, Section 2.2), device and data plan cost (S32, Section 2.8.3), vehicle maintenance (S32, Section 3.2), insurance “at your sole cost and expense” (S32, Section 8.1), the Drive Pass subscription (S32, Section 4.1), and all taxes including GST (S32, Section 4.4). No net-of-costs earnings threshold is set anywhere.
- **absence_1_2_04** — bears on `1.2.a`: No official Uber document located for India commits to compensating or accounting for time spent logged in and waiting for a trip request. Uber does not explicitly mention payment for waiting or searching time.
- **absence_1_2_05** — bears on `1.2.a`: Uber’s own India statement on earnings levels (S26, 2017) explicitly declines to set a standard: “Earnings are not one size fits all.” No later India-specific figure was located on an Uber-published page.

## 5. Lever L2 — Fair Conditions

- **lever**: L2
- **fairwork_principle**: P2
- **thresholds**: 2.1, 2.2

### 5.1 Threshold 2.1 — Mitigates task specific risk

- **threshold_id**: 2.1
- **lever**: L2
- **criteria**: `2.1.a`, `2.1.b`, `2.1.c`
- **extract_count**: 13
- **audience_driver**: 13
- **audience_mixed**: 0
- **absence_count**: 3

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> The platform must satisfy the following:

- **[2.1.a]** Adequate equipment and training are provided to protect workers' health and safety from task-specific risks.[7] These should be implemented at no additional cost to the worker.
- **[2.1.b]** The platform mitigates the risks of lone working by providing adequate support and designing processes with occupational safety and health in mind.
- **[2.1.c]** Platforms take meaningful steps to ensure that workers do not suffer significant costs as a result of accident, injury or disease resulting from work.

> **INLINED FOOTNOTE [7]**
> The ILO recognises health and safety at work as a fundamental right. Where the platform directly engages the
> worker, the starting point is the ILO's Occupational Safety and Health Convention, 1981 (C155). This stipulates that
> employers shall be required "so far as is reasonably practicable, the workplaces, machinery, equipment and
> processes under their control are safe and without risk to health", and that "where necessary, adequate protective
> clothing and protective equipment [should be provided] to prevent, so far as is reasonably practicable, risk of
> accidents or of adverse effects on health."

#### Extracts from official Uber documentation

##### Maximum continuous driving time and mandatory offline period

- **chunk_id**: `L2-2.1-001`
- **source_id**: S18
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help global English article. No India-specific version was located.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `1.1.b` (CONTRADICTS), `2.1.b` (SCOPE LIMITED), `2.2.c` (SCOPE LIMITED)
- **policy_surfaces**: `driving_hours_limit`, `rest_period`, `fatigue_management`
- **section**: Article body
- **note**: This Uber Help article is a global English article. No India-specific driving-hours-limit page published by Uber was located during this search, so the India applicability of the 12-hour figure is not asserted on an Uber India page.

Verbatim text:

> Uber drivers may transport passengers in their vehicles for up to 12 hours. After 12 hours, drivers must be offline for 6 consecutive hours before driving again.
>
> If you go offline at any point, that time will not be counted toward the 12-hour limit.
>
> Any time spent online and driving with Uber counts toward the 12-hour driving limit. Time spent engaged in driving will count, for example, when you are temporarily stopped at a traffic light. If you’re online but stopped, for instance, waiting for a trip in an airport parking lot, that time is not counted.
>
> You’ll know if you’re getting close to your maximum driving time through the app. We’ll notify you 2 hours, 1 hour, and 30 minutes before you reach the 12-hour driving limit so you can plan when you want to go offline.
>
> Anytime you’re offline for 6 or more hours, your driving hours will reset to 12.

*Citation: Uber Technologies Inc. Driving time limit (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help global English article. No India-specific version was located. Article body. URL: https://help.uber.com/en/driving-and-delivering/article/driving-time-limit?nodeId=a50a72e1-d315-4154-ac66-b17bd5bd050a. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S18.*

##### Safety obligations placed on drivers in the India Community Guidelines

- **chunk_id**: `L2-2.1-002`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.a` (ASSERTED)
- **policy_surfaces**: `driver_safety_duties`, `fatigue_management`
- **section**: Section heading: Safety first

Verbatim text:

> Everyone wants to get from A to B safely. So please ensure that you follow the local law. Check out our rider safety tips. When you’re sitting in the car, buckle up. Of course, drivers have a particular responsibility when it comes to safety at Uber. That means keeping to the speed limit; not texting while driving; always using a phone mount; and never driving under the influence of alcohol or drugs. And if you’re driving and feel tired, take a break. As the experts say, “sleep is the only true preventative measure against the risks of drowsy driving.”

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section heading: Safety first. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

##### Driver Safety Toolkit as launched in India

- **chunk_id**: `L2-2.1-003`
- **source_id**: S25
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.a` (PARTIAL), `2.1.b` (SUPPORTS)
- **policy_surfaces**: `in_app_safety_features`, `emergency_button`
- **section**: Section heading: Driver Safety Toolkit

Verbatim text:

> With the objective of offering a safer experience for everyone and to create an environment of mutual respect, Uber, the world’s largest on-demand ride-sharing company, launched its “Driver Safety Toolkit” — a comprehensive set of in-app safety features for driver partners — in India today.
>
> Share Trip. Driver partners can now share their trip details with their loved ones straight from the app, letting their family and friends follow them along as they drive.
>
> Emergency button.The Emergency assistance button offers driver partners an option to connect with law enforcement during an unwanted emergency situation
>
> Speed Limit. A feature where driver partners will be alerted when they exceed the speed so that they can drive at safe speeds for their personal safety, the comfort of their riders, as well as others on the road.
>
> For Uber, India was the first market where the emergency button was launched. Now, it will be a part of a larger Safety Toolkit in the app, giving driver partners access to all possible protective and preventive measures under the shield icon.

*Citation: Uber Newsroom India (IndiaSA Comms Team). Uber puts Safety at the heart of Driver Experience. Jurisdiction stated or inferred: India. Section heading: Driver Safety Toolkit. URL: https://www.uber.com/in/en/newsroom/uber-puts-safety-at-the-heart-of-driver-experience/. Document date: 2019-01-29 (dateline on page). Retrieved: 2026-09-13. Source ID: S25.*

##### Safety features listed on the India driver safety page

- **chunk_id**: `L2-2.1-004`
- **source_id**: S15
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.a` (PARTIAL), `2.1.b` (SUPPORTS), `4.2.e` (ASSERTED)
- **policy_surfaces**: `in_app_safety_features`, `incident_response`, `gps_tracking`, `ridecheck`
- **section**: Section heading: Your safety drives us

Verbatim text:

> Safety is designed into the experience. So you feel comfortable driving at night. So you can tell loved ones where you’re going. And so you know you have someone to turn to if anything happens.*
>
> 24/7 incident support
>
> Uber customer associates trained in incident response are available around the clock.
>
> Follow My Ride
>
> Friends and family can follow your route and will know as soon as you arrive.
>
> 2-way ratings
>
> Your feedback matters. Low-rated trips are logged, and users may be removed to protect the Uber community.
>
> Anonymous Calls
>
> We use technology to help keep your phone number private, so neither drivers nor riders will see each other’s numbers when communicating through the Uber app.
>
> GPS tracking
>
> All Uber trips are tracked from start to finish, so there’s a record of your trip if something happens.
>
> RideCheck
>
> Using sensors and GPS data, RideCheck can help detect if a trip has an unexpected long stop. If so, we’ll check on you and offer tools to get help.
>
> Emergency assistance button
>
> You can use the in-app Emergency Button to call local authorities to get help if you need it. The app displays your location and trip details, so you can quickly share them with emergency dispatchers.
>
> Speed Limits Alerts
>
> To help keep you safe, the app will notify you if you are going above the speed limit.
>
> Dangerous Driving Notifications
>
> Personalized driver feedback helps contribute to safer roads.
>
> *Certain requirements and features vary by region and may be unavailable.

*Citation: Uber Technologies Inc. Drive with confidence (Driver Safety). Jurisdiction stated or inferred: India. Section heading: Your safety drives us. URL: https://www.uber.com/in/en/drive/safety/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S15.*

##### India-specific safety features announced in November 2024

- **chunk_id**: `L2-2.1-005`
- **source_id**: S20
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.a` (CONTRADICTS), `2.1.b` (SUPPORTS)
- **policy_surfaces**: `in_app_safety_features`, `helmet_verification`, `gender_matching`, `audio_recording`
- **section**: Section heading: Safer Driving Experience

Verbatim text:

> Uber has launched industry-first safety features to provide additional security and confidence to drivers:
>
> Helmet Selfie Verification: Two-wheeler drivers will now be prompted to take a selfie with their helmet on before each trip, reinforcing road safety and aligning with government guidelines for safer roads.
>
> Women Rider Preference: Female drivers can now match exclusively with female riders, especially helpful during late hours, creating a safer, more comfortable experience.
>
> Audio Recording: Drivers can activate audio recording if they feel uncomfortable during a trip. These encrypted recordings are stored securely and can only be accessed if submitted for a safety report, offering peace of mind without compromising privacy.

*Citation: Uber Newsroom India (IndiaSA Comms). Uber's New Features to Make Driving Safer, Easier, and Fairer. Jurisdiction stated or inferred: India. Section heading: Safer Driving Experience. URL: https://www.uber.com/in/en/newsroom/uber-features-to-make-driving-safer-easier-and-fairer/. Document date: 2024-11-15 (dateline on page). Retrieved: 2026-09-13. Source ID: S20.*

##### Vehicle maintenance standard imposed on the driver

- **chunk_id**: `L2-2.1-006`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.a` (CONTRADICTS)
- **policy_surfaces**: `vehicle_standards`, `cost_allocation`
- **section**: Section heading: Safety issues, sub-heading Unsafe vehicles

Verbatim text:

> This includes not maintaining a vehicle according to industry safety and maintenance standards. For example, not keeping brakes, seat belts, and tires in good operating condition; disregarding recalls; and ignoring dashboard warning lights.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Safety issues, sub-heading Unsafe vehicles. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Licensing, training and professionalism obligations on the driver

- **chunk_id**: `L2-2.1-007`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.a` (CONTRADICTS)
- **policy_surfaces**: `licensing`, `competence`, `professional_standards`, `background_check`
- **section**: Section 3.1 Your/Driver Requirements

Verbatim text:

> (a) hold and maintain:
>
> (i) a valid driver's license with the appropriate level of certification to operate the Vehicle assigned by you to yourself or to such Drivers, and
>
> (ii) all licenses, permits, approvals and authority applicable to you and/or your Drivers that are necessary to provide passenger transportation services to third parties in the Territory;
>
> (b) possess the appropriate and current level of training, expertise and experience to provide Transportation Services in a professional manner with due skill, care and diligence; and
>
> (c) maintain high standards of professionalism, service and courtesy. You acknowledge and agree that you or your Drivers may be subject to certain background and driving record checks from time to time in order for you or your Drivers to qualify to provide, and remain eligible to provide, Transportation Services.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 3.1 Your/Driver Requirements. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Vehicle condition and maintenance obligations

- **chunk_id**: `L2-2.1-008`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.a` (CONTRADICTS)
- **policy_surfaces**: `vehicle_standards`, `cost_allocation`
- **section**: Section 3.2 Vehicle Requirements

Verbatim text:

> Vehicle Requirements. You acknowledge and agree that each Vehicle shall at all times be: (a) properly registered and licensed to operate as a passenger transportation vehicle in the Territory; (b) owned or leased by you or your Driver, or otherwise in your or your Driver's lawful possession; (c) suitable for performing the passenger transportation services contemplated by this Agreement; and (d) maintained in good operating condition, consistent with industry safety and maintenance standards for a Vehicle of its kind and any additional standards or requirements in the applicable Territory, and in a clean and sanitary condition.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 3.2 Vehicle Requirements. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Allocation of safety precautions and third-party risk to the driver

- **chunk_id**: `L2-2.1-009`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.b` (CONTRADICTS)
- **policy_surfaces**: `risk_allocation`, `safety_precautions`, `liability`
- **section**: Section 2.3 Your Relationship with Users

Verbatim text:

> You acknowledge and agree that you and each of your Drivers are solely responsible for taking such precautions as may be reasonable and proper (including maintaining adequate insurance that meets the requirements of all applicable laws) regarding any acts or omissions of a User or third party.
>
> You and/or your Drivers are solely responsible and liable for any failure to complete an accepted request of Transportation Services, failure to pick up User(s) at the requested time and/or pick-up location, any act or omission including rash and negligent driving, harassment (whether verbal, physical or of any other nature), any violation or non-adherence to applicable laws, any physical and/or mortal danger caused to the Users while providing Transportation Services, charging amounts from the Users that are different from the Suggested Fare and for providing the Transportation Services in your capacity as an independent service provider.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.3 Your Relationship with Users. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Uber's disclaimer regarding harm or risk from third parties encountered through the platform

- **chunk_id**: `L2-2.1-010`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.b` (CONTRADICTS), `3.2.b` (CONTRADICTS)
- **policy_surfaces**: `risk_allocation`, `safety_disclaimer`, `user_screening`
- **section**: Section 9.2 Disclaimer of Warranties

Verbatim text:

> Uber and its Affiliates function as an on-demand lead generation and related service providers only and make no representations, warranties or guarantees as to the actions or inactions of the Users who may request or receive Transportation Services from you or your Drivers hereunder, and Uber and its Affiliates need not screen or otherwise evaluate Users. By using the Uber Service and Driver App, you acknowledge and agree that you or your Drivers may be introduced to a third party (including Users) that may pose harm or risk to you, your Drivers or other third parties. You and your Drivers are advised to take reasonable precautions with respect to interactions with third parties encountered in connection with the use of the Uber Service or Driver App.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 9.2 Disclaimer of Warranties. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Discretionary basis on which Uber states it may provide safety and support services

- **chunk_id**: `L2-2.1-011`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.b` (CONTRADICTS)
- **policy_surfaces**: `safety_support`, `discretion`
- **section**: Section 2.4 Your Relationship with Uber

Verbatim text:

> Uber may provide safety and support services to you at its sole discretion subject to compliance with applicable laws.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.4 Your Relationship with Uber. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### On-trip accident insurance for India driver partners

- **chunk_id**: `L2-2.2-004`
- **source_id**: S27
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.c` (ASSERTED)
- **refiled_from**: 2.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `insurance_access`
- **section**: Article body

Verbatim text:

> Last year, we launched on-trip accident insurance for the driver partners to protect their families. And now we have Uber Care, an industry-first initiative that is aimed at providing welfare choices to thousands of driver partners who choose to drive on the Uber app every day. Uber Care helps the driver partner seek health and life insurance and micro-credit opportunities from leading insurance and credit companies to safeguard and empower their families, and fulfil aspirations that may have gone abegging in their own lives.

*Citation: Uber Newsroom India (Prabhjeet Singh). Keeping driver partners at heart. Jurisdiction stated or inferred: India. Article body. URL: https://www.uber.com/in/en/newsroom/keeping-driver-partners-at-heart/. Document date: 2018-12-20 (dateline on page). Retrieved: 2026-09-13. Source ID: S27.*

##### Uber's statement that a commercial motor policy may not cover the driver while providing Transportation Services

- **chunk_id**: `L2-2.2-009`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.1
- **criteria**: `2.1.c` (CONTRADICTS)
- **refiled_from**: 2.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `insurance_gap`, `risk_allocation`
- **section**: Section 8.4 Insurance

Verbatim text:

> You understand and acknowledge that your commercial automobile insurance policy may not afford liability, comprehensive, collision, medical payments, first or third party no fault personal injury protection, uninsured motorist, underinsured motorist or other coverage while you provide any Transportation Services pursuant to this Agreement. If you have any questions or concerns about the scope or applicability of your own insurance coverage, it is your responsibility, not Uber’s, to resolve them with your insurer(s).

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 8.4 Insurance. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_2_1_02** — bears on `2.1.b`: No official Uber document located for India describes a systematic process for identifying, assessing and monitoring occupational health and safety risks for driver partners, including psychological or psychosocial risk. Uber does not explicitly mention occupational risk assessment for drivers in the India documentation reviewed.
- **absence_2_1_04** — bears on `2.1.b`: The published India driver Services Agreement states that provision of safety and support services is discretionary rather than owed: “Uber may provide safety and support services to you at its sole discretion” (S32, Section 2.4). The in-app safety features described at S15, S20 and S25 are not stated in the Agreement as contractual entitlements.
- **absence_2_2_03** — bears on `2.1.c`: The published India driver Services Agreement places industrial-injury cover on the driver and makes it optional: “if permitted by applicable law, you may choose not to insure yourself or your Drivers against industrial injuries at all, but you shall do so at your own risk” (S32, Section 8.3). All insurance required by the Agreement is to be obtained “at your sole cost and expense” (S32, Section 8.1).  *(Re-filed from 2.2.)*

### 5.2 Threshold 2.2 — Ensures safe working conditions and a safety net

- **threshold_id**: 2.2
- **lever**: L2
- **criteria**: `2.2.a`, `2.2.b`, `2.2.c`
- **extract_count**: 9
- **audience_driver**: 9
- **audience_mixed**: 0
- **absence_count**: 5

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> Platform workers are vulnerable to the possibility of abruptly losing their income as the
> result of unexpected or external circumstances, such as, for example, sickness, or
> parenthood. Most countries provide a social safety net to ensure workers don't
> experience sudden poverty due to circumstances outside their control.[8] However,
> platform workers usually don't qualify for protections such as sick pay, because of
> their independent contractor status. In recognition of the fact that most workers are
> dependent on income they earn from platform work, platforms should ensure that
> workers are compensated for loss of income due to inability to work. In addition,
> platforms must minimise the risk of sickness and injury even when all the basic steps
> have been taken.

> **INLINED FOOTNOTE [8]**
> The ILO's Social Security (Minimum Standards) Convention, 1952 (No. 102), establishes nine classes of benefit
> (medical care and benefits in respect of sickness, unemployment, old age, employment injury, family, maternity,
> invalidity and survivors). Source: https://webapps.ilo.org/public/english/revue/download/pdf/ghai.pdf, p.122.

> The platform must satisfy ALL of the following:

- **[2.2.a]** Platform take meaningful steps towards the social protection of its workers.
- **[2.2.b]** Where workers are unable to work for an extended period due to unexpected circumstances, their standing on the platform is not negatively impacted.
- **[2.2.c]** The platform implements policies or practices that protect workers' safety from task-specific risks. (See footnote 7) In particular, the platform should ensure that pay is not structured in a way that incentivizes workers to take excessive levels of risk.

> **INLINED FOOTNOTE [7] (re-cited at [2.2.c] as "See footnote 7")**
> The ILO recognises health and safety at work as a fundamental right. Where the platform directly engages the
> worker, the starting point is the ILO's Occupational Safety and Health Convention, 1981 (C155). This stipulates that
> employers shall be required "so far as is reasonably practicable, the workplaces, machinery, equipment and
> processes under their control are safe and without risk to health", and that "where necessary, adequate protective
> clothing and protective equipment [should be provided] to prevent, so far as is reasonably practicable, risk of
> accidents or of adverse effects on health."

#### Extracts from official Uber documentation

##### Insurance and wellness offered as an Uber Pro reward in India

- **chunk_id**: `L2-2.2-001`
- **source_id**: S03
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.2
- **criteria**: `2.2.a` (PARTIAL)
- **policy_surfaces**: `insurance_access`, `third_party_provision`, `uber_disclaimer`
- **section**: Section heading: Insurance & Wellness

Verbatim text:

> Who is Eligible:
>
> All Program Members are eligible for special insurance and wellness offers offered by the third party service providers including but not limited to insurers, insurance brokers, Master Policyholders and wellness service providers offering these services. Please check your Uber Driver App from time to time to see whether this Reward is available in your Participating City.
>
> Details: This Reward is for Program Members across all Tiers. The Program Members will be communicated a helpline number and the Program Members shall be required to call on this number to avail this Reward.
>
> This Reward may also require acceptance to additional terms and conditions of the relevant insurers, Brokers, Master Policyholders and the wellness service providers. Uber makes no guarantee as to specific conditions on which the insurance or wellness offers may be provided by the respective service providers. All the financial transactions in relation to the grant of insurance shall be between these service providers and the concerned Driver Partners. The ultimate decision of granting the insurance and decision on eligibility of a Program Member for the insurance and wellness benefits shall be at the sole discretion of these service providers.
>
> By participating in Uber Pro, the Driver Partners hereby consent to becoming a member of the Master Policyholder’s relevant group for availing relevant offers including but not limited to insurance. Membership of the group of the Master Policyholder is subject to the terms and conditions governing such membership and Uber does not bear any responsibility towards the same.
>
> The Driver Partners hereby acknowledge that Uber, its subsidiaries, associates, directors or its employees are not engaged in the business of solicitation for insurance. Uber is neither an insurer nor an intermediary and does not earn any premium, commission, brokerage or any other benefit from the subscription of these insurance products by the Driver Partners. All insurance products are underwritten directly by the relevant insurers subject to such terms that govern the issuance of such products.

*Citation: Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction stated or inferred: India. Section heading: Insurance & Wellness. URL: https://www.uber.com/in/en/legal/uber-pro-program-terms/. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved: 2026-09-13. Source ID: S03.*

##### Micro credit access as an Uber Pro reward in India

- **chunk_id**: `L2-2.2-002`
- **source_id**: S03
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.2
- **criteria**: `2.2.a` (PARTIAL)
- **policy_surfaces**: `credit_access`, `third_party_provision`, `uber_disclaimer`
- **section**: Section heading: Micro Credit Access

Verbatim text:

> Driver Partners-cum-car owners in the Blue, Gold, Platinum and Diamond tiers who meet the eligibility criteria at the relevant time shall be eligible for loans from third parties in their Participating City, subject to fulfillment of other conditions as may be imposed by such third parties. Please check your Uber App from time to time to see whether the said Reward is available in your Participating City.
>
> Details: Availing benefit of this Reward may also require acceptance to additional terms and conditions of the third party.
>
> Uber neither specifies nor has any control over the specific conditions on which the loan may be provided by the third party. All the financial transactions in relation to the grant of loan shall be between the third party and the relevant Driver Partners. The ultimate decision of granting the loan and decision on eligibility of a Program Member for a loan shall be at the sole discretion of the third party.
>
> This Reward may also require disclosing certain information of the Program Member by us to the concerned third party, which shall be subject to our Privacy Notice.

*Citation: Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction stated or inferred: India. Section heading: Micro Credit Access. URL: https://www.uber.com/in/en/legal/uber-pro-program-terms/. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved: 2026-09-13. Source ID: S03.*

##### Uber Care insurance and micro-loan programme for India

- **chunk_id**: `L2-2.2-003`
- **source_id**: S23
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.2
- **criteria**: `2.2.a` (PARTIAL)
- **policy_surfaces**: `insurance_access`, `credit_access`, `social_protection`
- **section**: Article body

Verbatim text:

> Uber, the world’s largest on-demand ride-sharing company, has announced the launch of Uber Care, a first-of-its-kind comprehensive platform for thousands of driver partners who choose to drive using the Uber App. The platform provides easy access to Term insurance from HDFC Life Insurance Company Ltd., a family health insurance program from Reliance General Insurance Company Ltd and driver partners can also avail micro-loan(s) from Supermoney (GetClarity Fintech Services Pvt Ltd).
>
> Uber Care facilitates driver partners across the country with access to a life insurance program with insured sums ranging from INR 200,000 to 1,000,000 from HDFC Life. Additionally, the program also includes a separate family health insurance coverage including the driver partner, his/her spouse and first two children from Reliance General Insurance. Driver partners can also access microloans within a range of INR 5,000 up to INR 25,000 at a monthly interest rate of 2% from Supermoney (GetClarity Fintech Services Pvt Ltd). With the introduction of Uber Care, the company aims to extend its support not just to driver partners but their families as well, providing them with financial security and stability.

*Citation: Uber Newsroom India (Shonali Chakravarty). Uber introduces Uber Care for its driver partner community in India. Jurisdiction stated or inferred: India. Article body. URL: https://www.uber.com/in/en/newsroom/ubercare/. Document date: 2018-11-26 (dateline on page). Retrieved: 2026-09-13. Source ID: S23.*

##### COVID-period welfare expenditure stated by Uber India

- **chunk_id**: `L2-2.2-005`
- **source_id**: S24
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.2
- **criteria**: `2.2.a` (ASSERTED)
- **policy_surfaces**: `hardship_fund`, `social_protection`
- **section**: Article body

Verbatim text:

> In line with that, Uber committed approx. INR 100 crores towards supporting drivers partners and their families to weather the impact of COVID 19.
>
> Driver partners across Moto, Auto and Car have benefited from initiatives like the Uber Care Driver fund, COVID financial assistance, vaccination compensation for drivers, safety kit distribution, free online doctor consultation, and micro-loans.
>
> Uber Care Driver Fund: To help driver partners during the early days of the pandemic, we created the Uber Care Driver Fund, with an initial commitment of INR 25 crores from Uber, benefitting approximately 1,00,000 driver partners.
>
> Prioritising Safety: We spent INR 6 crores each towards safety kit and safety screen distribution among driver partners.
>
> COVID Financial Assistance: Earlier this year, we announced approximately 2 crores worth of COVID financial assistance program for driver partners.
>
> Driver Vaccination: An additional INR 18.5 crore worth of cash incentives was pledged to encourage driver partners to get vaccinated by compensating them for the time spent in getting the shots. More than 300,000 driver partners on our platform have already received at least one vaccine shot.
>
> Micro Loans: Micro loans worth INR 18 crores were facilitated for driver partners in the last 2 years (2020 and 2021)
>
> Online Doctor Consultations: Over 75K drivers and their families were facilitated free online doctor consultations in the last 2 years (2020 and 2021)
>
> Miscellaneous: Another INR 22.6 crores went into various other driver benefits, and forging meaningful partnerships with the driver community.

*Citation: Uber Newsroom India (IndiaSA Comms Team). Uber commits INR 100 crores towards driver welfare initiatives. Jurisdiction stated or inferred: India. Article body. URL: https://www.uber.com/in/en/newsroom/uber-commits-inr-100-crores-towards-driver-welfare-initiatives/. Document date: 2021-12-15 (dateline on page). Retrieved: 2026-09-13. Source ID: S24.*

##### Support for e-Shram registration under the Code on Social Security

- **chunk_id**: `L2-2.2-006`
- **source_id**: S20
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.2
- **criteria**: `2.2.a` (PARTIAL)
- **policy_surfaces**: `social_protection`, `statutory_registration`
- **section**: Section heading: Supporting Social Security

Verbatim text:

> Aligned with India’s Code on Social Security, Uber is also supporting driver registrations on the e-Shram portal, a national database for gig and unorganized workers. To encourage sign-ups, Uber is offering cash incentives to the first 10,000 drivers who register, helping drivers secure future social benefits.

*Citation: Uber Newsroom India (IndiaSA Comms). Uber's New Features to Make Driving Safer, Easier, and Fairer. Jurisdiction stated or inferred: India. Section heading: Supporting Social Security. URL: https://www.uber.com/in/en/newsroom/uber-features-to-make-driving-safer-easier-and-fairer/. Document date: 2024-11-15 (dateline on page). Retrieved: 2026-09-13. Source ID: S20.*

##### Insurance to be obtained and maintained at the driver's sole cost

- **chunk_id**: `L2-2.2-007`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.2
- **criteria**: `2.1.c` (CONTRADICTS), `2.2.a` (CONTRADICTS)
- **policy_surfaces**: `insurance_obligation`, `cost_allocation`
- **section**: Sections 8.1 and 8.2 Insurance

Verbatim text:

> Prior to doing business with Uber, you agree to obtain the coverage required by Sections 8.2 and 8.3 below at your sole cost and expense. You agree to review the terms and conditions of such coverage to ensure that it provides the amounts of coverage required by Sections 8.2 and 8.3 below while you or your Drivers are using a Vehicle to provide Transportation Services. It is your sole responsibility to inform your insurer of the use of your Vehicle while providing Transportation Services.
>
> You agree to maintain, during the term of this Agreement, on all Vehicles operated by you and/or your Drivers under this Agreement, automobile commercial liability insurance that provides protection against bodily injury and property damage to yourself/your Drivers, your passengers and third parties at levels of coverage that satisfy the minimum requirements to operate a commercial passenger vehicle on the public roads as per applicable laws within the Territory. This coverage must also include any other insurance required by law for the operation of a commercial motor vehicle in the Territory that may not be waived by an insured. You agree to provide Uber and its Affiliates a copy of the insurance policy, policy declarations, proof of insurance identification card and proof of premium payment for the insurance policy required in this Section 8.2 upon request. Furthermore, you must provide Uber with a written notice of cancellation of any insurance policy required by Uber. Uber shall have no right to control your selection or maintenance of your policy. You and/or your Drivers must be a named insured or individually rated driver, for which a premium is charged, on the insurance policy required in this Section 8.2 at all times.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 8.1 and 8.2 Insurance. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Industrial injury cover treated as optional and at the driver's own risk

- **chunk_id**: `L2-2.2-008`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L2
- **threshold**: 2.2
- **criteria**: `2.1.c` (CONTRADICTS), `2.2.a` (CONTRADICTS)
- **policy_surfaces**: `occupational_injury`, `social_protection`, `risk_allocation`
- **section**: Section 8.3 Insurance

Verbatim text:

> You agree to maintain during the term of this Agreement, relevant workers’ compensation insurance if and as required by any applicable laws in the Territory. If permitted by applicable law, you may choose to insure yourself and/or your Drivers against industrial injuries by maintaining occupational accident insurance in place of workers’ compensation insurance. Further, if permitted by applicable law, you may choose not to insure yourself or your Drivers against industrial injuries at all, but you shall do so at your own risk.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 8.3 Insurance. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Consequence attached to declining trip requests

- **chunk_id**: `L3-3.1-008`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 2.2
- **criteria**: `2.2.c` (CONTRADICTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `acceptance_rate`, `freedom_to_refuse`, `forced_logout`
- **section**: Section heading: WHY DRIVERS CAN LOSE ACCESS TO UBER, sub-heading Acceptance Rates

Verbatim text:

> High acceptance rates are a critical part of reliable, high-quality service. We understand that there may be times when something comes up and you may not accept a trip. But maximizing acceptance is critical for the reliability of the system.
>
> Consistently accepting trip requests helps maximize earnings for drivers and keeps the system running smoothly. We know that sometimes things come up that prevent you from accepting every trip request, or you may want to take a break. But not accepting dispatches causes delays and degrades the reliability of the system. If you don’t want to accept trips, just log off.
>
> If you consistently decline trip requests, we will assume you do not want to accept more trips and you may be logged out of the app for a period of time. This helps ensure that drivers who are online are ready to accept trips. That protects the quality of the system as riders are matched with available drivers as efficiently as possible.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section heading: WHY DRIVERS CAN LOSE ACCESS TO UBER, sub-heading Acceptance Rates. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

##### Performance metrics that govern tier status, and how a driver can inspect them

- **chunk_id**: `L4-4.2-010`
- **source_id**: S03
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 2.2
- **criteria**: `2.2.c` (CONTRADICTS), `3.2.d` (CONTRADICTS), `4.2.d` (CONTRADICTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `performance_metrics`, `acceptance_rate`, `cancellation_rate`, `star_ratings`, `data_refresh`, `dispute_window`
- **section**: Section headings: PROGRAM TIERS AND PROGRAM STANDARDS; MAINTAINING YOUR TIER & PROGRAM STANDARDS; HOW TO VIEW POINTS BALANCES

Verbatim text:

> There are no additional requirements for the Blue Tier other than as set forth in the “Eligibility” section above. To obtain Gold, Platinum, and Diamond Tiers, in addition to the required number of Points for your Participating City, you must also have, at the beginning of or during the Program Period: (1) a minimum of driver star rating average over the past 500 trips as applicable to the Program (or all lifetime trips if you have completed less than 500 trips); (2) no greater than a cancellation rate as applicable to the different Participating Cities and Tiers ; and (3) no less than an acceptance rate as applicable to the different Participating Cities and Tiers, as may be determined and notified by Uber from time to time on the Uber Driver App (collectively, "Program Standards").
>
> See the “How Uber Pro Works” section under "Uber Pro" in your Uber Driver App for the applicable Program Standards for the Gold, Platinum and Diamond Tiers for your Participating City and the method of calculation of cancellation rate and acceptance rate for purposes of this Program.
>
> If you fail to meet any of the Program Standards applicable to your Tier, you will be moved to the Blue Tier. You will lose your access to the Rewards available to higher Tiers, but will maintain access to the Blue Tier and the corresponding Rewards as long as you remain in the Uber Pro Program. Your former Tier can be reinstated if all Program Standards are met during the current Program Period.
>
> You can view your current Points balances within the settings of your Uber Driver App. Any errors or omissions on transactions posted to your Program Account must be reported within one month by contacting Uber as noted in the 'Contact Us' section below. Failure to supply necessary documentation may result in an inability to award Points or adjust Tier status. For verification, you should retain all receipts and documentation until your Points are credited to your Program Account.
>
> It may take approximately 72 hours for your cancellation and acceptance rates to refresh. In the event of an outage of the Uber systems, your Points may be delayed in displaying in your Program Account. Additionally, if the outage occurs near the end of a Program Period, it is possible the Points will not be applied until the next Program Period.
>
> Points may be revoked if an Uber Trip, for which Points were earned, is refunded or if Uber believes, in its sole discretion, that Points were earned through or in connection with any fraud, abuse of the platform, or in violation of your Services Agreement and/or Uber’s Community Guidelines.

*Citation: Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction stated or inferred: India. Section headings: PROGRAM TIERS AND PROGRAM STANDARDS; MAINTAINING YOUR TIER & PROGRAM STANDARDS; HOW TO VIEW POINTS BALANCES. URL: https://www.uber.com/in/en/legal/uber-pro-program-terms/. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved: 2026-09-13. Source ID: S03.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_2_1_01** — bears on `2.2.c`: No official Uber document located for India states a maximum limit on standard working time expressed as weekly hours, nor an entitlement to breaks of a defined length during working time. The only working-time instrument located is the driving time limit at S18, which is a global Uber Help article and is framed as a fatigue-safety cap. The published India driver Services Agreement states the converse: “you and/or your Drivers retain the sole right to determine when and for how long you or each of your Drivers will utilize the Driver App or the Uber Service” (S32, Section 2.4).  *(Re-filed from 2.1.)*
- **absence_2_2_01** — bears on `2.2.a`: No official Uber document located for India provides paid time off of any kind for driver partners, including sick leave, parental leave, bereavement leave or annual leave. Uber does not explicitly mention paid leave for India driver partners.
- **absence_2_2_02** — bears on `2.2.a`: No official Uber document located for India provides Uber-funded sickness or injury income replacement for driver partners. The insurance arrangements Uber describes for India (S03, S23, S27) are stated by Uber to be underwritten and administered by third parties, with eligibility at those third parties’ sole discretion.
- **absence_2_2_04** — bears on `2.2.b`: No official Uber document located for India states that a driver’s standing on the platform will not be negatively affected if they are unable to work for an extended period. Uber does not explicitly mention protection of platform standing during extended absence.
- **absence_3_1_04** — bears on `2.2.c`: No official Uber document located for India states that declining tasks will not punitively affect a driver’s rating or reputation. The Services Agreement preserves the option to decline (S32, Section 2.4), while the India Community Guidelines state that consistent declining may result in being logged out of the app for a period of time (S01).  *(Re-filed from 3.1.)*

## 6. Lever L3 — Fair Contracts

- **lever**: L3
- **fairwork_principle**: P3
- **thresholds**: 3.1, 3.2

### 6.1 Threshold 3.1 — Provides clear and transparent terms and conditions

- **threshold_id**: 3.1
- **lever**: L3
- **criteria**: `3.1.a`, `3.1.b`, `3.1.c`, `3.1.d`, `3.1.e`, `3.1.f`
- **extract_count**: 20
- **audience_driver**: 20
- **audience_mixed**: 0
- **absence_count**: 6

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> The platform must satisfy ALL of the following:

- **[3.1.a]** The party contracting with the worker must be identified in the contract, and subject to the law of the country/state/region in which the worker works.
- **[3.1.b]** The contract/terms & conditions are presented in full in clear and comprehensible language that all workers could be expected to understand.
- **[3.1.c]** Workers have to sign a contract and/or give informed consent to terms of conditions upon signing up for the platform.
- **[3.1.d]** The contracts/terms and conditions are easily accessible to workers in paper form, or via the app/platform interface at all times.
- **[3.1.e]** Contracts/terms & conditions do not include clauses that revert prevailing legal frameworks in the respective countries.
- **[3.1.f]** Platforms take adequate, responsible and ethical data protection and management measures, laid out in a documented policy.[10]

> **INLINED FOOTNOTE [10]**
> As stated in international standards, ethical data protection includes aspects such as legitimacy and
> lawfulness, proportionality, purpose limitation, transparency, data subject's rights (access, rectification, evaluation,
> erasure, and portability), and accountability. Also, when using AI, the rights to be informed about it and to have a
> human interface.

#### Extracts from official Uber documentation

##### How a driver accepts the agreement and where the accepted terms can be read

- **chunk_id**: `L3-3.1-001`
- **source_id**: S28
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article served to India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.b` (CONTRADICTS), `3.1.c` (SUPPORTS), `3.1.d` (SUPPORTS)
- **policy_surfaces**: `contract_acceptance`, `contract_access`, `legal_advice_disclaimer`
- **section**: Section headings: How to accept Uber’s Terms and Conditions; How to see terms you’ve agreed to

Verbatim text:

> Before you can start driving and accepting rides, you’ll need to agree to Uber’s Terms and Conditions. Any terms, conditions, or agreements that you haven’t acknowledged will be shown to you in the Uber Driver app when you try to go online.
>
> Go to your profile by signing in at drivers.uber.com/profile.
>
> Under “Contracts,” you’ll find the agreements listed. Click on the one you need to review.
>
> Please note, while we can provide information on how to accept Uber’s Terms and Conditions, we can’t offer advice about the terms themselves. Always consider seeking independent legal advice if you have questions about the agreement.

*Citation: Uber Technologies Inc. Agreeing to terms and conditions (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article served to India. Section headings: How to accept Uber’s Terms and Conditions; How to see terms you’ve agreed to. URL: https://help.uber.com/en/driving-and-delivering/article/agreeing-to-terms-and-conditions?nodeId=44cf1f0e-27ca-4919-9621-f1321a0381c1. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S28.*

##### Status of the Uber Pro programme and its relation to the Services Agreement

- **chunk_id**: `L3-3.1-004`
- **source_id**: S03
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.c` (PARTIAL)
- **policy_surfaces**: `contract_hierarchy`, `employment_status`, `discretionary_terms`
- **section**: Opening recitals

Verbatim text:

> Uber Pro (the “Program”) is brought to you by Uber India Systems Private Limited, or its respective subsidiaries, licensees and affiliated companies (collectively “Uber” or “we”). These Program Terms (defined below) constitute a legal agreement between you and Uber.
>
> Participation in the Program is subject to these terms and conditions, and also to our Privacy Notice and your Services Agreement, which are incorporated herein (collectively, the “Program Terms”). By participating in this Program you are agreeing to these Program Terms.
>
> Uber is a technology service provider, not a provider of transportation services, as such all Rewards (defined below) offered under the Program are offered on an “as available” basis, contingent upon requests from riders for the transportation services and other contingencies which may impact availability of some Rewards at certain times and places.
>
> THE PROGRAM IS CURRENTLY BEING OFFERED IN SELECT CITIES, WITH CERTAIN REWARDS AVAILABLE IN CERTAIN CITIES. YOU UNDERSTAND THAT UBER MAY TERMINATE OR MODIFY THE TERMS OF THE PROGRAM (INCLUDING, WITHOUT LIMITATION, WHAT THE REWARDS ARE, HOW YOU QUALIFY FOR THEM, THE DURATION OF THE PROGRAM) AT ANY TIME AT UBER’S SOLE DISCRETION. ALL AND ANY REWARDS ON OFFER BY UBER ARE AT THE COMPLETE DISCRETION OF UBER AND UBER MAY CHOOSE TO PROVIDE ALL OR ANY REWARDS IN ALL OR ANY CITIES IN INDIA AS DETERMINED BY UBER AT ITS SOLE DISCRETION. THE REWARDS OFFERED UNDER THE PROGRAM ARE NOT IN THE NATURE OF EMOLUMENTS AND DO NOT CREATE ANY EMPLOYER-EMPLOYEE OR AGENCY RELATIONSHIP BETWEEN UBER AND THE DRIVER PARTNERS. THE PROGRAM IS A LOYALTY PROGRAM BEING INTRODUCED BY UBER TO INCREASE LOYALTY AND ADAPTATION OF UBER PLATFORM BY DRIVER PARTNERS.
>
> You understand that all central, state and local taxes on the Rewards that you accept are your sole responsibility as the Reward recipient.

*Citation: Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction stated or inferred: India. Opening recitals. URL: https://www.uber.com/in/en/legal/uber-pro-program-terms/. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved: 2026-09-13. Source ID: S03.*

##### Languages in which the India legal hub publishes its documents

- **chunk_id**: `L3-3.1-006`
- **source_id**: S31
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.b` (SUPPORTS)
- **policy_surfaces**: `language_accessibility`
- **section**: Language selector on the India legal hub
- **note**: Reproduced as the language options presented by the India legal hub interface.

Verbatim text:

> Bangla, বাংলা
>
> English, English
>
> Hindi, हिन्दी
>
> Kannada, ಕನ್ನಡ
>
> Marathi, मराठी
>
> Tamil, தமிழ்
>
> Telugu, తెలుగు
>
> Urdu, اردو

*Citation: Uber Technologies Inc. Uber Legal Hub, India index (jurisdiction and language selector). Jurisdiction stated or inferred: India. Language selector on the India legal hub. URL: https://www.uber.com/in/en/legal/?country=india&lang=en. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S31.*

##### Support language coverage stated by Uber India

- **chunk_id**: `L3-3.1-007`
- **source_id**: S27
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.b` (ASSERTED)
- **policy_surfaces**: `language_accessibility`, `support_access`
- **section**: Article body

Verbatim text:

> At Uber, we are obsessed about making driver experience better. From how even minor tweaks to the user interface will impact them, to providing support in 7 languages or by bringing innovations, such as driver destination that allows them to choose a trip in the direction of their home at their discretion.

*Citation: Uber Newsroom India (Prabhjeet Singh). Keeping driver partners at heart. Jurisdiction stated or inferred: India. Article body. URL: https://www.uber.com/in/en/newsroom/keeping-driver-partners-at-heart/. Document date: 2018-12-20 (dateline on page). Retrieved: 2026-09-13. Source ID: S27.*

##### Contracting models recognised by Uber India for drivers and vehicle owners

- **chunk_id**: `L3-3.1-012`
- **source_id**: S16
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.a` (PARTIAL), `3.2.c` (PARTIAL)
- **policy_surfaces**: `engagement_models`, `fleet_partner`, `intermediary`
- **section**: Section heading: Three ways to earn

Verbatim text:

> A driver cum owner drives a vehicle that he or she owns. Requirements vary by city, but there are a few minimum requirements:
>
> Driving License
>
> Vehicle Registration
>
> Vehicle Insurance
>
> Vehicle Permit
>
> A driver under partner drives a vehicle owned by a non-driving partner. The following document is required of a driver under partner:
>
> Driving License
>
> A non-driving partner or fleet partner is someone who does not drive on the Uber platform but owns vehicle(s) and manages at least one driver. Becoming a non-driving partner requires:
>
> Vehicle Insurance
>
> Vehicle Registration
>
> Vehicle Permit
>
> The information provided on this web page is intended for informational purposes only and may not be applicable in your country, region, or city. It is subject to change and may be updated without notice.

*Citation: Uber Technologies Inc. Driver requirements. Jurisdiction stated or inferred: India. Section heading: Three ways to earn. URL: https://www.uber.com/in/en/drive/requirements/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S16.*

##### Parties, scope and applicable categories of the driver contract

- **chunk_id**: `L3-3.1-013`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.a` (SUPPORTS), `3.1.d` (SCOPE LIMITED)
- **policy_surfaces**: `contracting_entity`, `contract_scope`, `supersession`, `fleet_partner`
- **section**: Preamble and scope statement

Verbatim text:

> This Services Agreement (“Agreement”) constitutes a legal agreement between Uber India Systems Private Limited, a private limited company incorporated under the laws of India, having corporate identity number U74120MH2013FTC247008 and having its registered office at Regus Business Platinum Centre Pvt. Ltd., Level 13 Platinum Techno Park, Plot No.17/18, Sec-30A, Vashi, Thane, Navi Mumbai, Maharashtra, India, 400705 (“Uber”), also located at Plot No.300, 1st Floor, Sector-29, Gurgaon, Haryana - 122001 and either:
>
> (i) an individual driver engaged in the business of providing transportation services, in which case, provisions in this Agreement that are addressed to ‘your Driver’ do not apply to you; or
>
> (ii) a fleet partner, being either an individual, a sole proprietorship or any other corporate entity providing transportation services through drivers who are engaged by such a fleet partner (“Fleet Partner”), in which case provisions in this Agreement that are addressed to ‘your Driver’ refer to drivers engaged by such a Fleet Partner.
>
> This Agreement applies solely to the Uber Service as defined in Section 1.2 below, as made applicable by Uber (See applicable categories and effective dates on the top of this document). If you are using Uber's services outside the scope of this Agreement, the other applicable terms and conditions issued by Uber for those services shall continue to apply. In order to avail the Uber Service, you must agree to the terms and conditions that are set forth below and any other terms and conditions as notified by Uber or any of its Affiliates to you and/or your Drivers from time to time. Upon your acceptance (electronic or otherwise) of this Agreement, you and Uber shall be bound by the terms and conditions set forth herein.
>
> You acknowledge and agree that Uber is a technology services provider that neither provides Transportation Services, nor functions as a transportation carrier, nor does it operate as an agent for the transportation of passengers.
>
> This Agreement supersedes any previous agreement between you and Uber, and any supplements, amendments or modifications to such services agreement.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Preamble and scope statement. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### The acceptance clause

- **chunk_id**: `L3-3.1-014`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.c` (SUPPORTS)
- **policy_surfaces**: `contract_acceptance`, `informed_consent`
- **section**: Closing acceptance statement

Verbatim text:

> By clicking “I accept”, you expressly acknowledge that you have read, understood, and taken steps to thoughtfully consider the consequences of this Agreement, that you agree to be bound by the terms and conditions of this Agreement, and that you are legally competent to enter into this Agreement with Uber.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Closing acceptance statement. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Waiver of consumer status under the Consumer Protection Act, 2019

- **chunk_id**: `L3-3.1-017`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.b` (PARTIAL), `3.1.e` (CONTRADICTS), `3.2.b` (CONTRADICTS)
- **policy_surfaces**: `consumer_protection_waiver`, `legal_recourse`, `commercial_activity`
- **section**: Section 2.6

Verbatim text:

> You acknowledge and agree that by using the Uber Service and utilizing the Uber Driver App, you are engaging in commercial activity. As such, you expressly agree that you are not a 'consumer' under the Consumer Protection Act, 2019, and shall not be entitled to any rights or remedies available to consumers under the said Act. You understand that Uber provides Uber Service for the limited purpose of connecting you to the Users. Uber does not provide Transportation Services itself. Uber’s role ends on such a connection. The relationship between Uber and you is that of independent contracting parties, and you shall have no claim against Uber under consumer protection laws.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.6. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Relationship of the parties and indemnity against a finding of employment

- **chunk_id**: `L3-3.1-019`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.e` (CONTRADICTS)
- **policy_surfaces**: `employment_status`, `independent_contractor`, `misclassification_indemnity`
- **section**: Section 13 Relationship of the Parties

Verbatim text:

> Except as otherwise expressly provided in Sections 4.3.3 and 4.3.5, the relationship between the parties under this Agreement is solely that of independent contractors. The parties expressly agree that: (a) this Agreement is not an employment agreement, nor does it create an employment relationship (including from a labour law, tax law, social security law or insurance law perspective), between you and Uber; and (b) no joint venture, partnership, or agency relationship exists between you and Uber or Uber and any Driver.
>
> You have no authority to bind Uber and/or its Affiliates, and undertake not to hold yourself out, and to ensure that none of your Drivers hold themselves out, as an employee, worker, agent or authorized representative of Uber and/or its Affiliates. Uber’s facilitation of Suggested Fare payments from Users to you does not alter this relationship at all.
>
> Where, by implication of mandatory law or otherwise, you or any Driver may be deemed an employee, worker, agent or representative of Uber or any of its Affiliates, you, undertake and agree to indemnify, defend (at Uber’s or the concerned Affiliates's option) and hold Uber and its Affiliates harmless from and against any claims by any person, entity, regulators or governmental authorities based on such implied employment, agency or representative relationship.
>
> You expressly acknowledge and agree that by agreeing to the terms and conditions of this Agreement, you and/or your Drivers intend to perform Transportation Services in a non­-incidental manner.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 13 Relationship of the Parties. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Indemnification obligations placed on the driver

- **chunk_id**: `L3-3.1-022`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.b` (PARTIAL), `3.1.e` (CONTRADICTS), `3.2.b` (CONTRADICTS)
- **policy_surfaces**: `indemnity`, `liability`, `risk_allocation`
- **section**: Section 10 Indemnification

Verbatim text:

> You shall indemnify, defend (at Uber’s option) and hold harmless Uber and its Affiliates and each of their respective officers, directors, employees, agents, successors and assigns from and against any and all liabilities, losses, costs, expenses (including legal fees), damages, penalties, fines, social security contributions and taxes arising out of or related to: (a) a breach of your representations, warranties or obligations under this Agreement; or (b) a claim by a third party (including Users, regulators and governmental authorities) directly or indirectly related to your provision of Transportation Services or use of the Uber Service.
>
> As between you and Uber, you are and shall be solely responsible for your and/or your Drivers’ provision of Transportation Services. As such, you shall indemnify, defend (at Uber’s option) and hold harmless Uber and its Affiliates and each of their respective officers, directors, employees, agents, successors and assigns from and against any and all liabilities, losses, costs, expenses (including legal fees), damages, penalties, fines, social security contributions and taxes directly or indirectly arising out of or related to your and/or your Drivers’ provision of Transportation Services or use of the Uber Service.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 10 Indemnification. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Limitation of Uber's liability and the one-year claim notification window

- **chunk_id**: `L3-3.1-023`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.b` (PARTIAL), `3.2.b` (CONTRADICTS)
- **policy_surfaces**: `liability_cap`, `claim_limitation`, `legal_recourse`
- **section**: Section 11 Limits of Liability

Verbatim text:

> Uber and its Affiliates shall not be liable under or related to this Agreement for any of the following, whether based on contract, tort or any other legal theory, even if a party has been advised of the possibility of such damages: (i) any incidental, punitive, special, exemplary, consequential, or other indirect damages of any type or kind; or (ii) your, your Drivers’ or any third party’s property damage, or loss or inaccuracy of data, or loss of business, revenue, profits, use or other economic advantage. Except for Uber’s obligations to remit amounts due to you pursuant to Section 4 above, but subject to any limitations or other provisions contained in this Agreement which are applicable thereto, in no event shall the liability of Uber and/or any of its Affiliates under this Agreement exceed the amount actually paid by or due from you to Uber hereunder in the six (6) months period immediately preceding the event giving rise to such claim. You acknowledge and agree that any and all claims you have or purport to have against Uber and/or its Affiliates should be notified to Uber and/or its Affiliates within one (1) year after the event(s) that gave rise to such claim and that you forfeit all rights in respect of that claim if you fail to do so. These limitations do not purport to limit liability that cannot be excluded by applicable law.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 11 Limits of Liability. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Notices, grievance contact, governing law and dispute resolution

- **chunk_id**: `L3-3.1-025`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.1
- **criteria**: `3.1.a` (SUPPORTS), `3.1.e` (PARTIAL), `3.2.a` (PARTIAL), `4.1.a` (PARTIAL)
- **policy_surfaces**: `notice_channel`, `grievance_channel`, `governing_law`, `dispute_resolution`
- **section**: Sections 14.7 Notices and 15 Governing Law; Arbitration

Verbatim text:

> Notices. Any notice delivered by Uber to you under this Agreement will be delivered by email to the email address associated with your account or by posting on the Driver App or the online portal available to you via the Uber Serviced. Any notice delivered by you to Uber under this Agreement must be delivered by contacting Uber at grievanceredressaloffice@uber.com.
>
> Governing Law; Arbitration. Except as otherwise set forth in this Agreement, this Agreement shall be exclusively governed by and construed in accordance with the laws of India, excluding its rules on conflicts of laws. Any dispute, conflict or controversy, however arising out of or broadly in connection with or relating to this Agreement, including those relating to its validity, its construction or its enforceability, shall be settled amicably between the parties within 30 (thirty) days of arising of such dispute. If the amicable settlement fails then the dispute shall be subject to the exclusive jurisdiction of the courts of India.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 14.7 Notices and 15 Governing Law; Arbitration. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Uber's stated scope of automated processes affecting drivers

- **chunk_id**: `L4-4.2-001`
- **source_id**: S08
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (SUPPORTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `automated_decision`, `explainability`, `contact_channel`
- **section**: Section II.C Core automated processes, introduction

Verbatim text:

> Uber uses automated processes to enable certain parts of our services, including functions essential to our business such as matching, pricing, safety, and fraud detection and prevention.
>
> Uber relies on automated processes to enable essential parts of our services, including matching (pairing users requesting and providing transportation and/or delivery services), pricing (determining the amount you are owed for providing such services), safety and fraud detection and prevention. These processes allow Uber to provide a seamless and safe experience to millions of users globally every day.
>
> This section describes how automated matching, pricing, safety, and fraud prevention and detection work, including how they impact your Uber experience and the personal and non-personal data used to enable these processes.
>
> You may contact Uber here if you have questions or concerns regarding these processes.

*Citation: Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction stated or inferred: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Section II.C Core automated processes, introduction. URL: https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved: 2026-09-13. Source ID: S08.*

##### Driver access to, correction and deletion of personal data

- **chunk_id**: `L4-4.2-005`
- **source_id**: S08
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (SUPPORTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `data_access`, `data_portability`, `data_deletion`, `data_correction`, `objection_rights`
- **section**: Section III. Choice and transparency

Verbatim text:

> Uber enables you to access and/or control data that Uber collects, including through:
>
> Privacy settings
>
> Device permissions
>
> In-app ratings pages
>
> Marketing and advertising choices
>
> You may also request access to or copies of your data, make changes or updates to your account, request account deletion, or request that Uber restrict its processing of your data.
>
> After every trip, Drivers and riders can rate each other on a scale from 1 to 5. An average of the ratings you receive is displayed to your riders.
>
> You can find your average rating in the Account section of the Uber app, and also access a breakdown of your average rating in Uber’s Privacy Center.
>
> Depending on where you are located, you may have the right to access your data and to portability of your data.
>
> Regardless of your location, you can access your data, including your profile data and ride or delivery history, through the Uber apps or website.
>
> You can also use our Explore Your Data to view a summary of certain information about your account, such as your rating, ride or delivery count, rewards status, and how long you’ve been using Uber.
>
> You can also use our Download Your Data feature to download a copy of the most requested data relating to use of Uber, including account, usage, communications, and device data.
>
> You can edit your name, phone number, email address, payment method, and profile picture through the Settings menu in Uber’s apps.
>
> You may request that Uber delete your account through Uber’s Privacy Center.
>
> You may request that we stop using all or some of your data, or that we limit our use of your data. This includes objecting to our use of data that is based on Uber’s legitimate interests. Uber may continue to process data after such objection or request to the extent necessary to provide our services, or required or permitted by law.
>
> In addition, depending on your location, you may have the right to file a complaint relating to Uber’s handling of your data with the data protection authority in your country.

*Citation: Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction stated or inferred: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Section III. Choice and transparency. URL: https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved: 2026-09-13. Source ID: S08.*

##### Data controller and Data Protection Officer

- **chunk_id**: `L4-4.2-006`
- **source_id**: S08
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (SUPPORTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `data_controller`, `dpo_contact`
- **section**: Section IV.A Data controllers and Data Protection Officer
- **note**: The list of jurisdiction-specific controller arrangements in this clause names Mexico, the EEA, the UK, Switzerland, South Korea and Türkiye. India is not named, so the general rule stated in the first sentence applies.

Verbatim text:

> Uber Technologies, Inc. is the sole controller of the data processed by Uber when you use Uber’s services globally, except where it is a joint controller with other Uber affiliates.
>
> You may also contact Uber’s Data Protection Officer at uber.com/privacy-dpo, or by mail to Uber B.V. (Burgerweeshuispad 301, 1076 HR Amsterdam, the Netherlands), regarding issues relating to Uber’s processing of your personal data and your data protection rights.

*Citation: Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction stated or inferred: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Section IV.A Data controllers and Data Protection Officer. URL: https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved: 2026-09-13. Source ID: S08.*

##### Monitoring and automated analysis of communications, and the limits of opting out

- **chunk_id**: `L4-4.2-007`
- **source_id**: S06
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `communications_monitoring`, `ai_analysis`, `opt_out_limits`, `human_review`
- **section**: Full text of the notice

Verbatim text:

> At Uber, we use technology with the goal of making every interaction you have with us clearer, safer, and more useful. That includes the ways we monitor and analyze certain communications on our platform — like messages and calls between you and Uber, and, in some cases, messages and calls between users (for example, riders and drivers, or eaters and couriers) that happen through Uber’s in‑app tools.
>
> “Communications intelligence” is how we describe the systems that help us further understand messages and calls on Uber — for example:
>
> Spotting potentially unsafe or abusive language in chats routed through Uber
>
> Detecting fraud and account takeover attempts
>
> Identifying confusing or misleading messages so we can improve our templates and product flows
>
> Measuring whether our notifications (like trip updates or support follow‑ups) are actually helpful
>
> For voice, chat, SMS, email, and other messages and calls that Uber facilitates, including in-app chat, calling between users, SMS or WhatsApp relays, and certain communications we facilitate with third-party apps, our technology may automatically analyze things like message text, voice recordings or transcripts, timing, delivery status, and how often conversations lead to issues or escalations. These processes may include the use of automated systems, including AI and machine learning tools, to help analyze and categorize communications. Our systems may also automatically detect certain types of personal information or unusual sharing patterns to help prevent scams, account takeovers, and other fraud. In certain cases, trained specialists may review these communications. For example, to investigate a safety report, address suspected fraud, or resolve a complex support case.
>
> We design these tools with privacy and security in mind, using access controls, audit logs, and strict internal policies to help protect your information.
>
> When you use Uber’s communication tools, our systems may automatically analyze:
>
> Content and metadata: message text, timestamps, delivery status, and limited technical information (like language or channel type).
>
> Response patterns: whether messages are opened or frequently escalated to support.
>
> Safety and trust indicators: phrases or behavior that may suggest harassment, scams, or other violations of our Community Guidelines.
>
> Detect patterns linked to harassment, fraud, or other harmful behavior, and to identify accounts for review when something goes wrong.
>
> You can manage many of your communication preferences, such as marketing emails, SMS, and push notifications, through your account settings. Please refer to the Privacy Notice to learn more about Uber’s privacy practices.
>
> However, certain monitoring cannot be opted out of. Automated analysis for safety and security purposes, such as detecting harassment, fraud, and account takeover attempts, is fundamental to how Uber operates and applies to all in-app communications. These safeguards are in place to protect everyone on the platform, including you.
>
> We’re committed to using communications intelligence responsibly: with clear purpose, limited access, and safeguards designed to protect your privacy while still delivering a safer, more reliable experience every time you use Uber.

*Citation: Uber Technologies Inc. How Uber Uses Communications Intelligence to Improve Your Experience. Jurisdiction stated or inferred: India. Full text of the notice. URL: https://www.uber.com/in/en/legal/communication-intelligence/. Document date: 2026-07-07 (page states: Last modified: 7/7/2026). Retrieved: 2026-09-13. Source ID: S06.*

##### Mandatory geo-location transmission

- **chunk_id**: `L4-4.2-014`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `location_tracking`, `mandatory_data_collection`
- **section**: Section 2.9 Location Based Services

Verbatim text:

> Location Based Services. You acknowledge and agree that your or each of your Driver's geo-­location information must be provided to Uber via a Device in order to provide Transportation Services, in accordance with the Uber Privacy Notice.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.9 Location Based Services. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Definition and ownership of Uber Data, including data generated by the driver's work

- **chunk_id**: `L4-4.2-015`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (CONTRADICTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `data_ownership`, `worker_data_access`, `intellectual_property`
- **section**: Definition 1.20 Uber Data and Section 5.1 Ownership

Verbatim text:

> “Uber Data” means all data related to the access and use of the Uber Service hereunder, including all data related to Users (including User Information), all data related to the provision of Transportation Services via the Uber Service and the Driver App, and the Driver IDs.
>
> Ownership. The Uber Service, Driver App and Uber Data, including all intellectual property rights therein, and the Uber Devices are and shall remain the property of Uber, its Affiliates or their respective licensors. Neither this Agreement nor your or your Drivers’ use of Uber Service, Driver App or Uber Data conveys or grants to you or your Drivers any rights: (a) in or related to Uber Service, Driver App or Uber Data, except for the limited license granted above; or (b) to use or reference in any manner Uber’s, its Affiliates’, or their respective licensors’ company names, logos, product and service names, trademarks, service marks or other indicia of ownership.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Definition 1.20 Uber Data and Section 5.1 Ownership. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Privacy clause and the warranty placed on Fleet Partners regarding driver data

- **chunk_id**: `L4-4.2-016`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `privacy_notice_incorporation`, `consent_warranty`, `fleet_partner`
- **section**: Sections 7.1 and 7.2 Privacy

Verbatim text:

> You acknowledge and agree that Uber processes personal data about you and/or your Drivers in accordance with its Privacy Notice.
>
> Where you provide Uber and/or its Affiliates with any personal data of your own and/or your Drivers, you represent and warrant that: (i) you have provided the personal data with your and/or such Drivers' consent and in compliance with all applicable laws; and (ii) you have taken reasonable steps to ensure that such personal data is accurate, complete, up-to-date and fit for purpose.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 7.1 and 7.2 Privacy. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Restrictions on extracting data from the platform

- **chunk_id**: `L4-4.2-017`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.1
- **criteria**: `3.1.f` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `data_extraction_ban`, `platform_restrictions`
- **section**: Section 5.3 Restrictions

Verbatim text:

> (h) improperly use Uber Service or Driver App, including creating Internet “links” to any part of the Uber Service or Driver App, “framing” or “mirroring” any part of the Uber Service or Driver App on any other websites or systems, or “scraping” or otherwise improperly obtaining data from the Uber Service or Driver App;
>
> In addition, you shall not, and shall not allow your Drivers or any other party to, access or use the Uber Service or Driver App to: (i) design or develop a competitive or substantially similar product or service; (ii) copy or extract any features, functionality, or content thereof;

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 5.3 Restrictions. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_3_1_01** — bears on `3.1.d`: The published India driver Services Agreement (S32) covers only the categories it names: Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. No equivalent published driver contract was located for Uber Moto, Uber Auto, Uber Intercity, Uber Hire or courier work in India. For those categories the governing contract remains unpublished and is accessible only after authentication at drivers.uber.com/profile (S28).
- **absence_3_1_03** — bears on `3.1.b`: No official Uber document located for India states that the driver contract is provided in a language the driver is proficient in. The Services Agreement (S32) is published in English on the India legal hub, which offers the language options listed at S31, but the Agreement itself contains no language-provision clause.
- **absence_4_2_03** — bears on `3.1.f`: No official Uber document located for India states a data minimisation commitment in those terms, or restricts the use of invasive monitoring technologies. The Services Agreement makes geo-location transmission a condition of providing the service (S32, Section 2.9). Uber does not explicitly mention data minimisation for India driver data.  *(Re-filed from 4.2.)*
- **absence_4_2_04** — bears on `3.1.f`: No official Uber document located for India allows a driver to opt out of non-essential data processing without penalty in general terms. The Communications Intelligence notice states the contrary for safety and security analysis: “certain monitoring cannot be opted out of” (S06).  *(Re-filed from 4.2.)*
- **absence_4_2_05** — bears on `3.1.f`: No official Uber document located for India gives a driver any ownership of, or continuing right to, the data generated by their own work. The Services Agreement defines “Uber Data” to include “all data related to the provision of Transportation Services via the Uber Service and the Driver App” and states that it “shall remain the property of Uber, its Affiliates or their respective licensors” (S32, definition 1.20 and Section 5.1). The data-access rights described at S08 are those in the Privacy Notice, not in the contract.  *(Re-filed from 4.2.)*
- **absence_4_2_06** — bears on `3.1.f`: No official Uber document located for India names an India data controller for driver data. The controller clause of the driver Privacy Notice (S08) names Mexico, the EEA, the UK, Switzerland, South Korea and Türkiye, and does not name India. The driver Services Agreement names grievanceredressaloffice@uber.com as the notice address (S32, Section 14.7) but does not identify a data protection or grievance officer by name or office.  *(Re-filed from 4.2.)*

### 6.2 Threshold 3.2 — Ensures that no unfair contract terms are imposed

- **threshold_id**: 3.2
- **lever**: L3
- **criteria**: `3.2.a`, `3.2.b`, `3.2.c`, `3.2.d`
- **extract_count**: 22
- **audience_driver**: 21
- **audience_mixed**: 1
- **absence_count**: 4

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> In some cases, especially under 'independent contractor' classifications, workers carry
> a disproportionate amount of risk for engaging in a contract with the service user. They
> may be liable for any damage arising in the course of their work, and they may be
> prevented by unfair clauses from seeking legal redress for grievances. To achieve this
> point, platforms must demonstrate that risks and liability of engaging in the work are
> shared between parties.
>
> Regardless of how the contractual status of the worker is classified, the platform must
> satisfy ALL of the following:

- **[3.2.a]** Every worker is notified of proposed changes in clear and understandable language within a reasonable timeframe before changes come into effect; and the changes should not reverse existing accrued benefits and reasonable expectations on which workers have relied.
- **[3.2.b]** The contract/terms and conditions neither include clauses which exclude liability for negligence nor unreasonably exempt the platform from liability for working conditions. The platform takes appropriate steps to ensure that the contract does not include clauses which prevent workers from effectively seeking redress for grievances which arise from the working relationship.
- **[3.2.c]** In case platform labour is mediated by subcontractors: The platform implements a reliable mechanism to monitor and ensure that the subcontractor is living up to the standards expected from the platform itself regarding working conditions.
- **[3.2.d]** In cases where algorithms are used to determine pricing, bonuses, ratings and/or allocate jobs, the data collected, and calculations used must be transparent and documented in a form available to workers in clear and comprehensible language that all workers could be expected to understand.

> **INLINED DEFINITION — SUBCONTRACTING (cited by [3.2.c])**
> Some platforms outsource parts of their operations to other enterprises. While some of these companies operate
> under the same name as the main company, or a slightly different version of it (e.g. Amazon and Amazon Flex),
> there might also be others that provide their services to the platform but also carry out their own operations (e.g.
> Amazon, DPD and myHermes). Where subcontracting relations are in place, the responsibility for ensuring fairness
> standards still rests on the main platform that outsources its operations.

#### Extracts from official Uber documentation

##### Unilateral change, interpretation and assignment provisions in the India Uber Pro terms

- **chunk_id**: `L3-3.1-005`
- **source_id**: S03
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.a` (CONTRADICTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `unilateral_amendment`, `notice_period`, `assignment`, `interpretation_discretion`
- **section**: Section headings: PROGRAM CHANGES AND PROGRAM TERMINATION; TRANSFER OF RIGHTS; INTERPRETATION OF PROGRAM TERMS; ACCOUNT TERMINATION

Verbatim text:

> Uber may suspend, revoke, terminate or discontinue your Program Account at any time for any reason. If your Program membership is terminated, all Points associated with your Program membership and any Rewards may be forfeited immediately upon termination, in accordance with the terms of the specific Reward, as detailed below. If your Program membership is terminated due to fraudulent activity or non-compliance with these Program Terms, in addition to forfeiting all Points and Rewards associated with your Program membership immediately, you cannot participate in or rejoin the Program.
>
> We reserve the right to modify, suspend or discontinue the Program, or any part thereof, at any time without notice and without further obligations to you or any other Program Members, including, but not limited to modifications that: a) govern how Points are earned on and after the date of change; b) change the number of Points required to access a Tier; c) change the specific Rewards provided in each Tier; d) change any other requirements necessary to obtain Rewards within a Tier; or e) change the Rewards available. No Points will be earned after the effective date of termination. Any and all changes and/or amendments to these Program Terms will become binding upon all Program Members immediately upon being updated.
>
> Uber’s rights and obligations under the Program may be assigned or transferred by Uber to any other related or unrelated entity at any time, and performances shall be the responsibility of that entity.
>
> All interpretations of these Program Terms will be at Uber’s sole discretion and Uber’s decisions will be final.

*Citation: Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction stated or inferred: India. Section headings: PROGRAM CHANGES AND PROGRAM TERMINATION; TRANSFER OF RIGHTS; INTERPRETATION OF PROGRAM TERMS; ACCOUNT TERMINATION. URL: https://www.uber.com/in/en/legal/uber-pro-program-terms/. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved: 2026-09-13. Source ID: S03.*

##### Statement that use of Trip Radar is optional and does not affect confirmation rate

- **chunk_id**: `L3-3.1-009`
- **source_id**: S19
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article. The text references the GMB union and speeds in mph, indicating a UK-facing version.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (SUPPORTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `freedom_to_refuse`, `confirmation_rate`
- **section**: Article body

Verbatim text:

> You do not need to browse through the nearby trips if you don’t want to, though! The Trip Radar feature is there for you if you want to use it, but it is not compulsory.
>
> When you are selecting trip requests on Trip Radar, you can tap as many as you like and it won’t impact your confirmation rate.

*Citation: Uber Technologies Inc. What is Trip Radar and how does it work? (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article. The text references the GMB union and speeds in mph, indicating a UK-facing version. Article body. URL: https://help.uber.com/driving-and-delivering/article/what-is-trip-radar-and-how-does-it-work?nodeId=b6fb7065-ce66-490c-a911-d4e6d5c10d29. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S19.*

##### Control, working time and the freedom to accept, decline or cancel

- **chunk_id**: `L3-3.1-015`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (PARTIAL)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `freedom_to_refuse`, `working_time_autonomy`, `control`, `fare_negotiation`
- **section**: Section 2.4 Your Relationship with Uber

Verbatim text:

> You acknowledge and agree that Uber’s provision to you of the Driver App and the Uber Service creates a legal and direct business relationship between you and Uber. Uber does not, and shall not be deemed to, direct or control you or your Drivers generally, or in your or your Drivers' performance under this Agreement, specifically, including in connection with the operation of your business, your or your Drivers' provision of Transportation Services, your or your Drivers' acts or omissions, or the operation and maintenance of any Vehicles. Uber does not control or interfere with the actual provision of Transportation Services by you or your Drivers including the quality of the Transportation Services, Vehicle condition, or your or your Drivers' conduct or settlement or negotiation of the Fare actually paid/payable by the Users.
>
> You acknowledge and agree that you and/or your Drivers retain the sole right to determine when and for how long you or each of your Drivers will utilize the Driver App or the Uber Service. You agree and acknowledge that you and/or your Drivers retain the option, via the Driver App, to attempt to accept or to decline or ignore a User’s request for Transportation Services, or to cancel an accepted request for Transportation Services via the Driver App, subject to Uber’s applicable policies (including the Community Guidelines, to the extent applicable).

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.4 Your Relationship with Uber. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Express right to operate other businesses and to use competing applications

- **chunk_id**: `L3-3.1-016`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (SUPPORTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `multi_apping`, `exclusivity`, `branding_restriction`
- **section**: Section 2.5

Verbatim text:

> You will not, and shall ensure that your Drivers do not: (a) display Uber’s or any of its Affiliates' names, logos or colours on any Vehicle(s); or (b) wear a uniform or any other clothing displaying Uber’s or any of its Affiliates’ names, logos or colors. The foregoing does not apply if you and Uber have agreed otherwise or if so required by law.
>
> You acknowledge and agree you have the complete right and discretion to engage in or operate other independent business(es) or income generating activities, and the right to direct your Drivers to do so at your own discretion, including the ability to provide services at any time to any third party, which are separate from the Transportation Services. For the sake of clarity, you understand that you retain the complete right to provide transportation services to your existing customers and to use other software application services in addition to the Uber Service.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.5. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Fleet Partner responsibility for the drivers it engages

- **chunk_id**: `L3-3.1-018`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.c` (CONTRADICTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `intermediary`, `fleet_partner`, `labour_law_compliance`, `liability`
- **section**: Section 2.7 Your Relationship with Drivers

Verbatim text:

> In the event you are a Fleet Partner, you shall have the sole responsibility for any obligations or liabilities towards your Drivers that arise from your relationship with your Drivers (including in relation to the provision of Transportation Services). You acknowledge and agree that you exercise sole control over your Drivers and will comply with all applicable laws (including tax, social security and employment laws) governing or otherwise applicable to your relationship with your Drivers. You shall require each of your Drivers to comply with the applicable terms and conditions of this Agreement, the Community Guidelines as well as applicable laws. Notwithstanding the acceptance of the terms of this Agreement by your Drivers at the time of signing up to the Driver App and/or your right (if applicable) to take recourse against a Driver, you acknowledge and agree that you are at all times responsible and liable for the acts and omissions of your Drivers vis-­à-­vis Users and Uber, even where such liability may not be mandated under applicable law.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.7 Your Relationship with Drivers. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Unilateral modification of the agreement

- **chunk_id**: `L3-3.1-020`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.a` (CONTRADICTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `unilateral_amendment`, `notice_period`, `supplemental_terms`
- **section**: Sections 14.1 Modification and 14.2 Supplemental Terms and Addenda

Verbatim text:

> Modification. Uber reserves the right to modify the terms and conditions of this Agreement at any time, effective upon publishing an updated version of this Agreement on the online portal available to you on the Uber Service. Uber reserves the right to modify any information referenced at hyperlinks from this Agreement from time to time. You hereby acknowledge and agree that, by using the Uber Service, or downloading, installing or using the Driver App, you are bound by any future amendments and additions to this Agreement, information referenced at hyperlinks herein, or documents incorporated herein, including with respect to Fare Calculations. Continued use of the Uber Service or Driver App after any such changes shall constitute your consent to such changes.
>
> Supplemental Terms and Addenda. Supplemental terms may apply to your and/or your Drivers use of the Uber Service, such as use policies or terms related to certain features and functionality, which may be modified from time to time (“Supplemental Terms”). Addenda to this Agreement may also apply, setting forth additional Territory specific and/or service-specific terms, as made available and as updated by Uber from time to time (individually "Addendum"). You may be presented with certain Supplemental Terms and/or Addenda from time to time, which are in addition to, and shall be deemed a part of this Agreement. Supplemental Terms and Addenda shall prevail over this Agreement in the event of a conflict.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 14.1 Modification and 14.2 Supplemental Terms and Addenda. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Assignment, subcontracting and entire agreement

- **chunk_id**: `L3-3.1-021`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (CONTRADICTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `assignment`, `subcontracting`, `entire_agreement`
- **section**: Sections 14.4 Assignment and 14.5 Entire Agreement

Verbatim text:

> Assignment. You may not assign or transfer this Agreement or any of its rights or obligations hereunder, in whole or in part, without Uber's prior written consent. You may not subcontract your rights or obligations under this Agreement to any person, without Uber's prior written consent. Uber may assign or transfer this Agreement or any or all of its rights or obligations hereunder, in whole or in part, without consent. Uber may subcontract its rights and obligations under this Agreement to any person without consent.
>
> Entire Agreement. This Agreement, including the recitals, terms contained in any hyperlinks referenced in this Agreement and all Addenda and Supplemental Terms, constitutes the entire agreement and understanding of the parties with respect to its subject matter, and replaces and supersedes all prior or contemporaneous agreements or undertakings regarding such subject matter. In this Agreement, the words “including” and “include” mean “including, but not limited to.” The recitals form a part of this Agreement.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Sections 14.4 Assignment and 14.5 Entire Agreement. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Confidentiality obligations binding the driver

- **chunk_id**: `L3-3.1-024`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (PARTIAL), `5.1.c` (PARTIAL)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `confidentiality`, `nda`, `information_restriction`
- **section**: Section 6 Confidentiality

Verbatim text:

> Each party acknowledges and agrees that in the performance of this Agreement it may have access to or may be exposed to, directly or indirectly, confidential information of the other party ("Confidential Information"). Confidential Information includes Uber Data, Driver IDs, User Information, and the transaction volume, marketing and business plans, business, financial, technical, operational and such other non--public information of each party (whether disclosed in writing or verbally) that such party designates as being proprietary or confidential or of which the other party should reasonably know that it should be treated as confidential.
>
> Each party acknowledges and agrees that: (a) all Confidential Information shall remain the exclusive property of the disclosing party; (b) it shall not use Confidential Information of the other party for any purpose except in furtherance of this Agreement; (c) it shall not disclose Confidential Information of the other party to any third party, except to its employees, officers, contractors, agents and service providers ("Permitted Persons") as necessary to perform under this Agreement, provided Permitted Persons are bound in writing to obligations of confidentiality and non-­use of Confidential Information no less protective than the terms hereof; and (d) it shall return or destroy all Confidential Information of the disclosing party upon the termination of this Agreement or at the request of the other party (subject to applicable law and, with respect to Uber, its internal record-­keeping requirements).
>
> Notwithstanding the foregoing, Confidential Information shall not include any information to the extent it: (a) is or becomes part of the public domain through no act or omission on the part of the receiving party; (b) was possessed by the receiving party prior to the date of this Agreement without an obligation of confidentiality; (c) is disclosed to the receiving party by a third party having no obligation of confidentiality with respect thereto; or (d) is required to be disclosed pursuant to law, court order, subpoena or governmental authority, provided the receiving party notifies the disclosing party thereof and provides the disclosing party a reasonable opportunity to contest or limit such required disclosure, provided further that no such notice or opportunity shall be required if disclosure is made pursuant to Section 7.1 below.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 6 Confidentiality. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Uber's stated role and the driver partner's independence in the Mumbai auto service

- **chunk_id**: `L3-3.1-027`
- **source_id**: S33
- **source_type**: `company_terms_rider_facing`
- **jurisdiction**: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners.
- **audience**: `mixed`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (CONTRADICTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `uber_role`, `independent_contractor`, `cancellation`, `service_quality`
- **section**: Section 1 Nature of Services & Role of Uber
- **driver_relevance**: Rider-facing addendum. It states Uber's position on the driver partner's independence and on Uber's non-responsibility for a driver's cancellation or refusal of a trip.

Verbatim text:

> Uber provides a technology platform that enables riders to connect with independent Driver Partners who subscribe to Uber’s Auto software-as-a-service. Uber does not provide transportation services or function as a transportation carrier. The transportation services are provided solely by Driver Partners, who operate independently. Uber has no control over the execution, completion, or quality of the rides. Uber shall not be responsible for any cancellation by the Driver Partner or refusal to provide transportation services by the Driver Partner.

*Citation: Uber India Systems Private Limited. Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai). Jurisdiction stated or inferred: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners. Section 1 Nature of Services & Role of Uber. URL: https://www.uber.com/in/en/legal/india-auto-saas-rider-terms-and-conditions---mumbai/. Document date: 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025. Retrieved: 2026-09-13. Source ID: S33.*

##### Tenure as a factor in access decisions

- **chunk_id**: `L3-3.2-001`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (ASSERTED)
- **policy_surfaces**: `tenure_consideration`, `deactivation_grounds`
- **section**: Section heading: Our commitment to drivers

Verbatim text:

> Drivers who have been using the platform for years have built trust with their customers and Uber. Uber may consider time on the platform and number of trips in decisions around access, except for serious incidents.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Our commitment to drivers. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Term of the agreement

- **chunk_id**: `L3-3.2-002`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (PARTIAL)
- **policy_surfaces**: `contract_term`
- **section**: Section 12.1 Term

Verbatim text:

> Term. This Agreement shall commence on the date that the Agreement is executed by you (electronically or otherwise) and shall continue until terminated as set forth herein.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 12.1 Term. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Termination rights and notice periods

- **chunk_id**: `L3-3.2-003`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (SUPPORTS)
- **policy_surfaces**: `termination`, `notice_period`, `immediate_deactivation`
- **section**: Section 12.2 Termination

Verbatim text:

> Termination. Either party may terminate this Agreement: (a) without cause at any time upon seven (7) days prior notice to the other party; (b) immediately, without notice, for the other party’s material breach of this Agreement; or (c) immediately, without notice, in the event of the insolvency or bankruptcy of the other party, or upon the other party’s filing or submission of request for suspension of payment (or similar action or event) against the terminating party. In addition, Uber may terminate this Agreement or deactivate your and/or any of your Drivers’ account immediately, without notice, in the event you and/or such Driver of yours, as applicable, no longer qualifies, under applicable law or the standards and policies of Uber, to provide Transportation Services or to operate the Vehicle, or as otherwise set forth in this Agreement.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 12.2 Termination. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Effect of termination and surviving clauses

- **chunk_id**: `L3-3.2-004`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (PARTIAL)
- **policy_surfaces**: `termination_effect`, `survival`
- **section**: Section 12.3 Effect of Termination

Verbatim text:

> Effect of Termination. Upon termination of the Agreement, you and your Drivers, as applicable, shall: immediately delete and fully remove the Driver App from all the Driver Devices. Outstanding payment obligations and Sections 1, 2.3, 2.4, 2.5, 2.6, 2.7, 4.4, 5.3, 6, 7, 9, 10, 11, 12.3, 13, 14 and 15 shall survive the termination of this Agreement.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 12.3 Effect of Termination. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Absence of a post-engagement restriction on working elsewhere

- **chunk_id**: `L3-3.2-005`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L3
- **threshold**: 3.2
- **criteria**: `3.2.b` (SUPPORTS)
- **policy_surfaces**: `post_engagement_restriction`, `multi_apping`
- **section**: Section 2.5
- **note**: Reproduced under this threshold because it is the clause that addresses the driver's freedom to work elsewhere. It is framed as a right during the term and the Agreement states no restriction applying after termination.

Verbatim text:

> You acknowledge and agree you have the complete right and discretion to engage in or operate other independent business(es) or income generating activities, and the right to direct your Drivers to do so at your own discretion, including the ability to provide services at any time to any third party, which are separate from the Transportation Services. For the sake of clarity, you understand that you retain the complete right to provide transportation services to your existing customers and to use other software application services in addition to the Uber Service.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.5. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### The three quality metrics Uber India applies to drivers

- **chunk_id**: `L4-4.1-011`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.2.d` (PARTIAL)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `quality_metrics`, `star_ratings`, `cancellation_rate`, `acceptance_rate`
- **section**: Section heading: WHY DRIVERS CAN LOSE ACCESS TO UBER, sub-heading Quality

Verbatim text:

> There will always be unforeseen events that may ultimately lead to you losing access to your driver account — and we’ll update this policy regularly—but the following are sufficient causes for Uber to take action: quality; safety; fraud; and discrimination.
>
> Riders who use Uber expect their drivers to drive safely, as well as be courteous and professional. The higher the quality of the service, the more riders want to take trips, which in turn means more opportunities for drivers to earn money. Poor service has the opposite effect over time.
>
> There are several ways we measure driver quality, with the most important being Star Ratings, Cancellation Rate, and Acceptance Rate:
>
> After every trip, drivers and riders are able to rate each other on a scale of one to five stars, as well as give feedback on how the trip went. This two-way system holds everyone accountable for their behavior. Accountability helps create a respectful, safe environment for both drivers and riders. Drivers can see their current rating in the Ratings tab of the Uber Partner app.
>
> How is my rating as a driver calculated? Your rating is based on an average of the number of post-trip stars riders gave you (from 1 to 5 stars), up to your last 500 rated trips or the total number of rated trips you’ve taken, if less than 500.
>
> What leads to you losing access to your account? There is a minimum average rating in each city. This is because there are cultural differences in the way people in different cities rate each other. We will alert you over time if your rating is approaching this limit, and you’ll also get information about quality improvement courses that may help you improve. However, if your average rating still falls below the minimum after multiple notifications, you will lose access to your account.
>
> A trip cancellation is when you accept a trip request and then cancel it, or in some cases, when a rider cancels a trip and such cancellation may be attributable to your actions. This may include instances where a cancellation is flagged as one where a rider was influenced by you to cancel or you accepted a trip without the intent to complete it.
>
> How is my cancellation rate calculated? Your cancellation rate is calculated as a percentage of trips canceled out of your last 100 accepted requests. This includes cancellations you initiated, and in some cases, rider cancellations that may be attributed to you (for example, if you’ve accepted 100 trips and 4 of them are canceled, your cancellation rate would be 4%.). High-quality drivers typically have a cancellation rate lower than 5%.
>
> What leads to you losing access to your account? Maintaining a high quality experience is essential for riders using our platform. We will alert you multiple times if your cancellation rate is consistently high. Continued high cancellation rates may result in temporary or permanent loss of account access.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section heading: WHY DRIVERS CAN LOSE ACCESS TO UBER, sub-heading Quality. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

##### Documentation verification and deactivation for non-compliance

- **chunk_id**: `L4-4.1-021`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.2.a` (PARTIAL)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `document_validity`, `verification`, `deactivation_grounds`, `material_breach`
- **section**: Section 3.3 Documentation

Verbatim text:

> Documentation. To ensure your and/or each of your Driver’s compliance with all requirements in Sections 3.1 and 3.2 above, you must provide Uber with written copies of all such licenses, permits, approvals, authority, registrations and certifications prior to your or your Drivers' provision of any Transportation Services. Thereafter, you must submit to Uber written evidence of all such licenses, permits, approvals, authority, registrations and certifications as they are renewed. Uber shall, upon request, be entitled to review such licenses, permits, approvals, authority, registrations and certifications from time to time, and your failure to provide or maintain any of the foregoing shall constitute a material breach of this Agreement. Uber reserves the right to independently verify your and/or any of your Drivers' documentation from time to time in any way Uber deems appropriate in its reasonable discretion. You acknowledge and agree that Uber reserves the right, at any time in Uber's sole discretion, to deactivate or otherwise restrict you and/or your Drivers from accessing or using the Driver App or the Uber Service if you and/or any of your Drivers fail to meet the requirements set forth in this Section 3.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 3.3 Documentation. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### How Uber describes the matching algorithm

- **chunk_id**: `L4-4.2-002`
- **source_id**: S08
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.2.d` (PARTIAL), `4.2.d` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `matching_algorithm`, `automated_decision`, `work_allocation`
- **section**: Section II.C.1 Matching

Verbatim text:

> Uber uses algorithms and machine learning models to efficiently match riders and Drivers, or Delivery People and order recipients.
>
> The matching process is triggered when riders or order recipients request transportation or deliveries through Uber. Our algorithms then evaluate various factors to determine the best match for a given trip or delivery request based on the available Drivers/Delivery People in the area. These factors include your location, proximity to the rider/order recipient, requested destination, traffic conditions and historical data (including, in some markets, whether you and the rider have previously reported having negative experiences with each other).
>
> The trip or delivery request is then communicated to you and other Drivers/Delivery Persons matched through this process. Once a ride or delivery is accepted, we send confirmation of the match to the Driver/Delivery Person and the rider/order recipient.
>
> We continually refine our matching process to provide the best experience to all users on our platform, and may consider different factors depending on where you use Uber.

*Citation: Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction stated or inferred: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Section II.C.1 Matching. URL: https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved: 2026-09-13. Source ID: S08.*

##### Automated safety uses of driver data, including pairing avoidance and deactivation triggers

- **chunk_id**: `L4-4.2-004`
- **source_id**: S08
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.2.d` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `automated_decision`, `rating_data_use`, `deactivation_trigger`, `monitoring`
- **section**: Section II.B How we use data, safety and security uses

Verbatim text:

> Cross-comparing user-submitted ID documents, profile photos and selfies to detect for duplicate accounts and prevent previously deactivated users from regaining access to our platforms
>
> Predicting and helping avoid pairings of users that may result in increased risk of conflict,* or where one user has previously given the other a low (for instance, one star) rating.
>
> Identifying potentially unsafe Drivers and driving. This can lead to your receiving messages encouraging safer driving, and/or account deactivation.

*Citation: Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction stated or inferred: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Section II.B How we use data, safety and security uses. URL: https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved: 2026-09-13. Source ID: S08.*

##### Trip Radar as a described work-allocation mechanism

- **chunk_id**: `L4-4.2-008`
- **source_id**: S19
- **source_type**: `company_help_centre`
- **jurisdiction**: Uber Help article. The text references the GMB union and speeds in mph, indicating a UK-facing version.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.1.f` (SCOPE LIMITED), `3.2.d` (SUPPORTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `work_allocation`, `matching_algorithm`, `driver_feedback_changes`
- **section**: Article body
- **note**: This Uber Help article references the GMB union and speeds in mph, indicating a UK-facing version. No India-specific Trip Radar article published by Uber was located during this search.

Verbatim text:

> Trip Radar is a feature that shows you more trips to choose from in your area. Multiple drivers can look at trip requests at the same time and choose according to their personal preferences, such as the destination of the trip.
>
> Trip Radar is a system that complements standard trip offers, giving you more visibility on earning opportunities and improving wait times for riders and drivers. Since its initial launch in 2022, we’ve made adjustments to trip Radar based on driver feedback, including from the GMB. These adjustments include:
>
> Ensuring the trip Radar trip request contains the same information as standard offers, such as the map, route, and rider location.
>
> Decreasing the frequency of trip Radar offers and reducing interruptions from standard offers.
>
> Displaying only one offer at a time when driving below 10 mph.
>
> Displaying trip Radar offers in the same format as standard offers when driving above 10 mph.
>
> You will continue to receive individual trip offers as well as being able to use Trip Radar.
>
> Since other drivers will also have access to this list, you won’t necessarily get all of your trips you are interested in, but you can tap as many as you like.
>
> By bidding on more Trip Radar offers within the Job Board, you are maximising your chances of getting assigned to a trip that meets your preferences.
>
> You will see up to five trips. Please note in times of lower rider demand you may see less than five trips.
>
> When you wish to select a trip, the app will let you know if you have been successfully matched with a rider.
>
> If you are not successfully matched, you will see refreshed trips within the app.

*Citation: Uber Technologies Inc. What is Trip Radar and how does it work? (Uber Help, Driving and Delivering). Jurisdiction stated or inferred: Uber Help article. The text references the GMB union and speeds in mph, indicating a UK-facing version. Article body. URL: https://help.uber.com/driving-and-delivering/article/what-is-trip-radar-and-how-does-it-work?nodeId=b6fb7065-ce66-490c-a911-d4e6d5c10d29. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S19.*

##### Algorithmic prioritisation of work as an Uber Pro reward in India

- **chunk_id**: `L4-4.2-009`
- **source_id**: S03
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.2.d` (PARTIAL), `4.2.d` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `work_allocation`, `tiered_dispatch`, `matching_algorithm`
- **section**: Section headings: Priority Rides; Airport Advantage; Priority Queue Access; Area Preferences

Verbatim text:

> Details: Eligible Driver Partners will receive a higher proportion of ride requests, which may be based on their past preferences on the Uber Driver App, and are sent directly to them and which are exclusively theirs to accept or decline before they expire. The following Uber Trip types are not eligible for this Reward: Reserve, Uber Black, IxC, Rentals and Uber XL.
>
> Details: Airport Advantage provides eligible Driver Partners with the benefit of receiving priority matching for ride requests through the Uber Driver App’s Trip Radar feature. The following ride types are not eligible for priority matching for Trip Radar at airports: Reserve, Uber Black, IxC, Rentals and Uber XL.
>
> Details: Driver Partners in the Diamond Tier who are not rematched when dropping off a passenger at a participating airport (see list below) will be given Priority Queue Access, which will be automatically redeemed upon entering the FIFO queue. Such Driver Partners must enter the FIFO queue before the time specified on the in-app pop-up notification. The Driver Partners in the Diamond Tier who enter the FIFO queue will be moved to the front of the line and should expect shorter waiting times for trips. Priority Queue Access is available only at select terminals in Delhi, Mumbai, Chennai, Pune, Kolkata, Ahmedabad and Chandigarh airports.
>
> Details: Area Preferences allows Driver Partners to select areas in their city that they would like to drive in. Driver Partners will only receive trips where the pick-up and drop-off destinations are within the boundaries of the areas they have selected within the Uber Driver App. This feature is redeemable for up to 2 hours per day. While using Area Preferences, Driver Partners will not receive Airport pick-up requests. In order to be added to Airport queues, Drivers must first have Area Preferences turned off and be located at a Staging lot.
>
> *Area Preferences currently is only available in the following markets: Delhi NCR, Kolkata, Bangalore, Chennai, Hyderabad, Guwahati, Jaipur, Ahmedabad, Mumbai, Pune, Chandigarh, Lucknow

*Citation: Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction stated or inferred: India. Section headings: Priority Rides; Airport Advantage; Priority Queue Access; Area Preferences. URL: https://www.uber.com/in/en/legal/uber-pro-program-terms/. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved: 2026-09-13. Source ID: S03.*

##### Product changes Uber India attributes to consultation with drivers

- **chunk_id**: `L4-4.2-012`
- **source_id**: S21
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.2.d` (SUPPORTS), `4.1.a` (SUPPORTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `worker_consultation`, `pre_acceptance_disclosure`, `product_change`
- **section**: Section headings: Reduction in driver cancellations; Easier app-experience for driver partners

Verbatim text:

> Reduction in driver cancellations: The Council meetings helped Uber better understand the issues faced by driver partners that led them to cancel rides. Subsequently, we made the drop-off destination and mode of payment known upfront to driver partners prior to their acceptance of trip requests. These changes helped driver partners make an informed decision and reduced trip cancellations.
>
> Easier app-experience for driver partners: Driver partners also highlighted bugs or missing features on the Uber app such as the lack of a convenient login interface. We now provide a phone button on the homepage added to the driver-partner’s Uber app to call for support and display the customer’s chosen payment method for a trip.
>
> Based on these sessions, and recommendations from Aapti Institute, we implemented several changes last year. As per an internal survey of 80,000 driver partners by Uber, 85% of the respondents believed that the changes had a positive impact on their driving experience and 92% drivers wanted DAC to continue.

*Citation: Uber Newsroom India (IndiaSA Comms Team). Uber announces 2nd edition of Driver Advisory Council. Jurisdiction stated or inferred: India. Section headings: Reduction in driver cancellations; Easier app-experience for driver partners. URL: https://www.uber.com/in/en/newsroom/uber-second-edition-driver-advisory-council/. Document date: 2023-04-17 (dateline on page). Retrieved: 2026-09-13. Source ID: S21.*

##### Contractual treatment of ratings and comments

- **chunk_id**: `L4-4.2-013`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 3.2
- **criteria**: `3.2.d` (CONTRADICTS), `4.1.b` (CONTRADICTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `rating_data_use`, `rating_publication`, `rating_moderation`, `voluntary_rating`
- **section**: Section 2.8 Ratings

Verbatim text:

> You acknowledge and agree that: (a) after receiving Transportation Services, a User will be prompted by the Uber App to provide a rating of, and optionally, to provide comments and feedback, about such Transportation Services, and about you or your Driver, and (b) after providing Transportation Services, you or your Driver will be prompted by the Driver App to provide a rating of the User, and optionally, to provide comments or feedback about the User. You shall yourself, or shall instruct all your Drivers to, provide ratings and feedback in good faith.
>
> Uber and its Affiliates reserve the right to use, share and display your and/or your Drivers’ ratings and comments (including User comments) in any manner in connection with the business of Uber and its Affiliates without your or your Drivers' approval. You agree and acknowledge that Uber and its Affiliates are distributors (without any obligation to verify) and not publishers of your, Driver and User ratings and comments, provided that Uber and its Affiliates reserve the right to censor or remove comments in the event that such comments include obscenities or other objectionable content, include an individual’s name or other personal information, or violate any privacy laws, other applicable laws or Uber’s or its Affiliates’ content policies. There is no obligation on you or your Drivers to provide ratings or comments nor is there any consequence of not providing the same.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.8 Ratings. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_3_1_02** — bears on `3.2.a`: No official Uber document located for India commits to advance notice or to consultation with worker representatives, trade unions, recognised worker bodies, or a representative sample of affected drivers before substantial changes to contractual terms or working conditions. The published change mechanism is unilateral: Uber may modify the Agreement “at any time, effective upon publishing an updated version of this Agreement on the online portal” and continued use “shall constitute your consent to such changes” (S32, Section 14.1). The same pattern appears at S03.  *(Re-filed from 3.1.)*
- **absence_4_1_05** — bears on `3.2.d`: No official Uber document located for India publishes the numerical minimum average rating applicable in any Indian city. Uber states only that “There is a minimum average rating in each city” (S01).  *(Re-filed from 4.1.)*
- **absence_4_1_06** — bears on `3.2.d`: No official Uber document located for India publishes the numerical acceptance-rate, cancellation-rate or star-rating thresholds used as Uber Pro Program Standards. The Uber Pro terms defer these to the app (S03).  *(Re-filed from 4.1.)*
- **absence_4_2_01** — bears on `3.2.d`: No official Uber document located for India publishes a transparency report, question-and-answer process, or equivalent explainability mechanism that lets a driver understand the behaviour of Uber’s algorithmic systems as a whole. Uber’s published explanation of its algorithms is the descriptive account in the global driver Privacy Notice (S08). The India driver Services Agreement (S32) contains no clause on algorithmic explainability.  *(Re-filed from 4.2.)*

## 7. Lever L4 — Fair Management

- **lever**: L4
- **fairwork_principle**: P4
- **thresholds**: 4.1, 4.2

### 7.1 Threshold 4.1 — Provides due process for decisions affecting workers

- **threshold_id**: 4.1
- **lever**: L4
- **criteria**: `4.1.a`, `4.1.b`, `4.1.c`, `4.1.d`
- **extract_count**: 12
- **audience_driver**: 12
- **audience_mixed**: 0
- **absence_count**: 4

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> The platform must satisfy ALL of the following

- **[4.1.a]** There is an easily accessible channel for workers to communicate with a human representative of the platform and to effectively solve problems. This channel is documented in the contract and available on the platform interface. Platforms should respond to workers within a reasonable timeframe.
- **[4.1.b]** There is a process for workers to meaningfully and effectively appeal low ratings, non-payment, payment issues, deactivations, and other penalties and disciplinary actions. This process is documented in a contract and available on the platform interface.[11]
- **[4.1.c]** In the case of deactivations, the appeals process must be available to workers who no longer have access to the platform.
- **[4.1.d]** Workers are not disadvantaged for voicing concerns or appealing disciplinary actions.

> **INLINED FOOTNOTE [11]**
> Workers should have the option of escalating grievances that have not been satisfactorily addressed and, in the
> case of automated decisions, should have the option of escalating it for human mediation.

#### Extracts from official Uber documentation

##### Breach of the driver agreement as a ground for action

- **chunk_id**: `L3-3.1-011`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L3
- **threshold**: 4.1
- **criteria**: `3.2.b` (PARTIAL), `4.1.d` (CONTRADICTS)
- **refiled_from**: 3.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `contract_breach`, `deactivation_grounds`
- **section**: Section heading: Unacceptable Activities

Verbatim text:

> To maintain the transparency and safety of each trip for all users, activities conducted outside of Uber’s system—like anonymous pickups—are prohibited.
>
> What leads to you losing access to your account? We will take action against a driver for activities such as: accepting illegal street hails while using the Uber app; harming the business or brand, like unauthorized use of Uber’s trademark or intellectual property, or otherwise violating the drivers’ agreement with Uber; and soliciting payment of fares outside the Uber system.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section heading: Unacceptable Activities. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

##### Principles Uber states govern loss of account access

- **chunk_id**: `L4-4.1-001`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.a` (ASSERTED), `4.1.b` (PARTIAL)
- **policy_surfaces**: `deactivation_principles`, `notice`, `appeal_threshold`, `transparency_of_reasons`
- **section**: Section heading: Our commitment to drivers

Verbatim text:

> We’re strongly motivated to keep access to the Uber platform open and to help drivers get online when they want to work. Losing account access doesn’t happen often, but when it does, we know it can be frustrating.
>
> It’s our responsibility to ensure that our processes are fair, accurate, and transparent—and that drivers trust that we’re doing the right thing. That’s why we’ve developed the following principles to guide us:
>
> Drivers should be aware of the behaviors that can put their account access at risk.
>
> Drivers who have been using the platform for years have built trust with their customers and Uber. Uber may consider time on the platform and number of trips in decisions around access, except for serious incidents.
>
> If any loss of access occurs, Uber will make every effort to be clear, empathetic, and consistent in our communications and specific and transparent about the reasons behind our decision, except where doing so poses a risk to other users.
>
> Outside of the most serious cases, drivers should have the ability to request a review of any decision that removes access for more than 7 days and can’t be resolved on their own.
>
> Uber should take a consistent approach to creating, reviewing, and updating account deactivation and review standards.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Our commitment to drivers. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### The account review process: human involvement, notice, evidence and false allegations

- **chunk_id**: `L4-4.1-002`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.b` (ASSERTED), `4.1.d` (ASSERTED)
- **policy_surfaces**: `human_review`, `advance_notice`, `appeal_channel`, `evidence_submission`, `false_allegation_protection`
- **section**: Section heading: Our account review process

Verbatim text:

> While data and technology are useful tools for improving the safety and security of the Uber platform, manual reviews will always play a role in helping to make sure drivers and delivery people are treated fairly and that their accounts aren’t affected by fraudulent reports.
>
> Whenever possible, we’ll inform a driver if they’re at risk of losing access to their account in the form of warning messages. However, there are times when we may need to remove access without warning, such as for legal or safety reasons.
>
> Drivers should have the ability to request a review of an account deactivation and provide additional information to support their case, like audio or video recordings. That’s why we built an in-app Review Center which drivers can use to appeal their account deactivations.
>
> We’ve established processes to identify riders who abuse our ratings or customer support systems, often with the aim of getting a refund. We work to help ensure that allegations made by these customers aren’t considered in account deactivation decisions.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Our account review process. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### How loss of access happens and what Uber states it does

- **chunk_id**: `L4-4.1-003`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.b` (SUPPORTS)
- **policy_surfaces**: `deactivation_grounds`, `warning_process`, `appeal_channel`, `support_access`
- **section**: Section heading: Why losing access happens and what to do

Verbatim text:

> The reasons why a driver might lose access to their account can include issues like expired documents or an issue with their background check.
>
> Sometimes, drivers may also temporarily or permanently lose access of their accounts due to certain quality issues, for example, in case of unusually high rate of cancellations, pressuring customers to cancel trips and taking the trip out of the Uber app, or pressuring customers to pay in cash or asking for extra cash outside the fare shown on the Uber app. In such cases, we alert you multiple times before logging you out of the Driver app.
>
> Drivers should have the ability to request that an account deactivation be reviewed and to provide evidence to support their case. That’s why we built an in-app Review Center and are continuing to expand it around the world.
>
> Losing access, even temporarily, can be disruptive, so we review each report fairly and promptly. If there are steps to take to regain account access, we’ll include them in the message we send to the driver. Uber’s customer support team can always be contacted for help.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Why losing access happens and what to do. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Operation of the Review Centre, evidence and timelines

- **chunk_id**: `L4-4.1-004`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.b` (PARTIAL), `4.1.c` (SUPPORTS)
- **policy_surfaces**: `appeal_channel`, `appeal_timeline`, `status_during_review`, `evidence_submission`
- **section**: Section heading: Frequently asked questions

Verbatim text:

> There is a review center live on the app in case you have been rejected from the platform. You can choose to request a review and upload relevant supporting information, including video and audio recordings and photos.
>
> Agents are able to review audio recordings made through the Uber app. There you can choose to request a review and upload relevant supporting information, including video and audio recordings and photos.
>
> The review time may differ from case to case. Once a driver submits a review request, they will be notified of the expected processing time and status. Accounts remain deactivated while the review is underway.
>
> No. We understand that drivers feel like we often take the other side, but everyone who uses Uber follows the same Community Guidelines. It’s an unfortunate reality that some people may abuse our rating and customer support systems in order to get refunds or discounts. We’ve put in place processes to better identify these customers and to help ensure that their allegations aren’t considered in account deactivation decisions.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Frequently asked questions. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### In-app deactivation appeal announced for India

- **chunk_id**: `L4-4.1-005`
- **source_id**: S20
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.b` (SUPPORTS)
- **policy_surfaces**: `appeal_channel`
- **section**: Section heading: Transparent and Fair Processes

Verbatim text:

> Deactivation Review Center: Drivers can now appeal deactivations directly in the app if they believe they’re treated unfairly

*Citation: Uber Newsroom India (IndiaSA Comms). Uber's New Features to Make Driving Safer, Easier, and Fairer. Jurisdiction stated or inferred: India. Section heading: Transparent and Fair Processes. URL: https://www.uber.com/in/en/newsroom/uber-features-to-make-driving-safer-easier-and-fairer/. Document date: 2024-11-15 (dateline on page). Retrieved: 2026-09-13. Source ID: S20.*

##### Ratings as a ground of deactivation and the exclusion mechanism

- **chunk_id**: `L4-4.1-010`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.b` (ASSERTED), `4.2.e` (ASSERTED)
- **policy_surfaces**: `minimum_rating_threshold`, `rating_exclusion`, `warning_process`
- **section**: Section heading: Ratings

Verbatim text:

> A driver can lose access to part or all of the Uber platform for ratings that are below the minimum average rating in their city. If their rating is approaching the minimum limit, we will let them know and may share information that may help them improve their rating from riders.
>
> Driver ratings are an average of the last 500 ratings from riders. We understand there are things out of a driver’s control that may affect their rating. We have put in place a system to exclude ratings provided by overly negative or biased riders, and ratings with feedback that are beyond a driver’s control. Learn more here.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Ratings. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Support channels available to drivers in India

- **chunk_id**: `L4-4.1-019`
- **source_id**: S17
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.a` (SCOPE LIMITED)
- **policy_surfaces**: `support_access`, `in_person_support`
- **section**: Section heading: Get more information

Verbatim text:

> Have questions about driving with Uber? We’re here to give you answers.
>
> Browse frequently asked questions from drivers.
>
> In some cities, you might be able to get support in person at a Greenlight location.
>
> To check availability, go to Help in your Driver app, then Book an in person appointment, choose the issue you need help with, and tap Schedule an appointment if you want more help. Or you can visit our website.

*Citation: Uber Technologies Inc. Contact Uber (Drivers: How to Get Help). Jurisdiction stated or inferred: India. Section heading: Get more information. URL: https://www.uber.com/in/en/drive/contact/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S17.*

##### Contractual grounds on which Uber may deactivate or restrict access

- **chunk_id**: `L4-4.1-020`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.d` (CONTRADICTS)
- **policy_surfaces**: `deactivation_grounds`, `discretion`, `disparagement`, `reputational_harm`
- **section**: Section 2.5

Verbatim text:

> Uber retains the right, at any time in Uber's sole discretion, to deactivate or otherwise restrict you and/or your Drivers from accessing or using the Driver App or the Uber Service in the event of a violation of this Agreement or any other applicable relevant Uber policy, including the Community Guidelines (to the extent applicable); or your or your Drivers' disparagement of Uber or any of its Affiliates; or your or your Drivers' act or omission that causes harm to Uber’s or its Affiliates’ brand, reputation or business as determined by Uber in its sole discretion. Uber also retains the right to deactivate or otherwise restrict you and/or your Drivers from accessing or using the Driver App or the Uber Service for any other reason at the sole and reasonable discretion of Uber.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.5. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### The grievance address named in the driver contract

- **chunk_id**: `L4-4.1-022`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.a` (PARTIAL), `4.1.b` (PARTIAL)
- **policy_surfaces**: `grievance_channel`, `notice_channel`
- **section**: Section 14.7 Notices

Verbatim text:

> Any notice delivered by you to Uber under this Agreement must be delivered by contacting Uber at grievanceredressaloffice@uber.com.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 14.7 Notices. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

##### Automated safety, identity and fraud systems and the resulting right of appeal

- **chunk_id**: `L4-4.2-003`
- **source_id**: S08
- **source_type**: `company_policy_privacy_notice`
- **jurisdiction**: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located.
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `4.1.b` (SUPPORTS), `4.1.c` (SUPPORTS), `4.2.d` (PARTIAL)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `fraud_detection`, `biometric_verification`, `human_review`, `appeal_right`, `automated_decision`
- **section**: Section II.C.3 Safety, security, and fraud prevention and detection

Verbatim text:

> Uber uses algorithms and machine learning models to prevent and detect safety incidents or fraud against Uber or our users. This includes efforts to monitor for account takeovers, unauthorized account sharing, altered or false document submissions, duplicate or fake accounts and other suspicious user behaviors.
>
> For example, Uber uses identity verification tools, like Real-Time ID Check, to help verify that your account is being used by you and not someone pretending to be you. The Real-Time ID Check process requires Drivers/Delivery People to occasionally take a real-time selfie before going online. Where permitted by law, we may also use facial recognition technology to compare your selfie to your profile photo to verify that you are the person using your account, and that it is not being used by other people.
>
> We also use automated processes to validate your ID documents and profile photo associated with your account. These include checks to verify that (1) the driver’s license you submit at or after onboarding is valid, unaltered, and not associated with any other account; and (2) the profile photo you submit is of a real person and isn’t digitally altered, manipulated or associated with any other account.*
>
> If these processes flag your documents or photos as potentially fraudulent or not a match, specialized customer support agents will manually review them. If these agents determine that the documents or photos are invalid, don’t match or are otherwise noncompliant, your account may be deactivated. You have the right to appeal deactivation of your account. Please go here for more information on Uber’s deactivation process.
>
> Uber also uses tools that look for patterns that may indicate fraudulent or unsafe behavior, such as those which vary significantly from typical user behavior. To do this, Uber performs real-time monitoring of information collected from or generated by users, including location data, payment information and Uber usage. We also examine historical data and compare it against real-time data to help detect suspicious behavior.
>
> Uber may limit your access to our services, or require that you undertake a particular action such as verifying your identity before allowing such access, if Uber detects potential fraudulent or unsafe activity.
>
> You may contact Uber Support here if you have questions or concerns about these processes.

*Citation: Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction stated or inferred: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Section II.C.3 Safety, security, and fraud prevention and detection. URL: https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved: 2026-09-13. Source ID: S08.*

##### Anonymity of ratings and what drivers can see

- **chunk_id**: `L4-4.2-011`
- **source_id**: S14
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.1
- **criteria**: `3.2.d` (PARTIAL), `4.1.b` (CONTRADICTS)
- **refiled_from**: 4.2 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `rating_transparency`, `rating_anonymity`
- **section**: Section headings: The basics of ratings; How to give, get, and check ratings

Verbatim text:

> The Uber platform features a 2-way rating system: drivers and riders give each other ratings based on their trip experience. Your driver rating is an average of the last 500 ratings from your riders.
>
> After each trip, riders and drivers have the opportunity to rate each other from 1 to 5 stars, based on their trip experience. Ratings are anonymous. You won’t see individual ratings tied to a particular trip or person.
>
> If you or your rider chooses lower than 5 stars, the app may ask for a bit more feedback about why that rating was chosen.
>
> The app adds the ratings you get into an average that’s displayed to your riders before and during a trip. Your average rating is an average of the last 500 ratings you’ve received.
>
> You can see your ratings, feedback, and compliments in your Driver app. Tap the menu icon in the upper left corner, then your profile photo, and then tap the average rating under your name for details.

*Citation: Uber Technologies Inc. How star ratings work (Driver App basics). Jurisdiction stated or inferred: India. Section headings: The basics of ratings; How to give, get, and check ratings. URL: https://www.uber.com/in/en/drive/basics/how-ratings-work/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S14.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_3_2_04** — bears on `4.1.b`: The seven-day notice at S32 Section 12.2 applies to termination without cause only. The same clause permits Uber to terminate or deactivate immediately and without notice for material breach, or where the driver “no longer qualifies, under applicable law or the standards and policies of Uber, to provide Transportation Services or to operate the Vehicle, or as otherwise set forth in this Agreement.” No official Uber document located for India states how the seven-day notice interacts with the deactivation processes described at S01 and S02.  *(Re-filed from 3.2.)*
- **absence_4_1_02** — bears on `4.1.b`: No official Uber document located for India commits to a defined response time for appeals. Uber states only that “The review time may differ from case to case” and that the driver “will be notified of the expected processing time and status” (S02).
- **absence_4_1_03** — bears on `4.1.d`: No official Uber document located for India describes safeguards against retaliation for drivers who raise concerns or appeal disciplinary action. The published driver Services Agreement instead names “disparagement of Uber or any of its Affiliates” and acts causing harm to Uber’s “brand, reputation or business as determined by Uber in its sole discretion” as grounds on which Uber may deactivate (S32, Section 2.5).
- **absence_4_1_04** — bears on `4.1.d`: No official Uber document located for India reconciles the review commitments published at S02 with the contractual position at S32 Section 2.5, under which Uber “retains the right to deactivate or otherwise restrict you and/or your Drivers from accessing or using the Driver App or the Uber Service for any other reason at the sole and reasonable discretion of Uber.” The Services Agreement contains no appeal or review clause.

### 7.2 Threshold 4.2 — Provides equity in the management process

- **threshold_id**: 4.2
- **lever**: L4
- **criteria**: `4.2.a`, `4.2.b`, `4.2.c`, `4.2.d`, `4.2.e`
- **extract_count**: 6
- **audience_driver**: 2
- **audience_mixed**: 4
- **absence_count**: 2

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> The majority of platforms do not actively discriminate against particular groups of
> workers. However, they may inadvertently exacerbate already existing inequalities in
> their design and management. For example, there is a lot of gender segregation
> between different types of platform work. To achieve this point, platforms must show
> not only that they have policies against discrimination, but also that they seek to
> remove barriers for disadvantaged groups and promote inclusion.
>
> Platforms must satisfy ALL of the following:

- **[4.2.a]** The platform has an effective anti-discrimination policy laying out a clear process for reporting, correcting and penalising discrimination of workers on the platform on grounds such as race, social origin, caste, ethnicity, nationality, gender, sex, gender identity and expression, sexual orientation, disability, religion or belief, age or any other status.[12]
- **[4.2.b]** The platform has measures in place to promote diversity, equality and inclusion on the platform. It takes practical measures to promote equality of opportunity for workers from disadvantaged groups, including reasonable accommodation for pregnancy, disability, and religion or belief.
- **[4.2.c]** Where persons from a disadvantaged group (such as women) are significantly under-represented among a pool of workers, it seeks to identify and remove barriers to access by persons from that group.
- **[4.2.d]** If algorithms are used to determine access to work or remuneration or the type of work and pay scales available to workers seeking to use the platform, these are transparent and do not result in inequitable outcomes for workers from historically or currently disadvantaged groups.
- **[4.2.e]** It has mechanisms to reduce the risk of users discriminating against workers from disadvantaged groups in accessing and carrying out work.

> **INLINED FOOTNOTE [12]**
> In accordance with the ILO Convention No. 111 concerning Discrimination in Respect of Employment and
> Occupation and applicable national law.

#### Extracts from official Uber documentation

##### Grounds of deactivation, discrimination and refusal of service

- **chunk_id**: `L4-4.1-009`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.2
- **criteria**: `4.2.a` (PARTIAL)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `discrimination_policy`, `deactivation_grounds`, `accessibility`
- **section**: Section heading: Discrimination or refusing service

Verbatim text:

> A driver can lose access to their account for:
>
> Discriminating or making offensive remarks on the basis of race, color, disability, gender identity, marital status, pregnancy, national origin, age, religion, sex, sexual orientation, or any other characteristic protected under relevant law
>
> Refusing or canceling trips for riders because of wheelchairs, or other assistive devices
>
> Refusing to help fit wheelchairs or other assistive devices like walkers in the car. These devices can often be folded or disassembled to fit in the trunk.
>
> Making negative comments about someone’s personal characteristics, such as race, color, disability, gender identity, marital status, pregnancy, national origin, age, religion, sex, and sexual orientation.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Discrimination or refusing service. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Discrimination as a ground for permanent deactivation in India

- **chunk_id**: `L4-4.1-014`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: 4.2
- **criteria**: `4.2.a` (PARTIAL)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `discrimination_policy`, `immediate_deactivation`, `protected_characteristics`
- **section**: Section heading: Discrimination (drivers)

Verbatim text:

> Uber’s mission is to connect riders to reliable transportation, everywhere for everyone. We have a zero tolerance policy towards discrimination of any kind at Uber.
>
> What leads to you losing access to your account? It is unacceptable to refuse to provide services based on where someone is going, or characteristics like a person’s race, caste, religion, national origin, disability, sexual orientation, sex, marital status, gender identity, age or any other characteristic protected under relevant central, state or local law. Actions like these will result in permanent deactivation of your account.
>
> We want to help increase the transportation options for riders with disabilities. That’s why we have information available for drivers on this topic. See here for more on Uber’s commitment to accessibility. We expect drivers using the Uber app to comply with all relevant state, central, and local laws governing the transportation of riders with disabilities.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section heading: Discrimination (drivers). URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

##### The Non-Discrimination Policy as applied in India

- **chunk_id**: `L4-4.1-015`
- **source_id**: S04
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `mixed`
- **levers**: L4
- **threshold**: 4.2
- **criteria**: `4.2.a` (PARTIAL)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `discrimination_policy`, `protected_characteristics`, `geographic_discrimination`
- **section**: Full text of the policy
- **driver_relevance**: The Non-Discrimination Policy is addressed to all users of the platform. It operates on the driver directly: it defines conduct for which a driver loses platform access, and it is the instrument that carves out a driver declining a trip from what counts as geographical discrimination.

Verbatim text:

> Uber is committed to providing access to inclusive, reliable, and high-quality service options to everyone. Uber and its affiliates therefore prohibit discrimination against users based on race, ethnicity, skin color, age, disability, gender identity, marital status, pregnancy, national origin, religion, sex, sexual orientation, language, geographical location, or any other characteristic protected under relevant law. Such discrimination includes, but is not limited to, any user refusing to provide or accept services based on any of these characteristics or rating another user based on any protected trait.
>
> Discrimination on the basis of disability may include refusal to accommodate a rider with a service animal or assistive devices, if set forth in Uber’s Service Animal and Assistive Device Policy.
>
> Discrimination on the basis of geographical location does not include a driver or delivery person declining a trip that does not work for them, but intentionally refusing or canceling requests, or using features on the Uber Marketplace Platform to avoid receiving trip or delivery requests, solely for the purpose of avoiding a particular neighborhood due to the characteristics of the people or business that are located in that area, is not allowed.
>
> Any user found to have violated this prohibition will lose access to the Uber platform. Applicable laws in certain jurisdictions may require and/or allow the provision of services by and for the benefit of a specific category of persons. In such jurisdictions, services provided in compliance with these laws and the relevant applicable terms are permissible under this policy.

*Citation: Uber Technologies Inc. Uber Non-Discrimination Policy. Jurisdiction stated or inferred: India. Full text of the policy. URL: https://www.uber.com/in/en/legal/non-discrimination-policy/. Document date: 2024-07-23 (page states: Last modified: 7/23/2024). Retrieved: 2026-09-13. Source ID: S04.*

##### Zero Tolerance Policy on alcohol and drugs

- **chunk_id**: `L4-4.1-016`
- **source_id**: S05
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: Global document listed on the India legal hub index
- **audience**: `mixed`
- **levers**: L4
- **threshold**: 4.2
- **criteria**: `4.2.a` (PARTIAL)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `zero_tolerance`, `reporting_channel`
- **section**: Full text of the policy
- **driver_relevance**: The Zero Tolerance Policy is written to riders and tells them how to report a driver. It operates on the driver directly: it is the policy under which a report of alcohol or drug use is raised, and Uber states at S01 that a driver found under the influence is permanently deactivated.

Verbatim text:

> Uber does not tolerate the use of alcohol or drugs by drivers using the Uber app. If you believe your driver may be under the influence of drugs or alcohol, please ask the driver to END THE TRIP IMMEDIATELY. Then exit the car and call 911.
>
> After the driver has ended the trip, please report any feedback directly in the app by tapping Help from the menu and selecting your issue. You can also get in contact by visiting help.uber.com or emailing customercomplaints@uber.com.
>
> Read Uber’s Community Guidelines to learn more about how Uber enforces this policy.

*Citation: Uber Technologies Inc. Zero Tolerance Policy. Jurisdiction stated or inferred: Global document listed on the India legal hub index. Full text of the policy. URL: https://www.uber.com/global/en/legal/zero-tolerance-policy/. Document date: 2023-05-19 (page states: Last modified: 5/19/2023). Retrieved: 2026-09-13. Source ID: S05.*

##### Respect and conduct expectations set for all platform users in India

- **chunk_id**: `L4-4.1-017`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `mixed`
- **levers**: L4
- **threshold**: 4.2
- **criteria**: `4.2.e` (ASSERTED)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `respect_and_dignity`, `two_way_rating`, `reporting_channel`
- **section**: Section headings: Respect each other; Give riders and drivers some personal space; Feedback makes us all better
- **driver_relevance**: General sections of the Community Guidelines addressed to riders and drivers together. They set the conduct standard a driver is held to and the two-way rating and reporting mechanism a driver is measured by.

Verbatim text:

> We want Uber to be enjoyable and safe for everyone. These ground rules are designed to ensure that riders and drivers have a five star ride when using Uber. Please take a moment to read them. Because whether you’re a rider trying to get from A to B—or a partner wanting to earn money by driving —your behaviour matters.
>
> Treat your fellow riders and drivers as you would like to be treated yourself: with respect. It’s common courtesy not to shout, swear or slam the car door. And by tidying up after yourself—whether it’s taking your trash home or cleaning up a spilled drink—you’ll keep the car in good condition and ensure the next person has a pleasant ride too. Most important of all, remember that when you use Uber you will meet people who may look different or think differently from you. Please respect those differences. We want everyone to feel welcome when they use Uber.
>
> Whether you are a rider or driver, please rate your journey at the end of the trip. Honest feedback helps ensure that everyone is accountable for their behaviour. This accountability creates a respectful, safe environment for both riders and drivers. And if something happens during a ride—whether it’s a traffic accident or an argument—make sure to report it by tapping “Help” in the app so that our customer support team can follow up.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section headings: Respect each other; Give riders and drivers some personal space; Feedback makes us all better. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

##### Rider-side accountability that Uber applies in India

- **chunk_id**: `L4-4.1-018`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `mixed`
- **levers**: L4
- **threshold**: 4.2
- **criteria**: `4.2.e` (PARTIAL)
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `rider_accountability`, `two_way_rating`, `discrimination_policy`
- **section**: Section heading: WHY RIDERS CAN LOSE ACCESS TO UBER
- **driver_relevance**: Rider-side grounds for losing access, from the Community Guidelines. Kept because it is the enforcement the driver is on the receiving end of: it defines the rider conduct Uber states it will act on, including conduct directed at drivers, and it sets rider ratings and rider discrimination against drivers as grounds for rider deactivation.

Verbatim text:

> Here are some reasons why you could lose access to Uber as a rider:
>
> Damaging drivers’ or other passengers’ property. For example, damaging the car, breaking or vandalising a phone, intentionally spilling food or drink, smoking, or vomiting due to excessive alcohol consumption.
>
> Physical contact with the driver or fellow riders. As these Community Guidelines make clear, you shouldn’t touch or flirt with other people in the car. As a reminder, Uber has a no sex rule. That’s no sexual conduct with drivers or fellow riders, no matter what. And you should never hit or otherwise hurt a driver or fellow passenger.
>
> Use of inappropriate and abusive language or gestures. For example, asking overly personal questions, using verbal threats, and making comments or gestures that are aggressive, sexual, discriminatory, or disrespectful.
>
> Unwanted contact with the driver or fellow passenger after the trip is over. For example, texting, calling, or visiting someone in person after a ride has been completed.
>
> Rider behaviour. Riders may lose access to Uber if they don’t meet the Star Ratings requirements set out in these Community Guidelines.
>
> Uber has a zero tolerance policy towards discrimination of any kind. This means you will lose access to your account if you are found to have discriminated against drivers or other riders based on their race, caste, religion, national origin, disability, sexual orientation, sex, marital status, gender identity, age or any other characteristic protected under applicable law.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section heading: WHY RIDERS CAN LOSE ACCESS TO UBER. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_2_1_03** — bears on `4.2.b`: No official Uber document located for India describes a policy on reasonable accommodation for drivers with additional needs arising from pregnancy, care responsibilities, disability or other health conditions. Uber does not explicitly mention such accommodations.  *(Re-filed from 2.1.)*
- **absence_4_1_01** — bears on `4.2.d`: No official Uber document located for India states that Uber conducts regular impact assessments of AI or algorithmic systems used for evaluation, monitoring or performance management, to identify and mitigate risks of bias or discrimination. Uber does not explicitly mention algorithmic bias impact assessments in the India documentation reviewed.  *(Re-filed from 4.1.)*

## 8. Lever L5 — Fair Representation

- **lever**: L5
- **fairwork_principle**: P5
- **thresholds**: 5.1, 5.2

### 8.1 Threshold 5.1 — Assures freedom of association and the expression of worker voice

- **threshold_id**: 5.1
- **lever**: L5
- **criteria**: `5.1.a`, `5.1.b`, `5.1.c`
- **extract_count**: 5
- **audience_driver**: 5
- **audience_mixed**: 0
- **absence_count**: 6

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> Platforms must satisfy ALL of the following:

- **[5.1.a]** There is a documented mechanism[13] for the expression of collective worker voice that allows ALL workers, regardless of employment status, to participate without risks.
- **[5.1.b]** There is a formal, written statement of willingness to recognise, and bargain with, a collective, independent body of workers or trade union, that is clearly communicated to all workers, and available on the platform interface.[14]
- **[5.1.c]** Freedom of association is not inhibited, and workers are not disadvantaged in any way for communicating their concerns, wishes and demands to the platform, or expressing willingness to form independent collective bodies of representation.[15][16]

> **INLINED FOOTNOTE [13]**
> A mechanism for the expression of collective worker voice will allow workers to participate in the setting of
> agendas so as to be able to table issues that most concern them. This mechanism can be in physical or virtual
> form (e.g. online meetings) and should involve meaningful interaction (e.g. not surveys). It should also allow for
> ALL workers to participate in regular meetings with the management.

> **INLINED FOOTNOTE [14]**
> For example, "[the platform] will support any effort by its workers to collectively organise or form a trade union.
> Collective bargaining through trade unions can often bring about more favourable working conditions."

> **INLINED FOOTNOTE [15]**
> See the ILO's Freedom of Association and Protection of the Right to Organise Convention, 1948 (C087), which
> stipulates that "workers and employers, without distinction, shall have the right to establish and join organisations
> of their own choosing without previous authorisation" (Article 2); "the public authorities shall refrain from any
> interference which would restrict the right or impede the lawful exercise thereof" (Article 3) and that "workers' and
> employers' organisations shall not be liable to be dissolved or suspended by administrative authority" (Article 4).
> Similarly the ILO's Right to Organise and Collective Bargaining Convention, 1949 (C098) protects the workers
> against acts of anti-union discrimination in respect of their employment, explaining that not joining a union or
> relinquishing trade union membership cannot be made a condition of employment or cause for dismissal. Out of
> the 185 ILO member states, currently 155 ratified C087 and 167 ratified C098.

> **INLINED FOOTNOTE [16]**
> If workers choose to seek representation from an independent collective body of workers or union that is not
> readily recognized by the platform, the platform should then be open to adopt multiple channels of representation,
> when the legal framework allows, or seek ways to implement workers' queries to its communication with the
> existing representative body.

#### Extracts from official Uber documentation

##### Establishment and composition of the Driver Advisory Council in India

- **chunk_id**: `L5-5.1-001`
- **source_id**: S22
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L5
- **threshold**: 5.1
- **criteria**: `5.1.a` (SCOPE LIMITED), `5.2.a` (PARTIAL)
- **policy_surfaces**: `worker_voice_mechanism`, `consultative_body`, `third_party_oversight`
- **section**: Article body

Verbatim text:

> Drivers are at the heart of what we do at Uber. Now, to bring their voice to the table, we’re launching India’s first Driver Advisory Council (DAC). The Council will facilitate a two-way dialogue between Uber and drivers to address critical issues and improve drivers’ platform experience. The newly formed council held its inaugural national meeting in Gurugram.
>
> 35+ drivers were chosen from 6 cities to be a part of the first Council. These drivers work across a range of product offerings available on Uber including cars, auto-rickshaws, and motorbikes, and represent the interests of tens of thousands of drivers on our platform. The focus of every meeting is decided by the Council members. For the maiden meeting, a wide range of issues was discussed with a special focus on driver earnings and support – an area we’re committed to making improvements in.
>
> The Driver Advisory Council has a third-party review board led by Aapti Institute, a Bengaluru-based think tank to provide independent oversight on the Council’s work. Involved from the start in helping build the DAC, Aapti will anchor the initiative. The Independent Review Board will moderate discussions, identify actionable insights and follow up to create an ongoing dialogue. This will help focus on issues that matter and drive a deeper engagement between drivers and Uber.

*Citation: Uber Newsroom India (IndiaSA Comms Team). Moving Forward Together: Launching Driver Advisory Council. Jurisdiction stated or inferred: India. Article body. URL: https://www.uber.com/in/en/newsroom/uber-driver-advisory-council/. Document date: 2022-03-24 (dateline on page). Retrieved: 2026-09-13. Source ID: S22.*

##### Selection process and term of Driver Advisory Council members

- **chunk_id**: `L5-5.1-002`
- **source_id**: S22
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L5
- **threshold**: 5.1
- **criteria**: `5.1.a` (CONTRADICTS), `5.2.a` (PARTIAL)
- **policy_surfaces**: `consultative_body`, `selection_criteria`, `term_of_office`
- **section**: Section heading: How were the Driver Advisory Council members selected?

Verbatim text:

> Drivers underwent a three-phase selection process to be a part of the council as the entries were invited through self-nomination. After an overwhelming response, entries were filtered based on various parameters including the driver being active on the Uber platform and having no prior safety incidents. Finally, through meetings with the independent review board, the drivers were tested on their potential to contribute to solutions to prevailing challenges. The selected drivers will represent their community for a year after which the selection process will be repeated.

*Citation: Uber Newsroom India (IndiaSA Comms Team). Moving Forward Together: Launching Driver Advisory Council. Jurisdiction stated or inferred: India. Section heading: How were the Driver Advisory Council members selected?. URL: https://www.uber.com/in/en/newsroom/uber-driver-advisory-council/. Document date: 2022-03-24 (dateline on page). Retrieved: 2026-09-13. Source ID: S22.*

##### uberSAMAAJ driver focus group discussions

- **chunk_id**: `L5-5.1-003`
- **source_id**: S26
- **source_type**: `company_blog`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L5
- **threshold**: 5.1
- **criteria**: `4.1.a` (ASSERTED), `5.1.a` (ASSERTED)
- **policy_surfaces**: `worker_voice_mechanism`, `focus_groups`
- **section**: Section heading: What is your response to drivers protesting?

Verbatim text:

> Drivers’ individual concerns vary tremendously. We care deeply about their concerns and we can and will do better in our communications to reduce confusion. Last year we established uberSAMAAJ, our regular driver focus group discussions, which I personally oversee, where no topics are off limits. Activities are already taking place across five cities and we are rolling this out across more cities.
>
> This year everyone on my team, including myself, has committed to personally responding and resolving driver queries and will be accountable for meeting targets on engagement and resolution.

*Citation: Uber Blog India (Amit Jain, President of Uber India). Driving with Uber: Setting the record straight. Jurisdiction stated or inferred: India. Section heading: What is your response to drivers protesting?. URL: https://www.uber.com/in/en/blog/drivingwithuber/. Document date: 2017-03-03 (dateline on page). Retrieved: 2026-09-13. Source ID: S26.*

##### Uber India statement on driver protest and on individuals preventing drivers from working

- **chunk_id**: `L5-5.1-004`
- **source_id**: S26
- **source_type**: `company_blog`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L5
- **threshold**: 5.1
- **criteria**: `5.1.c` (PARTIAL)
- **policy_surfaces**: `collective_action`, `company_position`
- **section**: Section heading: What is your response to drivers protesting?

Verbatim text:

> Firstly, I want to say on behalf of the team at Uber in India, we are sorry for the disruption that both riders and drivers who rely on Uber have experienced over the last few weeks. It has been a difficult time, and we are grateful for the strong support we’ve received from riders and drivers across the country, and to the courts and law enforcement in condemning the use of violence and intimidation.
>
> Small numbers of individuals, who do not represent the majority of the driver community, have been preventing drivers who want to work from doing so. We have been communicating daily to drivers – through phone support, text and video messages and in person at our greenlight centres, where every day thousands of drivers walk in to resolve their concerns.

*Citation: Uber Blog India (Amit Jain, President of Uber India). Driving with Uber: Setting the record straight. Jurisdiction stated or inferred: India. Section heading: What is your response to drivers protesting?. URL: https://www.uber.com/in/en/blog/drivingwithuber/. Document date: 2017-03-03 (dateline on page). Retrieved: 2026-09-13. Source ID: S26.*

##### Disparagement of Uber as a contractual ground for deactivation

- **chunk_id**: `L5-5.1-005`
- **source_id**: S32
- **source_type**: `company_contract_driver_facing`
- **jurisdiction**: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories.
- **audience**: `driver`
- **levers**: L5
- **threshold**: 5.1
- **criteria**: `4.1.d` (CONTRADICTS), `5.1.c` (CONTRADICTS)
- **policy_surfaces**: `disparagement`, `worker_voice_limits`, `deactivation_grounds`
- **section**: Section 2.5
- **note**: Filed under this threshold because it is the clause in the driver contract that bears on what a driver may say about Uber. The clause is reproduced without interpretation.

Verbatim text:

> Uber retains the right, at any time in Uber's sole discretion, to deactivate or otherwise restrict you and/or your Drivers from accessing or using the Driver App or the Uber Service in the event of a violation of this Agreement or any other applicable relevant Uber policy, including the Community Guidelines (to the extent applicable); or your or your Drivers' disparagement of Uber or any of its Affiliates; or your or your Drivers' act or omission that causes harm to Uber’s or its Affiliates’ brand, reputation or business as determined by Uber in its sole discretion.

*Citation: Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction stated or inferred: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Section 2.5. URL: https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved: 2026-09-13. Source ID: S32.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_3_1_05** — bears on `5.1.c`: No official Uber document located for India states that contractual or policy provisions will not prevent workers from reporting health and safety concerns, seeking support, or organising collectively, or that workers are not required to waive legal recourse. The Services Agreement contains a consumer-status waiver (S32, Section 2.6), a one-year claim forfeiture window and a liability cap (S32, Section 11), and a confidentiality clause covering Uber Data and non-public operational information (S32, Section 6). None of these carries a carve-out for health and safety reporting or collective organising.  *(Re-filed from 3.1.)*
- **absence_4_2_02** — bears on `5.1.a`: No official Uber document located for India states that drivers are consulted on the setting or review of task rates, productivity targets or performance metrics. The Driver Advisory Council material (S21, S22) describes a discussion forum whose agenda includes earnings, but does not state that rate-setting or metric-setting is subject to consultation.  *(Re-filed from 4.2.)*
- **absence_5_1_01** — bears on `5.1.b`: No official Uber document located for India contains a formal, written statement of willingness to recognise, or to bargain with, an independent collective body of workers or a trade union. The published India driver Services Agreement (S32) contains no clause on freedom of association, collective representation or collective bargaining.
- **absence_5_1_02** — bears on `5.1.c`: No official Uber document located for India states that drivers will not be disadvantaged for communicating concerns to management or for forming or joining independent collective bodies of representation. The Services Agreement instead names disparagement of Uber and harm to Uber’s brand, reputation or business as grounds for deactivation at Uber’s sole discretion (S32, Section 2.5), with no carve-out for collective expression or for raising concerns.
- **absence_5_1_03** — bears on `5.1.a`: The Driver Advisory Council as Uber describes it is a company-convened consultative forum with a company-appointed third-party moderator, whose members are selected through a process that filters on platform activity and safety record (S22). Uber does not describe it as an independent worker body, and does not state that it has a bargaining function.
- **absence_5_2_03** — bears on `5.1.b`: No official Uber document located for India states that new drivers are informed of the existence of collective representative bodies. The Services Agreement, which is the document a new driver accepts, does not mention any such body (S32).  *(Re-filed from 5.2.)*

### 8.2 Threshold 5.2 — Supports democratic governance

- **threshold_id**: 5.2
- **lever**: L5
- **criteria**: `5.2.a`, `5.2.b`
- **extract_count**: 1
- **audience_driver**: 1
- **audience_mixed**: 0
- **absence_count**: 3

*Fairwork Location-based Platform Work Principles, threshold text reproduced verbatim for
orientation only. Not an Uber document.*

> While rates of organisation remain low, platform workers' associations are emerging in
> many sectors and countries. We are also seeing a growing number of cooperative
> worker-owned platforms. To realise fair representation, workers must have a say in the
> conditions of their work. This could be through a democratically governed cooperative
> model, a formally recognised union, or the ability to undertake collective bargaining
> with the platform.
>
> The platform must satisfy at least ONE of the following:

- **[5.2.a]** Workers play a meaningful role in governing it.
- **[5.2.b]** In a written document available at all times on the platform interface, the platform publicly and formally recognises an independent collective body of workers, an elected works council, or trade union. This recognition is not exclusive and, when the legal framework allows, the platform should recognise any significant collective body seeking representation.[17]

> **INLINED FOOTNOTE [17]**
> If workers choose to seek representation from an independent collective body of workers or union that is not
> readily recognized by the platform, the platform should then be open to adopt multiple channels of representation,
> when the legal framework allows, or seek ways to implement workers' queries to its communication with the
> existing representative body.

*(Note: footnotes [16] and [17] are identical in the published source. Both are reproduced as published.)*

#### Extracts from official Uber documentation

##### Continuation, scope and stated results of the Driver Advisory Council

- **chunk_id**: `L5-5.2-001`
- **source_id**: S21
- **source_type**: `company_newsroom`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L5
- **threshold**: 5.2
- **criteria**: `5.1.a` (PARTIAL), `5.2.a` (PARTIAL)
- **policy_surfaces**: `consultative_body`, `worker_voice_mechanism`, `third_party_oversight`
- **section**: Article body

Verbatim text:

> Drivers are at the heart of what we do at Uber, and we are determined to be the platform of choice for them. To make sure we are listening to them, we launched India’s first Driver Advisory Council (DAC) along with Aapti Institute last year. We marked the first year milestone of the Council by sharing what we learnt and announcing the second edition of the Council.
>
> The Council provides gig workers a space to discuss issues that impact them. It comprises drivers from 6 cities across cars, auto-rickshaws and motorbikes who represent the interests of tens of thousands of driver partners using the Uber platform. Last year, the Council comprised 58 driver partners who were part of 3 in-person sessions and two online sessions, convened by Aapti between March 2022 and March 2023. Topics discussed included earnings, product enhancements, social security, app experience and safety.
>
> Aapti Institute unveiled an impact report on the learnings from the Council meetings in its inaugural year. The report highlights changes introduced by Uber as per the recommendations from the Independent Review Board (IRB) led by Aapti Institute:
>
> Driver partners on Council nominate themselves after meeting certain eligibility requirements. Finally, through meetings with the IRB, the driver partners are tested on their potential to contribute to solutions to prevailing challenges. After the selected drivers have been part of the Council for a year, the selection process is repeated.
>
> The Driver Advisory Council is a global best practice for Uber with similar models in the US, UK, Australia and New Zealand. Uber continues to stay committed to supporting the rights of gig workers using the Uber platform.

*Citation: Uber Newsroom India (IndiaSA Comms Team). Uber announces 2nd edition of Driver Advisory Council. Jurisdiction stated or inferred: India. Article body. URL: https://www.uber.com/in/en/newsroom/uber-second-edition-driver-advisory-council/. Document date: 2023-04-17 (dateline on page). Retrieved: 2026-09-13. Source ID: S21.*

#### Recorded absences

The following matters are addressed by this threshold and are not addressed in any
official Uber document located for India. Nothing has been supplied in their place.

- **absence_5_2_01** — bears on `5.2.a`: No official Uber document located for India describes a democratically governed cooperative model or equivalent structure giving drivers a role in governing the company. Uber does not explicitly mention worker governance.
- **absence_5_2_02** — bears on `5.2.b`: No official Uber document located for India states that Uber formally recognises or engages with an independent collective body of workers, an elected works council, or a trade union in India, nor that it has not refused to engage with bodies seeking recognition. Uber does not explicitly mention any such body in India.
- **absence_5_2_04** — bears on `5.2.b`: No official Uber document located for India describes a formal process of dialogue with local or international representative bodies of workers about what structures of representation could look like. The Driver Advisory Council material (S21, S22) describes dialogue with individually selected drivers convened by Uber and moderated by Aapti Institute, not with representative bodies of workers.

## 9. Appendix A — Coverage table

| Threshold | Lever | Name | Criteria | Extracts | Driver | Mixed | Absences |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1.1 | L1 | Ensures workers earn at least the local minimum wage after costs | 2 | 33 | 30 | 3 | 0 |
| 1.2 | L1 | Ensures workers earn at least a local living wage after costs | 1 | 0 | 0 | 0 | 5 |
| 2.1 | L2 | Mitigates task specific risk | 3 | 13 | 13 | 0 | 3 |
| 2.2 | L2 | Ensures safe working conditions and a safety net | 3 | 9 | 9 | 0 | 5 |
| 3.1 | L3 | Provides clear and transparent terms and conditions | 6 | 20 | 20 | 0 | 6 |
| 3.2 | L3 | Ensures that no unfair contract terms are imposed | 4 | 22 | 21 | 1 | 4 |
| 4.1 | L4 | Provides due process for decisions affecting workers | 4 | 12 | 12 | 0 | 4 |
| 4.2 | L4 | Provides equity in the management process | 5 | 6 | 2 | 4 | 2 |
| 5.1 | L5 | Assures freedom of association and the expression of worker voice | 3 | 5 | 5 | 0 | 6 |
| 5.2 | L5 | Supports democratic governance | 2 | 1 | 1 | 0 | 3 |
| **Total** |  |  | **33** | **121** | **113** | **8** | **38** |

Five extracts and four recorded absences match no location-based criterion and are held in
Appendix D. 121 of the 126 extracts are cited as evidence in the codebook.

## 10. Appendix B — Material sought and not found

- A published driver Services Agreement for Uber Moto, Uber Auto, Uber Intercity, Uber Hire or courier work in India. The published Agreement (S32) names only Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green as its applicable categories. For the remaining categories Uber states the agreement is available to a signed-in driver at drivers.uber.com/profile under Contracts (S28).
- The Pass Terms governing the Drive Pass subscription. The Services Agreement incorporates them by hyperlink (S32, Section 4.1) but they are a separate document and were not compiled here.
- The price of a Drive Pass in any Indian city, and its duration options. The Services Agreement states these are specified in the Driver App at the time of selection (S32, Section 4.1).
- A driver rate card or fare table for any Indian city published by Uber on a current page. Uber directs drivers to the driver addendum inside the signed-in dashboard instead.
- The numerical service fee percentage applied in India. Uber describes the service fee and states where its percentage can be read, but does not publish the figure on an open page.
- The numerical minimum average star rating applied in any Indian city.
- The numerical acceptance-rate and cancellation-rate thresholds used as Uber Pro Program Standards in Indian cities. Uber defers these to the Uber Driver app.
- An India-specific published statement of the driving-hours limit. Only the global Uber Help article was found.
- An India-specific Trip Radar help article. Only a version referencing the GMB union and speeds in mph was found.
- An India-specific driver privacy notice, or an India data controller or grievance officer named in the driver privacy notice.
- Any Uber-published India document addressing trade union recognition, collective bargaining, paid leave, severance, or working-time entitlements for driver partners. The published driver Services Agreement (S32) contains no clause on any of these.
- Any Uber-published India document reconciling the subscription and Suggested Fare model in the Services Agreement (S32) with the Service Fee and Uber-calculated fare model described on the Uber Help and India driver product pages (S09, S11, S12).
- Any Uber-published India document stating an appeal or review right inside the driver contract itself. The review commitments appear only on the Deactivations product page (S02); the Services Agreement (S32) has no appeal clause.

## 11. Appendix C — Material removed as rider-only

Passages extracted from India sources and then removed because they govern only the
rider's own transaction with Uber and do not operate on the driver partner.

- **removed `L1-1.1-019`**: Rider-side explanation of how Uber estimates a rider's upfront price. It describes what the rider is quoted, not what the driver is paid, and the driver-side pricing account is already carried by S09, S11 and S32 Section 4.3. Nothing in it operates on the driver.
- **removed `L3-3.1-002`**: Clause 1 of the rider Terms of Use. Those Terms state at clause 2 that the Services are made available solely for personal, noncommercial use, which places driver partners outside their scope. The contracting entity, the amendment mechanism and the supersession rule for drivers are now carried by the driver Services Agreement itself at S32.
- **removed `L3-3.1-003`**: Clause 2 of the rider Terms of Use. The equivalent statement binding on drivers is in the driver Services Agreement preamble and Section 13 at S32.
- **removed `L3-3.1-026`**: Sections 6.1 and 6.2 of the Mumbai auto rider addendum. These govern Uber's right to change the rider terms and the scope of the rider addendum. They bind riders and do not operate on the driver partner.

Sources retired with those passages, because no surviving extract relies on them:

- **retired `S07`**: Rider Terms of Use for India. Retained in earlier drafts only because the driver contract was not then available. Superseded for this purpose by S32.
- **retired `S29`**: Rider-facing upfront pricing page for India.

Rider-facing or all-user documents kept because they operate on the driver:

- **kept `L1-1.1-031`**: Rider-facing addendum. It states the fare mechanism the Mumbai auto driver partner operates under, including that the Suggested Fare does not bind the driver, that rider and driver negotiate the fare, and that the rider pays the driver directly.
- **kept `L1-1.1-032`**: Rider-facing addendum. It operates on the driver because these are the non-trip amounts the driver collects from the rider and remits to Uber under S32 Section 4.3.3.
- **kept `L1-1.1-033`**: Rider-facing addendum. It allocates the risk of an incomplete ride, stating that what the rider has paid the driver is not refundable, and that fare and service disputes are settled between rider and driver with Uber outside them.
- **kept `L3-3.1-027`**: Rider-facing addendum. It states Uber's position on the driver partner's independence and on Uber's non-responsibility for a driver's cancellation or refusal of a trip.
- **kept `L4-4.1-015`**: The Non-Discrimination Policy is addressed to all users of the platform. It operates on the driver directly: it defines conduct for which a driver loses platform access, and it is the instrument that carves out a driver declining a trip from what counts as geographical discrimination.
- **kept `L4-4.1-016`**: The Zero Tolerance Policy is written to riders and tells them how to report a driver. It operates on the driver directly: it is the policy under which a report of alcohol or drug use is raised, and Uber states at S01 that a driver found under the influence is permanently deactivated.
- **kept `L4-4.1-017`**: General sections of the Community Guidelines addressed to riders and drivers together. They set the conduct standard a driver is held to and the two-way rating and reporting mechanism a driver is measured by.
- **kept `L4-4.1-018`**: Rider-side grounds for losing access, from the Community Guidelines. Kept because it is the enforcement the driver is on the receiving end of: it defines the rider conduct Uber states it will act on, including conduct directed at drivers, and it sets rider ratings and rider discrimination against drivers as grounds for rider deactivation.

## 12. Appendix D — Extracts and absences recorded as out of frame

These match no criterion under the Fairwork Location-based Platform Work Principles. They are
recorded rather than forced into a rule they do not fit, and they are not evidence of compliance
or of its absence. Each keeps its identifier and its citation.

### Extracts

The five below describe the substantive grounds on which Uber may deactivate a driver. The
location-based standard makes due process a criterion at 4.1 but does not make the grounds
themselves one.

| Extract | Source | Subject |
| --- | --- | --- |
| `L4-4.1-006` | S02 | Grounds of deactivation, background checks |
| `L4-4.1-007` | S02 | Grounds of deactivation, safety issues |
| `L4-4.1-008` | S02 | Grounds of deactivation, fraudulent activities |
| `L4-4.1-012` | S01 | Safety, drugs and alcohol, and legal compliance as grounds for deactivation in India |
| `L4-4.1-013` | S01 | Fraud and accurate personal information as grounds for deactivation in India |

The full entries follow, carrying `threshold: OUT_OF_FRAME`.

##### Grounds of deactivation, background checks

- **chunk_id**: `L4-4.1-006`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: OUT_OF_FRAME
- **criteria**: none — no location-based criterion addresses this passage
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `background_check`, `deactivation_grounds`
- **section**: Section heading: Background checks

Verbatim text:

> All drivers must agree to regular background screenings, which include evaluating their motor vehicle records and criminal history. The exact eligibility criteria depend on where they take trips and are largely based on the laws that apply in their city or state. Here are some general reasons for losing access based on background checks:
>
> Recent serious criminal offenses—including sexual assault, sex crimes against children, murder/homicide, terrorism, human trafficking, and kidnapping
>
> Any serious criminal charges that are still pending
>
> Multiple traffic violations or accidents in the last 3 years
>
> Driving with a suspended license within the last 3 years
>
> Any recent serious driving violation, such as drunk driving,, reckless driving, or hit-and-run
>
> Depending on local applicable regulations, laws, and practices, background checks may include a driver’s entire adult history, beginning at the age of 18.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Background checks. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Grounds of deactivation, safety issues

- **chunk_id**: `L4-4.1-007`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: OUT_OF_FRAME
- **criteria**: none — no location-based criterion addresses this passage
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `deactivation_grounds`, `identity_verification`, `temporary_suspension`
- **section**: Section heading: Safety issues

Verbatim text:

> Uber uses Real-Time ID Check to ensure that the person driving matches the identity of the person who has passed our screening checks. The real-time photo must match their profile photo. Drivers are not permitted to share their account with or delegate it to anyone else to ensure the safety of riders.
>
> This includes reports that the driver has had a crash or traffic citation during a trip, or repeated reports of poor, unsafe, or distracted driving while using the Driver app.
>
> This includes reports of driving while drowsy or while under the influence of alcohol, illegal drugs, or over-the-counter or prescription drugs that should not be used while operating a motor vehicle. It also includes reports of having drugs and/or open containers of alcohol in the car. Smells of alcohol or drugs—even if left by riders—can be interpreted as impairment, and Uber can be required by law to temporarily place an account on hold while we investigate.
>
> Exhibiting aggressive, confrontational, or harassing behavior. This includes:
>
> Using language, making gestures, or taking actions that could be disrespectful, threatening, or inappropriate
>
> Sharing graphic images that are sexually explicit or depict physical violence with others in the Uber community, including unsolicited sharing of such images through Uber’s online support systems or in connection with an Uber platform experience
>
> Any kind of sexual harassment, which includes sexual assault and sexual misconduct by anyone—including drivers, riders and third parties—is not allowed while using Uber, and may also be illegal. Sexual assault is physical or attempted physical conduct that is sexual and done without consent, such as touching, kissing, or sex. Sexual misconduct includes nonphysical behavior that is sexual or romantic and done without consent, or has the effect of threatening or intimidating someone. Uber’s no-sex rule prohibits sexual contact regardless of whether the driver or delivery person knows the other person or receives their consent.
>
> If you are driving a vehicle from an account that does not belong to you, or you allow anyone else to drive from your profile, you might lose access to your account. This is done from a safety point of view. Riders can complain against such incidents and it might lead to losing account access.
>
> Only vehicles or other modes of transportation associated with a driver’s profile, and that meet their city’s minimum requirements, are acceptable.

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Safety issues. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Grounds of deactivation, fraudulent activities

- **chunk_id**: `L4-4.1-008`
- **source_id**: S02
- **source_type**: `company_policy_product_page`
- **jurisdiction**: India (India driver site)
- **audience**: `driver`
- **levers**: L4
- **threshold**: OUT_OF_FRAME
- **criteria**: none — no location-based criterion addresses this passage
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `fraud_detection`, `automated_detection`, `deactivation_grounds`
- **section**: Section heading: Fraudulent activities

Verbatim text:

> In order for our platform to operate as properly and safely as possible, we rely on everyone who uses the Uber platform to comply with our terms and refrain from fraudulent activities. We’re always working to prevent and detect fraud that affects everyone who uses Uber.
>
> Uber relies on automated and manual systems, including reviews by fraud specialists, to detect fraudulent activity that violates our terms and conditions. In some cases, such activity may result in deactivation of a user’s account.
>
> Fraudulent activities that may result in account deactivation include but are not limited to:
>
> Deliberately increasing the time or distance of a trip
>
> Accepting trip requests without the intention to complete them, including causing users to cancel
>
> Creating fake, duplicate, or otherwise improper accounts
>
> Claiming unwarranted fees or charges, like asking for parking fees from customers when they are included in the fare
>
> Intentionally requesting, accepting, or completing fraudulent or falsified trips
>
> Claiming to complete a delivery without ever picking up the delivery item
>
> Picking up a delivery item but retaining all or a portion of the item, and not delivering the entire order
>
> Disrupting or manipulating the normal functioning of the Uber platform, including the use of unauthorized or manipulated devices, apps, or programs to prevent or circumvent the proper functioning of the platform and the GPS system
>
> Abusing any program, such as promotions or referrals, or not using them for their intended purpose
>
> Disputing charges for fraudulent or illegitimate reasons
>
> Falsifying documentation
>
> This includes a driver falsifying information, assuming someone else’s identity, sharing an account with someone else, submitting personal documents that don’t belong to them, or attempting to bypass identity verification checks.
>
> Fraudulent financial activity includes, but is not limited to, improperly increasing the time or distance of a trip on purpose or abusing fees and promotions.
>
> Cooperating with riders who call before a trip and ask the driver to do things that are against Uber’s Community Guidelines like cancelling a trip on the app and doing it offline (paying drivers in cash)

*Citation: Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction stated or inferred: India (India driver site). Section heading: Fraudulent activities. URL: https://www.uber.com/in/en/drive/driver-app/deactivation-review/. Document date: Not stated on page. Retrieved: 2026-09-13. Source ID: S02.*

##### Safety, drugs and alcohol, and legal compliance as grounds for deactivation in India

- **chunk_id**: `L4-4.1-012`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: OUT_OF_FRAME
- **criteria**: none — no location-based criterion addresses this passage
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `deactivation_grounds`, `immediate_deactivation`, `zero_tolerance`
- **section**: Section headings: Safety; Zero Tolerance for Drugs and Alcohol; Compliance with the Law; Background Checks

Verbatim text:

> Actions that threaten the safety of drivers and riders will be investigated and, if confirmed, lead to permanent deactivation of your account.
>
> What leads to you losing access to your account? If we are made aware of these kinds of problematic behavior, we will contact you so we can investigate them. Depending on the nature of the concern, we may put a hold on your account during our investigation. If the issues raised are serious or a repeat offense, or you refuse to cooperate, you may lose access to Uber. Any behavior involving violence, sexual misconduct, harassment, discrimination, or illegal activity while using Uber can result in the immediate loss of your account. Uber will also deactivate the account of any driver who receives several or serious complaints of poor, unsafe, or distracted driving while using the Uber app. Additionally, when law enforcement is involved, we will cooperate with their investigation in accordance with our Law Enforcement Guidelines.
>
> Uber does not tolerate the use of drugs or alcohol by partners while driving.
>
> What leads to you losing access to your account? The account of any driver found to be under the influence of drugs or alcohol while using the Uber app will be permanently deactivated. Uber may also deactivate the account of any driver who receives several unconfirmed complaints of drug or alcohol use.
>
> We expect drivers using the Uber app to act in compliance with all relevant central, state, and local laws and the rules of the road at all times. This includes meeting the regulatory requirements for drivers and vehicles in your area.
>
> What leads to you losing access to your account? Uber may permanently deactivate your account for activities such as: engaging in serious illegal activity while using the Uber app; not maintaining valid vehicle registration or driver’s license; and receiving serious traffic citations, or several traffic citations that indicate unsafe driving, while using the Uber app.
>
> All drivers wanting to use the Uber app are required to undergo a screening process, like motor vehicle record and background checks, to ensure safety and compliance with our criteria.
>
> What leads to you losing access to your account? We will permanently deactivate a driver’s account if a routine motor vehicle record or background check uncovers a violation of Uber’s safety standards or of other criteria required by local regulators.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section headings: Safety; Zero Tolerance for Drugs and Alcohol; Compliance with the Law; Background Checks. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

##### Fraud and accurate personal information as grounds for deactivation in India

- **chunk_id**: `L4-4.1-013`
- **source_id**: S01
- **source_type**: `company_policy_legal_hub`
- **jurisdiction**: India
- **audience**: `driver`
- **levers**: L4
- **threshold**: OUT_OF_FRAME
- **criteria**: none — no location-based criterion addresses this passage
- **refiled_from**: 4.1 (Fairwork AI Principles filing in corpus v2026.09)
- **policy_surfaces**: `fraud_detection`, `deactivation_grounds`, `document_validity`
- **section**: Section headings: Fraud; Accurate Personal Information

Verbatim text:

> Fraudulent activity undermines the trust on which Uber is built. That’s why we are constantly on the lookout for fraud by riders and drivers who are gaming our systems.
>
> What leads to you losing access to your account? We will deactivate any account or accounts associated with fraudulent activity, which may include: deliberately increasing the time or distance of a trip; accepting trips without the intention to complete, including provoking riders to cancel; creating dummy rider or driver accounts for fraudulent purposes; claiming fraudulent fees or charges, like false cleaning fees; and intentionally accepting or completing fraudulent or falsified trips.
>
> What leads to you losing access to your account? We will deactivate your account for activities such as: providing Uber with inaccurate information; allowing someone else to use your account; and taking a trip using an unapproved vehicle.
>
> In addition, we will take action to prevent any driver whose required documentation becomes invalid — like a driver’s license that expires — from going online until the driver provides Uber with updated information.

*Citation: Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction stated or inferred: India. Section headings: Fraud; Accurate Personal Information. URL: https://www.uber.com/in/en/legal/general-community-guidelines/. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved: 2026-09-13. Source ID: S01.*

### Absences

Recorded in corpus v2026.09 against Fairwork AI Principles thresholds whose subject the
location-based standard does not carry.

- **absence_3_1_06** — No official Uber document located for India states that clients or Uber provide drivers with information about the purpose or expected outputs of work beyond the per-trip information described in S11 and S32 Section 2.2. *(Recorded in v2026.09 under 3.1. Information about the purpose or expected outputs of work is a Fairwork AI Principles contract-content matter. No location-based criterion addresses it.)*

- **absence_3_2_01** — No official Uber document located for India offers a route from repeated engagement to a permanent contract. The Services Agreement states the relationship “is not an employment agreement, nor does it create an employment relationship” (S32, Section 13.1). Uber does not explicitly mention contract conversion. *(Recorded in v2026.09 under 3.2. A route from repeated engagement to a permanent contract is contract continuity. The location-based standard has no criterion on continuity of engagement.)*

- **absence_3_2_02** — No official Uber document located for India provides severance, redundancy compensation, or retraining on termination of access. The Effect of Termination clause (S32, Section 12.3) addresses only deletion of the Driver App, outstanding payment obligations and survival of clauses. Uber does not explicitly mention severance or redundancy provisions for driver partners. *(Recorded in v2026.09 under 3.2. Severance, redundancy and retraining on termination are contract continuity. No location-based criterion addresses them.)*

- **absence_3_2_03** — No official Uber document located for India provides for consultation with drivers or their representatives where access is withdrawn, or for a driver to bring a representative to an end-of-engagement discussion. Uber does not explicitly mention either. *(Recorded in v2026.09 under 3.2. Consultation or representation at the point access is withdrawn is contract continuity. Location-based 4.1 covers appeal against the decision, not consultation before it.)*

Recording them is not neutral housekeeping. Contract continuity, severance and the route from
repeated engagement to a permanent contract are real features of Uber's published position.
They are outside what this standard scores, and a later study that wants to test them starts here.

## 13. Appendix E — Full reference list

These are web-published documents and Uber does not paginate them, so the locator is the
section, clause or heading within the document rather than a page number. All sources
were retrieved on 2026-09-13.

### R01. S01 — Uber Community Guidelines

Uber India Systems Private Limited. Uber Community Guidelines. Jurisdiction: India. Document date: 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/legal/general-community-guidelines/>

- **levers_supplied**: L2 / 2.1; L3 / 3.1; L4 / 4.1
- **extract_count**: 9

Sections cited from this source:

- `L2-2.1-002` | threshold 2.1 | audience `driver` | Section heading: Safety first
- `L3-3.1-008` | threshold 2.2 | audience `driver` | Section heading: WHY DRIVERS CAN LOSE ACCESS TO UBER, sub-heading Acceptance Rates
- `L3-3.1-011` | threshold 4.1 | audience `driver` | Section heading: Unacceptable Activities
- `L4-4.1-011` | threshold 3.2 | audience `driver` | Section heading: WHY DRIVERS CAN LOSE ACCESS TO UBER, sub-heading Quality
- `L4-4.1-012` | threshold OUT_OF_FRAME | audience `driver` | Section headings: Safety; Zero Tolerance for Drugs and Alcohol; Compliance with the Law; Background Checks
- `L4-4.1-013` | threshold OUT_OF_FRAME | audience `driver` | Section headings: Fraud; Accurate Personal Information
- `L4-4.1-014` | threshold 4.2 | audience `driver` | Section heading: Discrimination (drivers)
- `L4-4.1-017` | threshold 4.2 | audience `mixed` | Section headings: Respect each other; Give riders and drivers some personal space; Feedback makes us all better
- `L4-4.1-018` | threshold 4.2 | audience `mixed` | Section heading: WHY RIDERS CAN LOSE ACCESS TO UBER

### R02. S02 — Deactivations: Losing Account Access

Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Jurisdiction: India (India driver site). Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/driver-app/deactivation-review/>

- **levers_supplied**: L2 / 2.1; L3 / 3.1; L3 / 3.2; L4 / 4.1
- **extract_count**: 12

Sections cited from this source:

- `L2-2.1-006` | threshold 2.1 | audience `driver` | Section heading: Safety issues, sub-heading Unsafe vehicles
- `L3-3.1-010` | threshold 1.1 | audience `driver` | Footer note headed Policy violations
- `L3-3.2-001` | threshold 3.2 | audience `driver` | Section heading: Our commitment to drivers
- `L4-4.1-001` | threshold 4.1 | audience `driver` | Section heading: Our commitment to drivers
- `L4-4.1-002` | threshold 4.1 | audience `driver` | Section heading: Our account review process
- `L4-4.1-003` | threshold 4.1 | audience `driver` | Section heading: Why losing access happens and what to do
- `L4-4.1-004` | threshold 4.1 | audience `driver` | Section heading: Frequently asked questions
- `L4-4.1-006` | threshold OUT_OF_FRAME | audience `driver` | Section heading: Background checks
- `L4-4.1-007` | threshold OUT_OF_FRAME | audience `driver` | Section heading: Safety issues
- `L4-4.1-008` | threshold OUT_OF_FRAME | audience `driver` | Section heading: Fraudulent activities
- `L4-4.1-009` | threshold 4.2 | audience `driver` | Section heading: Discrimination or refusing service
- `L4-4.1-010` | threshold 4.1 | audience `driver` | Section heading: Ratings

### R03. S03 — Uber Pro Terms and Conditions

Uber India Systems Private Limited. Uber Pro Terms and Conditions. Jurisdiction: India. Document date: 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/legal/uber-pro-program-terms/>

- **levers_supplied**: L1 / 1.1; L2 / 2.2; L3 / 3.1; L4 / 4.2
- **extract_count**: 7

Sections cited from this source:

- `L1-1.1-016` | threshold 1.1 | audience `driver` | Section heading: Pro Perk - Additional Earnings
- `L2-2.2-001` | threshold 2.2 | audience `driver` | Section heading: Insurance & Wellness
- `L2-2.2-002` | threshold 2.2 | audience `driver` | Section heading: Micro Credit Access
- `L3-3.1-004` | threshold 3.1 | audience `driver` | Opening recitals
- `L3-3.1-005` | threshold 3.2 | audience `driver` | Section headings: PROGRAM CHANGES AND PROGRAM TERMINATION; TRANSFER OF RIGHTS; INTERPRETATION OF PROGRAM TERMS; ACCOUNT TERMINATION
- `L4-4.2-009` | threshold 3.2 | audience `driver` | Section headings: Priority Rides; Airport Advantage; Priority Queue Access; Area Preferences
- `L4-4.2-010` | threshold 2.2 | audience `driver` | Section headings: PROGRAM TIERS AND PROGRAM STANDARDS; MAINTAINING YOUR TIER & PROGRAM STANDARDS; HOW TO VIEW POINTS BALANCES

### R04. S04 — Uber Non-Discrimination Policy

Uber Technologies Inc. Uber Non-Discrimination Policy. Jurisdiction: India. Document date: 2024-07-23 (page states: Last modified: 7/23/2024). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/legal/non-discrimination-policy/>

- **levers_supplied**: L4 / 4.1
- **extract_count**: 1

Sections cited from this source:

- `L4-4.1-015` | threshold 4.2 | audience `mixed` | Full text of the policy

### R05. S05 — Zero Tolerance Policy

Uber Technologies Inc. Zero Tolerance Policy. Jurisdiction: Global document listed on the India legal hub index. Document date: 2023-05-19 (page states: Last modified: 5/19/2023). Retrieved 2026-09-13. Available at: <https://www.uber.com/global/en/legal/zero-tolerance-policy/>

- **levers_supplied**: L4 / 4.1
- **extract_count**: 1

Sections cited from this source:

- `L4-4.1-016` | threshold 4.2 | audience `mixed` | Full text of the policy

### R06. S06 — How Uber Uses Communications Intelligence to Improve Your Experience

Uber Technologies Inc. How Uber Uses Communications Intelligence to Improve Your Experience. Jurisdiction: India. Document date: 2026-07-07 (page states: Last modified: 7/7/2026). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/legal/communication-intelligence/>

- **levers_supplied**: L4 / 4.2
- **extract_count**: 1

Sections cited from this source:

- `L4-4.2-007` | threshold 3.1 | audience `driver` | Full text of the notice

### R07. S08 — Uber Privacy Notice: Drivers and Delivery People

Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. Jurisdiction: Global. No India-specific carve-out appears in the text and no separate India driver privacy notice was located. Document date: 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved 2026-09-13. Available at: <https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/>

- **levers_supplied**: L1 / 1.1; L4 / 4.2
- **extract_count**: 7

Sections cited from this source:

- `L1-1.1-018` | threshold 1.1 | audience `driver` | Section II.C.2 Pricing
- `L4-4.2-001` | threshold 3.1 | audience `driver` | Section II.C Core automated processes, introduction
- `L4-4.2-002` | threshold 3.2 | audience `driver` | Section II.C.1 Matching
- `L4-4.2-003` | threshold 4.1 | audience `driver` | Section II.C.3 Safety, security, and fraud prevention and detection
- `L4-4.2-004` | threshold 3.2 | audience `driver` | Section II.B How we use data, safety and security uses
- `L4-4.2-005` | threshold 3.1 | audience `driver` | Section III. Choice and transparency
- `L4-4.2-006` | threshold 3.1 | audience `driver` | Section IV.A Data controllers and Data Protection Officer

### R08. S09 — How earnings are calculated for rides (Uber Help, Driving and Delivering)

Uber Technologies Inc. How earnings are calculated for rides (Uber Help, Driving and Delivering). Jurisdiction: Uber Help article served to India; uses per-kilometre terminology. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2>

- **levers_supplied**: L1 / 1.1
- **extract_count**: 5

Sections cited from this source:

- `L1-1.1-001` | threshold 1.1 | audience `driver` | Section heading: What drivers earn
- `L1-1.1-002` | threshold 1.1 | audience `driver` | Section heading: What riders pay
- `L1-1.1-003` | threshold 1.1 | audience `driver` | Section heading: Why riders pay more than driver earnings
- `L1-1.1-004` | threshold 1.1 | audience `driver` | Section headings: Viewing earnings statement breakdown; Finding trip receipts
- `L1-1.1-005` | threshold 1.1 | audience `driver` | Section heading: Rider promotions and discounts

### R09. S10 — Upfront fares (Uber Help, Driving and Delivering)

Uber Technologies Inc. Upfront fares (Uber Help, Driving and Delivering). Jurisdiction: Uber Help article. The product list inside it names US and global ride types, indicating a non-India-specific version. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://help.uber.com/driving-and-delivering/article/what-is-the-upfront-fare?nodeId=bc83ed7e-6725-41de-afcb-72d263e5589f>

- **levers_supplied**: L1 / 1.1
- **extract_count**: 1

Sections cited from this source:

- `L1-1.1-008` | threshold 1.1 | audience `driver` | Article body

### R10. S11 — Upfront Fares, explained (Tracking Your Earnings, Driver App basics)

Uber Technologies Inc. Upfront Fares, explained (Tracking Your Earnings, Driver App basics). Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/basics/tracking-your-earnings/>

- **levers_supplied**: L1 / 1.1
- **extract_count**: 2

Sections cited from this source:

- `L1-1.1-006` | threshold 1.1 | audience `driver` | Section heading: How are Upfront Fares calculated?
- `L1-1.1-007` | threshold 1.1 | audience `driver` | Section headings: What you’ll see upfront; Upfront Fares can be higher or lower than the pricing based on fixed time and distance rates. Why is this?; When changes happen

### R11. S12 — How much can drivers make with Uber?

Uber Technologies Inc. How much can drivers make with Uber?. Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/how-much-drivers-make/>

- **levers_supplied**: L1 / 1.1
- **extract_count**: 3

Sections cited from this source:

- `L1-1.1-009` | threshold 1.1 | audience `driver` | Section heading: How earnings are calculated
- `L1-1.1-010` | threshold 1.1 | audience `driver` | Section headings: Promotions and how they work; Getting tipped for your service; When and how you get paid
- `L1-1.1-011` | threshold 1.1 | audience `driver` | Page footnotes 1 and 2

### R12. S13 — How payments work (Driver App basics)

Uber Technologies Inc. How payments work (Driver App basics). Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/basics/how-payments-work/>

- **levers_supplied**: L1 / 1.1
- **extract_count**: 1

Sections cited from this source:

- `L1-1.1-012` | threshold 1.1 | audience `driver` | Section headings: How payments work; How to set up a bank transfer

### R13. S14 — How star ratings work (Driver App basics)

Uber Technologies Inc. How star ratings work (Driver App basics). Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/basics/how-ratings-work/>

- **levers_supplied**: L4 / 4.2
- **extract_count**: 1

Sections cited from this source:

- `L4-4.2-011` | threshold 4.1 | audience `driver` | Section headings: The basics of ratings; How to give, get, and check ratings

### R14. S15 — Drive with confidence (Driver Safety)

Uber Technologies Inc. Drive with confidence (Driver Safety). Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/safety/>

- **levers_supplied**: L2 / 2.1
- **extract_count**: 1

Sections cited from this source:

- `L2-2.1-004` | threshold 2.1 | audience `driver` | Section heading: Your safety drives us

### R15. S16 — Driver requirements

Uber Technologies Inc. Driver requirements. Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/requirements/>

- **levers_supplied**: L3 / 3.1
- **extract_count**: 1

Sections cited from this source:

- `L3-3.1-012` | threshold 3.1 | audience `driver` | Section heading: Three ways to earn

### R16. S17 — Contact Uber (Drivers: How to Get Help)

Uber Technologies Inc. Contact Uber (Drivers: How to Get Help). Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/drive/contact/>

- **levers_supplied**: L4 / 4.1
- **extract_count**: 1

Sections cited from this source:

- `L4-4.1-019` | threshold 4.1 | audience `driver` | Section heading: Get more information

### R17. S18 — Driving time limit (Uber Help, Driving and Delivering)

Uber Technologies Inc. Driving time limit (Uber Help, Driving and Delivering). Jurisdiction: Uber Help global English article. No India-specific version was located. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://help.uber.com/en/driving-and-delivering/article/driving-time-limit?nodeId=a50a72e1-d315-4154-ac66-b17bd5bd050a>

- **levers_supplied**: L2 / 2.1
- **extract_count**: 1

Sections cited from this source:

- `L2-2.1-001` | threshold 2.1 | audience `driver` | Article body

### R18. S19 — What is Trip Radar and how does it work? (Uber Help, Driving and Delivering)

Uber Technologies Inc. What is Trip Radar and how does it work? (Uber Help, Driving and Delivering). Jurisdiction: Uber Help article. The text references the GMB union and speeds in mph, indicating a UK-facing version. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://help.uber.com/driving-and-delivering/article/what-is-trip-radar-and-how-does-it-work?nodeId=b6fb7065-ce66-490c-a911-d4e6d5c10d29>

- **levers_supplied**: L3 / 3.1; L4 / 4.2
- **extract_count**: 2

Sections cited from this source:

- `L3-3.1-009` | threshold 3.2 | audience `driver` | Article body
- `L4-4.2-008` | threshold 3.2 | audience `driver` | Article body

### R19. S20 — Uber's New Features to Make Driving Safer, Easier, and Fairer

Uber Newsroom India (IndiaSA Comms). Uber's New Features to Make Driving Safer, Easier, and Fairer. Jurisdiction: India. Document date: 2024-11-15 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/newsroom/uber-features-to-make-driving-safer-easier-and-fairer/>

- **levers_supplied**: L1 / 1.1; L2 / 2.1; L2 / 2.2; L4 / 4.1
- **extract_count**: 4

Sections cited from this source:

- `L1-1.1-013` | threshold 1.1 | audience `driver` | Section headings: Easier Earnings and Flexibility; Transparent and Fair Processes
- `L2-2.1-005` | threshold 2.1 | audience `driver` | Section heading: Safer Driving Experience
- `L2-2.2-006` | threshold 2.2 | audience `driver` | Section heading: Supporting Social Security
- `L4-4.1-005` | threshold 4.1 | audience `driver` | Section heading: Transparent and Fair Processes

### R20. S21 — Uber announces 2nd edition of Driver Advisory Council

Uber Newsroom India (IndiaSA Comms Team). Uber announces 2nd edition of Driver Advisory Council. Jurisdiction: India. Document date: 2023-04-17 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/newsroom/uber-second-edition-driver-advisory-council/>

- **levers_supplied**: L1 / 1.1; L4 / 4.2; L5 / 5.2
- **extract_count**: 3

Sections cited from this source:

- `L1-1.1-014` | threshold 1.1 | audience `driver` | Section heading: Transparency in driver earnings
- `L4-4.2-012` | threshold 3.2 | audience `driver` | Section headings: Reduction in driver cancellations; Easier app-experience for driver partners
- `L5-5.2-001` | threshold 5.2 | audience `driver` | Article body

### R21. S22 — Moving Forward Together: Launching Driver Advisory Council

Uber Newsroom India (IndiaSA Comms Team). Moving Forward Together: Launching Driver Advisory Council. Jurisdiction: India. Document date: 2022-03-24 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/newsroom/uber-driver-advisory-council/>

- **levers_supplied**: L5 / 5.1
- **extract_count**: 2

Sections cited from this source:

- `L5-5.1-001` | threshold 5.1 | audience `driver` | Article body
- `L5-5.1-002` | threshold 5.1 | audience `driver` | Section heading: How were the Driver Advisory Council members selected?

### R22. S23 — Uber introduces Uber Care for its driver partner community in India

Uber Newsroom India (Shonali Chakravarty). Uber introduces Uber Care for its driver partner community in India. Jurisdiction: India. Document date: 2018-11-26 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/newsroom/ubercare/>

- **levers_supplied**: L2 / 2.2
- **extract_count**: 1

Sections cited from this source:

- `L2-2.2-003` | threshold 2.2 | audience `driver` | Article body

### R23. S24 — Uber commits INR 100 crores towards driver welfare initiatives

Uber Newsroom India (IndiaSA Comms Team). Uber commits INR 100 crores towards driver welfare initiatives. Jurisdiction: India. Document date: 2021-12-15 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/newsroom/uber-commits-inr-100-crores-towards-driver-welfare-initiatives/>

- **levers_supplied**: L2 / 2.2
- **extract_count**: 1

Sections cited from this source:

- `L2-2.2-005` | threshold 2.2 | audience `driver` | Article body

### R24. S25 — Uber puts Safety at the heart of Driver Experience

Uber Newsroom India (IndiaSA Comms Team). Uber puts Safety at the heart of Driver Experience. Jurisdiction: India. Document date: 2019-01-29 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/newsroom/uber-puts-safety-at-the-heart-of-driver-experience/>

- **levers_supplied**: L2 / 2.1
- **extract_count**: 1

Sections cited from this source:

- `L2-2.1-003` | threshold 2.1 | audience `driver` | Section heading: Driver Safety Toolkit

### R25. S26 — Driving with Uber: Setting the record straight

Uber Blog India (Amit Jain, President of Uber India). Driving with Uber: Setting the record straight. Jurisdiction: India. Document date: 2017-03-03 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/blog/drivingwithuber/>

- **levers_supplied**: L1 / 1.1; L5 / 5.1
- **extract_count**: 3

Sections cited from this source:

- `L1-1.1-015` | threshold 1.1 | audience `driver` | Section headings: How much does a driver make with Uber?; How do incentives work? Have incentives changed and why?; Are drivers earning more or less now?; Why do some drivers earn more or less than others?
- `L5-5.1-003` | threshold 5.1 | audience `driver` | Section heading: What is your response to drivers protesting?
- `L5-5.1-004` | threshold 5.1 | audience `driver` | Section heading: What is your response to drivers protesting?

### R26. S27 — Keeping driver partners at heart

Uber Newsroom India (Prabhjeet Singh). Keeping driver partners at heart. Jurisdiction: India. Document date: 2018-12-20 (dateline on page). Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/newsroom/keeping-driver-partners-at-heart/>

- **levers_supplied**: L2 / 2.2; L3 / 3.1
- **extract_count**: 2

Sections cited from this source:

- `L2-2.2-004` | threshold 2.1 | audience `driver` | Article body
- `L3-3.1-007` | threshold 3.1 | audience `driver` | Article body

### R27. S28 — Agreeing to terms and conditions (Uber Help, Driving and Delivering)

Uber Technologies Inc. Agreeing to terms and conditions (Uber Help, Driving and Delivering). Jurisdiction: Uber Help article served to India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://help.uber.com/en/driving-and-delivering/article/agreeing-to-terms-and-conditions?nodeId=44cf1f0e-27ca-4919-9621-f1321a0381c1>

- **levers_supplied**: L3 / 3.1
- **extract_count**: 1

Sections cited from this source:

- `L3-3.1-001` | threshold 3.1 | audience `driver` | Section headings: How to accept Uber’s Terms and Conditions; How to see terms you’ve agreed to

### R28. S30 — I have an inquiry about cancellation fee (Uber Help, Driving and Delivering)

Uber Technologies Inc. I have an inquiry about cancellation fee (Uber Help, Driving and Delivering). Jurisdiction: Uber Help article served to India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://help.uber.com/driving-and-delivering/article/request-cancellation-fee?nodeId=41fee0a6-8941-4418-bf25-3327db4f50aa>

- **levers_supplied**: L1 / 1.1
- **extract_count**: 1

Sections cited from this source:

- `L1-1.1-017` | threshold 1.1 | audience `driver` | Article body

### R29. S31 — Uber Legal Hub, India index (jurisdiction and language selector)

Uber Technologies Inc. Uber Legal Hub, India index (jurisdiction and language selector). Jurisdiction: India. Document date: Not stated on page. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/legal/?country=india&lang=en>

- **levers_supplied**: L3 / 3.1
- **extract_count**: 1

Sections cited from this source:

- `L3-3.1-006` | threshold 3.1 | audience `driver` | Language selector on the India legal hub

### R30. S32 — Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions)

Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). Jurisdiction: India. The agreement states its applicable categories as Uber Premier, Uber Go Priority, Uber Go, Uber Go Sedan, Request any and Uber Green. It does not state that it applies to Uber Moto, Uber Auto, Uber Intercity or other categories. Document date: 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/>

- **levers_supplied**: L1 / 1.1; L2 / 2.1; L2 / 2.2; L3 / 3.1; L3 / 3.2; L4 / 4.1; L4 / 4.2; L5 / 5.1
- **extract_count**: 45

Sections cited from this source:

- `L1-1.1-020` | threshold 1.1 | audience `driver` | Section 4.1 Drive Pass
- `L1-1.1-021` | threshold 1.1 | audience `driver` | Section 4.2 Fees
- `L1-1.1-022` | threshold 1.1 | audience `driver` | Sections 4.3.1 and 4.3.2 Fare Calculation and Payment; definition 1.10 Suggested Fare
- `L1-1.1-023` | threshold 1.1 | audience `driver` | Section 4.3.3
- `L1-1.1-024` | threshold 1.1 | audience `driver` | Section 4.3.4
- `L1-1.1-025` | threshold 1.1 | audience `driver` | Sections 4.3.5 and 4.3.6
- `L1-1.1-026` | threshold 1.1 | audience `driver` | Sections 4.3.7 and 4.3.8
- `L1-1.1-027` | threshold 1.1 | audience `driver` | Section 4.3.9
- `L1-1.1-028` | threshold 1.1 | audience `driver` | Section 4.4 Taxes
- `L1-1.1-029` | threshold 1.1 | audience `driver` | Section 2.2 Provision of Transportation Services
- `L1-1.1-030` | threshold 1.1 | audience `driver` | Section 2.8.3 Device
- `L2-2.1-007` | threshold 2.1 | audience `driver` | Section 3.1 Your/Driver Requirements
- `L2-2.1-008` | threshold 2.1 | audience `driver` | Section 3.2 Vehicle Requirements
- `L2-2.1-009` | threshold 2.1 | audience `driver` | Section 2.3 Your Relationship with Users
- `L2-2.1-010` | threshold 2.1 | audience `driver` | Section 9.2 Disclaimer of Warranties
- `L2-2.1-011` | threshold 2.1 | audience `driver` | Section 2.4 Your Relationship with Uber
- `L2-2.2-007` | threshold 2.2 | audience `driver` | Sections 8.1 and 8.2 Insurance
- `L2-2.2-008` | threshold 2.2 | audience `driver` | Section 8.3 Insurance
- `L2-2.2-009` | threshold 2.1 | audience `driver` | Section 8.4 Insurance
- `L3-3.1-013` | threshold 3.1 | audience `driver` | Preamble and scope statement
- `L3-3.1-014` | threshold 3.1 | audience `driver` | Closing acceptance statement
- `L3-3.1-015` | threshold 3.2 | audience `driver` | Section 2.4 Your Relationship with Uber
- `L3-3.1-016` | threshold 3.2 | audience `driver` | Section 2.5
- `L3-3.1-017` | threshold 3.1 | audience `driver` | Section 2.6
- `L3-3.1-018` | threshold 3.2 | audience `driver` | Section 2.7 Your Relationship with Drivers
- `L3-3.1-019` | threshold 3.1 | audience `driver` | Section 13 Relationship of the Parties
- `L3-3.1-020` | threshold 3.2 | audience `driver` | Sections 14.1 Modification and 14.2 Supplemental Terms and Addenda
- `L3-3.1-021` | threshold 3.2 | audience `driver` | Sections 14.4 Assignment and 14.5 Entire Agreement
- `L3-3.1-022` | threshold 3.1 | audience `driver` | Section 10 Indemnification
- `L3-3.1-023` | threshold 3.1 | audience `driver` | Section 11 Limits of Liability
- `L3-3.1-024` | threshold 3.2 | audience `driver` | Section 6 Confidentiality
- `L3-3.1-025` | threshold 3.1 | audience `driver` | Sections 14.7 Notices and 15 Governing Law; Arbitration
- `L3-3.2-002` | threshold 3.2 | audience `driver` | Section 12.1 Term
- `L3-3.2-003` | threshold 3.2 | audience `driver` | Section 12.2 Termination
- `L3-3.2-004` | threshold 3.2 | audience `driver` | Section 12.3 Effect of Termination
- `L3-3.2-005` | threshold 3.2 | audience `driver` | Section 2.5
- `L4-4.1-020` | threshold 4.1 | audience `driver` | Section 2.5
- `L4-4.1-021` | threshold 3.2 | audience `driver` | Section 3.3 Documentation
- `L4-4.1-022` | threshold 4.1 | audience `driver` | Section 14.7 Notices
- `L4-4.2-013` | threshold 3.2 | audience `driver` | Section 2.8 Ratings
- `L4-4.2-014` | threshold 3.1 | audience `driver` | Section 2.9 Location Based Services
- `L4-4.2-015` | threshold 3.1 | audience `driver` | Definition 1.20 Uber Data and Section 5.1 Ownership
- `L4-4.2-016` | threshold 3.1 | audience `driver` | Sections 7.1 and 7.2 Privacy
- `L4-4.2-017` | threshold 3.1 | audience `driver` | Section 5.3 Restrictions
- `L5-5.1-005` | threshold 5.1 | audience `driver` | Section 2.5

### R31. S33 — Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai)

Uber India Systems Private Limited. Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai). Jurisdiction: India, Mumbai only. This is a rider-facing addendum. It binds riders, not driver partners, but it states Uber's position on the auto SaaS fare model and on the role of Driver Partners. Document date: 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025. Retrieved 2026-09-13. Available at: <https://www.uber.com/in/en/legal/india-auto-saas-rider-terms-and-conditions---mumbai/>

- **levers_supplied**: L1 / 1.1; L3 / 3.1
- **extract_count**: 4

Sections cited from this source:

- `L1-1.1-031` | threshold 1.1 | audience `mixed` | Sections 2.1, 2.2 and 2.3 Fare Estimation, Negotiation & Payment Responsibilities
- `L1-1.1-032` | threshold 1.1 | audience `mixed` | Section 3 Platform-Related Charges & Other Fees
- `L1-1.1-033` | threshold 1.1 | audience `mixed` | Section 4.1 Limitation of Liability
- `L3-3.1-027` | threshold 3.2 | audience `mixed` | Section 1 Nature of Services & Role of Uber

### Reference list, plain citation form

- [R01] Uber India Systems Private Limited. Uber Community Guidelines. 2025-04-21 (page states: Last modified: 4/21/2025). Retrieved 2026-09-13 from <https://www.uber.com/in/en/legal/general-community-guidelines/>
- [R02] Uber Technologies Inc. / Uber India Systems Private Limited. Deactivations: Losing Account Access. Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/driver-app/deactivation-review/>
- [R03] Uber India Systems Private Limited. Uber Pro Terms and Conditions. 2026-08-05 (page states: Last modified: 8/5/2026). Retrieved 2026-09-13 from <https://www.uber.com/in/en/legal/uber-pro-program-terms/>
- [R04] Uber Technologies Inc. Uber Non-Discrimination Policy. 2024-07-23 (page states: Last modified: 7/23/2024). Retrieved 2026-09-13 from <https://www.uber.com/in/en/legal/non-discrimination-policy/>
- [R05] Uber Technologies Inc. Zero Tolerance Policy. 2023-05-19 (page states: Last modified: 5/19/2023). Retrieved 2026-09-13 from <https://www.uber.com/global/en/legal/zero-tolerance-policy/>
- [R06] Uber Technologies Inc. How Uber Uses Communications Intelligence to Improve Your Experience. 2026-07-07 (page states: Last modified: 7/7/2026). Retrieved 2026-09-13 from <https://www.uber.com/in/en/legal/communication-intelligence/>
- [R07] Uber Technologies Inc. Uber Privacy Notice: Drivers and Delivery People. 2026-09-01 (page states: Last updated: September 1, 2026). Retrieved 2026-09-13 from <https://www.uber.com/global/en/privacy-notice-drivers-delivery-people/>
- [R08] Uber Technologies Inc. How earnings are calculated for rides (Uber Help, Driving and Delivering). Not stated on page. Retrieved 2026-09-13 from <https://help.uber.com/driving-and-delivering/article/how-earnings-are-calculated-for-rides?nodeId=ee1ec727-106d-4e3b-88d9-dd22de70e4c2>
- [R09] Uber Technologies Inc. Upfront fares (Uber Help, Driving and Delivering). Not stated on page. Retrieved 2026-09-13 from <https://help.uber.com/driving-and-delivering/article/what-is-the-upfront-fare?nodeId=bc83ed7e-6725-41de-afcb-72d263e5589f>
- [R10] Uber Technologies Inc. Upfront Fares, explained (Tracking Your Earnings, Driver App basics). Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/basics/tracking-your-earnings/>
- [R11] Uber Technologies Inc. How much can drivers make with Uber?. Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/how-much-drivers-make/>
- [R12] Uber Technologies Inc. How payments work (Driver App basics). Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/basics/how-payments-work/>
- [R13] Uber Technologies Inc. How star ratings work (Driver App basics). Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/basics/how-ratings-work/>
- [R14] Uber Technologies Inc. Drive with confidence (Driver Safety). Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/safety/>
- [R15] Uber Technologies Inc. Driver requirements. Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/requirements/>
- [R16] Uber Technologies Inc. Contact Uber (Drivers: How to Get Help). Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/drive/contact/>
- [R17] Uber Technologies Inc. Driving time limit (Uber Help, Driving and Delivering). Not stated on page. Retrieved 2026-09-13 from <https://help.uber.com/en/driving-and-delivering/article/driving-time-limit?nodeId=a50a72e1-d315-4154-ac66-b17bd5bd050a>
- [R18] Uber Technologies Inc. What is Trip Radar and how does it work? (Uber Help, Driving and Delivering). Not stated on page. Retrieved 2026-09-13 from <https://help.uber.com/driving-and-delivering/article/what-is-trip-radar-and-how-does-it-work?nodeId=b6fb7065-ce66-490c-a911-d4e6d5c10d29>
- [R19] Uber Newsroom India (IndiaSA Comms). Uber's New Features to Make Driving Safer, Easier, and Fairer. 2024-11-15 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/newsroom/uber-features-to-make-driving-safer-easier-and-fairer/>
- [R20] Uber Newsroom India (IndiaSA Comms Team). Uber announces 2nd edition of Driver Advisory Council. 2023-04-17 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/newsroom/uber-second-edition-driver-advisory-council/>
- [R21] Uber Newsroom India (IndiaSA Comms Team). Moving Forward Together: Launching Driver Advisory Council. 2022-03-24 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/newsroom/uber-driver-advisory-council/>
- [R22] Uber Newsroom India (Shonali Chakravarty). Uber introduces Uber Care for its driver partner community in India. 2018-11-26 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/newsroom/ubercare/>
- [R23] Uber Newsroom India (IndiaSA Comms Team). Uber commits INR 100 crores towards driver welfare initiatives. 2021-12-15 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/newsroom/uber-commits-inr-100-crores-towards-driver-welfare-initiatives/>
- [R24] Uber Newsroom India (IndiaSA Comms Team). Uber puts Safety at the heart of Driver Experience. 2019-01-29 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/newsroom/uber-puts-safety-at-the-heart-of-driver-experience/>
- [R25] Uber Blog India (Amit Jain, President of Uber India). Driving with Uber: Setting the record straight. 2017-03-03 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/blog/drivingwithuber/>
- [R26] Uber Newsroom India (Prabhjeet Singh). Keeping driver partners at heart. 2018-12-20 (dateline on page). Retrieved 2026-09-13 from <https://www.uber.com/in/en/newsroom/keeping-driver-partners-at-heart/>
- [R27] Uber Technologies Inc. Agreeing to terms and conditions (Uber Help, Driving and Delivering). Not stated on page. Retrieved 2026-09-13 from <https://help.uber.com/en/driving-and-delivering/article/agreeing-to-terms-and-conditions?nodeId=44cf1f0e-27ca-4919-9621-f1321a0381c1>
- [R28] Uber Technologies Inc. I have an inquiry about cancellation fee (Uber Help, Driving and Delivering). Not stated on page. Retrieved 2026-09-13 from <https://help.uber.com/driving-and-delivering/article/request-cancellation-fee?nodeId=41fee0a6-8941-4418-bf25-3327db4f50aa>
- [R29] Uber Technologies Inc. Uber Legal Hub, India index (jurisdiction and language selector). Not stated on page. Retrieved 2026-09-13 from <https://www.uber.com/in/en/legal/?country=india&lang=en>
- [R30] Uber India Systems Private Limited. Uber India Systems Private Limited Services Agreement (published as India Earner Car Subscription Model Terms and Conditions). 2025-10-06 (page states: Last modified: 10/6/2025). Effective date stated in the document: 01 October, 2025. Retrieved 2026-09-13 from <https://www.uber.com/in/en/legal/india-earner-car-subscription-model-terms-and-conditions/>
- [R31] Uber India Systems Private Limited. Addendum to Uber Rider Terms & Conditions, Auto software-as-a-service (Mumbai). 2025-08-07 (page states: Last modified: 8/7/2025). Effective date stated in the document: 29th July 2025. Retrieved 2026-09-13 from <https://www.uber.com/in/en/legal/india-auto-saas-rider-terms-and-conditions---mumbai/>

### Standard reference

- [R00] Fairwork. *Location-based Platform Work Principles.* Oxford Internet Institute, University of Oxford. In effect from 15 October 2024. Five principles, ten thresholds, thirty-three criteria, maximum score ten. Reproduced verbatim, threshold-wise and with footnotes inlined, in `Fairwork_LocationBased_Principles_verbatim.md`. Retrieved 2026-09-20 from <https://fairwork.oii.ox.ac.uk/en/fw/principles/fairwork-principles-location-based-work/>.
- [R00b] Fairwork. *Fairwork AI Principles.* 14 pp. The standard corpus v2026.09 was filed against, superseded for this purpose by [R00]. Retained so the v2026.09 filing stays traceable.
