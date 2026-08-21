const definitions = [
  {
    id: 'analyze',
    label: 'Analyze Sources',
    description: 'Read and extract information from product evidence.',
    stages: ['SOURCE_PROCESSING'],
  },
  {
    id: 'understand',
    label: 'Understand Product',
    description: 'Determine the industrial product category.',
    stages: ['PRODUCT_CLASSIFICATION'],
  },
  {
    id: 'structure',
    label: 'Structure Attributes',
    description: 'Extract and normalize canonical specifications.',
    stages: ['ATTRIBUTE_EXTRACTION', 'ATTRIBUTE_NORMALIZATION'],
  },
  {
    id: 'validate',
    label: 'Validate Catalog',
    description: 'Check agreement, completeness, rules, and candidate quality.',
    stages: [
      'CONFLICT_DETECTION',
      'COMPLETENESS',
      'ATTRIBUTE_VALIDATION',
      'ATTRIBUTE_SELECTION',
    ],
  },
  {
    id: 'review',
    label: 'Human Review',
    description: 'Confirm proposed attributes before final materialization.',
    stages: ['HUMAN_REVIEW'],
  },
  {
    id: 'prepare',
    label: 'Prepare Catalog',
    description: 'Build the reviewed catalog and evaluate readiness.',
    stages: [
      'REVIEWED_ATTRIBUTE_MATERIALIZATION',
      'CATALOG_PROJECTION',
      'PUBLISHING_READINESS',
    ],
  },
  {
    id: 'outputs',
    label: 'Generate Outputs',
    description: 'Prepare export artifacts and grounded commerce content.',
    stages: ['CATALOG_EXPORT', 'AI_ENRICHMENT'],
  },
  {
    id: 'quality',
    label: 'Quality Evaluation',
    description: 'Calculate the Product Intelligence Score.',
    stages: ['PRODUCT_INTELLIGENCE_SCORE'],
  },
]

function aggregate(stages) {
  const statuses = stages.map((stage) => stage.status)
  if (statuses.includes('FAILED')) return 'FAILED'
  if (statuses.includes('RUNNING')) return 'RUNNING'
  if (statuses.includes('WAITING')) return 'WAITING'
  if (statuses.every((status) => status === 'COMPLETED')) return 'COMPLETED'
  if (statuses.every((status) => status === 'SKIPPED')) return 'SKIPPED'
  return 'NOT_STARTED'
}

export function buildWorkflowPhases(stages = []) {
  const byName = new Map(stages.map((stage) => [stage.stage, stage]))
  return definitions.map((phase) => {
    const children = phase.stages
      .map((name) => byName.get(name))
      .filter(Boolean)
    return {
      ...phase,
      status: children.length ? aggregate(children) : 'NOT_STARTED',
      children,
    }
  })
}
