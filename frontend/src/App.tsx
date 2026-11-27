import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import AppLayout from './components/layout/AppLayout'
import AssistantPage from './pages/AssistantPage'
import DashboardPage from './pages/DashboardPage'
import DocumentReviewPage from './pages/document-review/DocumentReviewPage'
import DocumentsPage from './pages/DocumentsPage'
import LandingPage from './pages/landing/LandingPage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import NotificationsPage from './pages/NotificationsPage'
import SettingsPage from './pages/settings/SettingsPage'
import SubmitPage from './pages/submit/SubmitPage'

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <AppLayout />,
    children: [
      { path: '/dashboard', element: <DashboardPage /> },
      { path: '/documents', element: <DocumentsPage /> },
      { path: '/documents/:docId', element: <DocumentReviewPage /> },
      { path: '/submit', element: <SubmitPage /> },
      { path: '/notifications', element: <NotificationsPage /> },
      { path: '/assistant', element: <AssistantPage /> },
      { path: '/settings', element: <SettingsPage /> },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])

function App() {
  return <RouterProvider router={router} />
}

export default App
