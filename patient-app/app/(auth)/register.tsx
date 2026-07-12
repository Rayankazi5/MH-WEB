import { Redirect } from 'expo-router'

// Registration is handled inside the login screen (tab toggle)
export default function Register() {
  return <Redirect href="/(auth)/login" />
}
