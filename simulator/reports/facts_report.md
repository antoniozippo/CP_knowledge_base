# Facts Report — literature-grounded simulation checks

| id | claim | source_ref | expected | observed | verdict |
|---|---|---|---|---|---|
| F-01 | Naive animals show negligible pain signaling that stays flat over a 180-day horizon (no spontaneous transition to chronic pain). | theme_01#F1.14 | max pain_score over [1,180] < 0.1500 | pain_score=0.0500 | PASS |
| F-02 | Every agent state remains within the unit interval [0,1] at every tick of the SNI run (model well-posedness). | EC-0001 | [0,1] everywhere | all states in [0,1] at every tick | PASS |
| F-03 | When tonic injury drives stop, TNF-alpha activity falls significantly below the driver-maintained SNI arm (pathology is driver-maintained and reversible, not self-locking). | theme_03#F3.3 | mean state[TNF_TNF_alpha] sni_28d_drive_decay is below sni_28d by >= 0.1000 over [20,27] | gap=0.1564 (0.9730 -> 0.8166) | PASS |
| F-04 | After sustained-drive decay the pain readout sits below the driver-maintained arm (tonic drivers sustain the pain phenotype). | KCC2.md | mean pain_score sni_28d_drive_decay is below sni_28d by >= 0.0300 over [20,27] | gap=0.0312 (0.3447 -> 0.3136) | PASS |
| F-05 | Microglial activation rises no later than TNF-alpha after SNI (glial activation is proximal to cytokine elevation). | theme_03#F3.4 | shared_microglia crosses before/equal TNF_TNF_alpha (+/-1 tick) | shared_microglia@t=1 vs TNF_TNF_alpha@t=1 | PASS |
| F-06 | TNF-alpha rises no later than MMP-9 after SNI (cytokines precede or accompany ECM protease induction). | EC-0074 | TNF_TNF_alpha crosses before/equal PNN_ECM_MMP9 (+/-1 tick) | TNF_TNF_alpha@t=1 vs PNN_ECM_MMP9@t=1 | PASS |
| F-07 | BDNF rises before the KCC2 decline (microglia-BDNF-TrkB axis drives chloride dysregulation). | theme_01#F1.10 | assaying_molecularly_structural_plasticity_BDNF crosses before/equal BDNF_TrkB_KCC2 (+/-1 tick) | assaying_molecularly_structural_plasticity_BDNF@t=1 vs BDNF_TrkB_KCC2@t=2 | PASS |
| F-08 | KCC2 decline precedes the pain-score rise (spinal disinhibition is upstream of behavioral pain). | theme_01#F1.3 | BDNF_TrkB_KCC2 crosses before/equal readout:pain_score (+/-1 tick) | BDNF_TrkB_KCC2@t=2 vs readout:pain_score@t=3 | PASS |
| F-09 | Mean pain score over days 14-28 is elevated in SNI versus naive by more than the pre-registered separation margin. | theme_02#F2.3 | mean pain_score sni_28d - naive_28d over [14,28] >= 0.0500 | gap=0.2942 (0.3442 vs 0.0500) | PASS |
| F-10 | Barrier integrity is lower in SNI than naive from day 10 onward (BSCB/BBB disruption follows nerve injury). | theme_04#F4.2 | mean barrier_integrity naive_28d - sni_28d over [10,28] >= 0.0300 | gap=0.1717 (0.5000 vs 0.3283) | PASS |
| F-11 | Inflammation index is higher in SNI than naive during days 7-21 (neuroinflammatory response to peripheral nerve injury). | theme_03#F3.1 | mean inflammation_index sni_28d - naive_28d over [7,21] >= 0.0500 | gap=0.1350 (0.6350 vs 0.5000) | PASS |
| F-12 | Pain remains elevated in the chronic phase: SNI at days 150-179 is still separated from naive (persistence beyond the transition epoch). | theme_06#F6.1 | mean pain_score sni_180d - naive_180d over [150,179] >= 0.0500 | gap=0.2960 (0.3460 vs 0.0500) | PASS |
| F-13 | CLP257 (KCC2 enhancer) lowers mean pain score over days 14-28 versus SNI by at least the pilot margin. | theme_01#F1.2 | mean readout pain_score reduction >= 0.0300 over [14,28] | sni_28d-sni_28d_clp257=0.0350 (0.3442 -> 0.3092) | PASS |
| F-14 | Fasudil (ROCK inhibitor) engages its target: mean ROCK activity over days 14-28 is reduced versus SNI by at least 0.2. | RhoA-ROCK.md | mean state[RhoA_ROCK_ROCK] reduction >= 0.2000 over [14,28] | sni_28d-sni_28d_fasudil=0.3575 (0.8728 -> 0.5153) | PASS |
| F-16 | XPro1595 (solTNF/TNFR1-selective inhibitor) lowers the inflammation index versus SNI. | theme_03#F3.1 | mean readout inflammation_index reduction >= 0.0300 over [7,21] | sni_28d-sni_28d_xpro1595=0.0306 (0.6350 -> 0.6044) | PASS |
| F-17 | Re-running sni_28d with identical inputs produces byte-identical tick logs (rules-only runs are fully deterministic). | theme_01#F1.14 | tick_log bytes identical across reruns of sni_28d | identical | PASS |
| F-18 | A second run sharing the delta cache makes zero LLM client calls (caching sanity with a fake client). | EC-0100 | cached second run makes 0 LLM calls | warm=24, second=0 | PASS |

Overall: PASS (17/17 facts)
