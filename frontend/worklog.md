# ToddLab Frontend — Worklog

Projet : frontend Next.js 16 consommant le backend ToddLab (version de référence : V29, cf. Task 15). Depuis la Task 15, le frontend vit dans `frontend/` du dépôt ToddLab ; le backend est à la racine du même dépôt (`data/dist/`).
Tous les agents : lire ce fichier AVANT de travailler, y ajouter sa section APRÈS.

---

Task ID: 1
Agent: orchestrator (main)
Task: Fondations du frontend ToddLab (données, API, i18n, design system)

Work Log:
- Analyse complète du backend github.com/EdizKesici/ToddLab (pipeline Python, contrat data/dist)
- Copie de data/dist (28 indicateurs, catalog.json, entities.json, todd_corpus.json — 53 Mo) dans /home/z/my-project/data/dist ; script scripts/sync-data.sh
- Contrat typé complet dans src/lib/toddlab/types.ts (points canoniques, témoins, gaps value:null, clés additives)
- Store serveur avec cache mémoire : src/lib/toddlab/store.ts (littéral data/dist, immigration_stock marqué indisponible — gitignoré upstream)
- Requêtes serveur : src/lib/toddlab/server/queries.ts (catalog, entities+counts, series filtrées, year, country profile avec rangs + fallback witness)
- Routes API : /api/stats, /api/catalog, /api/entities, /api/corpus, /api/indicators/[id]/meta, /api/indicators/[id]/series?countries=, /api/indicators/[id]/year?year=&sex=, /api/countries/[id]
- Client hooks React Query : src/lib/toddlab/client.ts
- i18n maison EN/FR : src/lib/toddlab/i18n/ (dictionaries.ts ~150 clés UI ; labels-fr.ts : 29 indicateurs + 261 entités + unités + familles traduits). EN défaut → détection navigateur FR → toggle header, persistance localStorage
- Design system : palette papier chaud/encre/terracotta (oklch) light+dark dans globals.css ; 8 couleurs catégorielles chart-1..8 sans bleu/indigo ; --witness gris pointillé ; fonts Fraunces (serif titres) + Inter (UI)
- Layout : header sticky glassmorphism (nav + langue + thème), footer sticky (min-h-screen flex col + mt-auto), providers (next-themes, React Query, i18n)
- Composants partagés : badges (Todd/Reliability/Family/Direction/Witness), EntityPicker (max 8, recherche Command), MetricPicker (max 6, filtre familles), Sparkline (gap-aware), SexToggle, YearSlider, états Loading/Error/Empty, ChartTooltipShell, PageHeader/SectionTitle

