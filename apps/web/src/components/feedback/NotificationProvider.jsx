import { Alert, Snackbar } from '@mui/material'
import { useMemo, useState } from 'react'
import { NotificationContext } from './notificationContext'
export function NotificationProvider({ children }) {
  const [notification, setNotification] = useState(null)
  const value = useMemo(
    () => ({
      notify: (message, severity = 'info') =>
        setNotification({ message, severity }),
    }),
    [],
  )
  return (
    <NotificationContext.Provider value={value}>
      {children}
      <Snackbar
        open={Boolean(notification)}
        autoHideDuration={4500}
        onClose={() => setNotification(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        {notification ? (
          <Alert
            severity={notification.severity}
            variant="filled"
            onClose={() => setNotification(null)}
          >
            {notification.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </NotificationContext.Provider>
  )
}
