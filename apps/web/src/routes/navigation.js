import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined'
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined'
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined'
import IosShareOutlinedIcon from '@mui/icons-material/IosShareOutlined'
import RouteOutlinedIcon from '@mui/icons-material/RouteOutlined'
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined'
import WorkspacePremiumOutlinedIcon from '@mui/icons-material/WorkspacePremiumOutlined'
export const navigationSections = [
  {
    label: null,
    items: [
      { label: 'Overview', href: '/dashboard', icon: DashboardOutlinedIcon },
      { label: 'Products', href: '/products', icon: Inventory2OutlinedIcon },
      { label: 'Workflows', href: '/workflows', icon: RouteOutlinedIcon },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      {
        label: 'Quality',
        href: '/quality',
        icon: WorkspacePremiumOutlinedIcon,
      },
      {
        label: 'AI Enrichment',
        href: '/ai-enrichment',
        icon: AutoAwesomeOutlinedIcon,
      },
    ],
  },
  {
    label: 'Outputs',
    items: [{ label: 'Exports', href: '/exports', icon: IosShareOutlinedIcon }],
  },
  {
    label: 'System',
    items: [
      { label: 'Settings', href: '/settings', icon: SettingsOutlinedIcon },
    ],
  },
]