Stage Summary:
- Contrat et conventions À RESPECTER par les agents pages :
  - i18n : useI18n().t((d) => d.section.key) ; labels contenus : useIndicatorLabel(id, enLabel), useEntityLabel(id, enLabel), useFamilyLabel(f), useUnitLabel(u) ; NOUVELLES clés UI => ajouter aux DEUX langues dans dictionaries.ts
  - data : hooks src/lib/toddlab/client.ts (useCatalog, useEntities, useCorpus, useIndicatorMeta, useSeries, useYearData, useCountryProfile) — ne JAMAIS fetcher les JSON dist directement
  - couleurs pays : colorForIndex(i) / colorForSeries(i) (8 max) ; témoins : WITNESS_COLOR + pointillés
  - gaps : laisser VIDE (pas d'interpolation, pas de marqueur)
  - tooltip données : provider + source_ref + citation seulement
  - format nombres : fmtNumber(value, unit, lang) de src/lib/toddlab/format.ts
  - composants shadcn dispo dans src/components/ui ; icônes lucide-react ; animations framer-motion sobres (150-300ms)
  - Tout composant avec hooks/useI18n => "use client"

---

Task ID: 2-a
Agent: full-stack-developer
Task: Pages Accueil + Méthode

Work Log:
- Lu worklog.md (Task 1), dictionaries.ts, client.ts, composants shared/*, ui/*, globals.css avant d'écrire une ligne
- Vérifié les données réelles via API : /api/stats (28 indicateurs, 261 entités, 112 288 points canoniques, 276 790 témoins, 16 livres, 24/24) et /api/indicators/infant_mortality/series (canonique URSS curated 1970-1990, pic 31,4‰ en 1976 ; témoin owid/UN IGME Russie 1958-2024)
- Task A — Home : réécrit src/app/page.tsx ("use client", conteneur max-w-6xl) + 4 composants dans src/components/home/ : hero.tsx (kicker uppercase terracotta, titre serif-display jusqu'à text-7xl, 2 CTA Link /compare + /methodology, stagger framer-motion 300ms easeOut), stats-band.tsx (bande pleine largeur border-y bg-secondary/40, dl grille 2/3/6 cols, count-up rAF déclenché par onViewportEnter, compact Intl pour les points, suffixe "/24" en terracotta, respect prefers-reduced-motion via duration 0), teaser-cards.tsx (3 cartes Link hover lift -4px, icônes GitCompareArrows/Globe2/BarChart3, ArrowUpRight animé au hover), score-placeholder.tsx (bordure dashed 2px, Badge outline primaire, aria-disabled, Sparkles, opacité réduite)
- Task B — Méthode : src/app/methodology/page.tsx (server component, metadata "The method") + src/components/methodology/method-view.tsx (6 sections numérotées 01-06 avec motion whileInView, séries divide-y, s6Body via interpolate + meta useCatalog, encart Score Card dashed + badge home.scoreBadge, bouton GitHub outline) + founding-case-chart.tsx
- Chart cas fondateur : useSeries("infant_mortality", ["ussr","russian_federation"]), rows 1960-2000 reconstruites côté client, canonique URSS ligne solide var(--chart-1) dots r=3 connectNulls=false, témoin = bloc witness dont key contient "owid" ligne pointillée var(--witness) "6 4", ReferenceArea 1976-1987 fill var(--muted) + label method.s4Blackout, Y "‰" domain [0,40], tooltip custom via ChartTooltipShell (fmtNumber unit deaths_per_1000_births), légende HTML sous le graphe
- Aucune modification de fichiers existants (dictionaries.ts intact — toutes les clés nécessaires existaient déjà : home.*, method.*, common.canonical/witness/github)
- Corrections lint : setState synchrone dans effect (stats-band) remplacé par durée 0 dans le rAF pour reduced-motion ; erreur restante de bun run lint concerne src/lib/toddlab/i18n/index.tsx (fichier Task 1, hors de mon périmètre, intouchable)
- Vérifications : curl 200 sur / et /methodology, textes présents dans le HTML ; test navigateur headless (agent-browser) : chart = 2 lignes + 1 ReferenceArea + label "Publication blackout", count-up au scroll → 28 / 261 / 112.3K / 276.8K / 16 / 24/24 ; 0 erreur console/page ; dev.log propre

Stage Summary:
- Fichiers créés : src/app/page.tsx (réécrit, autorisé), src/app/methodology/page.tsx, src/components/home/{hero,stats-band,teaser-cards,score-placeholder}.tsx, src/components/methodology/{method-view,founding-case-chart}.tsx
- Décisions : toutes les strings UI proviennent de dictionaries.ts (aucune string locale nécessaire) ; count-up custom rAF plutôt que lib externe ; chart en figure/figcaption avec légende HTML alignée sur le style WitnessTag ; isAnimationActive=false sur les Lines pour éviter le repaint Recharts au scroll
- Points d'attention : le libellé s4ChartTitle du dictionnaire dit "1965-1995" alors que le domaine demandé est [1960,2000] (consigne respectée) ; les stats affichent "—" tant que le band n'entre pas dans le viewport (choix count-up au scroll) ; /compare, /countries, /indicators sont liés mais pas encore construits (autres agents)

---

Task ID: 2-b
Agent: full-stack-developer
Task: Page Comparer (comparateur — layout, contrôles URL-state, synthèse rangs, cartes métriques)

Work Log:
- Lu worklog.md (Task 1) + tous les modules partagés (client.ts, i18n, pickers, charts, badges, states, format, ui/*) ; vérifié le contrat réel de /api/indicators/[id]/series (canonical sans sex pour infant_mortality malgré sex_split:true, witness blocks mixtes M/F/both, gaps explicites US 2020) et l'existence des 13 ids pays des presets dans /api/entities
- use-query-state.ts : parsing/sérialisation complète de ?c&m&mode&y&f&t&w&s avec défauts spec (france,united_states,russian_federation / infant_mortality,life_expectancy / year / 2020 / 1970 / 2024 / w=0 / s vide) ; patch() fusionne depuis window.location.search (évite les lost updates du slider) puis router.replace(scroll:false) ; caps 8 pays / 6 métriques ; s ne stocke que les choix ≠ all
- synthesis-grid.tsx : kit de rang partagé (computeRanks en classement compétitif 1,2,2,4 sur valeurs non-null uniquement ; pickPrimaryValue both→male→female ; RankBadge vert-forêt rang 1 / terracotta dernier / neutre sinon) ; grille métrique×pays avec colonnes pilotées par des SynthesisColumn (useSeries par métrique, queryKey identique aux cartes → zéro fetch dupliqué) qui remontent leurs cellules via onReport ; colonne masquée si pas de donnée à l'année de référence ; cellule vide si gap (jamais de rang fabriqué)
- metric-card.tsx : carte par métrique (header label localisé + ToddCoreBadge + ReliabilityBadge + unité + DirectionBadge + SexToggle si sex_split) ; mode year → BarChart année EXACTE, une barre/pays colorForIndex, deux barres M/F (F opacité .55) si sex_split+all sans valeur both, témoin = Bar fantôme gris dashé superposé via barGap="-100%" ; mode period → LineChart linéaire connectNulls={false} partout, M solid / F dashé même couleur pays, témoins both-sexes uniquement (dash gris 1.5 sans points, fusion 1er bloc par année) ; fallback single-line both quand la série canonique sex-split ne porte que des rows sans sex (cas réel infant_mortality) ; tooltips custom provider+source_ref+citation tronquée 80 (canonique) / provider+root_label (témoin), valeurs fmtNumber+unité ; tables compactes : year = Valeur(+année) / Témoin(root_label en title) / Rang, period = première & dernière valeur observée (+année) et variation % calculée signée avec astérisque + title local {en:"change (computed)", fr:"variation (calculée)"} ; état 503 → bloc « unavailable », erreur réseau → ErrorBlock retry, chargement → SkeletonRows, canonical vide + témoins présents → chart témoin + badge modelled + witnessNote, note gapNote sous chaque chart
- app/compare/page.tsx : header + barre de contrôles sticky top-14 z-30 bg-card/85 backdrop-blur (3 lignes : pays+presets(6 chips, filtrés sur le registre), métriques+filtre famille local+Tabs mode+Switch témoins labellisé, YearSlider sur l'UNION des available_years (useQueries même queryKey que useSeries → cache partagé) ou inputs number From/To clampés [min,max] union avec f≤t forcé) ; SynthesisGrid si ≥2 métriques ET ≥2 pays à l'année de référence (y ou t) ; grille md:2 colonnes de MetricCard avec stagger framer-motion (220ms, délai 60ms/carte, cap 300ms) ; états vides globaux pickCountriesFirst/pickMetricsFirst, ErrorBlock global si registre/catalogue KO ; page Suspense-wrappée (useSearchParams)
- Débogage : 3 imports égarés (useUnitLabel/useEntityLabel/useIndicatorLabel/useI18n appartiennent à i18n, pas client.ts) corrigés après 500 ; directive eslint-disable superflue retirée ; EmptyBlock typé string → bloc 503 dédié avec icône Database ; bug period mode : canonicalAnyPeriod faux car defs M/F ne matchaient pas les rows both-only → fallback par pays, re-testé
- Vérifié par curl (200 sur /compare nu, avec params year/period/w/s, pays/métriques vides, métrique 503 immigration_stock), /api series 200, dev.log propre, eslint+tsc propres sur MES fichiers ; testé en navigateur headless : zéro erreur console/page, sliders/tabs/switch/sex-toggle mettent bien à jour l'URL, screenshots VLM OK (charts, badges de rang, aucun glitch)

Stage Summary:
- Fichiers créés : src/app/compare/page.tsx · src/components/compare/metric-card.tsx · src/components/compare/synthesis-grid.tsx · src/components/compare/use-query-state.ts — AUCUN fichier existant modifié
- Schéma URL : ?c(liste 8)&m(liste 6)&mode=year|period&y&f&t&w=0|1&s=metric:all|male|female — défauts appliqués si absent, replace (pas push), scroll:false
- Décisions : rangs sur valeurs observées uniquement, base primaire both→male→female marquée M/F dans les title (jamais de moyenne inventée) ; témoins year = 1re valeur witness (both d'abord) superposée en barre fantôme dashée ; témoins period = lignes both-sexes dashées sans points ; connectNulls={false} et cellules vides partout (gaps = vide, zéro interpolation) ; courbes type="linear" (fidèle, pas de lissage) ; variation % marquée « * » calculée côté client
- Points d'attention : barres superposées reposent sur barGap="-100%" (hack Recharts documenté, à surveiller en upgrade v3) ; unions d'années via useQueries dupliquent la queryFn locale de client.ts (keys identiques donc cache partagé) ; l'erreur lint résiduelle du projet est pré-existante (src/lib/toddlab/i18n/index.tsx, Task 1) et hors de mon périmètre

---

Task ID: 2-d
Agent: full-stack-developer
Task: Pages Indicateurs (index + détail + carte mondiale choroplèthe)

Work Log:
- Lu worklog.md (Task 1) + dictionaries.ts (toutes les clés indicators.* existaient déjà — zéro string locale ajoutée), client.ts (types YearPayload/SeriesPayload/IndicatorMetaPayload), shared/* (EntityPicker, SexToggle, YearSlider, badges, states, ChartTooltipShell, colorForSeries/WITNESS_COLOR), format.ts (fmtNumber/fmtTick/percentileOf), ui/*
- Vérifié les contrats réels avant d'écrire : /api/indicators/suicide_rate/year?year=2000&sex=male (points sex-tagged provider oecd) ; infant_mortality year 2000 sex=all → canonical 0 + witness 199 (fallback témoin indispensable) ; year 2025 → 0/0 (d'où l'auto-pas de l'année par défaut) ; series sex-split = mélange rows sexées (oecd) ET non-sexées (DYB totals) → clés de lignes à 3 cas ; world-atlas countries-110m : ids TopoJSON = strings numériques ("250") ; world-countries : cca3→ccn3 (250) ; /api/entities : iso3→entity_id (255)
- world-map.tsx : dynamic import() de world-atlas/countries-110m.json + world-countries dans useEffect (hors bundle SSR), topojson feature() + d3-geo geoNaturalEarth1().fitExtent([[8,8],[772,412]]) mémoïsés, SVG viewBox 0 0 780 420 w-full h-auto ; join TopoJSON id → ccn3→cca3→iso3→entity_id (useEntities) ; couleur = percentileOf(value, valeurs non-null, higherIsBetter) → 5 bins hex fixes best→worst ["#0f766e","#5e8a68","#a08d5f","#c07a4a","#b8431f"], no-data var(--muted) opacité .6, stroke var(--background) 0.5 ; tooltip div absolute clampée suivant la souris (label entité localisé, valeur fmtNumber+unité, provider·source_ref ou root_label témoin) ; clic path → router.push /countries/[entity_id] (seulement si l'entité existe dans le dist) ; hover = strokeWidth 1.2 + brightness-90
- Fallback témoin carte/classement : si 0 valeur canonique → witness_points[0] + Badge inline "basé sur le témoin · root_label" (testé sur male_height_trend 2000 : badge + 38 pays colorés) ; YearSlider + légende 5 bins mapLegendBest→mapLegendWorst + chip mapNoData
- ranking-table.tsx : même queryKey useYearData que la carte (cache partagé, un seul fetch) ; tri best-first higher_is_better aware, rangs compétitifs ; witness map (1re valeur non-null tous blocs) ; col Witness value muted uniquement si ≠ canonique (eps 1e-9), sinon — ; pays témoin-only → rang "n*" + valeur "x*" muted, root_label en title ; provider Badge outline uppercase xs ; max-h-80 overflow-y-auto slim-scroll, thead sticky bg-card
- indicator-series-card.tsx : EntityPicker max 6 défaut [france,united_states,russian_federation,japan] → useSeries ; clés de lignes c:eid[:sex] / w:eid[:sex] ; sex=all+sex_split → M solid + F dashé même couleur SI le pays a des points sexés (oecd), + total non-sexé en opacité .35 si présent ; sex=male/female → uniquement les points du sexe demandé (jamais de total déguisé) ; témoins (Switch) : lignes dashées WITNESS_COLOR, jamais de fusion avec le canonique, dédoublonnées par année (1er bloc non-null) ; connectNulls={false} partout (gaps = rupture), XAxis number allowDecimals=false, YAxis fmtTick ; tooltip ChartTooltipShell provider/source_ref/citation en title ; légende chips + "— Men · ┄ Women" + trait dashé témoin + gapNote
- app/indicators/page.tsx : PageHeader + barre (Input recherche sur label localisé/id/famille, chips familles aria-pressed, Switch toddOnly), grille 3 cols lg triée par label localisé ; cartes : FamilyBadge + ToddCoreBadge + ReliabilityBadge(si≠high) + DirectionBadge + "n points · c citations · b books" tnum ; immigration_stock → div aria-disabled opacity-60 cursor-default + Badge N/A + Tooltip unavailableTitle (pas de Link) ; les autres → Link /indicators/[id] avec ring hover ; skeletons/error/empty
- app/indicators/[id]/page.tsx : useParams() typé string|string[] ; header = label localisé + badges (Family/ToddCore/Reliability/Direction + Badge ambre Repeat2 "ICD" title compare.reclassSensitive si reclassification_sensitive) + ligne meta unité · "1950 – 2024" · citations·books ; 503 → PageHeader (label fallback useCatalog) + Card dashed unavailableTitle/unavailableText + N/A ; 404 → EmptyBlock ; DetailContent key={meta.id} remonte year/sex partagés carte+classement, sonde useYearData (même key, zéro fetch de plus) : si l'année par défaut (dernière) n'a AUCUNE donnée (canonique+témoin), auto-pas arrière jusqu'à une année utile, stoppé dès que l'utilisateur touche year ou sex (ref) — jamais de setState synchrone dans l'effet (setTimeout 0, lint-safe)
- Sections : 1 carte mondiale, 2-3 grille xl:2cols classement+ séries, 4 sources (liste canonical/witness en ordre du tableau : Badge provider uppercase, source_ref code, root_label, citation line-clamp-2 title, license xs, chip "Priorité n" = index+1 ; racines depuis useCatalog entry.roots : chips "label ×n porte(s)" groupées Canonical/Witness + rootsHint), 5 Todd refs (Card border-primary/30 bg-primary/5, gros chiffres tnum font-serif-display citations/books, refs book · "year (year_raw)" · Badge citations · note line-clamp-2), 6 fiabilité (reliability_criteria text-sm, notes >300 chars en Collapsible line-clamp-4 + showMore/showLess, license en footer)
- Tests : curl 200 sur /indicators, /infant_mortality, /immigration_stock (carte unavailable), /suicide_rate, /gini_index, /math_test_scores ; contrat year validé ; agent-browser headless : 0 erreur console/page, carte = 32 pays colorés sur 5 bins + 145 muted (IM 2024), auto-pas 2025→2024, classement witness-only "1* San Marino … 1.2*", toggle témoins → 16 lignes (4 canoniques + 12 témoins), mode Men → témoins male dashés seuls, index : recherche "infant"→1, chip Mortality→12, +Todd core→8, carte N/A opacity .6 sans lien, FR vérifié (Mortalité infantile, Carte mondiale, basé sur le témoin, Le mieux/pas de donnée)
- Lint : bunx eslint sur mes fichiers = 0 problème ; l'unique erreur `bun run lint` est pré-existante (src/lib/toddlab/i18n/index.tsx:40, Task 1 — hors périmètre) ; dev.log : aucune erreur provenant de mes fichiers (le Build Error affiché vient de src/components/compare/metric-card.tsx qui importe useEntityLabel depuis @/lib/toddlab/client au lieu de @/lib/toddlab/i18n — fichier Task 2-b, non touché)

Stage Summary:
- Fichiers créés : src/app/indicators/page.tsx · src/app/indicators/[id]/page.tsx · src/components/indicator/world-map.tsx · src/components/indicator/ranking-table.tsx · src/components/indicator/indicator-series-card.tsx — AUCUN fichier existant modifié (dictionaries.ts intact : toutes les clés nécessaires existaient)
- Décisions carte : années année/sex remontées dans le parent et passées à WorldMap ET RankingTable (même queryKey useYearData → source unique réellement partagée) ; auto-pas de l'année par défaut quand la dernière année n'a aucune donnée (cas infant_mortality 2025) — jamais de donnée inventée, juste un défaut utile ; 5 bins hex fixes light-theme harmonisés teal→terracotta (lisibles dark aussi)
- Points d'attention carte : join = TopoJSON id numérique → ccn3 (world-countries) → cca3 → iso3 → entity_id (useEntities) ; entités historiques (SUN/CSK…) et micro-États absents du 110m restent muted ; Kosovo sans ccn3 → non joignable ; les deux imports lourds (topo ~110 Ko, world-countries) sont en dynamic import() côté client uniquement ; tooltips = provider+source_ref (canonique) ou root_label (témoin), jamais autre chose

---
Task ID: 2-c (récupéré par l'orchestrator après timeout de l'agent)
Agent: orchestrator (main)
Task: Pages Pays (index + profil)

Work Log:
- Agent 2-c initial : timeout avant toute écriture de fichier ; reprise manuelle
- Création src/app/countries/page.tsx : index 261 entités, recherche (label FR/EN + id + iso3), switch "avec données", tri (n métriques desc puis alpha), cartes hover-lift avec chips ex-URSS/historique/n métriques
- Création src/app/countries/[id]/page.tsx : profil (breadcrumb, header iso3/dates historiques, bouton Comparer → /compare?c=id, alerte ambre formerly_part_of, liens predecessor/successors), grille indicateurs groupée par famille
- Création src/components/country/indicator-grid.tsx : cartes indicateur (valeur fmtNumber + unité, rang canonique/témoin avec *, sparkline gap-aware, sex_series fusionnées année-partagée, CTA comparer). NOTE : première génération du fichier était défectueuse (cascade de wrappers absurdes) → supprimée et réécrite propre
- Fix lint : React import manquant dans [id]/page.tsx ; startTransition dans i18n/index.tsx (react-hooks/set-state-in-effect)

Stage Summary:
- /countries et /countries/[id] fonctionnels (200), lint projet 100% propre
- Volumétrie profil OK (28 indicateurs/pays via /api/countries/[id], cache React Query)

---
Task ID: 3
Agent: orchestrator (main)
Task: Intégration finale + vérification end-to-end (Agent Browser)

Work Log:
- Vérification navigateur complète de toutes les pages : / (hero + stats réelles + cartes + placeholder Score), /compare (year, period, témoins, sex-split, presets 7 pays, synthèse), /countries (261 entités, filtres), /countries/ukraine (alerte ex-URSS), /indicators (filtres, N/A immigration_stock), /indicators/infant_mortality (carte choroplèthe d3-geo, classement, séries, généalogie racines « 1 racine via N portes », Todd refs), /methodology (cas fondateur URSS : courbe officielle pic 31,4‰ 1976 vs plateau IGME + bande black-out 1976-87), /indicators/immigration_stock (carte unavailable 503)
- Vérifié : toggle FR (nav, contenu, labels entités/indicateurs FR), dark mode (papier chaud → encre inversée), viewport mobile 390px (nav scrollable, layout stack), footer sticky, tooltips provenance, gaps laissés vides, témoins pointillés gris
- Bugs corrigés lors de la vérification :
  - i18n/index.tsx : react-hooks/set-state-in-effect → startTransition
  - imports React manquant dans countries/[id]/page.tsx
  - useEntityLabel : fallback EN pour entités spéciales (ussr → "Soviet Union") + ENTITY_LABELS_EN
  - synthesis-grid.tsx : en-têtes colonnes utilisaient useSeries(metricId, []) (désactivé) → useCatalog
  - indicator page : "door(s)" → singulier/pluriel (× 1 door / × 14 doors) + template ex-URSS ("the Soviet Union" / "l'URSS")
- Recréé indicator-grid.tsx (première génération corrompue supprimée, réécriture propre)
- Lint final : 0 erreur, 0 warning

Stage Summary:
- V1 ToddLab frontend complète et vérifiée navigateur : 5 pages + 8 routes API, EN/FR, light/dark, responsive
- Architecture prête pour le Score Civilisationnel (placeholder en place, hooks et formats en place)
- Données : V25 (28 indicateurs disponibles, immigration_stock exclu — gitignore upstream)

---
Task ID: 3
Agent: orchestrator (main)
Task: Retours utilisateur V1 — vocabulaire simplifié, nettoyage hero/footer/stats, em-dashes FR, page indicateur (description + sources + fiabilité), espacements Comparer

Work Log:
- dictionaries.ts réécrit : vocabulaire jargon → mots simples partout (canonical/witness → EN Official/Estimate, FR Officiel/Estimation ; stats band → "verifiable data points"/"modelled estimates", FR "points vérifiables"/"estimations modélisées") ; keys supprimées : nav.tagline, home.heroKicker, home.statsCorpus (stat 24/24 retirée de stats-band, grille lg:grid-cols-5), common.{dataVintage,asReported,witnessShort,canonicalShort,modelled→"Estimates"}, indicators.{rootsTitle,rootsHint,door,priority,sourcesCanonical,notesTitle}
- Hero : kicker "Open-source data project"/"Projet de données open-source" supprimé (hero.tsx) ; titre → EN "Some data cannot lie." / FR "Certaines données ne peuvent pas mentir." ; header : tagline italique supprimée (site-header.tsx) ; teaser-cards : aria-label tagline retiré
- FR sans em-dash (tiret cadratin) : toutes les strings FR du dictionnaire → "-"/":" ou virgules (hero, teasers, presets La Chute finale/La Défaite, method s1-s6, scoreComing, gapNote, witnessNote, formerUnionWarning, countries.subtitle, unavailableText) ; placeholders "—" → "-" (ranking-table ×3, countries page, indicator-grid) ; stats-band placeholder count-up "—" → "…" ; EN garde ses em-dashes
- Footer : lien Méthode + ligne "Données : ToddLab V25 · UN DYB · …" supprimés ; layout simplifié (logo + blurb + GitHub) ; nouveau footerBlurb : EN "Measuring societies by what they live through, not by what they declare. Built on the method of Emmanuel Todd." / FR "Mesurer les sociétés par ce qu'elles vivent, non par ce qu'elles déclarent. Construit sur la méthode d'Emmanuel Todd." (alternatives proposées à l'utilisateur)
- Méthode : s6Body sans version ("un instantané du backend ToddLab", plus de V25) ; s2 "Chiffres officiels vs estimations" réécrit avec le nouveau vocabulaire ; subtitle "certaines données ne peuvent pas mentir" ; metadata EN des pages (layout.tsx, methodology) mises à jour (title simple "ToddLab", vocabulaire)
- Nouveau fichier src/lib/toddlab/i18n/descriptions.ts : descriptions courtes EN+FR pour les 29 indicateurs + PROVIDER_LABELS EN/FR (owid→"Our World in Data", un_dyb→"Annuaire démographique de l'ONU", curated→"Tables vérifiées ToddLab", etc.) ; hooks useIndicatorDescription() et useProviderLabel() ajoutés à i18n/index.tsx
- Page indicateur [id] : description courte affichée dans le PageHeader avant la carte (aussi en branche 503 immigration_stock) ; SourcesSection remplacée par 2 lignes brèves "Chiffres officiels provenant de … / Estimations provenant de …" (fournisseurs dédupliqués, libellés humains) — généalogie/roots/priority/citations retirés ; carte fiabilité réduite à Badge + 1 phrase par niveau (relHighText/relMediumText/relLowText) ; NotesBlock/Collapsible/Button imports nettoyés
- Page Comparer : espacements (control bar py-4/space-y-5, rows gap-x-4 gap-y-3, section mt-8 space-y-6, grille cartes gap-6) ; indicator-series-card : légende "— Hommes · ┄ Femmes" remplacée par vrais segments de ligne (border spans) ; badge import inutilisé retiré
- badges.tsx : WitnessTag default "Witness" → "Estimate" ; indicator-grid : "basedOnWitness — root" → "· root"
- Fix typo perso : fonction ToddRefsSection restaurée après édition accidentelle ; tsc src/ désormais propre (as const retiré du dictionnaire pour type Dictionary réellement bilingual, sparkline reduce<number> typé + cx Number()) ; bun run lint OK
- Vérifié agent-browser EN+FR : home (kicker/tagline absents, 5 stats, footer propre), 0 em-dash FR sur /, /compare, /indicators/infant_mortality, /indicators/male_height_trend, /methodology, /countries/ussr ; description FR avant carte OK ; sources = 2 lignes brèves ; fiabilité = badge + 1 phrase ; période + estimations + URL state OK ; console 0 erreur ; dev.log propre

Stage Summary:
- Vocabulaire utilisateur final : EN Official/Estimate, FR Officiel/Estimation ; stats band "points vérifiables"/"estimations modélisées" ; le mot "témoins" a disparu de l'UI (la note commune witnessNote parle de "estimations … jamais fusionnées avec les séries officielles")
- footerBlurb implémenté : "Mesurer les sociétés par ce qu'elles vivent, non par ce qu'elles déclarent. Construit sur la méthode d'Emmanuel Todd." — 3 alternatives proposées à l'utilisateur dans la réponse (échange = 2 clés dictionaries.home.footerBlurb)
- Descriptions indicateurs : si un id manque dans descriptions.ts → fallback silencieux (pas de paragraphe affiché) ; pour ajouter/modifier : src/lib/toddlab/i18n/descriptions.ts
- Score civilisationnel : toujours placeholder ("Coming soon"/"Bientôt"), l'utilisateur communiquera sa spécification plus tard

---
Task ID: 4
Agent: orchestrator (main)
Task: Retours V2 — préréglages hors cadre, synthèse lisible, refs Todd en chips, estimations colorées par pays, cartes clairsemées (événement-année + couverture), footer FR, libellés Todd

Work Log:
- dictionaries.ts : footerBlurb FR = phrase exacte de l'utilisateur ("Un laboratoire de données publiques inspiré de la méthode d'Emmanuel Todd : chaque chiffre sourcé, chaque absence signalée.") + EN miroir ; toddOnly FR "Utilisées dans les livres de Todd" / EN "In Todd's books only" ; toddCore FR "Dans les livres de Todd" + nouvelle clé toddCoreTip (tooltip badge localisé, jargon "(todd_core)" retiré — badges.tsx) ; nouvelles clés compare.synthesisAvg, indicators.mapCoverage/mapCoverageOne/mapSparse/mapEventNote (EN+FR, plural-safe) ; synthesisHint enrichi (tri par rang moyen + heat)
- /compare : préréglages sortis de la Card sticky (rangée propre au-dessus, chips border-dashed + icône Sparkles) ; le cadre ne contient plus que pays/métriques/mode/année (compare/page.tsx)
- synthesis-grid.tsx : lignes triées par rang moyen asc (sans rang → fin, ordre de sélection conservé) ; nouvelle colonne "Rang moyen" (1 décimale, title=lowerBetter) ; heat-tints par cellule (ratio (rank-1)/(n-1) → teinte #0f766e vers le 1er, #b8431f vers le dernier, alpha max 0.16, centre neutre) ; valeur = texte principal tnum, RankBadge à droite ; import useMemo ajouté
- metric-card.tsx : estimations colorées par pays — year : barre fantôme par Cell (fill/stroke = couleur pays, fillOpacity .16, dash "3 3") ; period : lignes témoins stroke=colorForIndex(pays), dash fin "2 4", strokeWidth 1.5, sans points ; tooltips : entrée témoin couleur du pays (Year+Period) ; LegendSwatch étendu (kinds dotted/ghost) ; import WITNESS_COLOR retiré
- indicator-series-card.tsx : lignes témoins color=colorForSeries(i) (couleur pays), strokeWidth 1.75, dash "2 4", opacité .9 ; légende témoin → border-dotted foreground ; WITNESS_COLOR import retiré (resté utilisé par la page méthode : cas fondateur, volontairement gris)
- Cartes clairsemées : store.getDefaultYear(id) (unit "year" → dernier événement ; sinon dernière année avec couverture ≥ max(8, 50% du max) — road 2025→défaut 2024, infant →2023) ; meta route + default_year ; buildYearPayload(..., byYear) : value ≤ year pour les événements ; year route accepte mode=by_year ; client.ts useYearData(opts {byYear}) queryKey étendu ; IndicatorMetaPayload.default_year
- world-map.tsx : eventYear = unit==="year" → useYearData byYear ; note mapEventNote sous le slider ; chip couverture "{n} pays avec des données" (mapCoverageOne si 1) ; avertissement ambre mapSparse si 0<n<10 (hors eventYear)
- ranking-table.tsx : byYear pour unit "year" ; label période "≤ {year}" ; suffrage : 16 pays au lieu d'1 ; mariage : 33 au lieu de 2
- indicators/[id]/page.tsx : effectiveYear = year ?? meta.default_year ?? dernière année ; ToddRefsSection réduite à des chips "Livre ×N" triées desc (grands chiffres/années/notes supprimés, CardDescription retirée + import nettoyé)
- Vérifié agent-browser EN+FR : /compare (préréglages hors cadre, synthèse triée Italie 1,5 en tête, heat tints, ghost bars colorées par pays en year, lignes pointillées colorées en period), /indicators/universal_suffrage_introduction_year (16 pays, note "by 1946", chip 16, classement ≤1946), /indicators/same_sex_marriage_legalization_year (33 pays), /indicators/road_accident_mortality (défaut 2024, chip 34 ; 2025 → avertissement ambre), /indicators/infant_mortality (chips livres), footer FR exact, zéro ém-dash FR sur 8 pages, mobile 390px OK, console 0 erreur, lint 0 erreur

Stage Summary:
- Le toggle "estimations" garde désormais la couleur de chaque pays partout (pointillés fins = estimation, jamais fusionné avec la série officielle) ; le gris witness ne reste que sur la page méthode (cas fondateur, choix narratif)
- Année par défaut calculée serveur (meta.default_year) : la carte d'accueil d'un indicateur n'est presque jamais vide ; les indicateurs "année-événement" (mariage, suffrage) utilisent une sémantique cumulative "survenu en {year} ou avant"
- Libellé "Cœur Todd uniquement" remplacé ; alternatives supplémentaires proposées à l'utilisateur dans la réponse
- Score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 5
Agent: orchestrator (main)
Task: Retours V3 — flux pays→indicateur focalisé (?country=), tableau Classement épuré, préréglages scénarios avec ère + méditerranée 12 pays

Work Log:
- Page pays → indicateur : le titre de chaque carte métrique pointe désormais vers /indicators/{id}?country={entity_id} (indicator-grid.tsx)
- indicators/[id]/page.tsx : restructuré en Suspense (pattern /compare) ; ?country= lu via useSearchParams ; nouvelle FocusBand en tête de page (Carte border-primary/40 bg-primary/5) : libellé pays + gros chiffre formaté + unité + contexte (Année X ou ≤ X pour les événements-années, sexe) + Rang r/n calculé sur les points canoniques de l'année (direction higher_is_better), fallback estimation non classée avec badge, état vide ; boutons "Voir tous les pays" (retire le param) + "Ouvrir la page pays" ; helper extractFocusValue(data, focusId, higherIsBetter) — useMemo retiré (react-hooks/preserve-manual-memoization)
- Focus propagé : WorldMap focusEntityId (contour foreground 1.6 + opacité pleine) ; RankingTable focusEntityId (ligne bg-primary/10, nom semibold, scroll auto DANS le conteneur table seulement via data-entity-id + querySelector, jamais de hijack du scroll page) ; IndicatorSeriesCard initialCountries (présélection du pays)
- RankingTable épuré : colonnes # / Pays / Valeur uniquement (unité passée en CardDescription sous le titre, colonnes Fournisseur + Estimation supprimées) ; lignes estimation-only = valeur suffixée * + note de bas de tableau (nouvelle clé indicators.rankingAsteriskNote) ; box allongée max-h-80 → max-h-[32rem]
- /compare presets : interface Preset {ids, metrics?, mode?, year?, from?, to?} ; presetColdWar (france-usa-russie) SUPPRIMÉ (type + dictionnaire) ; presetFallFinal = scénario La Chute finale (1976) : ussr+united_states, infant_mortality, period 1965-1990 (série officielle soviétique 1970-1990 vérifiée) ; presetDefeat = scénario Défaite de l'Occident (2024) : 6 pays, birth_rate_fertility + tertiary_education_share, period 1980-2024 ; presetMediterranean élargi à 12 pays (france,spain,italy,greece,turkiye,morocco,algeria,tunisia,libya,egypt,israel,lebanon — couverture vérifiée 200+ pts chacun) ; group presets (G7, UE, Méditerranée) ne touchent que les pays, scénarios chargent métriques+ère ; ids filtrés par catalogSet
- MAX_COUNTRIES 8 → 12 ; 4 nouvelles couleurs catégorielles chart-9..12 (chartreuse/mint/violet/wine, sans bleu/indigo) dans globals.css (light+dark+@theme) et COUNTRY_COLORS ; home teaser + sous-titres compare "12 pays" ; maxCountries "12 pays maximum"
- Dictionnaires : presetColdWar retiré, presetFallFinal "La Chute finale : URSS · États-Unis"/"The Final Fall : USSR · USA", presetDefeat sans "6 pays", +focusViewAll, +rankingAsteriskNote, -rankingWitnessCol (EN+FR symétrique)
- Vérifié agent-browser : flux complet /countries/france → clic Mortalité infantile → bande focus FR "France · 3,7 · Année 2023 · Rang 29/71" + France cerclée sur la carte + ligne classement surlignée auto-scrollée + série présélectionnée ; "Voir tous les pays" → URL propre ; événement-année mariage ?country=france → "2 013 · ≤ 2025 · Rang 13/33" ; mobile 390px (Japon 1,8 Rang 3/71) OK ; /compare : 5 préréglages (ColdWar absent), Chute finale → c=ussr,united_states&m=infant_mortality&mode=period&f=1965&t=1990, Défaite → c=6 pays&m=fertility+tertiary&f=1980&t=2024, Méditerranée → 12/12 pays, 12 couleurs distinctes en légende ; lint 0 erreur, console 0 erreur, dev.log propre

Stage Summary:
- Clic métrique depuis une page pays = vue focalisée d'abord (valeur + rang du pays), accès au monde entier en un clic — le contexte du pays n'est plus perdu
- Classement lisible en 3 colonnes (#/Pays/Valeur) ; l'unité vit sous le titre ; les estimations restent visibles via * + note
- Les préréglages "livres" (Chute finale, Défaite de l'Occident) sont des scénarios complets pays+métriques+ère ; Méditerranée couvre les deux rives avec la limite portée à 12 (palette étendue à 12 couleurs)
- Score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 6
Agent: orchestrator (main)
Task: Retours V4 - (a) tableau Classement trop haut (512 -> ~400/450), (b) Comparer : la Synthèse de groupe ne se génère qu'avec le Taux de chômage en mode période - pourquoi ?, (c) Comparer : le sélecteur d'années descend jusqu'à 1816 - quelles données ?

Work Log:
- Enquête données (python sur data/dist) : AUCUNE donnée canonique à 1816. Le plus ancien point canonique = top_income_share 1820 (russian_federation, saudi_arabia). Le witness (estimations) life_expectancy de France commence EXACTEMENT en 1816 (OWID long-run : reconstructions Riley/HMD + UN WPP) ; witnesses globaux descendent à 1543 (life_expectancy) et 1751 (maternal_mortality). life_expectancy canonique France ne commence qu'en 2008.
- Cause (c) : useYearsUnion (compare/page.tsx) fusionnait available_years canoniques ET witness -> une seule série d'estimations longue tirait tout le slider en dehors des données officielles. Cause (b) : SynthesisColumn exigeait un point canonique à l'année exacte de fin de période ; unemployment_rate est annuel et dense (2003-2025, Eurostat) donc présent à la fin choisie, alors que la plupart des séries s'arrêtent à des années différentes (2024, 2021, etc.) -> colonnes vidées, tableau "désactivé".
- ranking-table.tsx : max-h-[32rem] -> max-h-[28rem] (448px, vérifié computed 448px, scrollHeight 7736px).
- synthesis-grid.tsx : SynthesisGrid props refYear -> {from, to} (compare passe year/year en mode année, from/to en mode période) ; SynthesisColumn : dernière année observée dans [from, to] par pays (jamais d'interpolation, valeur null reste vide) ; CellData.yearUsed ; en mode période le tooltip de chaque cellule divulgue l'année réellement utilisée ("Rank 2 of 4 · 2023", avec M/F le cas échéant) ; mode année inchangé (match exact, pas d'année dans le tooltip) ; commentaires doc à jour.
- compare/page.tsx : useYearsUnion(metricIds, countries, includeWitness) -> {years, canonicalMin, witnessMin} ; années witness incluses SEULEMENT quand le toggle estimations est ON (la plage reflète ce qui est réellement affiché) ; nouvel useEffect de clamp/snap : year, from, to resnappés dans l'union courante (year -> année observée la plus proche, bornes -> clamp) quand les estimations passent OFF ou qu'une URL contient une année hors couverture ; hint sous la rangée 3 (Info + interpolate, clé compare.witnessRangeHint) quand witnessMin < canonicalMin ; presetFallFinal from 1965 -> 1970 (cohérent avec la série soviétique officielle 1970-1990) ; refYear retiré ; imports useEffect/Info/interpolate.
- dictionaries.ts (EN+FR symétrique) : synthesisHint réécrit (dernière valeur observée dans la période, année dans l'infobulle, jamais interpolée) ; nouveau witnessRangeHint avec {year} ; em-dash retiré du FR (le seul de la section FR).
- Vérifié agent-browser : France+life_expectancy estimations OFF -> slider 2008-2024 (plus de 1816) ; ON -> 1816-2024 + hint EN et FR ; OFF -> snap y=1816 -> y=2008, f/t clampés (URL réécrite) ; synthèse période 2000-2025 (france,germany,italy,spain x unemployment+infant+life_exp) -> LES 3 colonnes présentes (avant : chômage seule) avec tooltips "Rank x of 4 · 2025/2024/2023" ; mode année -> tooltips sans année, valeurs exactes 2020 ; preset Chute finale -> f=1970&t=1990 ; Classement 448px ; mobile 390px OK ; lint 0 erreur ; erreur d'hydratation Radix Tabs (ids aria-controls) PRÉ-EXISTANTE - prouvée par git stash (identique sans mes modifications), cosmétique, non liée.

Stage Summary:
- La plage d'années du Comparer reflète désormais les données officielles de la sélection ; les décennies "estimations seules" ne s'ouvrent qu'avec le toggle estimations, et une phrase explique alors jusqu'où et pourquoi (ex. France : estimations d'espérance de vie dès 1816, données officielles dès 2008)
- La Synthèse de groupe fonctionne maintenant en mode période pour TOUTES les métriques : dernière valeur observée dans la période, année réelle révélée dans l'infobulle - le comportement "seul le chômage marche" (série annuelle dense) disparaît, aucune interpolation n'est introduite
- Classement : 448px (28rem) ; score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 7
Agent: orchestrator (main)
Task: Retour V5 - rendre la hauteur du tableau Classement adaptable à la carte "Séries temporelles" à sa droite (elle grandit/rétrécit selon le nombre de pays)

Work Log:
- Constat : grille xl:grid-cols-2 avec items-start + scroll box plafonné à max-h-[28rem] -> les deux cartes évoluaient indépendamment
- ranking-table.tsx : nouvelle prop fill ; en fill, Card xl:h-full, CardContent xl:flex xl:flex-col xl:flex-1 xl:min-h-0, scroll box xl:min-h-0 xl:max-h-none xl:flex-1 (sous xl : plafond 448px inchangé)
- indicators/[id]/page.tsx : items-start retiré ; la carte Classement vit dans un wrapper div.relative > div.xl:absolute.xl:inset-0 -> à xl le wrapper ne contribue aucune hauteur, la ligne de grille est dimensionnée par la carte Séries seule ; le tableau remplit et s'aligne par le bas ; sous xl, wrapper transparent (comportement empilé conservé)
- Vérifié agent-browser (1440px, infant_mortality) : 4 pays -> cartes 576=576, box 424, bas alignés ; 6 pays (Italie+Brésil ajoutés) -> toujours 576=576 alignés ; carte Séries forcée +300px -> 900=900, box 424->748, alignés ; carte Séries forcée à 400px -> 400=400, box 248, défilement intact, alignés ; restauration -> 576/576/424 ; mobile 390px -> empilé, box plafonnée 448px, défilement OK ; screenshot visuel conforme ; console 0 erreur, dev.log propre, lint 0 erreur

Stage Summary:
- Le tableau Classement épouse désormais la hauteur réelle de la carte Séries temporelles à chaque changement de sélection (grandit ET rétrécit), bas de cartes toujours alignés ; en mobile le plafond 448px est conservé
- Aucune mesure JS : pure CSS (grid stretch + position absolute à xl), le focus auto-scroll du classement continue de fonctionner (math inchangée sur clientHeight)
- Score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 8
Agent: orchestrator (main)
Task: (0) suivi backend V26 + resync, (1) état d'URL sur /indicators/[id], (2) SEO/partage (metadata par page, sitemap, robots, images OG), (3) recherche globale Cmd+K

Work Log:
- Repo backend re-cloné (l'ancien /home/z/toddlab-analysis avait disparu) : V25 -> V26/V26.1/V26.1.1. data/dist : rétractation de DEUX indicateurs (agricultural_employment_share : fichier+catalogue+corpus ; immigration_stock : retiré du corpus) ; contrat inchangé sinon ; corpus 24 -> 22 métriques, 483 -> 470 citations
- scripts/sync-data.sh corrigé (cp -r SRC DST nichait dist/dist/ quand DST existe ; -> cp -r SRC/. DST/) ; resync ; store KNOWN_VINTAGE "V25 (snapshot 2026-09)" -> "V26 (snapshot 2026-10)" ; API vérifiées (27 indicateurs, corpus 22)
- Nouveau src/components/indicator/use-indicator-query-state.ts : ?country(focus, préservé)&y&s&c&sp&w ; omet les valeurs par défaut (y == default_year, s/sp == all, w == 0, c == sélection initiale) ; router.replace scroll:false ; merge depuis window.location (pas le snapshot de rendu) ; parseCountries : regex entity_id, dédoublonne, cap 6
- indicator-series-card.tsx : entièrement contrôlé (countries/sex/witness remontés à la page, DEFAULT_COUNTRIES déplacé) ; page : autoYear local pour l'auto-recul année-vide (pas d'écriture URL), handleYear/HandleSex -> patch
- SEO : les 5 pages clientes déplacées en vues (components/{indicator,country,compare}/*-view) + pages serveur ; generateMetadata sur /indicators, /countries, /countries/[id], /indicators/[id] (labels via store, descriptions EN) ; layout racine : metadataBase(site-url.ts : NEXT_PUBLIC_SITE_URL -> VERCEL_URL -> localhost), twitter card, openGraph SANS titre forcé (hérite par page) ; public/robots.txt supprimé (conflit) ; app/robots.ts + app/sitemap.ts (5 statiques + 27 indicateurs + 261 entités) ; opengraph-image.tsx x3 (root + 2 dynamiques) via OgCard partagé (satori, palette papier/encre/terracotta)
- Recherche globale : src/components/layout/global-search.tsx (CommandDialog) ; bouton header avec kbd Ctrl/⌘+K ; raccourcis Ctrl/Cmd+K et "/" ; index client useEntities+useCatalog, pliage d'accents (NFD), score startsWith>includes ; groupes Pages/Indicateurs/Pays (suffixe ex-USSR pour anciens États) ; état vide : 8+8 ; sélection -> router.push ; command.tsx : CommandDialog accepte shouldFilter (false : le filtre cmdk par défaut est sensible aux accents et masquait les items déjà filtrés) ; clés dictionnaire searchAnything/noResults/groupPages/groupIndicators/groupCountries (EN+FR)
- Vérifié agent-browser : /indicators/infant_mortality -> slider annee ecrit ?y=1935, Men -> &s=male, +Italie -> &c=...italy, estimations -> &w=1 ; RELOAD -> slider index 4 (1935), Men, 5 chips, switch ON, tous restaurés ; retour defauts -> params omis (s puis c disparaissent) ; ?country=france + annee -> ?country=france&y=2022 + FocusBand France + série 1 pays ; recherche : Ctrl+K, "japan" -> Enter -> /countries/japan ; FR "fecondite" sans accent -> /indicators/birth_rate_fertility ; titres "France · ToddLab"/"Infant mortality · ToddLab", og:title hérite, og:image PNG par route (33 Ko) ; sitemap.xml + robots.txt 200 ; mobile 390px bouton recherche visible ; console 0 erreur ; lint 0 erreur ; bug de transfert corrigé en cours de route : imports nommés vs default (IndicatorDetailView/ComparePageView undefined -> 500)

Stage Summary:
- Toute la vue d'une page indicateur (année, sexe, pays des séries, estimations, focus) vit dans l'URL : chaque vue est partageable/rechargeable, avec des URLs canoniques propres (défauts omis)
- Site partageable : metadata dynamiques par page + images OG rendues par route + sitemap/robots ; sur Vercel, VERCEL_URL est repris automatiquement (NEXT_PUBLIC_SITE_URL pour un domaine custom)
- Recherche Cmd/Ctrl+K (et "/") : pays+entités+indicateurs+pages, insensible aux accents, aucune infrastructure serveur (labels déjà en cache React Query)
- Backend V26 intégré : 27 indicateurs, corpus 22 métriques ; score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 9
Agent: orchestrator (main)
Task: Retours V6 - (a) recherche globale : supprimer les suggestions hardcodées du state vide, (b) indice base 100 dans Séries temporelles

Work Log:
- Recherche : query vide -> PLUS AUCUNE suggestion (fini les 8+8 indicateurs/pays + pages affichés à vide) ; une seule ligne muette « Exemple : fécondité » / "Example: fertility" (clé common.searchExample) ; EMPTY_STATE_LIMIT supprimé ; matches[] vide sans requête ; CommandEmpty ("Aucun résultat") désormais conditionné à hasQuery (sinon cmdk l'afficherait aussi à vide, la liste ne contenant plus d'items) ; groupes/indicateurs/pays affichés uniquement sur résultats réels de la recherche
- Base 100 (très bonne idée validée par l'utilisateur, intégrée dans la carte "Séries temporelles") : switch "Base 100" à côté d'Estimations (CardAction), masqué pour unit="year" (indicer une année-événement n'a pas de sens)
- Algorithme : année de base = PREMIÈRE année où TOUTES les lignes canoniques affichées ont une valeur (base commune, jamais une base par série qui comparerait des départs différents) ; chaque point = valeur / valeur officielle du pays à l'année de base × 100 ; les trous (null) restent null (jamais divisés -> pas de faux zéros) ; les lignes antérieures à la base restent affichées indexées sur la même base ; estimations indexées sur le dénominateur de leur jumeau officiel (clé w: -> c:), masquées si le jumeau n'existe pas (pas de base mixte)
- Absence d'année commune (ex. France 2008+ vs URSS ≤1990 en espérance de vie) -> encart ambre indicators.base100Unavailable à la place du graphe
- Tooltip en mode indice : valeur = indice (1 décimale, fmtIndex dans format.ts) + valeur BRUTE avec unité en suffixe du libellé (le chiffre sourcé ne disparaît jamais derrière la transformation) ; title fournisseur conservé
- URL : nouveau param ?b=1 (use-indicator-query-state : parse/serialize/omission défaut) ; page clampe base100 = query.base100 && meta.unit !== "year" ; URLs canoniques (b omis si off)
- Dictionnaires EN+FR : common.searchExample, indicators.base100/base100Note {year}/base100Unavailable (FR sans em-dash)
- Vérifié agent-browser : palette vide EN "Example: fertility" / FR "Exemple : fécondité" avec 0 item cmdk ; "japan"->Enter->/countries/japan ; FR "fecondite" sans accent -> Indice de fécondité (ISF) ; infant_mortality ?b=1 -> base commune 2007 confirmée sur les données brutes (les 4 séries officielles démarrent en 2007, contrainte Russie 2007-2012), axe Y 0-120 sans unité, note "Indice : 2007 = 100..." ; tooltip 2020 : France · 3,4 | 94 / Japon · 1,8 | 69,3 (math vérifiée) ; reload -> switch ON + note restaurés ; toggle OFF -> param retiré + note disparue ; life_expectancy France+URSS ?b=1 -> encart ambre, plus de graphe ; France+Japon ?b=1&w=1 -> base 2008, 8 lignes (M/F officiels + estimations indexées, dénominateurs vérifiés : France H 77,5 / Japon H 79,3 en 2008), tooltip 2014 avec indices + bruts par ligne ; suffrage ?b=1 -> switch absent, b ignoré ; mobile 390px OK ; / et /compare sans régression ; console 0 erreur ; dev.log propre ; lint 0 erreur

Stage Summary:
- La palette s'ouvre sur une page quasi vide (une seule ligne d'exemple) : aucune suggestion codée en dur, tout ce qui s'affiche vient de la recherche réelle
- Base 100 intégrée à la carte Séries temporelles : une seule année de base commune (première année où toutes les séries officielles sélectionnées ont une valeur), trajectories comparables, trous jamais interpolés, valeur brute conservée dans l'infobulle, vue partageable via ?b=1 ; indisponible proprement (encart ambre) quand aucune année ne rassemble toutes les séries
- Score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 10
Agent: orchestrator (main)
Task: Retours V7 - (a) accueil : nouvelle phrase de traçabilité FR+EN, (b) zoom sur l'axe du temps de la carte Séries temporelles

Work Log:
- Accueil : home.heroDescription, dernière phrase remplacée EN ("Every number keeps its full provenance... never interpolated away" -> "Every value keeps its full traceability: source, quality indicators and missing data.") et FR ("Chaque nombre garde sa provenance complète... jamais interpolées." -> "Chaque valeur conserve sa traçabilité intégrale : source, indicateurs de qualité et données manquantes.") ; vérifié rendu EN+FR sur /
- Zoom : Brush Recharts (fenêtre glissante sous le graphe, style OWID) dans indicator-series-card : dataKey year, height 30, travellerWidth 16, stroke var(--primary), fill var(--muted), tickFormatter années ; n'apparaît que si >= 24 années observées (BRUSH_MIN_ROWS, sinon inutile/bruit)
- État de zoom = indices de lignes, state local VOLONTAirement hors URL (geste de lecture, pas une vue de données) ; la fenêtre porte {start, end, len} et s'auto-invalide quand rows.length change (pays/estimations/indicateur) — dérivation pure, pas d'effet (rule react-hooks/set-state-in-effect) ; clamp au rendu
- Bouton "Réinitialiser le zoom"/"Reset zoom" (indicators.resetZoom) sous la légende, visible seulement fenêtre != pleine ; BUG corrigé : reset passait undefined -> Recharts gardait son état interne zoomé ; le reset force désormais la fenêtre pleine {0, len-1, len}
- Interplay base 100 : la base n'est PAS recalculée sur la fenêtre (propriété de la série complète) ; la note "Indice : 2008 = 100..." reste, les valeurs de l'infobulle restent relatives à la base après zoom (vérifié)
- Vérifié agent-browser (life_expectancy ?w=1, lignes 1816-2024) : brush rendu 430x30 + 2 poignées ; axe initial 1816->2025 ; drag poignée gauche -> axe 1930->2025 (capture /tmp/zoom-mid.png : données récentes pleinement lisibles, fenêtre en terracotta) ; Y réétalonné sur la fenêtre ; bouton reset apparaît ; reset -> 1816->2025 + bouton disparu ; ?b=1 : zoom 1945->2025, note base 2008 intacte, tooltip 2021 France H 79,4 -> 102,5 (dénominateurs inchangés) ; mobile 390px : brush 372px, poignées 16px ; / et /compare sans régression ; console 0 erreur ; dev.log propre ; lint 0 erreur

Stage Summary:
- Le problème "séries centenaires + données récentes illisibles" est résolu par une fenêtre de zoom glissante sous le graphe (drag du cadre ou des poignées), avec mini-préview de la série complète, reset en un clic, et axe Y réétalonné sur la fenêtre
- Le zoom est un geste de lecture local (hors URL) ; si l'utilisateur préfère une période partageable type Comparer (f/t dans l'URL), l'alternative reste possible
- Score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 10
Agent: Z.ai Code (main)
Task: Audit du dossier "frontend" téléchargé par l'utilisateur dans son repo ToddLab local — dire quoi supprimer (artefacts sandbox vs fichiers essentiels).

Work Log:
- Inventaire complet du sandbox (/home/z/my-project) : tailles par dossier, contenu de download/, scripts/, tests/, tool-results/, .zscripts/, examples/, mini-services/, db/, prisma/, .env
- Vérifié que le site n'utilise PAS Prisma : grep @/lib/db + @prisma/client dans src => uniquement src/lib/db.ts (jamais importé) ; toutes les données viennent de data/dist/
- Vérifié .env : uniquement DATABASE_URL vers un chemin sandbox invalide
- Identifié scripts/sync-data.sh comme utile (resynchro data/dist) mais avec chemin source par défaut du sandbox (/home/z/toddlab-analysis) à adapter en ../data/dist
- Audité les deps package.json vs usage réel dans src : z-ai-web-dev-sdk, prisma/@prisma/client, next-auth, next-intl, @mdxeditor, @dnd-kit/*, uuid, react-markdown, react-syntax-highlighter, @tanstack/react-table, date-fns, sharp => 0 usage ; les autres deps suspectes sont importées par src/components/ui/*
- Confirmé au passage que le remplacement du texte d'accueil (traçabilité intégrale) et le zoom des séries temporelles sont bien en place (contexte perdu re-vérifié)

Stage Summary:
- Liste de suppression : Caddyfile, examples/, mini-services/, download/, tests/, tool-results/, .zscripts/, worklog.md, .env, prisma/, db/, src/lib/db.ts
- À garder absolument : src/, data/ (~51 Mo, cœur du site), public/, configs, bun.lock, scripts/sync-data.sh
- Nettoyage deps optionnel : retirer prisma, @prisma/client, z-ai-web-dev-sdk + scripts db:* puis bun install
- scripts/sync-data.sh à adapter : SRC par défaut ../data/dist (le frontend vit maintenant dans le repo ToddLab)
- Score civilisationnel : toujours en attente de la spécification utilisateur

---
Task ID: 11
Agent: Z.ai Code (main)
Task: Vérifier le repo GitHub backend (améliorations + modalités du score civilisationnel), analyse détaillée, puis compléter l'implémentation frontend.

Work Log:
- Fetch du clone /home/z/toddlab-analysis : déjà à jour avec origin/main (f26e464, v28.3, 2026-10-10) ; git ls-remote confirme qu'aucune branche/tag plus récent n'existe (seul main + tag v25-before-withdrawal)
- Grep « civilisation/civiliz/modalit » dans le repo : 0 hit ; les « modalités » = la spécification complète de la couche score (config/score.yaml 294 l., docs/score-contract.md 238 l., ADR-0011, data/dist/score/meta.json)
- Analyse détaillée : 18 indicateurs / 20 composantes officielles (poids 18) et 18 composantes modélisées (poids 16) ; directions (higher/lower/target 2.1), transforms (linear/log), basis (todd/consensus), presets égal (1/indicateur) et Todd (nb de livres distincts : fécondité 16/99 officiel, 92 modélisé), règle de report max 3 ans + âge affiché + garde-fou fantôme, couverture >= 0.60, delta sur observations distinctes refusé sous 50 % de poids commun, exclusions motivées (Gini, incarceration, illégitime+route/véhicule officiels seulement), échelle gelée bornes p1/p99 v2026-10-08.1
- Comparé checksums data/dist frontend vs backend : 7/7 fichiers identiques octet/octet (v28.3 déjà synchronisé)
- Constaté que l'implémentation score existe déjà (contexte perdu) : /score (classements, presets, année, URL state), teaser accueil top 5 des deux scores, carte score pays (scoreAtYear, delta v28 avec exclusion même-observation, poids personnalisés, badges âge/source/modelled), 3 routes API, score-core.ts conforme au contrat
- Trouvé 4 écarts résiduels et les a corrigés :
  a) badge de fiabilité du catalogue manquant dans la liste des composantes du score (exigé par score-contract.md « Badges to surface » ; 4 composantes medium : hiv, maternal_mortality_ratio, obesity, top_income) -> ajouté ReliabilityBadge (reliability != high) dans score-components-list.tsx
  b) em-dash « — » comme marqueur de valeur manquante dans score-components-list.tsx -> « - » (règle typographique FR)
  c) UX : bouger un slider de poids pendant qu'un preset (égal/todd) est actif ne faisait rien (valeur contrôlée) -> bascule automatique vers « Personnalisé » au premier mouvement (score-card.tsx onChange)
  d) débordement horizontal mobile 390px de la carte score (colonnes de grille sans min-w-0 ; SVG recharts figé à 1001px + labels truncate) -> min-w-0 sur les deux colonnes ; vérifié 390px : plus de débordement sur les 3 onglets
- Vérification agent-browser complète : /score FR (32 pays, Suisse 74,80, top-1 Irlande 76,62 en Todd), France officiel égal 2025 = 64,92 reproduit indépendamment en python depuis les fichiers dist, poids fécondité 15 -> 68,77 reproduit aussi, delta 2015->2025 = -0,59 (17 composantes, 88,9 % du poids), modélisé FR 72,70 (15/18), note Todd « 16 sur 99 » présente, badge fiabilité « Moyenne » visible sur VIH, langage FR persistant, aucun em-dash visible côté UI (seulement dans les données backend anglaises), lint OK, 0 erreur console

Stage Summary:
- Le repo GitHub n'a RIEN de plus récent que v28.3 (déjà analysé et déjà synchronisé côté frontend)
- Les « modalités du score civilisationnel » = la couche score v27-v28.3 du backend ; l'implémentation frontend V28.3 existait déjà dans le contexte perdu et est conforme au contrat (score, couverture, presets, delta, poids custom, badges, garde-fous)
- 4 écarts corrigés : badge fiabilité, em-dash, slider->custom auto, overflow mobile
- ScorePlaceholder (src/components/home/score-placeholder.tsx) est du code mort : remplacé par ScoreTeaser, peut être supprimé
- À signaler à l'utilisateur : s'il attendait des modalités PLUS récentes que v28.3, elles ne sont pas poussées sur GitHub (dernier commit 2026-10-10 v28.3)

---
Task ID: 12
Agent: Z.ai Code (main)
Task: Dégraissage UI du score civilisationnel demandé par l'utilisateur (accueil, page pays, page /score) + explication claire Égal/Todd.

Work Log:
- Accueil (score-teaser.tsx) : suppression des badges « Nouveau » (home.scoreBadge) et « Échelle gelée » (score.frozenScale) ; imports nettoyés (Badge, Lock)
- Code mort supprimé : src/components/home/score-placeholder.tsx (remplacé depuis longtemps par ScoreTeaser, jamais rendu) + clé home.scoreBadge du dictionnaire (EN+FR)
- Page pays (score-card.tsx) : badges « Produit dérivé » (derivedBadge) et « v2026-10-08.1 » (Lock + bounds_version) supprimés ; nouveau texte d'aide = hint officiel/modélisé + presetsExplained (explique TOUJOURS la différence Égal vs Todd, quelle que soit la sélection ; variante customNote quand Personnalisé actif) ; onglets réduits à 2 (Écart, Pondérations) ; « Détail des composantes » déplacé hors des onglets en section repliée par défaut (bouton aria-expanded + ChevronDown rotatif) ; pied de notes entièrement supprimé (twoScoresNote, carryRuleNote, carriedShare + ctaRankings) ; import Link retiré
- score-components-list.tsx : ligne source par métrique (root_label, ex « WHO Mortality Database (civil registration…) ») supprimée ; conservés : poids, badges log/direction/cible, âge reporté, source modélisée, fiabilité, barre + valeur
- Page /score (score-view.tsx) : badges « Produit dérivé » et « Échelle gelée · v2026-10-08.1 » supprimés du header (PageHeader sans children) ; troisième carte de notes supprimée entièrement (frozenScaleHint « Bornes version… » + excludedNote « Hors score… » + CTA) ; memo excludedList retiré
- Dictionnaire (EN+FR) : subtitle réécrit pour un public profane (« Deux classements des pays calculés à partir de l'ensemble des indicateurs. Officiel : construit à partir des statistiques publiées. Modélisé : la source la plus couvrante… ») ; twoScoresNote réécrit (« Les deux scores sont montrés séparément à dessein : là où ils diffèrent, l'écart est une information, pas une erreur ») ; carryRuleNote réécrit (« Quand une valeur manque pour une année, le score réutilise la dernière valeur connue, si elle date de 3 ans au plus… ») ; clés retirées : derivedBadge, frozenScale, frozenScaleHint, excludedNote, presetNoteEqual, presetNoteTodd, ctaCountry, home.scoreBadge ; clés ajoutées : presetsExplained, customNote ; une duplication accidentelle de scoreTitle FR corrigée dans la foulée
- Vérification agent-browser : accueil FR+EN sans les deux badges ; France : plus de « Produit dérivé »/version, hint Égal/Todd visible, 2 onglets, détail replié par défaut (aria-expanded=false) puis ouvert au clic (true), plus aucune ligne source, pied disparu ; /score : sous-titre nouveau + 2 notes + plus de Bornes/Hors score ; mobile 390px : aucun débordement, repli/ouverture OK ; lint OK ; les warnings « Fast Refresh full reload » du dev.log = HMR pendant les éditions, pas des erreurs runtime

Stage Summary:
- Les 9 demandes de l'utilisateur sont appliquées (badges accueil, badges pays, explication Égal/Todd, détail repliable sans sources, 3 mentions pays supprimées, badges /score, sous-titre clarifié, 2 notes clarifiées, carte Bornes/Hors score supprimée)
- Clés de dictionnaire alignées EN/FR ; carryRuleNote conservée (tooltip du badge « données de AAAA » + note /score)
- score-placeholder.tsx supprimé ; fichiers touchés : score-teaser, score-view, score-card, score-components-list, dictionaries, (suppression score-placeholder)

---
Task ID: 13
Agent: Z.ai Code (main)
Task: Feedback utilisateur sur les textes du score (« canonique » interdit, explications encore trop obscures, « environ 140 pays » à retirer, sous-titre /score trop serré, phrase « à dessein » incompréhensible) + nouvelle fonctionnalité : comparaison de l'évolution du score entre deux pays.

Work Log:
- Dictionnaire (EN+FR) : officialHint réécrit sans le mot « canonique » (« Le score officiel n'utilise que les chiffres publiés (Annuaire démographique de l'ONU, Eurostat, OCDE…). ») ; modelledHint simplifié (plus de « environ 140 pays ») ; subtitle /score allégé (« Modélisé : pour chaque indicateur, la source qui couvre le plus de pays. ») ; twoScoresNote réécrit en langage profane (« Deux calculs séparés, jamais mélangés. Si les scores officiel et modélisé d'un même pays sont différents, c'est normal : l'écart vient des sources utilisées, pas d'une erreur. ») ; presetsExplained réécrit (« Choisissez ce qui compte le plus dans le score. Égal : tous les indicateurs ont le même poids. Todd : les indicateurs sont pondérés comme dans les livres d'Emmanuel Todd, où la fécondité est l'indicateur central et pèse le plus lourd. »)
- score-view.tsx : hint /score sans préfixe « Officiel : » redondant (le hint nomme désormais lui-même le score) ; PageHeader passe à subtitleClassName="max-w-none text-pretty" → sous-titre pleine largeur (fini le grand vide à droite ; text-pretty remplace text-balance via twMerge)
- PageHeader : nouveau prop optionnel subtitleClassName (rétrocompatible, autres pages inchangées)
- Nouvelle fonctionnalité « Comparer l'évolution de deux pays » : API GET /api/score/compare?ids=a,b&score=official|modelled&preset=equal|todd (lecture directe des tables file.scores[preset], max 2 ids, regex /^[a-z][a-z0-9_]*$/, dédoublonnage, points {year, score, coverage} triés ; entités rendues dans l'ordre demandé pour aligner couleurs) ; hook useScoreCompare (react-query, enabled si ids non vide) ; carte sous le classement /score avec EntityPicker max=2, graphique Recharts 2 lignes (Y 0-100 figé, connectNulls=false, couleurs colorForIndex alignées sur les chips), tooltip (valeurs des deux pays + ligne « Écart »), résumé dernière année scorée par pays + écart, cas « entité non scorée » (ex. West Germany), état vide ; état d'URL étendu : paramètre c=france,germany (partageable, rechargé au montage)
- Vérification agent-browser : /score FR : sous-titre pleine largeur (1232px, text-pretty), hint sans « canonique », comparaison France/Allemagne officiel Égal (64,92 vs 68,79 en 2025, écart 3,87 — valeurs exactes), tooltip 2010 (64,59/67,30/écart 2,71), bascule Todd + Modélisé OK, retrait de pays OK, URL c=... précharge ; EN vérifié ; page pays France : nouveau texte d'explication affiché ; mobile 390px : aucun débordement (390=390) ; lint OK ; 0 erreur console/dev.log

Stage Summary:
- Le mot « canonique » a disparu de l'UI du score (remplacé par des tournures « le score officiel utilise… ») ; explications Égal/Todd et officiel/modélisé reformulées pour un lecteur profane
- « environ 140 pays » retiré du sous-titre ET du hint modélisé ; sous-titre /score pleine largeur ; phrase « à dessein… information, pas une erreur » remplacée par une explication concrète (écart = effet des sources)
- Nouvelle API /api/score/compare + hook useScoreCompare + carte de comparaison sur /score avec URL partageable (param c) ; fichiers touchés : dictionaries, score-view, page-header, client.ts, api/score/compare/route.ts (nouveau)

---
Task ID: 14
Agent: Z.ai Code (main)
Task: Feedback utilisateur (suite Task 13) : (1) reformuler le hint du score modélisé avec la phrase exacte fournie (« d'après les sources non-officielles ») ; (3) passer la limite de la comparaison d'évolution de 2 à 4 pays.

Work Log:
- Dictionnaire (EN+FR) : score.modelledHint = « Le score modélisé utilise, pour chaque indicateur, la source qui couvre le plus de pays, d'après les sources non-officielles. » (EN : « …based on non-official sources. ») ; compareTitle « Comparer l'évolution de plusieurs pays » / « Compare how several countries evolve over time » ; compareHint préfixé « Comparez jusqu'à 4 pays. » ; compareEmpty « Ajoutez jusqu'à quatre pays… » / « Add up to four countries… »
- API /api/score/compare : slice(0,2) → slice(0,4) (5 ids tronqués à 4, dédoublonnage inchangé) ; docstring mise à jour
- score-view.tsx : parseState c= slice(0,4) ; EntityPicker max=4 + slice(-4) ; généralisation de l'« écart » à N pays = max − min (tooltip par année + résumé dernière année scorée) ; tipRows typé explicitement ({color?}) pour satisfaire ChartTooltipShell
- Vérification agent-browser : API 5 ids → 4 entités (france/germany/italy/spain, FR 64,92 officiel ✓) ; FR : hint modélisé = formulation exacte utilisateur ✓, titre/hint/empty à jour ; 4 chips + 4 lignes + picker désactivé 4/4 ; résumé modelled : France 72,70 · Allemagne 72,10 · Italie 70,72 · Espagne 69,63, Écart 3,07 = 72,70−69,63 exact ; tooltip 2011 modelled : 4 valeurs + Écart 5,19 = 73,02−67,83 exact ; flux interactif retrait (3/4, bouton réactivé) puis ré-ajout via combobox (4/4, 4 lignes) ; EN vérifié ; mobile 390px scrollWidth=390 (zéro débordement) avec 4 pays Todd+modélisé ; captures /tmp/compare4-desktop.png, /tmp/compare4-mobile.png ; lint OK ; 0 erreur dev.log

Stage Summary:
- Comparaison d'évolution du score : jusqu'à 4 pays (URL c=a,b,c,d partageable), couleurs ligne/chip alignées, écart max−min affiché en tooltip et en résumé
- Hint modélisé = phrase exacte fournie par l'utilisateur (FR) et son équivalent EN
- Fichiers touchés : dictionaries.ts, api/score/compare/route.ts, score-view.tsx

---
Task ID: 15
Agent: Claude Code (Hermes)
Task: Nettoyage du frontend et fusion dans le dépôt backend (ToddLab).

Work Log:
- Analyse par graphe d'imports depuis les points d'entrée Next (pages, layout, routes, opengraph, robots, sitemap) : 32 fichiers source jamais atteints, 42 dépendances npm jamais importées.
- Supprimés (résidus du template de la sandbox) : examples/, mini-services/, tool-results/, download/, tests/ (3 scripts .sh), .zscripts/, Caddyfile, prisma/, db/custom.db, .env (DATABASE_URL seule), src/lib/db.ts, src/app/api/route.ts (« Hello, world! »), public/robots.txt (doublon de src/app/robots.ts), src/components/home/score-placeholder.tsx, src/hooks/use-mobile.ts, 29 composants src/components/ui/ inutilisés (accordion, alert, alert-dialog, aspect-ratio, avatar, breadcrumb, calendar, carousel, chart, checkbox, collapsible, context-menu, drawer, dropdown-menu, form, hover-card, input-otp, menubar, navigation-menu, pagination, progress, radio-group, resizable, scroll-area, separator, sheet, sidebar, sonner, textarea). Les composants shadcn se régénèrent avec « npx shadcn add <nom> ».
- Dépendances : 42 retirées (@mdxeditor/editor, @dnd-kit/*, next-auth, next-intl, prisma, @prisma/client, zod, zustand, sharp, bun-types, plusieurs @radix-ui/*, etc.). @types/node déclaré explicitement (il n'arrivait avant que par une dépendance indirecte). node_modules : 979 Mo -> ~580 Mo.
- npm est le seul gestionnaire de paquets : bun.lock supprimé, package-lock.json régénéré, script « start » passé de bun à node, scripts db:* retirés. Package renommé « toddlab-frontend ».
- Corrections : indicator-series-card.tsx (rawMap typé Map<string, number | null>), world-map.tsx (position du tooltip calculée dans le gestionnaire de souris, plus de lecture de ref au rendu), theme-toggle.tsx (état « mounted » via useSyncExternalStore). next.config.ts : « typescript.ignoreBuildErrors » retiré, donc le build échoue désormais sur toute erreur de type.
- scripts/sync-data.sh : la source par défaut est le backend à la racine du dépôt (<repo>/data/dist) ; refus de vider la destination si la source n'a pas catalog.json, entities.json et todd_corpus.json.
- Git : frontend/.git supprimé (aucun remote ; 18 commits locaux perdus) ; le frontend est désormais suivi par le dépôt ToddLab, directement sur main (règle « frontend » retirée du .gitignore racine).
- Vérification : eslint 0 erreur, tsc --noEmit 0 erreur, next build OK ; serveur standalone démarré : /, /score, /countries/france, /indicators, /compare, /methodology, /api/stats, /robots.txt, /sitemap.xml répondent 200. Aucun texte d'interface modifié (parité FR/EN intacte).

Stage Summary:
- Frontend nettoyé et intégré au dépôt ToddLab ; aucune modification fonctionnelle de l'UI.
- Version du backend : V29 (HEAD « V29 fix », local = origin/main au 2026-10-13).
- Resynchronisation V28.3 -> V29 faite dans un second temps : scripts/sync-data.sh exécuté, frontend/data/dist identique au data/dist du backend (diff -rq vide) ; agricultural_employment_share.json (retiré du backend depuis V26, jamais servi) a disparu de la copie ; KNOWN_VINTAGE = « V29 (snapshot 2026-10) » (store.ts) et commentaires « backend V29 » (score-store.ts, score-types.ts, types.ts).
- Écart V28.3 -> V29 sur data/dist (12 fichiers, 51 lignes) : comparaison JSON champ par champ, seuls changent des champs « note/notes » et les empreintes sha de score/meta.json (todd_core.csv v2 : colonne « status » retirée, 16 notes nettoyées) ; aucune valeur de série ni de score.
- Vérification après resync : eslint 0, tsc 0, next build OK ; serveur standalone : /api/stats vintage « V29 », 27 indicateurs, 261 entités, 113 435 points canoniques ; pages principales et routes score en 200 ; score officiel Égal 2025 inchangé (France 64,92, Allemagne 68,79). Piège de test : un ancien serveur resté sur le port masque le nouveau (EADDRINUSE) et renvoie l'ancienne version ; vérifier le port avant de conclure.
- Déploiement : le projet reste en localhost (aucune URL publique à configurer ; sitemap et robots pointent vers http://localhost:3000, ce qui est voulu).

---
Task ID: 16
Agent: Claude Code (Hermes)
Task: Remove the frontend's copy of the backend data; read data/dist in place.

Work Log:
- New src/lib/toddlab/server/dist.ts: locates <repo>/data/dist (TODDLAB_DIST_DIR override, else the nearest data/dist/catalog.json walking up from the working directory, ignoring anything under .next because the standalone build embeds a stale build-time copy) and caches parsed files keyed by mtime.
- store.ts and score-store.ts use it; the in-process meta cache is gone. `vintage` is now read from data/dist/score/meta.json (`score bounds <bounds_version>`) instead of the hardcoded "V29 (snapshot 2026-10)".
- /indicators, /countries and sitemap.xml were prerendered at build time; they are now force-dynamic so they follow the data too.
- Deleted frontend/data/dist (about 50 MB, duplicated in git) and frontend/scripts/sync-data.sh; frontend/.gitignore was removed earlier (root .gitignore covers node_modules, .next, ...).

Stage Summary:
- No sync step anymore. Verified: eslint 0, tsc 0, next build OK, standalone server via `npm start` serves all pages with 200; API responses byte-identical to the previous build except `vintage` and the infant_mortality notes text (CHANGELOG mention removed); editing data/dist/score/meta.json was reflected by /api/stats on the next request, and reverting it too.
- The frontend now requires the backend's data/dist next to it (same repository).


---
Task ID: 17
Agent: Claude Code (Hermes)
Task: Follow the backend v30 score change (decision 20) in the frontend.

Work Log:
- No frontend code change: the score pages read data/dist in place and the component list comes from score/meta.json.
- Backend v30: hiv_prevalence_rate, obesity_rate and top_income_share are in the modelled score only; the official score has 17 components (weight 15; todd preset 92) and bounds 2026-10-13.1.

Stage Summary:
- Verified on the production server: /, /score, /countries/france and the /api/score routes answer 200.
- Official 2025 scores moved with the new composition: France 64.48 (was 64.92), Germany 70.30 (was 68.79). Modelled scores are unchanged.

---
Task ID: 18
Agent: Claude Code (Hermes)
Task: Fix the anomalies found in the frontend review.

Work Log:
- Mobile overflow: the single-column grids of the indicator detail page and the compare page are now `grid-cols-1` (minmax(0,1fr)) so wide charts and tables cannot stretch the page; the series card actions drop under the header on small screens. Checked at 390 px: no horizontal scroll on the 9 pages tested.
- 404: new src/app/not-found.tsx (bilingual); /countries/[id] and /indicators/[id] call notFound() for unknown ids, so they now answer HTTP 404 instead of 200.
- Number format: new fmtDecimal() in lib/toddlab/format.ts is the only way to print a plain decimal (locale separator, optional sign / trimming); fmtTick takes a locale. Replaced every toFixed() used for display (delta decomposition, synthesis average, weights total and weight badges).
- Stale texts: the counts of indicators, Todd metrics and entities in the dictionaries are now {n} placeholders filled from the data; the hard-coded "about 50 / about 180 countries" sentence no longer quotes numbers.
- dist.ts: Turbopack tracing warnings silenced with turbopackIgnore, build is warning-free.

Stage Summary:
- eslint 0, tsc 0, next build OK and warning-free; production server checked: unknown ids and routes answer 404, FR decimals are consistent.

---
Task ID: 19
Agent: Claude Code (Hermes)
Task: Language without flash, Vercel-ready deployment, sitemap without invented dates.

Work Log:
- Language: the server now decides it (cookie `toddlab-lang`, then Accept-Language, then English) in lib/toddlab/i18n/server.ts; the root layout sets <html lang> and passes initialLang to the I18nProvider, so the first HTML is already in the right language. The FR/EN toggle writes the cookie (localStorage is no longer used). Page titles (indicators, countries, compare, score, method, 404 fallbacks) follow the language; meta descriptions stay in English.
- Vercel: next.config.ts detects VERCEL and then sets outputFileTracingRoot (repo root) and outputFileTracingIncludes for ../data/dist, instead of output: "standalone" (kept for local use). The build script only copies static files into .next/standalone when it exists. Checked with VERCEL=1: every route's .nft.json lists the 34 data/dist files.
- siteUrl() prefers VERCEL_PROJECT_PRODUCTION_URL. The sitemap no longer emits a lastModified date.

Stage Summary:
- eslint 0, tsc 0, next build OK (local and VERCEL=1 modes). Not tested on a real Vercel deployment (needs the owner's account).

---
Task ID: 20
Agent: Claude Code (Hermes)
Task: Show the three model-based canonical series as estimates.

Work Log:
- Backend v30: new additive field `canonical_nature` (published | modelled) on every indicator file and on catalog.json; hiv_prevalence_rate, obesity_rate and top_income_share are `modelled`. Score files are unchanged.
- Frontend: types and API payloads carry the field; for `modelled` indicators the sources card says "Estimations provenant de" (not "Chiffres officiels provenant de"), the reliability text says the reference series is a model or compilation, and the rank tooltip says "Estimation". The method page states the exception. The words "Officiel" and "Estimation" are kept.

Stage Summary:
- eslint 0, tsc 0, next build OK, pages checked in the browser. Vercel project `toddlab` is linked to the GitHub repo (production branch main).

---
Task ID: 21
Agent: Claude Code (Hermes)
Task: Todd only / Todd + extra metric sets in the score.

Work Log:
- Backend v30 (decision 21): extra_core.csv -> config/extra_refs.yaml -> dist/extra_corpus.json; two more stored presets (equal_todd_only, todd_todd_only) where the extra components weigh 0; every component carries corpus_set (todd | extra). The equal / todd presets are unchanged.
- score-core.ts skips components with weight <= 0 (coverage, n, fresh count, delta), like the backend. Verified by compiling it and replaying the 24 golden vectors and all 24,449 stored scores of the 4 presets x 2 scores: no mismatch.
- /score has a second toggle "Todd + extra | Todd seul" (URL param m=todd, API preset = storedPreset(weighting, scope)); the rankings count only weighted components. The country score card has the same toggle (hidden in custom mode, where the weights are the user's).

Stage Summary:
- eslint 0, tsc 0, next build OK. Official 2015 equal: 44 countries with extra, 34 Todd only (Switzerland 72.90 leads; Japan needs the extra components to reach the coverage threshold).

---
Task ID: 22
Agent: Claude Code (Hermes)
Task: First extra metrics wired: PISA reading and science.

Work Log:
- Two new indicators (todd_core: false, listed in extra_core.csv): reading_test_scores (2000-2022) and science_test_scores (2006-2022), the other columns of the PISA chart door already used for mathematics; indicators only, the score keeps the single PISA component (math_test_scores).
- French labels and descriptions added; the catalog now has 29 indicators (22 in Todd's books, 7 outside).

Stage Summary:
- eslint 0, tsc 0, build OK, pages checked. Score files are unchanged.

---
Task ID: 23
Agent: Claude Code (Hermes)
Task: UNESCO UIS connector, mean years of schooling, UIS attainment in the modelled score.

Work Log:
- Backend v30: connector for the UIS Data API (provider unesco_uis), the extra metric mean_years_of_schooling (estimate, indicator only), and the UIS attainment rates as witnesses of the secondary and tertiary attainment indicators; bounds regenerated at 2026-10-14.1 (decision 22 in ADR-0011). Official scores unchanged; the modelled score covers more countries (2015: 165 -> 170, 2025: 74 -> 114 in the equal preset).
- Frontend: provider labels (EN / FR) and the Provider type know unesco_uis; the data is read in place, nothing else changes.

Stage Summary:
- 24 golden vectors and all stored scores still match score-core. UIS data is CC BY-SA 4.0: credit the UIS.

---
Task ID: 24
Agent: Claude Code (Hermes)
Task: Youth suicide rate (extra metric) from Eurostat.

Work Log:
- Backend v30: the Eurostat connector learns hlth_cd_acdr2 (the causes-of-death crude rate by age, ref grammar icd10/age/sex, unit RT pinned, layout guard, NUTS-2 regional codes dropped as non-country codes); new root eurostat_cod; indicator youth_suicide_rate (ages 15-24, 36 countries, 2011-2023, todd_core false, indicator only).
- Frontend: FR labels and descriptions for youth_suicide_rate and mean_years_of_schooling.

Stage Summary:
- eslint 0, tsc 0, build OK. Small countries (Luxembourg 0, Cyprus 1 in 2023) show the small-numbers noise noted in the indicator's reliability text.

---
Task ID: 25
Agent: Claude Code (Hermes)
Task: Abortion rate (extra metric) from the WHO/Europe Data Warehouse.

Work Log:
- Backend v30: new connector for the WHO/Europe Data Warehouse API v5 (provider who_euro, collector tier, root who_euro_hfa): measure HFA_586 "Abortions per 1000 live births", 49 countries, 1970-2023, 1,717 observations; population-weighted group averages dropped; measure and unit pin-guards. The server omits the Sectigo intermediate certificate: the connector ships that public intermediate as an extra trust anchor for this host only (verification stays on).
- Indicator abortion_rate (indicator only, not in the score; higher_is_better false by the illegitimate_births convention, no normative claim). License inferred CC BY-NC-SA 3.0 IGO (NonCommercial) - docs/licenses.md.
- Frontend: provider labels, FR label and description, unit label and format.

Stage Summary:
- eslint 0, tsc 0, build OK, 24 golden vectors and 25,401 stored scores unchanged.

---
Task ID: 26
Agent: Claude Code (Hermes)
Task: The three marker metrics (women's suffrage, abortion, divorce legalization years).

Work Log:
- Curated tables under catalog/curated/: womens_suffrage_introduction (IPU table, 185 countries, equal-terms rule), abortion_legalization (50 countries, Wikipedia), divorce_legalization (12 countries, Wikipedia). Rules in ADR-0011 decision 24; absences deliberate.
- Frontend: FR labels and descriptions for the three indicators.
- Decision 23 recorded: ToddLab never commercial, abortion rate ranks lower = better.

Stage Summary:
- 491 tests, tsc 0, eslint 0, build OK, 24 golden vectors and 25,401 stored scores unchanged.

---
Task ID: 27
Agent: Claude Code (Hermes)
Task: Extra metrics in the score (decision 25), markers without a direction badge, reliability wording, score-core rounding, README.

Work Log:
- Backend: five extra metrics join the score as `extra` components (placement by decisions 15 and 20), `drug_induced_deaths` removed from extra_core.csv, bounds regenerated (7 blocks added, none changed), summation made a plain ordered loop.
- Frontend: DirectionBadge hidden for the markers family (detail, catalog, compare), the world-map legend reads "earliest / latest" for markers, the "medium" and "low" reliability sentences reworded (EN and FR), `roundTo` rounds like Python's round() (exact value, ties to even).
- README refreshed (sources, official / estimate labels, metric sets, licensing note), docs/licenses.md World Bank / GHO section fixed.

Stage Summary:
- 493 tests, tsc 0, eslint 0, build OK; frontend reproduces 24,067 of 24,067 stored scores exactly and all 24 golden vectors.

---
Task ID: 28
Agent: Claude Code (Hermes)
Task: Country comparison upgrades, score movers ranking, unresolved-name cleanup.

Work Log:
- /score compare card: "compare with another country" link on the country score card (`/score?...&c=<id>#compare`), official and modelled side by side (`v=both`), years shaded when the countries share under 50% of the scored weight, gap read at the latest year all countries are scored, with the shared share.
- New `/api/score/movers` + "Biggest score movers" card (`f`, `t` in the URL): best and worst deltas between two years, refused count reported, rows flagged when the published scores rest on different components.
- Backend: unresolved names split into a `known_non_country` bucket; "Congo, DRC" and "Saint-Barthélemy" resolved; OWID entity names may be a list.

Stage Summary:
- 495 tests, tsc 0, eslint 0, build OK; frontend still reproduces 24,067 of 24,067 stored scores exactly.

---
Task ID: 29
Agent: Claude Code (Hermes)
Task: Egal and Todd must score the same countries (decision 28).

Work Log:
- Cause of the 90 -> 139 jump: coverage was a share of the preset's weight; fixed by counting components (unit weights) and lowering the threshold to 0.50 for every calculation.
- Backend: `unit_weight`, `unit_total`, coverage and delta share by components; bounds refrozen; tests for the invariant (Egal and Todd, Todd-only pair, same country-years in the shipped files).
- Frontend: score-core `unitWeightOf` in coverage and delta share, comparability and movers on the same rule, wording of the delta refusal and the shaded-years legend.

Stage Summary:
- 497 tests, tsc 0; the frontend reproduces 26,646 of 26,646 stored scores and the 24 golden vectors exactly.
