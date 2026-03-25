You are running the PREMISE UNIQUENESS CLUSTERING stage.

Inputs:
1. Search plan: `premise/premise_search_plan.json`
2. Candidate field: `premise/premise_candidates.jsonl`

{{PREMISE_BRIEF_BLOCK}}

Task:
1. Group the candidates by deep premise similarity.
2. Your job is not to rank quality, choose a winner, or identify the strongest premise.
3. Cluster candidates together when they are really the same underlying novel with cosmetic variation.
4. Judge similarity at the level of:
   - protagonist function
   - core engine
   - pressure mechanism
   - scene source: where the book keeps getting scenes from
   - social geometry: how people keep pressing on one another
   - narrative motion: how the pressure evolves over the book
   - institution or process role when it is actually central
   - world-shaping constraint
   - what kind of scenes the book would keep generating
5. Do not cluster by superficial label alone. Two coastal settings may still be very different books. Two wildly different settings may still be the same book if they share the same deeper scaffold.
6. Pay special attention to repeated concretization crutches. Documentary systems, certification, claims, archives, compliance, checkpoints, testimony, identity adjudication, laboratories, miracle verification, ecological field stations, and similar high-legibility machines are only examples. The larger question is whether multiple candidates are solving “how to make this premise concrete” with the same deeper scene-generating device.
7. Cover every candidate exactly once.
8. Be aggressive about deduplicating near-variants, but do not collapse genuinely different books into one cluster just because they share tone or speculative material.
9. Decide whether the field is sufficiently unique overall. This is about premise-family spread, not quality.
10. Treat fewer than `{{PREMISE_MIN_UNIQUE_CLUSTERS}}` clusters as insufficiently unique.

Required output:
1. `premise/uniqueness_clusters.json`

`premise/uniqueness_clusters.json` contract:
1. Write a single JSON object with exactly these keys:
   - `seed`
   - `reroll_index`
   - `clusters`
   - `unique_cluster_count`
   - `field_is_sufficiently_unique`
   - `insufficient_uniqueness_reason`
2. `seed` must match the search plan seed.
3. `reroll_index` must match the search plan reroll index.
4. `clusters` must be a non-empty array.
5. Each cluster must be an object with exactly these keys:
   - `cluster_id`
   - `member_ids`
   - `similarity_summary`
   - `shared_engine_shape`
   - `shared_pressure_shape`
   - `shared_world_shape`
6. `member_ids` must be a non-empty array of candidate ids from `premise/premise_candidates.jsonl`.
7. Every candidate id must appear in exactly one cluster.
8. `unique_cluster_count` must equal the number of clusters.
9. `field_is_sufficiently_unique` must be `true` or `false`.
10. If `field_is_sufficiently_unique` is `false`, `insufficient_uniqueness_reason` must briefly explain why the field is still too convergent. If it is `true`, the reason may be an empty string.
11. Do not include markdown, code fences, or commentary outside the JSON object.
