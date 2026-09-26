# 04 Tag vocabulary (v0.1, starter set)

These lists are deliberately small (D-002). Rules:
- The LLM labeller **must** choose IDs from these lists only.
- If nothing fits, the labeller outputs `suggested_new_tags` with a reason. These are logged for review,
  not stored as tags.
- A new tag is added when it keeps coming up (in suggestions or user searches). Record the change
  in the changelog at the bottom.
- Each ID is stable English snake_case. The Bangla and English labels are for display and for search text.

## format (1)
| id | bn | en |
|---|---|---|
| `novel` | উপন্যাস | Novel |
| `novella` | উপন্যাসিকা / বড় গল্প | Novella |
| `short_story_collection` | গল্পগ্রন্থ | Short story collection |
| `poetry` | কাব্যগ্রন্থ | Poetry |
| `nonfiction` | প্রবন্ধ / নন-ফিকশন | Non-fiction |
| `memoir` | স্মৃতিকথা / আত্মজীবনী | Memoir / autobiography |
| `comics` | কমিকস | Comics / graphic novel |

## audience (1)
| id | bn | en |
|---|---|---|
| `children` | শিশু-কিশোর (ছোটদের) | Children |
| `teen` | কিশোর | Teen |
| `adult` | প্রাপ্তবয়স্ক | Adult |
| `all_ages` | সব বয়সী | All ages |

## genres (1–3): 17 tags
| id | bn | en | Notes |
|---|---|---|---|
| `detective` | গোয়েন্দা | Detective | A detective solving cases (Feluda, Byomkesh) |
| `thriller` | থ্রিলার | Thriller | Suspense and danger drive the story |
| `spy` | গুপ্তচর / স্পাই | Spy | Masud Rana style |
| `crime` | অপরাধ | Crime | Told from the side of the criminal or the crime world |
| `horror` | ভৌতিক | Horror | Aims to frighten |
| `supernatural` | অতিপ্রাকৃত | Supernatural | Ghosts and the paranormal, not necessarily scary (Misir Ali) |
| `sci_fi` | কল্পবিজ্ঞান | Science fiction | |
| `fantasy` | ফ্যান্টাসি | Fantasy | Invented worlds, magic |
| `adventure` | অ্যাডভেঞ্চার | Adventure | Journeys, expeditions (Shankar, Tin Goyenda) |
| `romance` | প্রেম / রোমান্টিক | Romance | Love story at the centre |
| `family_drama` | পারিবারিক | Family drama | |
| `social` | সামাজিক | Social | Society, class and social problems |
| `historical` | ঐতিহাসিক | Historical | Set in a real historical period |
| `liberation_war` | মুক্তিযুদ্ধ | Liberation War | 1971 at the centre |
| `humor_satire` | রম্য / ব্যঙ্গ | Humour / satire | |
| `psychological` | মনস্তাত্ত্বিক | Psychological | Inner life, the mind |
| `mythology` | পৌরাণিক | Mythology | Myths, epics, retellings |

## moods (1–3): 10 tags
| id | bn | en |
|---|---|---|
| `dark` | অন্ধকার | Dark |
| `melancholic` | বিষণ্ণ | Melancholic |
| `tense` | টানটান উত্তেজনা | Tense |
| `eerie` | গা ছমছমে | Eerie |
| `funny` | হাস্যরসাত্মক | Funny |
| `heartwarming` | হৃদয়স্পর্শী | Heartwarming |
| `romantic` | রোমান্টিক | Romantic |
| `nostalgic` | স্মৃতিকাতর | Nostalgic |
| `inspiring` | অনুপ্রেরণাদায়ী | Inspiring |
| `bittersweet` | সুখ-দুঃখের মিশেল | Bittersweet |

## pace (1)
| id | bn | en |
|---|---|---|
| `slow` | ধীরগতির | Slow |
| `medium` | মাঝারি | Medium |
| `fast` | দ্রুতগতির | Fast |

