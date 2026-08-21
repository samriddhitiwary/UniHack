import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import { EmptyState } from './EmptyState'
import { TableSkeleton } from './LoadingSkeletons'

export function DataTableShell({
  columns,
  rows,
  loading = false,
  emptyTitle = 'No records yet',
  emptyDescription = 'Records will appear here when they are available.',
  pagination,
  getRowKey = (row) => row.id,
  onRowActivate,
}) {
  return (
    <Box>
      {loading ? (
        <TableSkeleton />
      ) : rows.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <TableContainer>
          <Table aria-label="Data table">
            <TableHead>
              <TableRow>
                {columns.map((column) => (
                  <TableCell
                    key={column.key}
                    align={column.align}
                    sx={column.sx}
                  >
                    {column.label}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow
                  key={getRowKey(row)}
                  hover
                  tabIndex={onRowActivate ? 0 : undefined}
                  onClick={() => onRowActivate?.(row)}
                  onKeyDown={(event) => {
                    if (
                      onRowActivate &&
                      (event.key === 'Enter' || event.key === ' ')
                    ) {
                      event.preventDefault()
                      onRowActivate(row)
                    }
                  }}
                  aria-label={onRowActivate ? `Open ${row.name}` : undefined}
                  sx={{
                    '&:last-child td': { borderBottom: 0 },
                    ...(onRowActivate && {
                      cursor: 'pointer',
                      '&:focus-visible': {
                        outline: '3px solid',
                        outlineColor: 'primary.light',
                        outlineOffset: -3,
                      },
                    }),
                  }}
                >
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      align={column.align}
                      sx={column.sx}
                    >
                      {column.render ? column.render(row) : row[column.key]}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {pagination && (
        <Box sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
          {pagination}
        </Box>
      )}
    </Box>
  )
}
