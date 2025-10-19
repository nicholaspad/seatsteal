import { createClient } from '@supabase/supabase-js'
import { config } from './config'

if (!config.supabase.url) {
  throw new Error('VITE_SUPABASE_URL environment variable is required')
}

if (!config.supabase.anonKey) {
  throw new Error('VITE_SUPABASE_ANON_KEY environment variable is required')
}

export const supabase = createClient(
  config.supabase.url,
  config.supabase.anonKey
)
