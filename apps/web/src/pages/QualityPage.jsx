import AssessmentOutlinedIcon from '@mui/icons-material/AssessmentOutlined'
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import { Alert, Box, Button, Chip, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { PageHeader } from '../components/common/PageHeader'
import { EmptyState } from '../components/common/EmptyState'
import { ErrorState } from '../components/common/ErrorState'
import { PageSkeleton } from '../components/common/LoadingSkeletons'
import { EvaluationKpis } from '../components/quality/EvaluationKpis'
import { GroundTruthAccuracy } from '../components/quality/GroundTruthAccuracy'
import { CoverageAnalytics } from '../components/quality/CoverageAnalytics'
import { BatchHealth } from '../components/quality/BatchHealth'
import { DescriptionCompliance } from '../components/quality/DescriptionCompliance'
import { ReviewAnalysis } from '../components/quality/ReviewAnalysis'
import { FieldGroupPerformance } from '../components/quality/FieldGroupPerformance'
import { ProblemFields } from '../components/quality/ProblemFields'
import { ImprovementOpportunities } from '../components/quality/ImprovementOpportunities'
import { LabelledRowComparison } from '../components/quality/LabelledRowComparison'
import { ClassificationCoverage } from '../components/quality/ClassificationCoverage'
import { AttributeCoverage } from '../components/quality/AttributeCoverage'
import { IdentityResolutionCoverage } from '../components/quality/IdentityResolutionCoverage'
import {
  useCreateUnilogEvaluation,
  useLatestUnilogEvaluation,
  useUnilogLabelledComparison,
} from '../hooks/useUnilogEvaluation'

export function QualityPage({
  state: forcedState,
  data: forcedData,
  comparisonData,
  requestId,
  onRetry,
}) {
  const live = useLatestUnilogEvaluation({ enabled: forcedState == null })
  const create = useCreateUnilogEvaluation()
  const data = forcedData ?? live.data
  const [selectedId, setSelectedId] = useState(null)
  useEffect(() => {
    if (!selectedId && data?.labelledRows?.length)
      setSelectedId(data.labelledRows[0].inputRowId)
  }, [data, selectedId])
  const comparison = useUnilogLabelledComparison(
    data?.evaluationId,
    selectedId,
    {
      enabled: forcedState == null && !comparisonData,
    },
  )
  const state =
    forcedState ??
    (live.isPending
      ? 'loading'
      : live.error?.status === 404
        ? 'empty'
        : live.isError
          ? 'error'
          : 'ready')

  if (state === 'loading') return <PageSkeleton />
  if (state === 'empty') {
    return (
      <EmptyState
        title="No challenge evaluation yet"
        description="Run the Unilog evaluation pipeline to measure the latest enrichment results."
        actionLabel={
          create.isPending ? 'Running evaluation…' : 'Run Evaluation'
        }
        onAction={() => create.mutate()}
        icon={<AssessmentOutlinedIcon />}
      />
    )
  }
  if (state === 'error') {
    return (
      <ErrorState
        title="We couldn't load challenge quality."
        requestId={requestId ?? live.error?.requestId}
        onRetry={onRetry ?? (() => live.refetch())}
      />
    )
  }
  if (!data) return null

  return (
    <Stack spacing={7}>
      <PageHeader
        title="Challenge Quality"
        subtitle="Measure enrichment accuracy, coverage, confidence, and delivery-format compliance."
        status={
          <Chip
            label="Evaluation policy v1"
            color="primary"
            variant="outlined"
          />
        }
        actions={
          <Button
            startIcon={<PlayArrowRoundedIcon />}
            variant="outlined"
            onClick={() => create.mutate()}
            disabled={create.isPending}
          >
            Re-run evaluation
          </Button>
        }
      />
      <Alert severity="info" icon={<AssessmentOutlinedIcon />}>
        <Typography fontWeight={720}>Evaluation context</Typography>
        Ground-truth accuracy is based on{' '}
        <strong>{data.labelledRowCount} officially labelled products</strong>.
        Batch quality metrics cover all{' '}
        <strong>
          {data.batchMetrics.totalRows.toLocaleString()} challenge input rows
        </strong>{' '}
        and do not measure correctness.
      </Alert>
      <Box
        sx={{
          p: { xs: 4, md: 5 },
          borderRadius: 4,
          color: 'common.white',
          background:
            'linear-gradient(125deg, #0f172a 0%, #312e81 62%, #4f46e5 100%)',
        }}
      >
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          justifyContent="space-between"
          gap={5}
        >
          <Stack spacing={1.5}>
            <Typography
              variant="overline"
              sx={{ color: 'rgba(255,255,255,.7)' }}
            >
              Unilog Challenge Evaluation
            </Typography>
            <Typography component="h2" variant="h2">
              Trustworthy metrics at challenge scale
            </Typography>
            <Typography sx={{ color: 'rgba(255,255,255,.72)' }}>
              Evaluation generated {new Date(data.createdAt).toLocaleString()} ·
              Policy: {data.policyVersion}
            </Typography>
          </Stack>
          <Stack direction="row" flexWrap="wrap" gap={4} alignItems="center">
            <HeroStat
              value={data.batchMetrics.totalRows.toLocaleString()}
              label="Input products"
            />
            <HeroStat value="252" label="Delivery columns" />
            <HeroStat
              value={String(data.labelledRowCount)}
              label="Official labels"
            />
          </Stack>
        </Stack>
      </Box>
      <EvaluationKpis data={data} />
      <Box sx={twoColumn}>
        <GroundTruthAccuracy
          accuracy={data.accuracy}
          labelledRowCount={data.labelledRowCount}
        />
        <BatchHealth batch={data.batchMetrics} />
      </Box>
      <Box sx={twoColumn}>
        <CoverageAnalytics coverage={data.coverageMetrics} />
        <ReviewAnalysis metrics={data.reviewMetrics} />
      </Box>
      <IdentityResolutionCoverage metrics={data.identityResolutionMetrics} />
      <ClassificationCoverage metrics={data.classificationMetrics} />
      <AttributeCoverage
        coverage={data.attributeCoverageMetrics}
        accuracy={data.attributeMetrics}
      />
      <Box sx={twoColumn}>
        <DescriptionCompliance metrics={data.descriptionMetrics} />
        <FieldGroupPerformance groups={data.groupMetrics} />
      </Box>
      <Box sx={twoColumn}>
        <ProblemFields
          problems={data.problems}
          blankFields={data.coverageMetrics.mostBlankSupportedFields}
        />
        <ImprovementOpportunities recommendations={data.recommendations} />
      </Box>
      <LabelledRowComparison
        rows={data.labelledRows}
        selectedId={selectedId}
        onSelect={setSelectedId}
        comparison={comparisonData ?? comparison.data}
        loading={!comparisonData && comparison.isPending}
      />
    </Stack>
  )
}

const twoColumn = {
  display: 'grid',
  gridTemplateColumns: {
    xs: 'minmax(0, 1fr)',
    lg: 'minmax(0, 1.12fr) minmax(0, .88fr)',
  },
  gap: 4,
  alignItems: 'start',
}

function HeroStat({ value, label }) {
  return (
    <Stack minWidth={90}>
      <Typography variant="h2">{value}</Typography>
      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,.7)' }}>
        {label}
      </Typography>
    </Stack>
  )
}