## tone (1)
| id | bn | en | Notes |
|---|---|---|---|
| `light` | হালকা | Light | Easy to read, entertainment |
| `moderate` | মাঝারি | Moderate | |
| `literary` | সাহিত্যধর্মী | Literary | Dense, serious literary fiction |

## themes (2–5): 24 tags
| id | bn | en |
|---|---|---|
| `family` | পরিবার | Family |
| `love` | প্রেম | Love |
| `friendship` | বন্ধুত্ব | Friendship |
| `childhood` | শৈশব | Childhood |
| `coming_of_age` | বেড়ে ওঠা | Coming of age |
| `poverty` | দারিদ্র্য | Poverty |
| `class_inequality` | শ্রেণিবৈষম্য | Class inequality |
| `womens_lives` | নারীর জীবন | Women's lives |
| `village_life` | গ্রামীণ জীবন | Village life |
| `urban_life` | নগরজীবন | Urban life |
| `war` | যুদ্ধ | War |
| `partition` | দেশভাগ | Partition |
| `politics` | রাজনীতি | Politics |
| `religion` | ধর্ম | Religion |
| `crime` | অপরাধ | Crime |
| `justice` | ন্যায়বিচার | Justice |
| `revenge` | প্রতিশোধ | Revenge |
| `death_grief` | মৃত্যু ও শোক | Death and grief |
| `loneliness` | একাকীত্ব | Loneliness |
| `identity` | আত্মপরিচয় | Identity |
| `mental_health` | মানসিক স্বাস্থ্য | Mental health |
| `nature` | প্রকৃতি | Nature |
| `migration` | অভিবাসন / প্রবাস | Migration / diaspora |
| `science` | বিজ্ঞান | Science |

## setting_region (1–2)
| id | bn | en |
|---|---|---|
| `dhaka` | ঢাকা | Dhaka |
| `other_bd_city` | বাংলাদেশের অন্য শহর | Other Bangladeshi city |
| `rural_bangladesh` | বাংলাদেশের গ্রাম | Rural Bangladesh |
| `kolkata` | কলকাতা | Kolkata |
| `rural_west_bengal` | পশ্চিমবঙ্গের গ্রাম | Rural West Bengal |
| `elsewhere_india` | ভারতের অন্যত্র | Elsewhere in India |
| `abroad` | বিদেশ | Abroad |
| `imaginary` | কাল্পনিক জগৎ | Imaginary world |

## setting_era (1)
| id | bn | en | Years |
|---|---|---|---|
| `pre_colonial` | প্রাক-ঔপনিবেশিক | Pre-colonial | before ~1757 |
| `colonial` | ব্রিটিশ আমল | British colonial | ~1757–1947 |
| `1947_1971` | দেশভাগ থেকে একাত্তর | 1947–1971 | Partition and the Pakistan era |
| `liberation_war_1971` | মুক্তিযুদ্ধকাল | 1971 | |
| `post_independence` | স্বাধীনতা-পরবর্তী | Post-independence | 1972–1999 |
| `contemporary` | সমকালীন | Contemporary | 2000– |
| `future` | ভবিষ্যৎ | Future | |
| `unspecified` | অনির্দিষ্ট | Unspecified | |

For West Bengal books set after 1947, use `1947_1971`, `post_independence` or `contemporary` by year.

## content_notes (0+)
| id | bn | en |
|---|---|---|
| `violence` | সহিংসতা | Violence |
| `gore` | বীভৎসতা | Gore |
| `sexual_content` | যৌনতা | Sexual content |
| `suicide` | আত্মহত্যা | Suicide |
| `abuse` | নির্যাতন | Abuse |
| `substance_use` | মাদক | Substance use |

## Deferred (not in v0.1)
- `protagonist_type` (detective, child, woman, student…): add if users search by it
- `ending_feel`: dropped under D-003 (spoiler)

## Changelog
- **v0.1 (2026-09-26):** first starter set. Bangla labels to be reviewed by a native reader.
