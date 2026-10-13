/**
 * Short, plain-language descriptions per indicator (shown at the top of each
 * indicator page) + human-readable provider names.
 * Backend stays English-only (ADR-0002) — these translations live in the frontend.
 */

export const INDICATOR_DESCRIPTIONS: Record<string, { en: string; fr: string }> = {
  agricultural_employment_share: {
    en: "Share of the workforce employed in agriculture. A classic marker of where a society stands in its industrial transition.",
    fr: "Part de la main-d'œuvre employée dans l'agriculture. Un marqueur classique de la position d'une société dans sa transition industrielle.",
  },
  birth_rate_fertility: {
    en: "Average number of children a woman would have over her lifetime at current rates.",
    fr: "Nombre moyen d'enfants qu'aurait une femme au cours de sa vie aux taux actuels.",
  },
  cirrhosis_alcohol_mortality: {
    en: "Deaths from liver cirrhosis per 100,000 people — a hard proxy for the weight of alcohol in a society.",
    fr: "Décès par cirrhose du foie pour 100 000 habitants : un indicateur dur du poids de l'alcool dans une société.",
  },
  consanguineous_marriage_rate: {
    en: "Share of marriages between close relatives (most often cousins). A structural marker of family systems.",
    fr: "Part des mariages entre proches parents (le plus souvent cousins). Un marqueur structurel des systèmes familiaux.",
  },
  crude_birth_rate: {
    en: "Live births per 1,000 inhabitants each year.",
    fr: "Naissances vivantes pour 1 000 habitants chaque année.",
  },
  gini_index: {
    en: "Income inequality, from 0 (perfect equality) to 100 (one person holds everything).",
    fr: "Inégalités de revenu, de 0 (égalité parfaite) à 100 (une seule personne concentre tout).",
  },
  hiv_prevalence_rate: {
    en: "Share of adults aged 15-49 living with HIV.",
    fr: "Part des adultes de 15 à 49 ans vivant avec le VIH.",
  },
  homicide_rate: {
    en: "Intentional homicides per 100,000 people — deaths recorded by police and health services, not opinions.",
    fr: "Homicides volontaires pour 100 000 habitants : des décès enregistrés par la police et les services de santé, pas des opinions.",
  },
  illegitimate_births: {
    en: "Share of births outside marriage. One of Todd's key markers of family-structure change.",
    fr: "Part des naissances hors mariage. L'un des marqueurs clés de Todd sur l'évolution des structures familiales.",
  },
  immigration_stock: {
    en: "Number of people living outside their country of birth.",
    fr: "Nombre de personnes vivant hors de leur pays de naissance.",
  },
  incarceration_rate: {
    en: "People in prison per 100,000 inhabitants.",
    fr: "Personnes emprisonnées pour 100 000 habitants.",
  },
  industrial_employment_share: {
    en: "Share of the workforce employed in industry. The rise and fall of this curve traces a society's industrial age.",
    fr: "Part de la main-d'œuvre employée dans l'industrie. La montée puis le déclin de cette courbe trace l'ère industrielle d'une société.",
  },
  infant_mortality: {
    en: "Babies who die before their first birthday, per 1,000 live births. The indicator behind Todd's 1976 prediction of the Soviet collapse.",
    fr: "Bébés qui décèdent avant leur premier anniversaire, pour 1 000 naissances vivantes. L'indicateur qui a fondé la prédiction de Todd sur l'effondrement soviétique en 1976.",
  },
  life_expectancy: {
    en: "Average number of years a newborn would live at current death rates.",
    fr: "Nombre moyen d'années qu'un nouveau-né vivrait aux taux de mortalité actuels.",
  },
  life_expectancy_60: {
    en: "Average number of years a 60-year-old can expect to live.",
    fr: "Nombre moyen d'années qu'une personne de 60 ans peut encore espérer vivre.",
  },
  male_height_trend: {
    en: "Average height of men by birth cohort. Height records what people ate and how they lived as children.",
    fr: "Taille moyenne des hommes par cohorte de naissance. La taille enregistre ce que les gens ont mangé et comment ils ont vécu pendant leur enfance.",
  },
  maternal_deaths: {
    en: "Number of women who die from causes linked to pregnancy or childbirth.",
    fr: "Nombre de femmes qui décèdent de causes liées à la grossesse ou à l'accouchement.",
  },
  maternal_mortality_ratio: {
    en: "Maternal deaths per 100,000 live births.",
    fr: "Décès maternels pour 100 000 naissances vivantes.",
  },
  math_test_scores: {
    en: "Average score of 15-year-olds on the OECD PISA mathematics test.",
    fr: "Score moyen des élèves de 15 ans au test PISA de mathématiques de l'OCDE.",
  },
  obesity_rate: {
    en: "Share of adults with a body mass index of 30 or more.",
    fr: "Part des adultes dont l'indice de masse corporelle est de 30 ou plus.",
  },
  road_accident_mortality: {
    en: "Road traffic deaths per 100,000 inhabitants.",
    fr: "Décès sur les routes pour 100 000 habitants.",
  },
  road_accident_mortality_per_vehicle: {
    en: "Road deaths per 10,000 motor vehicles: measures the safety of mobility, not just exposure.",
    fr: "Décès routiers pour 10 000 véhicules motorisés : mesure la sécurité des déplacements, pas seulement l'exposition.",
  },
  same_sex_marriage_legalization_year: {
    en: "Year same-sex marriage became legal, where it has been enacted.",
    fr: "Année de légalisation du mariage entre personnes de même sexe, là où il a été adopté.",
  },
  secondary_education_share: {
    en: "Share of the population that completed secondary education.",
    fr: "Part de la population ayant terminé l'enseignement secondaire.",
  },
  suicide_rate: {
    en: "Suicide deaths per 100,000 people.",
    fr: "Décès par suicide pour 100 000 habitants.",
  },
  tertiary_education_share: {
    en: "Share of the population that completed higher education.",
    fr: "Part de la population ayant terminé l'enseignement supérieur.",
  },
  top_income_share: {
    en: "Pre-tax income held by the richest 1%.",
    fr: "Part du revenu pré-impôt détenue par les 1 % les plus riches.",
  },
  unemployment_rate: {
    en: "Share of the labour force without work but available and looking for one.",
    fr: "Part de la population active sans emploi, disponible et en recherche d'un.",
  },
  universal_suffrage_introduction_year: {
    en: "Year universal suffrage was introduced, as enacted by law.",
    fr: "Année d'introduction du suffrage universel, telle qu'inscrite dans la loi.",
  },
};

/* ------------------------------ Provider names ------------------------------ */

export const PROVIDER_LABELS_EN: Record<string, string> = {
  owid: "Our World in Data",
  worldbank: "World Bank",
  who_gho: "WHO Global Health Observatory",
  un_dyb: "UN Demographic Yearbook",
  curated: "ToddLab curated tables",
  oecd: "OECD",
  eurostat: "Eurostat",
  ilostat: "ILOSTAT",
};

export const PROVIDER_LABELS_FR: Record<string, string> = {
  owid: "Our World in Data",
  worldbank: "Banque mondiale",
  who_gho: "OMS (Observatoire mondial de la santé)",
  un_dyb: "Annuaire démographique de l'ONU",
  curated: "Tables vérifiées ToddLab",
  oecd: "OCDE",
  eurostat: "Eurostat",
  ilostat: "ILOSTAT",
};
